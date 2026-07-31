from __future__ import annotations

from functools import lru_cache

from app.core import config
from app.providers.base import (
    ImageGenerationProvider,
    LLMProvider,
    Model3DGenerationProvider,
    ProviderNotConfigured,
)
from app.providers.image.huggingface_provider import (
    HuggingFaceImageProvider,
    OpenAIImageProvider,
    RiverflowImageProvider,
)
from app.providers.llm.gemma_provider import ClaudeProvider, GemmaProvider
from app.providers.model3d.huggingface_3d_provider import (
    HuggingFace3DProvider,
    StubGLBProvider,
)
from app.providers.model3d.tripo_provider import TripoProvider


def get_llm_provider() -> LLMProvider:
    name = (config.LLM_PROVIDER or "gemma").strip().lower()
    if name in {"gemma", "openrouter"}:
        return GemmaProvider()
    if name == "claude":
        return ClaudeProvider()
    raise ProviderNotConfigured(f"Unknown LLM_PROVIDER={name}")


def get_image_provider() -> ImageGenerationProvider:
    name = (config.IMAGE_PROVIDER or "huggingface").strip().lower()
    if name in {"huggingface", "hf", "flux"}:
        return HuggingFaceImageProvider()
    if name in {"riverflow", "sourceful"}:
        return RiverflowImageProvider()
    if name in {"openai", "dalle", "dall-e"}:
        return OpenAIImageProvider()
    raise ProviderNotConfigured(f"Unknown IMAGE_PROVIDER={name}")


def get_model3d_provider() -> Model3DGenerationProvider:
    name = (config.MODEL_3D_PROVIDER or "huggingface_3d").strip().lower()
    if name in {"huggingface_3d", "opensource", "hf_3d"}:
        return HuggingFace3DProvider()
    if name in {"stub", "stub_glb", "demo"}:
        return StubGLBProvider()
    if name == "tripo":
        return TripoProvider()
    raise ProviderNotConfigured(f"Unknown MODEL_3D_PROVIDER={name}")


@lru_cache(maxsize=1)
def provider_summary() -> dict[str, str]:
    return {
        "llm": config.LLM_PROVIDER,
        "image": config.IMAGE_PROVIDER,
        "model3d": config.MODEL_3D_PROVIDER,
    }
