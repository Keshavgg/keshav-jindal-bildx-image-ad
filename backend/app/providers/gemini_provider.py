import json
import logging
from typing import Optional
from PIL import Image
import httpx
from app.config import settings
from app.models.schemas import GenerationRequest, CreativeCopy
from app.prompts.copy_grounding import SYSTEM_INSTRUCTION, build_copy_generation_prompt
from app.providers.base import (
    BaseAIProvider,
    TemporaryProviderError,
    PermanentProviderError,
    ProviderTimeoutError,
)
from app.providers.fake_provider import FakeAIProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """
    Google Gemini provider utilizing Gemini models for grounded copy generation.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model = model or settings.GEMINI_MODEL
        self._fallback_synth = FakeAIProvider()

    @property
    def provider_name(self) -> str:
        return f"google-gemini-{self._model}"

    async def generate_ad_copy(self, request: GenerationRequest) -> CreativeCopy:
        if not self._api_key:
            raise PermanentProviderError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your environment or .env file."
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"
        user_prompt = build_copy_generation_prompt(
            product_name=request.product_name,
            product_description=request.product_description,
            target_audience=request.target_audience,
            key_benefits=request.key_benefits,
            tone=request.tone,
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_INSTRUCTION}\n\n{user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            }
        }

        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload)

            if response.status_code in (429, 500, 502, 503, 504):
                raise TemporaryProviderError(
                    f"Gemini service unavailable/rate limited: HTTP {response.status_code}"
                )
            elif response.status_code != 200:
                raise PermanentProviderError(
                    f"Gemini API returned client error: HTTP {response.status_code} - {response.text}"
                )

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise PermanentProviderError("Gemini returned empty candidates")

            text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            parsed = json.loads(text_content)

            return CreativeCopy(
                headline=parsed.get("headline", ""),
                supporting_text=parsed.get("supporting_text", ""),
                cta=parsed.get("cta", ""),
                visual_direction=parsed.get("visual_direction", f"Background tailored for {request.tone}"),
            )

        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"Gemini request timed out after {settings.PROVIDER_TIMEOUT_SECONDS}s: {exc}")
        except (TemporaryProviderError, PermanentProviderError):
            raise
        except json.JSONDecodeError as exc:
            raise PermanentProviderError(f"Failed to parse Gemini output as JSON: {exc}")
        except Exception as exc:
            raise PermanentProviderError(f"Gemini generation failed: {exc}")

    async def generate_background(
        self,
        visual_direction: str,
        tone: str,
        width: int = 1080,
        height: int = 1080
    ) -> Image.Image:
        # Use atmospheric studio synthesizer tuned to visual direction and tone
        return await self._fallback_synth.generate_background(visual_direction, tone, width, height)
