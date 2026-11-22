import asyncio
import math
from typing import Optional
from PIL import Image, ImageDraw
from app.models.schemas import GenerationRequest, CreativeCopy
from app.providers.base import (
    BaseAIProvider,
    TemporaryProviderError,
    PermanentProviderError,
    ProviderTimeoutError,
)


class FakeAIProvider(BaseAIProvider):
    """
    Mock AI Provider designed for automated testing and concurrent load demos.
    Produces zero paid API costs while providing deterministic, grounded outputs,
    configurable latency, and controllable failure injection.
    """

    def __init__(
        self,
        simulated_delay_seconds: float = 0.1,
        failure_mode: Optional[str] = None,  # None, "temporary", "permanent", "timeout"
        fail_times: int = 1,
    ):
        self._delay = simulated_delay_seconds
        self._failure_mode = failure_mode
        self._fail_times = fail_times
        self._call_count = 0

    @property
    def provider_name(self) -> str:
        return "fake-provider-v1"

    def set_failure_mode(self, mode: Optional[str], fail_times: int = 1):
        self._failure_mode = mode
        self._fail_times = fail_times
        self._call_count = 0

    async def generate_ad_copy(self, request: GenerationRequest) -> CreativeCopy:
        self._call_count += 1

        if self._failure_mode == "permanent":
            await asyncio.sleep(self._delay)
            raise PermanentProviderError(
                "Simulated permanent provider error: Invalid account credentials or schema mismatch"
            )

        if self._failure_mode == "timeout":
            # Sleep longer than standard timeout or raise timeout
            await asyncio.sleep(20.0)
            raise ProviderTimeoutError("Simulated provider timeout exceeded 15.0s")

        if self._failure_mode == "temporary" and self._call_count <= self._fail_times:
            await asyncio.sleep(self._delay)
            raise TemporaryProviderError(
                f"Simulated transient 503 Service Unavailable (attempt {self._call_count}/{self._fail_times})"
            )

        # Standard simulated processing time
        if self._delay > 0:
            await asyncio.sleep(self._delay)

        # Synthesize grounded copy strictly within limits using input facts
        first_benefit = request.key_benefits[0] if request.key_benefits else "Quality engineered"
        second_benefit = request.key_benefits[1] if len(request.key_benefits) > 1 else "Daily reliability"

        # Strictly <= 8 words headline
        if "lock" in request.product_name.lower() or "tumbler" in request.product_name.lower():
            headline = "Lock it. Loop it. Go."
        elif "audio" in request.tone.lower() or "sound" in request.product_name.lower():
            headline = "Pure Sound. Every Room."
        elif "glow" in request.product_name.lower() or "skin" in request.tone.lower():
            headline = "Radiance That Lasts All Day."
        else:
            words = f"Built for {request.product_name}. Ready always.".split()[:8]
            headline = " ".join(words)

        # Strictly <= 20 words supporting text
        supporting_text = (
            f"{first_benefit} and {second_benefit}. Designed for {request.target_audience.lower()}."
        )
        words = supporting_text.split()
        if len(words) > 20:
            supporting_text = " ".join(words[:20])

        # Strictly <= 4 words CTA
        cta_words = f"Explore {request.product_name.split()[0]}".split()[:4]
        cta = " ".join(cta_words)

        visual_direction = f"Premium aesthetic backdrop tailored for {request.tone.lower()} and {request.target_audience.lower()}."

        return CreativeCopy(
            headline=headline,
            supporting_text=supporting_text,
            cta=cta,
            visual_direction=visual_direction,
        )

    async def generate_background(
        self,
        visual_direction: str,
        tone: str,
        width: int = 1080,
        height: int = 1080
    ) -> Image.Image:
        """
        Creates an elegant, high-resolution procedural backdrop with lighting gradients
        tuned to the requested tone (outdoor adventurous, luxury, minimalist studio, dark modern).
        """
        if self._delay > 0:
            await asyncio.sleep(self._delay / 2)

        tone_lower = tone.lower()
        if "outdoor" in tone_lower or "adventurous" in tone_lower or "nature" in tone_lower:
            # Earthy forest/mountain gradient: deep slate blue to forest pine
            top_color = (24, 43, 40)
            bottom_color = (13, 20, 24)
            accent_color = (68, 114, 102)
        elif "luxury" in tone_lower or "warm" in tone_lower or "serum" in tone_lower:
            # Warm sand/rose gold studio ambiance
            top_color = (48, 38, 36)
            bottom_color = (25, 20, 20)
            accent_color = (140, 100, 80)
        elif "tech" in tone_lower or "audio" in tone_lower:
            # Sleek cyberpunk / dark navy studio
            top_color = (18, 24, 38)
            bottom_color = (8, 10, 18)
            accent_color = (45, 75, 120)
        else:
            # Modern editorial studio neutral charcoal
            top_color = (35, 39, 47)
            bottom_color = (18, 20, 26)
            accent_color = (70, 78, 92)

        # Render vertical gradient with soft radial glow
        img = Image.new("RGBA", (width, height), top_color + (255,))
        draw = ImageDraw.Draw(img)

        # Smooth linear vertical interpolation
        for y in range(height):
            t = y / float(height)
            r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
            g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
            b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

        # Soft radial spotlight in the center/upper-center
        center_x, center_y = width // 2, int(height * 0.45)
        max_radius = int(width * 0.55)
        spotlight = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(spotlight)

        steps = 40
        for i in range(steps, 0, -1):
            rad = int(max_radius * (i / steps))
            alpha = int(45 * (1 - (i / steps)))
            s_draw.ellipse(
                [
                    center_x - rad,
                    center_y - rad,
                    center_x + rad,
                    center_y + rad,
                ],
                fill=accent_color + (alpha,)
            )

        img = Image.alpha_composite(img, spotlight)
        return img.convert("RGB")
