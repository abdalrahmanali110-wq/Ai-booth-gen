from pydantic import BaseModel, Field

DEFAULT_SESSION_TITLE = "New Booth Consultation"


class CreateSessionRequest(BaseModel):
    title: str = DEFAULT_SESSION_TITLE


class UpdateSessionRequest(BaseModel):
    title: str


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


class UpdateRequirementsRequest(BaseModel):
    requirements: dict = Field(default_factory=dict)
