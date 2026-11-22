from .base import (
    BaseAIProvider,
    ProviderError,
    TemporaryProviderError,
    PermanentProviderError,
    ProviderTimeoutError,
)
from .fake_provider import FakeAIProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


def get_provider(provider_type: str = "fake") -> BaseAIProvider:
    """Factory helper to obtain configured AI provider."""
    ptype = provider_type.lower()
    if ptype == "gemini":
        return GeminiProvider()
    elif ptype == "openai":
        return OpenAIProvider()
    elif ptype == "fake":
        return FakeAIProvider()
    else:
        raise ValueError(f"Unsupported AI provider '{provider_type}'. Must be 'fake', 'gemini', or 'openai'.")


__all__ = [
    "BaseAIProvider",
    "ProviderError",
    "TemporaryProviderError",
    "PermanentProviderError",
    "ProviderTimeoutError",
    "FakeAIProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "get_provider",
]
