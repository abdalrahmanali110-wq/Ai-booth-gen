import struct
from pathlib import Path

gltf_json = bytearray(
    b'{"asset":{"version":"2.0"},"scenes":[{"nodes":[0]}],"scene":0,'
    b'"nodes":[{"mesh":0}],"meshes":[{"primitives":[{"attributes":{"POSITION":0},"indices":1}]}],'
    b'"accessors":['
    b'{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3","max":[1.0,1.0,0.0],"min":[-1.0,-1.0,0.0]},'
    b'{"bufferView":1,"componentType":5123,"count":3,"type":"SCALAR"}],'
    b'"bufferViews":['
    b'{"buffer":0,"byteOffset":0,"byteLength":36,"target":34962},'
    b'{"buffer":0,"byteOffset":36,"byteLength":6,"target":34963}],'
    b'"buffers":[{"byteLength":44}]}'
)
pad = (4 - (len(gltf_json) % 4)) % 4
gltf_json.extend(b" " * pad)

positions = struct.pack("<9f", -1.0, -1.0, 0.0, 1.0, -1.0, 0.0, 0.0, 1.0, 0.0)
indices = struct.pack("<3H", 0, 1, 2)
bin_chunk = bytearray(positions + indices)
bin_pad = (4 - (len(bin_chunk) % 4)) % 4
bin_chunk.extend(b"\x00" * bin_pad)

json_chunk = struct.pack("<I", len(gltf_json)) + b"JSON" + bytes(gltf_json)
bin_part = struct.pack("<I", len(bin_chunk)) + b"BIN\x00" + bytes(bin_chunk)
total = 12 + len(json_chunk) + len(bin_part)
header = struct.pack("<4sII", b"glTF", 2, total)
data = header + json_chunk + bin_part

out = Path(__file__).resolve().parents[1] / "frontend" / "public" / "demo-booth.glb"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(data)
print(f"wrote {out} ({len(data)} bytes)")
