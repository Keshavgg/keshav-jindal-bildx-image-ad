import io
import ipaddress
import logging
import socket
from urllib.parse import urlparse
from PIL import Image
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class ImageDownloadError(Exception):
    """Base exception for image retrieval issues."""
    pass


class ImageSecurityError(ImageDownloadError):
    """Raised when an image URL violates SSRF safety constraints."""
    pass


class ImageSizeError(ImageDownloadError):
    """Raised when an image exceeds the maximum permitted size."""
    pass


class InvalidImageError(ImageDownloadError):
    """Raised when the content cannot be decoded as an image."""
    pass


def validate_url_safety(url_str: str) -> None:
    """
    Validates scheme and prevents Server-Side Request Forgery (SSRF)
    by blocking requests to private, loopback, link-local, or cloud metadata IPs.
    """
    parsed = urlparse(url_str)
    if parsed.scheme not in ("http", "https"):
        raise ImageSecurityError(f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise ImageSecurityError("Invalid URL: Hostname is missing.")

    # Prevent loopback strings like 'localhost'
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "metadata.google.internal"):
        raise ImageSecurityError("Requests to localhost and internal hostnames are prohibited.")

    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ImageDownloadError(f"Failed to resolve host '{hostname}': {exc}")

    for item in addr_info:
        ip_str = item[4][0]
        ip = ipaddress.ip_address(ip_str)

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or str(ip) == "169.254.169.254"  # Cloud metadata IP
        ):
            raise ImageSecurityError(
                f"Security violation: Host '{hostname}' resolves to restricted internal IP {ip_str}."
            )


async def download_and_validate_image(url_str: str) -> Image.Image:
    """
    Safely downloads a remote image with SSRF checks, size capping, and format verification.
    """
    validate_url_safety(url_str)

    max_bytes = settings.IMAGE_DOWNLOAD_MAX_BYTES
    timeout_sec = settings.IMAGE_DOWNLOAD_TIMEOUT_SECONDS

    try:
        async with httpx.AsyncClient(
            timeout=timeout_sec,
            follow_redirects=True,
            headers={"User-Agent": "Bildx-Image-Ad-Bot/1.0"}
        ) as client:
            async with client.stream("GET", url_str) as response:
                if response.status_code == 404:
                    raise ImageDownloadError(f"Image not found (HTTP 404) at '{url_str}'")
                elif response.status_code != 200:
                    raise ImageDownloadError(f"Remote server returned HTTP {response.status_code} for image URL")

                # Validate Content-Length if present
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_bytes:
                    raise ImageSizeError(
                        f"Image size {content_length} bytes exceeds {max_bytes} bytes limit (10MB)"
                    )

                # Validate Content-Type
                content_type = response.headers.get("content-type", "").lower()
                if content_type and not (
                    content_type.startswith("image/")
                    or "application/octet-stream" in content_type
                ):
                    raise InvalidImageError(
                        f"Remote URL returned non-image Content-Type '{content_type}'"
                    )

                chunks = []
                total_downloaded = 0

                async for chunk in response.aiter_bytes():
                    total_downloaded += len(chunk)
                    if total_downloaded > max_bytes:
                        raise ImageSizeError(
                            f"Image download exceeded maximum size limit of {max_bytes} bytes (10MB)"
                        )
                    chunks.append(chunk)

                raw_bytes = b"".join(chunks)

    except httpx.TimeoutException as exc:
        raise ImageDownloadError(f"Connection timed out while downloading image: {exc}")
    except (ImageSecurityError, ImageSizeError, InvalidImageError, ImageDownloadError):
        raise
    except Exception as exc:
        raise ImageDownloadError(f"Unexpected network error downloading image: {exc}")

    # Verify and decode with Pillow
    try:
        buffer = io.BytesIO(raw_bytes)
        image = Image.open(buffer)
        image.load()  # Force decode to catch truncated or corrupted image data

        # Ensure image is in RGBA or RGB
        if image.mode in ("RGBA", "P"):
            return image.convert("RGBA")
        return image.convert("RGB")

    except Exception as exc:
        raise InvalidImageError(f"File at URL is not a valid or supported image: {exc}")
