import time
from urllib.parse import quote

import requests

from app.services.cloudinary_service import upload_image

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

FALLBACK_IMAGE_URL = (
    "https://picsum.photos/1024/1024"
)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def _normalize_prompt(prompt: str) -> str:
    return " ".join(prompt.split())


def _fetch_image(url: str) -> bytes:

    response = requests.get(
        url,
        timeout=90
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Image download failed "
            f"({response.status_code})"
        )

    content_type = response.headers.get(
        "Content-Type",
        ""
    )

    if (
        "image" not in content_type
        and len(response.content) < 1000
    ):
        raise RuntimeError(
            "Response is not an image"
        )

    return response.content


def _pollinations_url(prompt: str) -> str:

    encoded_prompt = quote(
        _normalize_prompt(prompt)
    )

    return (
        f"{POLLINATIONS_BASE}/"
        f"{encoded_prompt}"
        "?width=1024"
        "&height=1024"
        "&model=flux"
    )


def _is_rate_limited(error_text: str) -> bool:

    lowered = error_text.lower()

    return (
        "queue full" in lowered
        or "rate limit" in lowered
        or "too many requests" in lowered
        or "x402" in lowered
    )


def generate_booth_image(prompt: str):

    normalized_prompt = _normalize_prompt(
        prompt
    )

    last_error = None

    print("\n====================")
    print("AI PROMPT")
    print("====================")
    print(normalized_prompt)

    print("\n====================")
    print("POLLINATIONS URL")
    print("====================")
    print(
        _pollinations_url(
            normalized_prompt
        )
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            image_bytes = _fetch_image(
                _pollinations_url(
                    normalized_prompt
                )
            )

            cloudinary_url = upload_image(
                image_bytes
            )

            print(
                "SUCCESS -> Pollinations"
            )

            return {
                "image_url":
                    cloudinary_url,
                "provider":
                    "pollinations-ai"
            }

        except Exception as exc:

            last_error = exc

            print(
                f"Attempt {attempt} failed:"
            )
            print(str(exc))

            if (
                _is_rate_limited(str(exc))
                and attempt < MAX_RETRIES
            ):

                time.sleep(
                    RETRY_DELAY_SECONDS
                    * attempt
                )

                continue

            break

    print("\n====================")
    print("POLLINATIONS FAILED")
    print("====================")
    print(last_error)

    try:

        fallback_bytes = _fetch_image(
            FALLBACK_IMAGE_URL
        )

        cloudinary_url = upload_image(
            fallback_bytes
        )

        return {
            "image_url":
                cloudinary_url,
            "provider":
                "fallback-placeholder",
            "warning":
                (
                    "Pollinations failed. "
                    "Fallback image used."
                )
        }

    except Exception as fallback_error:

        raise RuntimeError(
            f"Pollinations Error: "
            f"{last_error} | "
            f"Fallback Error: "
            f"{fallback_error}"
        )