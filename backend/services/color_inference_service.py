"""
Lightweight color inference for older wardrobe items without color metadata.

This is intentionally conservative: explicit metadata should be authoritative,
and image inference should only return a color when there is clear chromatic
evidence. Dark or low-saturation images are left unknown instead of being
treated as black.
"""

import base64
import io
import os
from colorsys import rgb_to_hsv
from typing import Any, Optional, Tuple

import httpx
from PIL import Image


MAX_IMAGE_BYTES = 5 * 1024 * 1024
TIMEOUT_SECONDS = 2.5
_COLOR_CACHE = {}


def infer_dominant_color(image_value: Any) -> Optional[str]:
    """Infer a coarse color name from an image URL, local path, or data URI."""
    image_ref = str(image_value or "").strip()
    if not image_ref:
        return None

    if image_ref in _COLOR_CACHE:
        return _COLOR_CACHE[image_ref]

    try:
        image_bytes = _read_image_bytes(image_ref)
        if not image_bytes:
            _COLOR_CACHE[image_ref] = None
            return None

        with Image.open(io.BytesIO(image_bytes)) as image:
            rgb = _dominant_rgb(image)
            color = _rgb_to_color_name(rgb) if rgb else None
            _COLOR_CACHE[image_ref] = color
            return color
    except Exception as exc:
        print(f"[ColorInference] Could not infer color for image: {exc}")
        _COLOR_CACHE[image_ref] = None
        return None


def _read_image_bytes(image_ref: str) -> Optional[bytes]:
    if image_ref.startswith("data:"):
        _, _, encoded = image_ref.partition(",")
        if not encoded:
            return None
        return base64.b64decode(encoded)[:MAX_IMAGE_BYTES]

    if image_ref.startswith("http://") or image_ref.startswith("https://"):
        with httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = client.get(image_ref)
            if response.status_code != 200:
                return None
            content_type = response.headers.get("content-type", "")
            if content_type and not content_type.startswith("image/"):
                return None
            if len(response.content) > MAX_IMAGE_BYTES:
                return None
            return response.content

    file_path = _find_local_image(image_ref)
    if not file_path:
        return None

    if os.path.getsize(file_path) > MAX_IMAGE_BYTES:
        return None

    with open(file_path, "rb") as file:
        return file.read()


def _find_local_image(path: str) -> Optional[str]:
    clean_path = path.lstrip("/")
    possible_paths = [
        path,
        clean_path,
        os.path.join(os.getcwd(), clean_path),
        os.path.join(os.getcwd(), "backend", clean_path),
        os.path.join(os.getcwd(), "uploads", clean_path),
    ]

    for candidate in possible_paths:
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return candidate

    return None


def _dominant_rgb(image: Image.Image) -> Optional[Tuple[int, int, int]]:
    image = image.convert("RGBA")
    image.thumbnail((96, 96))

    buckets = {}
    for red, green, blue, alpha in image.getdata():
        if alpha < 128:
            continue

        hue, saturation, value = rgb_to_hsv(red / 255, green / 255, blue / 255)

        # Ignore common white/light-gray product-photo backgrounds.
        if value > 0.78 and saturation < 0.25:
            continue

        # Low-saturation pixels are ambiguous in product photos. Do not turn
        # every dark image into "black"; require explicit metadata or name text.
        if saturation < 0.18:
            continue

        bucket = (red // 32, green // 32, blue // 32)
        buckets[bucket] = buckets.get(bucket, 0) + 1

    if not buckets:
        return None

    dominant_bucket = max(buckets, key=buckets.get)
    return tuple(min(channel * 32 + 16, 255) for channel in dominant_bucket)


def _rgb_to_color_name(rgb: Tuple[int, int, int]) -> str:
    red, green, blue = rgb
    hue, saturation, value = rgb_to_hsv(red / 255, green / 255, blue / 255)
    hue_degrees = hue * 360

    if value < 0.24:
        return "unknown"

    if saturation < 0.18:
        if value > 0.82:
            return "white"
        return "gray"

    if hue_degrees < 15 or hue_degrees >= 345:
        return "red"
    if hue_degrees < 40:
        return "orange"
    if hue_degrees < 70:
        return "yellow"
    if hue_degrees < 170:
        return "green"
    if hue_degrees < 255:
        return "blue"
    if hue_degrees < 295:
        return "purple"
    if hue_degrees < 345:
        return "pink"

    return "gray"
