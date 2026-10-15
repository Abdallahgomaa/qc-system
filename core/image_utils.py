"""ضغط الصور تلقائياً قبل الرفع للسحابة.

الاستراتيجية:
1. تصحيح اتجاه الصورة (EXIF) وتحويلها إلى RGB.
2. تصغير الضلع الأطول إلى MAX_SIDE كحد أقصى.
3. حفظ بصيغة WebP بجودة تتناقص تدريجياً حتى يصل الحجم للهدف.
4. إن لم يكفِ خفض الجودة (حتى حد أدنى يحفظ وضوح الأرقام) تُصغَّر الأبعاد تدريجياً
   حتى حد أدنى للضلع الأطول MIN_SIDE، فلا تصبح الأرقام والكتابة غير مقروءة.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps

MAX_SIDE = 1800
MIN_SIDE = 1000       # لا نصغّر الصورة تحت هذا الحد حفاظاً على وضوح الكتابة
START_QUALITY = 85
MIN_QUALITY = 50


@dataclass
class CompressionResult:
    data: bytes
    ext: str
    mime: str
    original_kb: float
    final_kb: float
    within_target: bool


def _to_rgb(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return img.convert("RGB")


def _encode(img: Image.Image, fmt: str, quality: int) -> bytes:
    buf = io.BytesIO()
    if fmt == "WEBP":
        img.save(buf, "WEBP", quality=quality, method=6)
    else:
        img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def compress_image(raw: bytes, max_kb: int = 250, fmt: str = "WEBP") -> CompressionResult:
    fmt = fmt.upper()
    ext, mime = (".webp", "image/webp") if fmt == "WEBP" else (".jpg", "image/jpeg")
    target = max_kb * 1024

    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    img = _to_rgb(img)
    if max(img.size) > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

    quality = START_QUALITY
    data = _encode(img, fmt, quality)
    while len(data) > target:
        if quality > MIN_QUALITY:
            quality -= 7
        elif max(img.size) * 0.88 >= MIN_SIDE:
            img = img.resize((int(img.width * 0.88), int(img.height * 0.88)), Image.LANCZOS)
        else:
            break  # وصلنا لأدنى حد مسموح للوضوح
        data = _encode(img, fmt, quality)

    return CompressionResult(
        data=data, ext=ext, mime=mime,
        original_kb=len(raw) / 1024, final_kb=len(data) / 1024,
        within_target=len(data) <= target,
    )
