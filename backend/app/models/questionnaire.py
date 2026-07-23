from typing import Any

from pydantic import BaseModel, Field


class AnswerValue(BaseModel):
    value: str | list[str] | None = None
    other_text: str | None = None


class CreateDesignSessionRequest(BaseModel):
    title: str = "Booth Design"


class SaveAnswersRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)


class LeadCaptureRequest(BaseModel):
    name: str
    email: str
    phone: str | None = None
