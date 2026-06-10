import time
from io import BytesIO
from urllib.parse import quote

import httpx
from huggingface_hub import InferenceClient

from app.core.config import HUGGINGFACE_API_KEY, get_image_model
from app.services.cloudinary_service import upload_image

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

HF_PROVIDERS = ("auto", "hf-inference", "fal-ai", "together", "replicate", "nscale")
MAX_POLLINATIONS_RETRIES = 5
POLLINATIONS_RETRY_SECONDS = 15


def _booth_prompt(prompt: str) -> str:
    return (
        f"Photorealistic trade show exhibition booth, architectural visualization, "
        f"ultra realistic render. {prompt}"
    )


def _image_to_bytes(image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _generate_via_huggingface(booth_prompt: str) -> tuple[bytes, str]:
    if not HUGGINGFACE_API_KEY:
        raise RuntimeError(
            "HUGGINGFACE_API_KEY is not set. Add it to backend/.env"
        )

    last_error = None

    model = get_image_model()

    for provider in HF_PROVIDERS:
        try:
            client = InferenceClient(
                api_key=HUGGINGFACE_API_KEY,
                provider=provider,
            )
            image = client.text_to_image(
                booth_prompt,
                model=model,
            )
            return _image_to_bytes(image), f"huggingface-{provider}-{model}"
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            if "credit" in message or "402" in message:
                raise RuntimeError(
                    "Hugging Face free credits exhausted. "
                    "Wait for monthly reset or add credits at huggingface.co/settings/billing."
                ) from exc

    raise RuntimeError(f"Hugging Face image generation failed: {last_error}")


def _pollinations_url(prompt: str) -> str:
    # Pollinations URLs get long; keep the most descriptive tail of the prompt.
    normalized = " ".join(prompt.split())
    if len(normalized) > 800:
        normalized = normalized[:800]

    encoded_prompt = quote(normalized)
    return (
        f"{POLLINATIONS_BASE}/{encoded_prompt}"
        "?width=1024&height=1024&model=flux"
    )


def _is_rate_limited(error_text: str) -> bool:
    lowered = error_text.lower()
    return (
        "queue full" in lowered
        or "rate limit" in lowered
        or "too many requests" in lowered
        or "x402" in lowered
    )


def _generate_via_pollinations(booth_prompt: str) -> bytes:
    last_error = None

    for attempt in range(1, MAX_POLLINATIONS_RETRIES + 1):
        try:
            response = httpx.get(
                _pollinations_url(booth_prompt),
                timeout=120.0,
            )

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
            if _is_rate_limited(str(exc)) and attempt < MAX_POLLINATIONS_RETRIES:
                time.sleep(POLLINATIONS_RETRY_SECONDS * attempt)
                continue
            break

    raise RuntimeError(
        "Pollinations is busy (queue full). Please wait a minute and try again."
    ) from last_error


def generate_booth_image(prompt: str) -> dict:
    booth_prompt = _booth_prompt(prompt)

    try:
        image_bytes, provider = _generate_via_huggingface(booth_prompt)
    except Exception as hf_error:
        try:
            image_bytes = _generate_via_pollinations(booth_prompt)
            provider = "pollinations-flux"
        except Exception as poll_error:
            raise RuntimeError(
                f"Image generation failed. Hugging Face: {hf_error} | "
                f"Pollinations fallback: {poll_error}"
            ) from poll_error

    cloudinary_url = upload_image(image_bytes)

    return {
        "image_url": cloudinary_url,
        "provider": provider,
        "prompt_used": booth_prompt,
    }
