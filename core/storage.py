"""رفع المرفقات إلى Supabase Storage وروابط التحميل الموقّعة.

يعتمد على العميل المُهيَّأ في ``core/db.py`` وعلى ضغط الصور في ``core/image_utils.py``.
الـ Bucket هو ``cges-files`` (خاص) كما في ``schema.sql``، وأول مجلد في المسار هو
``project_id`` لتتوافق مع سياسات RLS الخاصة بالتخزين.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from core import image_utils
from core.config import UPLOAD_TYPES
from core.db import supabase

BUCKET = "cges-files"

# الأنواع المقبولة (بلا نقطة، كما يتوقّعها st.file_uploader).
# المصدر الوحيد للحقيقة هو UPLOAD_TYPES في core/config.py.
IMAGE_TYPES = ("png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff")
DOC_TYPES = tuple(t for t in UPLOAD_TYPES if t not in IMAGE_TYPES)

MAX_DOC_MB = 10          # حد ملفات PDF/Excel كما في المتطلبات
MAX_IMAGE_MB = 25        # حدّ أقصى للصورة قبل المعالجة (حماية من تحميل ملف ضخم)
IMAGE_TARGET_KB = 250    # هدف ضغط الصور كما في المتطلبات

_MIME = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "csv": "text/csv",
}


def _ext(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def upload_attachment(project_id: str, section: str, uploaded) -> str:
    """يرفع مرفقاً واحداً (صورة تُضغط تلقائياً) ويعيد المسار المخزَّن.

    يرفع استثناءً برسالة عربية واضحة عند فشل الرفع أو تجاوز الحدود.
    """
    path, _meta = upload_attachment_info(project_id, section, uploaded)
    return path


def upload_attachment_info(project_id: str, section: str, uploaded) -> tuple[str, dict]:
    """مثل ``upload_attachment`` لكنه يعيد أيضاً تفاصيل المعالجة.

    البند 2.5: العنصر الثاني يحوي ما يلزم للتحقّق من وضوح الأرقام بعد الضغط:
    ``is_image`` و``original_kb`` و``final_kb`` و``width`` و``height`` و``long_side``
    و``within_target`` و``summary`` و``warning`` (أو ``None``) وبايتات الصورة
    المضغوطة في ``data`` لعرضها كمعاينة.
    """
    if uploaded is None:
        raise ValueError("لم يتم اختيار أي ملف للرفع.")
    if not project_id:
        raise ValueError("لا يوجد مشروع نشط لربط المرفق به.")

    name = getattr(uploaded, "name", "file")
    ext = _ext(name)
    try:
        raw = uploaded.getvalue()
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"تعذّر قراءة الملف «{name}»: {e}") from e

    # معلومات افتراضية (تُستبدل للصور بنتيجة الضغط الفعلية).
    meta = {
        "name": name, "is_image": False, "original_kb": len(raw) / 1024,
        "final_kb": len(raw) / 1024, "width": 0, "height": 0, "long_side": 0,
        "within_target": True, "summary": f"الحجم {len(raw) / 1024:,.0f} ك.ب",
        "warning": None, "data": None,
    }

    try:
        if ext in IMAGE_TYPES:
            if len(raw) > MAX_IMAGE_MB * 1024 * 1024:
                raise ValueError(f"حجم الصورة «{name}» يتجاوز الحد المسموح ({MAX_IMAGE_MB} ميجابايت).")
            try:
                result = image_utils.compress_image(raw, max_kb=IMAGE_TARGET_KB, fmt="WEBP")
            except Exception as e:  # noqa: BLE001
                raise ValueError(
                    f"تعذّر معالجة الصورة «{name}»؛ تأكّد أنها صورة صالحة (PNG/JPG/WEBP)."
                ) from e
            data, stored_ext, content_type = result.data, result.ext.lstrip("."), result.mime
            summary, warning = image_utils.clarity_note(result)
            meta.update(
                is_image=True, original_kb=result.original_kb, final_kb=result.final_kb,
                width=result.width, height=result.height, long_side=result.long_side,
                within_target=result.within_target, summary=summary, warning=warning,
                data=result.data,
            )
        elif ext in DOC_TYPES:
            if len(raw) > MAX_DOC_MB * 1024 * 1024:
                raise ValueError(f"حجم الملف «{name}» يتجاوز الحد المسموح ({MAX_DOC_MB} ميجابايت).")
            data, stored_ext = raw, ext
            content_type = _MIME.get(ext, "application/octet-stream")
        else:
            raise ValueError(f"نوع الملف «{ext}» غير مدعوم. المسموح: {', '.join(UPLOAD_TYPES)}.")

        stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        path = f"{project_id}/{section}/{stamp}_{uuid.uuid4().hex[:8]}.{stored_ext}"
        supabase.storage.from_(BUCKET).upload(
            path, data, {"content-type": content_type, "upsert": False}
        )
        return path, meta
    except ValueError:
        raise
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"تعذّر رفع المرفق «{name}» إلى التخزين: {e}") from e


def delete_uploaded(paths) -> None:
    """يحذف مرفقات سبق رفعها.

    يُستعمل للتنظيف عند فشل حفظ السجل بعد رفع المرفقات، حتى لا تبقى ملفات
    يتيمة في الـ Bucket. لا يرفع استثناءً (التنظيف تفضيلي).
    """
    items = [p for p in (paths or []) if p]
    if not items:
        return
    try:
        supabase.storage.from_(BUCKET).remove(items)
    except Exception:  # noqa: BLE001 - التنظيف تفضيلي ولا يجب أن يُسقط العملية
        pass


def signed_url(path: str, expires_in: int = 3600):
    """يعيد رابطاً موقّعاً مؤقتاً (ساعة افتراضياً) للمرفق، أو ``None`` عند الفشل."""
    if not path:
        return None
    try:
        resp = supabase.storage.from_(BUCKET).create_signed_url(path, expires_in)
    except Exception:  # noqa: BLE001 - روابط المرفقات ميزة إضافية لا يجب أن تُسقط الصفحة
        return None
    if isinstance(resp, dict):
        return resp.get("signedURL") or resp.get("signedUrl") or resp.get("signed_url")
    return getattr(resp, "signed_url", None)
