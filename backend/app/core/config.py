import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=True)

DEFAULT_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv(
    "GEMMA_API_KEY"
)

GEMMA_API_KEY = OPENROUTER_API_KEY
GEMMA_MODEL = os.getenv(
    "GEMMA_MODEL",
    "google/gemma-4-31b-it:free",
)

def _resolve_image_model() -> str:
    raw = (os.getenv("IMAGE_MODEL") or DEFAULT_IMAGE_MODEL).strip()
    lowered = raw.lower()
    if any(
        marker in lowered
        for marker in ("riverflow", "sourceful", ":free", "openrouter")
    ):
        return DEFAULT_IMAGE_MODEL
    return raw


def get_image_model() -> str:
    return _resolve_image_model()


IMAGE_MODEL = get_image_model()

DEFAULT_USER_ID = os.getenv(
    "DEFAULT_USER_ID",
    "032f3894-2957-428b-8342-cfff63c9da47",
)

_site = os.getenv("SITE_URL") or os.getenv("VERCEL_URL") or "http://localhost:5173"
SITE_URL = _site if _site.startswith("http") else f"https://{_site}"
