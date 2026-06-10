from pydantic import BaseModel


class BoothRequestCreate(BaseModel):
    industry: str
    booth_theme: str
    booth_size: str
    colors: str
    prompt: str


class BoothRequestResponse(BaseModel):
    id: str
    industry: str
    booth_theme: str
    booth_size: str
    colors: str
    prompt: str
    status: str