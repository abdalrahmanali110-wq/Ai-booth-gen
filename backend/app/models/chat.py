from pydantic import BaseModel

DEFAULT_SESSION_TITLE = "New Booth Consultation"


class CreateSessionRequest(BaseModel):
    title: str = DEFAULT_SESSION_TITLE


class UpdateSessionRequest(BaseModel):
    title: str


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str
