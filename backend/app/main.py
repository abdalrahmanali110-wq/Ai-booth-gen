from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import SITE_URL
from app.api.chat import router as chat_router
from app.api.questionnaire import router as questionnaire_router

app = FastAPI(
    title="AI Booth Generator API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"https://([a-z0-9-]+\.)*vercel\.app"
        r"|http://(localhost|127\.0\.0\.1):\d+"
    ),
    allow_origins=[SITE_URL] if SITE_URL else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    chat_router,
    prefix="/chat",
    tags=["Chat"],
)

app.include_router(
    questionnaire_router,
    prefix="/design",
    tags=["Design Questionnaire"],
)


@app.get("/")
def root():
    return {"message": "AI Booth Generator API Running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
