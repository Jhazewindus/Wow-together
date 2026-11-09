#!/usr/bin/env python3
"""Render authored step-icon SVGs to deterministic, straight-alpha TGAs."""
from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import struct
import sys

import cairosvg
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "art" / "icons"
DESTINATION = ROOT / "WowTogether" / "Media" / "Icons"
SIZE = 64
NAMES = (
    "kill", "collect", "use", "talk", "accept", "turnin", "turnin-pending",
    "travel", "fly", "hearth", "teleport", "ship", "party", "wait", "farm",
    "dungeon", "pause", "menu", "close", "scan",
)


def render_tga(svg_path: Path) -> bytes:
    png = cairosvg.svg2png(url=str(svg_path), output_width=SIZE, output_height=SIZE)
    image = Image.open(BytesIO(png)).convert("RGBA")
    if image.size != (SIZE, SIZE):
        raise ValueError(f"Unexpected render size for {svg_path.name}: {image.size}")
    header = bytearray(18)
    header[2] = 2  # Uncompressed true-color image.
    header[12:14] = struct.pack("<H", SIZE)
    header[14:16] = struct.pack("<H", SIZE)
    header[16] = 32
    header[17] = 0x28  # 8 alpha bits, top-left origin.
    pixels = bytearray(image.tobytes("raw", "BGRA"))
    # Cairo's intermediate may contain color fringes on low-coverage pixels.
    # These monochrome icons use alpha only for edge coverage, so normalize all
    # visible RGB to the source color and keep fully transparent RGB at zero.
    for offset in range(0, len(pixels), 4):
        if pixels[offset + 3]:
            pixels[offset:offset + 3] = bytes((211, 226, 232))
        else:
            pixels[offset:offset + 3] = b"\0\0\0"
    return bytes(header) + pixels


def expected_files() -> dict[str, bytes]:
    actual = {path.stem for path in SOURCE.glob("*.svg")}
    if actual != set(NAMES):
        missing, extra = sorted(set(NAMES) - actual), sorted(actual - set(NAMES))
        raise ValueError(f"SVG set mismatch; missing={missing}, extra={extra}")
    return {name + ".tga": render_tga(SOURCE / (name + ".svg")) for name in NAMES}


def manifest_for(files: dict[str, bytes]) -> bytes:
    entries = [{"file": name, "sha256": hashlib.sha256(body).hexdigest()}
        for name, body in sorted(files.items())]
    payload = {"schema": 1, "size": SIZE, "format": "TGA 32-bit RGBA, uncompressed, straight alpha", "icons": entries}
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def build(check: bool = False) -> bool:
    files = expected_files()
    outputs = {**files, "manifest.json": manifest_for(files)}
    mismatches = []
    for name, expected in outputs.items():
        path = DESTINATION / name
        if check:
            if not path.is_file() or path.read_bytes() != expected:
                mismatches.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    if mismatches:
        print("Generated icon outputs differ: " + ", ".join(mismatches), file=sys.stderr)
        return False
    print(f"{'Verified' if check else 'Built'} {len(files)} step icons ({SIZE}x{SIZE} TGA).")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if committed outputs differ from SVG renders")
    args = parser.parse_args()
    return 0 if build(args.check) else 1


if __name__ == "__main__":
    raise SystemExit(main())
