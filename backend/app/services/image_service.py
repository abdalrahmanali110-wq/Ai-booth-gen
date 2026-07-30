"""Image generation facade — delegates to the configured ImageGenerationProvider."""

from app.providers.registry import get_image_provider
from app.services.cloudinary_service import upload_image


def generate_booth_image(prompt: str) -> dict:
    provider = get_image_provider()
    result = provider.generate(prompt)
    cloudinary_url = upload_image(result.image_bytes)

    return {
        "image_url": cloudinary_url,
        "provider": result.provider,
        "prompt_used": result.prompt_used,
    }
