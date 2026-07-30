from __future__ import annotations

import base64
import re
import time
from io import BytesIO
from urllib.parse import quote

import httpx
from huggingface_hub import InferenceClient

from app.core.config import (
    HUGGINGFACE_API_KEY,
    IMAGE_MODEL,
    OPENROUTER_API_KEY,
    SITE_URL,
    get_image_model,
)
from app.providers.base import ImageGenerationProvider, ImageResult, ProviderNotConfigured

HF_PROVIDERS = ("auto", "hf-inference", "fal-ai", "together", "replicate", "nscale")
POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"
MAX_POLLINATIONS_RETRIES = 5
POLLINATIONS_RETRY_SECONDS = 15


def _booth_prompt(prompt: str) -> str:
    return (
        "Photorealistic trade show exhibition booth, architectural visualization, "
        f"ultra realistic render. {prompt}"
    )


def _image_to_bytes(image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


class HuggingFaceImageProvider(ImageGenerationProvider):
    name = "huggingface"

    def generate(self, prompt: str) -> ImageResult:
        booth_prompt = _booth_prompt(prompt)

        if HUGGINGFACE_API_KEY:
            last_error = None
            model = get_image_model()
            for provider in HF_PROVIDERS:
                try:
                    client = InferenceClient(
                        api_key=HUGGINGFACE_API_KEY,
                        provider=provider,
                    )
                    image = client.text_to_image(booth_prompt, model=model)
                    return ImageResult(
                        image_bytes=_image_to_bytes(image),
                        provider=f"huggingface-{provider}-{model}",
                        prompt_used=booth_prompt,
                    )
                except Exception as exc:
                    last_error = exc
                    message = str(exc).lower()
                    if "credit" in message or "402" in message:
                        break

            # Fall through to Pollinations
            _ = last_error

        image_bytes = self._pollinations(booth_prompt)
        return ImageResult(
            image_bytes=image_bytes,
            provider="pollinations-flux",
            prompt_used=booth_prompt,
        )

    def _pollinations(self, booth_prompt: str) -> bytes:
        last_error = None
        normalized = " ".join(booth_prompt.split())
        if len(normalized) > 800:
            normalized = normalized[:800]
        url = (
            f"{POLLINATIONS_BASE}/{quote(normalized)}"
            "?width=1024&height=1024&model=flux"
        )

        for attempt in range(1, MAX_POLLINATIONS_RETRIES + 1):
            try:
                response = httpx.get(url, timeout=120.0)
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Pollinations error ({response.status_code}): "
                        f"{response.text[:300]}"
                    )
                content_type = response.headers.get("content-type", "")
                if "image" not in content_type and len(response.content) < 1000:
                    raise RuntimeError("Pollinations returned non-image response")
                return response.content
            except Exception as exc:
                last_error = exc
                lowered = str(exc).lower()
                if any(
                    token in lowered
                    for token in ("queue full", "rate limit", "too many requests")
                ) and attempt < MAX_POLLINATIONS_RETRIES:
                    time.sleep(POLLINATIONS_RETRY_SECONDS * attempt)
                    continue
                break

        raise RuntimeError(
            "Image generation failed via Hugging Face and Pollinations."
        ) from last_error


class RiverflowImageProvider(ImageGenerationProvider):
    name = "riverflow"

    def __init__(self, model: str | None = None):
        self.model = model or IMAGE_MODEL or "sourceful/riverflow-v2.5-fast"
        if "riverflow" not in self.model.lower() and "sourceful" not in self.model.lower():
            self.model = "sourceful/riverflow-v2.5-fast"
        if not OPENROUTER_API_KEY:
            raise ProviderNotConfigured("OPENROUTER_API_KEY is not set for Riverflow")

    def generate(self, prompt: str) -> ImageResult:
        booth_prompt = _booth_prompt(prompt)
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": SITE_URL,
                "X-Title": "AI Booth Generator",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": booth_prompt}],
                "modalities": ["image"],
            },
            timeout=120.0,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Riverflow error ({response.status_code}): {response.text[:500]}"
            )

        message = response.json()["choices"][0]["message"]
        images = message.get("images") or []
        if not images:
            raise RuntimeError("Riverflow returned no image")

        image_url = images[0].get("image_url", {}).get("url") or ""
        if image_url.startswith("data:"):
            match = re.match(r"data:image/[^;]+;base64,(.+)", image_url, re.DOTALL)
            if not match:
                raise RuntimeError("Invalid Riverflow data URL")
            image_bytes = base64.b64decode(match.group(1))
        else:
            dl = httpx.get(image_url, timeout=90.0)
            if dl.status_code != 200:
                raise RuntimeError(f"Failed to download Riverflow image ({dl.status_code})")
            image_bytes = dl.content

        return ImageResult(
            image_bytes=image_bytes,
            provider=f"openrouter-{self.model}",
            prompt_used=booth_prompt,
        )


class OpenAIImageProvider(ImageGenerationProvider):
    name = "openai"

    def generate(self, prompt: str) -> ImageResult:
        raise ProviderNotConfigured(
            "OpenAIImageProvider is not configured yet. "
            "Set IMAGE_PROVIDER=huggingface or riverflow for development."
        )
