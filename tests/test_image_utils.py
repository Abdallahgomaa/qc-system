"""اختبارات ضغط الصور (البند 3.8).

تعمل بطريقتين:
- مع pytest:  ``pytest tests/test_image_utils.py``
- بلا تثبيت أي حزمة:  ``python tests/test_image_utils.py``
"""
from __future__ import annotations

import io
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import image_utils  # noqa: E402


def _noisy_png(width: int = 2400, height: int = 1800) -> bytes:
    """صورة عشوائية الضجيج (يصعب ضغطها) بحجم كبير نسبياً."""
    import random
    random.seed(7)
    img = Image.new("RGB", (width, height))
    px = img.load()
    for y in range(0, height, 3):
        for x in range(0, width, 3):
            c = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            px[x, y] = c
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_returns_webp_and_reduces_size():
    raw = _noisy_png()
    res = image_utils.compress_image(raw, max_kb=250, fmt="WEBP")
    assert res.data
    assert res.ext == ".webp"
    assert res.mime == "image/webp"
    assert res.final_kb <= res.original_kb


def test_large_image_scaled_to_max_side():
    raw = _noisy_png(3000, 2000)
    res = image_utils.compress_image(raw, max_kb=250, fmt="WEBP")
    out = Image.open(io.BytesIO(res.data))
    assert max(out.size) <= image_utils.MAX_SIDE


def test_keeps_min_side_resolution():
    raw = _noisy_png(1400, 1200)
    res = image_utils.compress_image(raw, max_kb=250, fmt="WEBP")
    out = Image.open(io.BytesIO(res.data))
    assert max(out.size) >= image_utils.MIN_SIDE


def test_jpeg_format_supported():
    raw = _noisy_png(1600, 1200)
    res = image_utils.compress_image(raw, max_kb=250, fmt="JPEG")
    assert res.ext == ".jpg"
    assert res.mime == "image/jpeg"


if __name__ == "__main__":
    tests = [fn for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:  # noqa: PERF203
            failures += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"--- {len(tests) - failures}/{len(tests)} passed ---")
    sys.exit(1 if failures else 0)
