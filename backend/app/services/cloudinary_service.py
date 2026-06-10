import cloudinary
import cloudinary.uploader

from app.core.config import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)


def upload_image(image_bytes: bytes) -> str:
    result = cloudinary.uploader.upload(
        image_bytes,
        folder="ai-booth-generator",
    )
    return result["secure_url"]
