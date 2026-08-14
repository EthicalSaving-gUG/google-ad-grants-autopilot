#!/usr/bin/env python3
"""Validate basic Google Search image-asset file constraints.

This checks deterministic file properties only. It cannot prove that an image has
no text/logo overlay or that Google will approve the asset.
"""
from __future__ import annotations

import argparse
import pathlib
import struct
import sys

MAX_BYTES = 5_120 * 1024


def png_size(path: pathlib.Path) -> tuple[int, int]:
    with path.open("rb") as f:
        sig = f.read(24)
    if len(sig) < 24 or sig[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("invalid PNG")
    return struct.unpack(">II", sig[16:24])


def jpeg_size(path: pathlib.Path) -> tuple[int, int]:
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("invalid JPEG")
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        i += 2
        if marker in {0xD8, 0xD9}:
            continue
        if i + 2 > len(data):
            break
        length = int.from_bytes(data[i:i+2], "big")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if i + 7 >= len(data):
                break
            height = int.from_bytes(data[i+3:i+5], "big")
            width = int.from_bytes(data[i+5:i+7], "big")
            return width, height
        i += max(length, 2)
    raise ValueError("could not locate JPEG dimensions")


def dimensions(path: pathlib.Path) -> tuple[int, int]:
    ext = path.suffix.lower()
    if ext == ".png":
        return png_size(path)
    if ext in {".jpg", ".jpeg"}:
        return jpeg_size(path)
    raise ValueError("only PNG/JPG are supported")


def classify(width: int, height: int) -> str | None:
    ratio = width / height
    if abs(ratio - 1.0) <= 0.03:
        return "square"
    if abs(ratio - 1.91) <= 0.04:
        return "landscape"
    return None


def validate(path: pathlib.Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return ["file does not exist"]
    if path.stat().st_size > MAX_BYTES:
        errors.append(f"file exceeds 5120 KB: {path.stat().st_size} bytes")
    try:
        w, h = dimensions(path)
    except Exception as exc:
        return errors + [str(exc)]
    kind = classify(w, h)
    if kind is None:
        errors.append(f"unsupported aspect ratio {w}x{h}; expected about 1:1 or 1.91:1")
    elif kind == "square" and (w < 300 or h < 300):
        errors.append(f"square image below 300x300 minimum: {w}x{h}")
    elif kind == "landscape" and (w < 600 or h < 314):
        errors.append(f"landscape image below 600x314 minimum: {w}x{h}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    args = ap.parse_args()
    failed = False
    for raw in args.images:
        path = pathlib.Path(raw)
        errors = validate(path)
        if errors:
            failed = True
            for e in errors:
                print(f"ERROR {path}: {e}")
        else:
            w, h = dimensions(path)
            print(f"OK {path}: {w}x{h}, {path.stat().st_size} bytes")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
