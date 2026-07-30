from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderNotConfigured(RuntimeError):
    """Raised when a future/stub provider is selected without credentials."""


@dataclass
class ChatResult:
    content: str
    raw: dict[str, Any] = field(default_factory=dict)
    reasoning_details: Any = None


@dataclass
class ImageResult:
    image_bytes: bytes
    provider: str
    prompt_used: str
    mime_type: str = "image/jpeg"


@dataclass
class Model3DResult:
    model_bytes: bytes
    provider: str
    format: str = "glb"
    mime_type: str = "model/gltf-binary"
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> ChatResult:
        raise NotImplementedError


class ImageGenerationProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, prompt: str) -> ImageResult:
        raise NotImplementedError


class Model3DGenerationProvider(ABC):
    name: str

    @abstractmethod
    def generate_from_image(self, image_url: str, *, prompt: str | None = None) -> Model3DResult:
        raise NotImplementedError
