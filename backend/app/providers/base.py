from abc import ABC, abstractmethod
from PIL import Image
from app.models.schemas import GenerationRequest, CreativeCopy


class ProviderError(Exception):
    """Base exception for all AI provider failures."""
    pass


class TemporaryProviderError(ProviderError):
    """
    Transient failure (e.g. HTTP 429, 503, connection dropped, socket reset).
    Eligible for exponential backoff retry.
    """
    pass


class PermanentProviderError(ProviderError):
    """
    Permanent failure (e.g. invalid credentials, unparseable output, malformed request).
    Should fail-fast and NEVER be retried.
    """
    pass


class ProviderTimeoutError(TemporaryProviderError):
    """Call to AI provider exceeded configured timeout."""
    pass


class BaseAIProvider(ABC):
    """
    Replaceable AI provider interface.
    Decouples business logic from external LLM/Vision APIs.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider for metrics and audit metadata."""
        pass

    @abstractmethod
    async def generate_ad_copy(self, request: GenerationRequest) -> CreativeCopy:
        """
        Generates grounded headline, supporting text, CTA, and visual direction.
        Raises TemporaryProviderError or PermanentProviderError.
        """
        pass

    @abstractmethod
    async def generate_background(
        self,
        visual_direction: str,
        tone: str,
        width: int = 1080,
        height: int = 1080
    ) -> Image.Image:
        """
        Produces or synthesizes a background canvas matching the visual direction.
        """
        pass
