"""طبقة الوصول إلى بيانات أقسام الجودة في Supabase.

تُستعمل هذه الوحدة الجديدة بدل تكرار منطق قاعدة البيانات في الواجهات، وهي تعتمد
على العميل الوحيد المُهيَّأ مسبقاً في ``core/db.py`` (المتغيّر ``supabase``) دون
إعادة تعريفه. كل الدوال تعيد رفع استثناء برسالة عربية واضحة عند الفشل ليعرضها
طبقة الواجهة عبر ``st.error``.

أسماء الجداول والأعمدة هنا مطابقة تماماً لـ ``schema.sql``.

البند 3.5: جلب السجلات مُخزَّن مؤقتاً عبر ``st.cache_data`` لتقليل زمن التحميل،
ويُبطَل التخزين المؤقت تلقائياً بعد أي إضافة/تعديل/حذف. مفتاح التخزين يتضمّن
معرّف المستخدم حتى لا تتداخل بيانات مستخدمين مختلفين تحت سياسات RLS.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import audit
from core.db import supabase

# الجداول المسموح التعامل معها (حماية بسيطة ضد تمرير اسم جدول خاطئ).
ALLOWED_TABLES = frozenset({
    "concrete_pours",
    "soil_receipts",
    "material_tests",
    "station_calibrations",
})

# مدة صلاحية التخزين المؤقت بالثواني.
CACHE_TTL_SECONDS = 60


def _check_table(table: str) -> None:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"جدول غير معروف: {table!r}")


def _current_user_key() -> str:
    """مفتاح يميّز المستخدم الحالي في ذاكرة التخزين المؤقت (يمنع تداخل بيانات RLS)."""
    try:
        user = st.session_state.get("user")
    except Exception:  # noqa: BLE001 - خارج سياق Streamlit
        return "anon"
    if user is None:
        return "anon"
    return getattr(user, "id", None) or getattr(user, "email", None) or "anon"


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_rows(table: str, project_id: str, user_key: str) -> list[dict]:
    resp = (
        supabase.table(table)
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def invalidate_cache() -> None:
    """يُفرِّغ التخزين المؤقت للسجلات بعد أي كتابة (إضافة/تعديل/حذف)."""
    _fetch_rows.clear()


def fetch_records(table: str, project_id: str) -> pd.DataFrame:
    """جلب كل سجلات جدول معيّن لمشروع معيّن، الأحدث أولاً.

    يعيد ``DataFrame`` فارغاً إن لم توجد سجلات، ويرفع استثناءً واضحاً عند الفشل.
    """
    _check_table(table)
    if not project_id:
        raise ValueError("لا يوجد مشروع نشط محدد.")
    try:
        rows = _fetch_rows(table, project_id, _current_user_key())
    except Exception as e:  # noqa: BLE001 - نُغلّف أي خطأ برسالة مفهومة للمستخدم
        raise RuntimeError(f"تعذّر جلب بيانات «{table}» من قاعدة البيانات: {e}") from e
    return pd.DataFrame(rows)


def insert_record(table: str, row: dict, *, summary: str = "") -> dict:
    """إضافة سجل جديد إلى الجدول. يعيد الصف المُضاف فعلياً من قاعدة البيانات."""
    _check_table(table)
    if not isinstance(row, dict) or not row:
        raise ValueError("لا توجد بيانات للحفظ.")
    try:
        resp = supabase.table(table).insert(row).execute()
        if not resp.data:
            raise RuntimeError("لم تُعِد قاعدة البيانات أي صف بعد الحفظ.")
        invalidate_cache()
        saved = resp.data[0]
        # سجل التدقيق (البند 3.7) — أفضل جهد، لا يُفشل العملية.
        audit.log_action("insert", table, record_id=saved.get("id"),
                         project_id=row.get("project_id"), summary=summary)
        return saved
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"تعذّر حفظ السجل في «{table}»: {e}") from e


def update_record(table: str, record_id: str, row: dict, *, summary: str = "") -> dict:
    """تعديل سجل موجود بالمعرّف (البند 3.3). يعيد الصف المُحدَّث."""
    _check_table(table)
    if not record_id:
        raise ValueError("لم يتم تحديد السجل المطلوب تعديله.")
    if not isinstance(row, dict) or not row:
        raise ValueError("لا توجد بيانات للتعديل.")
    try:
        resp = supabase.table(table).update(row).eq("id", record_id).execute()
        invalidate_cache()
        saved = resp.data[0] if resp.data else {"id": record_id, **row}
        audit.log_action("update", table, record_id=record_id,
                         project_id=saved.get("project_id") or row.get("project_id"),
                         summary=summary)
        return saved
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"تعذّر تعديل السجل في «{table}»: {e}") from e


def delete_record(table: str, record_id: str, *, summary: str = "") -> None:
    """حذف سجل واحد بالمعرّف. مخصّص للمدير فقط (يُفرض كذلك في RLS)."""
    _check_table(table)
    if not record_id:
        raise ValueError("لم يتم تحديد السجل المطلوب حذفه.")
    try:
        supabase.table(table).delete().eq("id", record_id).execute()
        invalidate_cache()
        audit.log_action("delete", table, record_id=record_id, summary=summary)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"تعذّر حذف السجل من «{table}»: {e}") from e


# ---------------------------------------------------------------------------
# إدارة المشاريع (يُستعمل في شاشة الإدارة)
# ---------------------------------------------------------------------------
def add_project(code: str, name: str, client: str = "", location: str = "",
                status: str = "active") -> dict:
    """إنشاء مشروع جديد. أعمدة الجدول مطابقة لـ ``projects`` في schema.sql."""
    if not name or not name.strip():
        raise ValueError("اسم المشروع مطلوب.")
    row = {
        "code": (code or "").strip() or None,
        "name": name.strip(),
        "client": (client or "").strip() or None,
        "location": (location or "").strip() or None,
        "status": status,
    }
    try:
        resp = supabase.table("projects").insert(row).execute()
        if not resp.data:
            raise RuntimeError("لم تُعِد قاعدة البيانات أي صف بعد إنشاء المشروع.")
        created = resp.data[0]
        audit.log_action("create_project", "projects", record_id=created.get("id"),
                         project_id=created.get("id"), summary=created.get("name"))
        return created
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"تعذّر إنشاء المشروع: {e}") from e
