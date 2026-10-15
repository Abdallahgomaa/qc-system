"""سجل التدقيق (البند 3.7): تسجيل «من أضاف/عدّل/حذف ماذا ومتى».

التسجيل يعمل بأسلوب «أفضل جهد» (best-effort): إذا فشل التسجيل لأي سبب
(مثلاً الجدول غير منشأ بعد) فإن العملية الأصلية تُكمل بنجاح ولا تُفشَل.
لإنشاء الجدول نفّذ ``migrations/001_audit_log.sql`` في Supabase.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.db import supabase

# المدة المسموحة لتخزين السجل مؤقتاً (ثوانٍ) — قصيرة لأن السجل يتغيّر باستمرار.
CACHE_TTL_SECONDS = 20


def current_actor() -> tuple[str | None, str | None]:
    """يعيد (معرّف المستخدم، اسم المستخدم) من جلسة Streamlit، أو (None, None)."""
    try:
        user = st.session_state.get("user")
    except Exception:  # noqa: BLE001 - خارج سياق Streamlit
        return None, None
    if user is None:
        return None, None
    uid = getattr(user, "id", None)
    name = (getattr(user, "email", None) or "").split("@")[0] or None
    return uid, name


def log_action(action: str, table: str, *, record_id=None, project_id=None,
               summary: str = "", details: dict | None = None) -> None:
    """يسجّل عملية في ``audit_log``. لا يرفع استثناءً أبداً."""
    uid, uname = current_actor()
    row = {
        "user_id": uid,
        "username": uname,
        "action": action,
        "table_name": table,
        "record_id": record_id,
        "project_id": project_id,
        "summary": (summary or "").strip() or None,
        "details": details or None,
    }
    try:
        supabase.table("audit_log").insert(row).execute()
        _fetch_audit.clear()
    except Exception:  # noqa: BLE001 - التسجيل أفضل جهد ولا يُفشل العملية
        pass


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_audit(limit: int, user_key: str) -> list[dict]:
    resp = (
        supabase.table("audit_log")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def fetch_audit_log(limit: int = 200) -> list[dict]:
    """يجلب أحدث العمليات المسجّلة. يرفع استثناءً عربياً واضحاً عند الفشل."""
    key = "anon"
    try:
        user = st.session_state.get("user")
        if user is not None:
            key = getattr(user, "id", None) or getattr(user, "email", None) or "anon"
    except Exception:  # noqa: BLE001
        pass
    try:
        return _fetch_audit(int(limit), key)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"تعذّر جلب سجل التدقيق: {e}") from e


def to_frame(rows: list[dict]) -> pd.DataFrame:
    """يحوّل صفوف السجل إلى إطار عربي مقروء."""
    return pd.DataFrame([
        {
            "التاريخ والوقت": str(r.get("created_at") or "")[:16].replace("T", " "),
            "المستخدم": r.get("username") or "—",
            "العملية": r.get("action") or "—",
            "الجدول": r.get("table_name") or "—",
            "التفاصيل": r.get("summary") or "—",
        }
        for r in rows
    ])
