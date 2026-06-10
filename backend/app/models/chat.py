from typing import Any

from pydantic import BaseModel


DEFAULT_SESSION_TITLE = "New Booth Consultation"


class CreateSessionRequest(BaseModel):
    title: str = DEFAULT_SESSION_TITLE


class UpdateSessionRequest(BaseModel):
    title: str


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    success: bool = True
    reply: str
    requirements: dict[str, Any]
    requirements_complete: bool
    generation_result: dict[str, Any] | None = None
