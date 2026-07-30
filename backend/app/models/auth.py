from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    name: str | None = None
    phone: str | None = None
    company: str | None = None
    session_id: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str
    session_id: str | None = None


class OAuthCompleteRequest(BaseModel):
    access_token: str
    session_id: str | None = None
    name: str | None = None
    phone: str | None = None
    company: str | None = None


class ClaimSessionRequest(BaseModel):
    auth_user_id: str
    email: str | None = None
    name: str | None = None
    phone: str | None = None
    company: str | None = None


class CreateModel3DRequest(BaseModel):
    source_image_url: str
    source_image_id: str | None = None
    prompt: str | None = None
    auth_user_id: str
    process_now: bool = True
