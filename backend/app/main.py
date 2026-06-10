from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router

app = FastAPI(
    title="AI Booth Generator API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    chat_router,
    prefix="/chat",
    tags=["Chat"],
)


@app.get("/")
def root():
    return {"message": "AI Booth Generator API Running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
