"""صفحة الإدارة — إدارة المشاريع والمستخدمين (للمدير العام فقط)."""
from __future__ import annotations

import streamlit as st

from core import audit, auth, db, records, ui
from core.config import ROLE_LABELS
from core.db import supabase
from views._common import _render_table, flash, show_flash

STATUS_LABELS = {"active": "قائم", "on_hold": "متوقف", "closed": "مغلق"}

# تسميات عربية لعمليات سجل التدقيق (البند 3.7).
AUDIT_ACTIONS = {"insert": "إضافة", "update": "تعديل", "delete": "حذف",
                 "create_project": "إنشاء مشروع"}
# تسميات عربية لجداول السجل.
AUDIT_TABLES = {"concrete_pours": "الخرسانة", "soil_receipts": "التربة",
                "material_tests": "المواد والاختبارات",
                "station_calibrations": "معايرة المحطات", "projects": "المشاريع"}


def _list_projects():
    try:
        return db.list_projects(), None
    except Exception as e:  # noqa: BLE001
        return [], str(e)


def _fetch_profiles():
    try:
        resp = supabase.table("profiles").select("*").order("created_at", desc=True).execute()
        return resp.data or [], None
    except Exception as e:  # noqa: BLE001
        return [], str(e)


def _projects_tab() -> None:
    projects, err = _list_projects()
    if err:
        st.error(f"تعذّر جلب قائمة المشاريع: {err}")
    elif projects:
        st.success(f"تم جلب المشاريع بنجاح — العدد: {len(projects)}.")
        st.dataframe(
            [
                {"الكود": p.get("code") or "—", "الاسم": p.get("name"),
                 "العميل": p.get("client") or "—", "الموقع": p.get("location") or "—",
                 "الحالة": STATUS_LABELS.get(p.get("status"), p.get("status"))}
                for p in projects
            ],
            hide_index=True,
        )
    else:
        st.info("لا توجد مشاريع بعد. أنشئ أول مشروع من النموذج أدناه.")

    st.markdown("##### إضافة مشروع جديد")
    with st.form("add_project", clear_on_submit=True):
        col1, col2 = st.columns(2)
        code = col1.text_input("كود المشروع")
        name = col2.text_input("اسم المشروع *")
        client = col1.text_input("العميل")
        location = col2.text_input("الموقع")
        status = st.selectbox("الحالة", list(STATUS_LABELS),
                              format_func=lambda s: STATUS_LABELS[s])
        submitted = st.form_submit_button("إنشاء المشروع", type="primary")

    if submitted:
        try:
            created = records.add_project(code=code, name=name, client=client,
                                          location=location, status=status)
        except Exception as e:  # noqa: BLE001
            st.error(str(e))
        else:
            flash(f"تم إنشاء المشروع «{created.get('name')}» بنجاح.")
            st.rerun()


def _users_tab() -> None:
    profiles, err = _fetch_profiles()
    if err:
        st.error(f"تعذّر جلب المستخدمين: {err}")
    elif profiles:
        st.success(f"تم جلب المستخدمين بنجاح — العدد: {len(profiles)}.")
        st.dataframe(
            [
                {"اسم المستخدم": p.get("username"), "الاسم الكامل": p.get("full_name") or "—",
                 "الدور": ROLE_LABELS.get(p.get("role"), p.get("role"))}
                for p in profiles
            ],
            hide_index=True,
        )
    else:
        st.info("لا يوجد مستخدمون لعرضهم.")

    st.warning(
        "إنشاء المستخدمين وإسناد المشاريع يتم عبر لوحة Supabase. "
        "يتطلّب ذلك مفتاح `SUPABASE_SERVICE_KEY` (يُوضع في Secrets فقط ولا يُرفع للمستودع)."
    )


def _audit_tab() -> None:
    """سجل التدقيق (البند 3.7): من أضاف/عدّل/حذف ماذا ومتى."""
    try:
        rows = audit.fetch_audit_log(limit=200)
    except Exception as e:  # noqa: BLE001
        st.error(f"تعذّر جلب سجل التدقيق: {e}")
        st.info("تأكّد من إنشاء جدول `audit_log` — نفّذ الملف "
                "`migrations/001_audit_log.sql` في Supabase > SQL Editor.")
        return
    if not rows:
        st.info("لا توجد عمليات مسجّلة بعد.")
        return
    st.success(f"تم جلب سجل التدقيق بنجاح — العدد: {len(rows)}.")
    frame = audit.to_frame(rows)
    frame["العملية"] = frame["العملية"].map(lambda a: AUDIT_ACTIONS.get(a, a))
    frame["الجدول"] = frame["الجدول"].map(lambda t: AUDIT_TABLES.get(t, t))
    _render_table(frame)
    st.caption("يُعرض آخر 200 عملية. يُسجَّل كل من الإضافة والتعديل والحذف وإنشاء المشاريع.")


def render() -> None:
    if not auth.is_admin():
        st.error("هذه الصفحة متاحة للمدير العام فقط.")
        return

    ui.page_header("الإدارة", "إدارة المشاريع والمستخدمين")
    show_flash()
    tab_projects, tab_users, tab_audit = st.tabs(
        ["المشاريع", "المستخدمون والإسناد", "سجل التدقيق"])
    with tab_projects:
        _projects_tab()
    with tab_users:
        _users_tab()
    with tab_audit:
        _audit_tab()
