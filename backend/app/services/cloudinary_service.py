import cloudinary
import cloudinary.uploader

from app.core.config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET
)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)


def upload_image(image_bytes):

    result = cloudinary.uploader.upload(
        image_bytes,
        folder="ai-booth-generator"
    )

    return result["secure_url"]

def download_image(
    image_url,
    save_path
    ):

    response = requests.get(
        image_url
    )

    with open(
        save_path,
        "wb"
    ) as file:

        file.write(
            response.content
        )

    return save_path