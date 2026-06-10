import os
import sys

# Make backend package importable on Vercel
BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from mangum import Mangum  # noqa: E402

from app.main import app  # noqa: E402

handler = Mangum(app, lifespan="off")
