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


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI provider utilizing GPT models (e.g. gpt-4o-mini, gpt-4o).
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.OPENAI_MODEL
        self._fallback_synth = FakeAIProvider()

    @property
    def provider_name(self) -> str:
        return f"openai-{self._model}"

    async def generate_ad_copy(self, request: GenerationRequest) -> CreativeCopy:
        if not self._api_key:
            raise PermanentProviderError(
                "OpenAI API key is not configured. Please set OPENAI_API_KEY in your environment or .env file."
            )

        url = "https://api.openai.com/v1/chat/completions"
        user_prompt = build_copy_generation_prompt(
            product_name=request.product_name,
            product_description=request.product_description,
            target_audience=request.target_audience,
            key_benefits=request.key_benefits,
            tone=request.tone,
        )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                response = await client.post(url, headers=headers, json=payload)

            if response.status_code in (429, 500, 502, 503, 504):
                raise TemporaryProviderError(
                    f"OpenAI service unavailable or rate limited: HTTP {response.status_code}"
                )
            elif response.status_code != 200:
                raise PermanentProviderError(
                    f"OpenAI API error: HTTP {response.status_code} - {response.text}"
                )

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            return CreativeCopy(
                headline=parsed.get("headline", ""),
                supporting_text=parsed.get("supporting_text", ""),
                cta=parsed.get("cta", ""),
                visual_direction=parsed.get("visual_direction", f"Background tailored for {request.tone}"),
            )

        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"OpenAI request timed out after {settings.PROVIDER_TIMEOUT_SECONDS}s: {exc}")
        except (TemporaryProviderError, PermanentProviderError):
            raise
        except json.JSONDecodeError as exc:
            raise PermanentProviderError(f"Failed to parse OpenAI output as JSON: {exc}")
        except Exception as exc:
            raise PermanentProviderError(f"OpenAI generation failed: {exc}")

    async def generate_background(
        self,
        visual_direction: str,
        tone: str,
        width: int = 1080,
        height: int = 1080
    ) -> Image.Image:
        return await self._fallback_synth.generate_background(visual_direction, tone, width, height)
