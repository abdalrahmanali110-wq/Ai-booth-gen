from __future__ import annotations

import struct

import httpx

from app.core.config import HUGGINGFACE_API_KEY, MODEL_3D_HF_ENDPOINT
from app.providers.base import (
    Model3DGenerationProvider,
    Model3DResult,
)


def _minimal_glb_bytes() -> bytes:
    """Tiny valid-ish GLB-like container for demo fallback (triangle placeholder).

    Not a production mesh — used so the 3D workflow/viewer path can be demonstrated
    when an external image-to-3D endpoint is unavailable.
    """
    # Minimal glTF JSON pointing to no external buffers; some viewers may reject it.
    # Prefer a slightly larger generated binary glTF with one triangle.
    gltf_json = (
        b'{"asset":{"version":"2.0"},"scenes":[{"nodes":[0]}],"scene":0,'
        b'"nodes":[{"mesh":0}],"meshes":[{"primitives":[{"attributes":{"POSITION":0},"indices":1}]}],'
        b'"accessors":['
        b'{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3","max":[1,1,0],"min":[-1,-1,0]},'
        b'{"bufferView":1,"componentType":5123,"count":3,"type":"SCALAR"}],'
        b'"bufferViews":['
        b'{"buffer":0,"byteOffset":0,"byteLength":36},'
        b'{"buffer":0,"byteOffset":36,"byteLength":6}],'
        b'"buffers":[{"byteLength":44}]}'
    )
    # pad JSON to 4-byte boundary
    json_padding = (4 - (len(gltf_json) % 4)) % 4
    gltf_json += b" " * json_padding

    # 3 vertices (float32 xyz) + 3 indices (uint16) + pad
    positions = struct.pack("<9f", -1.0, -1.0, 0.0, 1.0, -1.0, 0.0, 0.0, 1.0, 0.0)
    indices = struct.pack("<3H", 0, 1, 2)
    bin_chunk = positions + indices
    bin_padding = (4 - (len(bin_chunk) % 4)) % 4
    bin_chunk += b"\x00" * bin_padding

    json_chunk = struct.pack("<I", len(gltf_json)) + b"JSON" + gltf_json
    bin_header = struct.pack("<I", len(bin_chunk)) + b"BIN\x00"
    total_length = 12 + len(json_chunk) + 8 + len(bin_chunk)
    header = struct.pack("<4sII", b"glTF", 2, total_length)
    return header + json_chunk + bin_header + bin_chunk


class StubGLBProvider(Model3DGenerationProvider):
    name = "stub_glb"

    def generate_from_image(self, image_url: str, *, prompt: str | None = None) -> Model3DResult:
        return Model3DResult(
            model_bytes=_minimal_glb_bytes(),
            provider=self.name,
            metadata={"source_image": image_url, "demo": True, "prompt": prompt},
        )


class HuggingFace3DProvider(Model3DGenerationProvider):
    """Best-effort open-source image-to-3D via a configurable HF endpoint.

    Falls back to StubGLBProvider when the endpoint is missing or fails.
    """

    name = "huggingface_3d"

    def __init__(self, endpoint: str | None = None):
        self.endpoint = (endpoint or MODEL_3D_HF_ENDPOINT or "").strip()
        self._fallback = StubGLBProvider()

    def generate_from_image(self, image_url: str, *, prompt: str | None = None) -> Model3DResult:
        if not self.endpoint or not HUGGINGFACE_API_KEY:
            return self._fallback.generate_from_image(image_url, prompt=prompt)

        try:
            response = httpx.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"},
                json={"inputs": image_url, "parameters": {"prompt": prompt or ""}},
                timeout=180.0,
            )
            if response.status_code != 200:
                return self._fallback.generate_from_image(image_url, prompt=prompt)

            content_type = response.headers.get("content-type", "")
            if "gltf" in content_type or "octet-stream" in content_type or response.content[:4] == b"glTF":
                return Model3DResult(
                    model_bytes=response.content,
                    provider=self.name,
                    metadata={"source_image": image_url},
                )
            # Some endpoints return a URL to the asset
            data = response.json() if "json" in content_type else None
            if isinstance(data, dict):
                model_url = data.get("model_url") or data.get("url")
                if model_url:
                    dl = httpx.get(model_url, timeout=120.0)
                    if dl.status_code == 200:
                        return Model3DResult(
                            model_bytes=dl.content,
                            provider=self.name,
                            metadata={"source_image": image_url, "remote_url": model_url},
                        )
        except Exception:
            pass

        return self._fallback.generate_from_image(image_url, prompt=prompt)
