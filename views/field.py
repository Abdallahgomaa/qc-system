"""الوضع الميداني (Field Offline Mode) — البند (ج) من مرحلة الأوفلاين/PWA.

الفكرة: يحفظ المهندس السجلات في ``static/field.html`` أثناء غياب الشبكة
(تعمل الصفحة بدون إنترنت بعد أن يزورها المستخدم مرة واحدة)، ثم تُرسَل إلى
التطبيق عبر رابط ``/?cges_queue=<base64url>`` عند عودة الاتصال، فيستورد هذا
الوحدة الطابور إلى Supabase عبر ``core.records.insert_record`` مع كشف
التكرار حتى لا تُدخل نفس السجل مرتين.
"""
from __future__ import annotations

import base64
import json

import streamlit as st

from core import pwa, records
from views import calibration, concrete, materials, soil

FIELD_PAGE = "/app/static/field.html"

_SECTIONS = (
    ("concrete_pours", "قسم الخرسانة", concrete.FIELDS),
    ("soil_receipts", "قسم التربة", soil.FIELDS),
    ("material_tests", "قسم المواد", materials.FIELDS),
    ("station_calibrations", "قسم معايرة المحطات", calibration.FIELDS),
)

# الحقول التي لا تدخل في مقارنة التكرار (تواريخ الإنشاء/الملفات/النص الحر)
_SKIP_KEYS = ("notes", "report_7d_path", "report_28d_path", "created_at", "id")


def _options(field: dict) -> list:
    """خيارات قائمة الاختيار المحمولة من ``config.yaml`` إن وُجدت."""
    opts = field.get("options") or []
    if opts:
        return list(opts)
    return []


def _schema() -> dict:
    return {
        "sections": [
            {
                "table": table,
                "title": title,
                "fields": [
                    {
                        "key": f.get("key"),
                        "label": f.get("label") or f.get("key"),
                        "type": f.get("type") or "text",
                        "required": bool(f.get("required")),
                        "options": _options(f),
                    }
                    for f in fields
                ],
            }
            for table, title, fields in _SECTIONS
        ]
    }


def _decode(raw: str) -> list:
    """يحوّل رمز base64url القادم من الرابط إلى قائمة سجلات."""
    try:
        padded = raw + "=" * (-len(raw) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception:  # noqa: BLE001
        return []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


def _norm(value) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_duplicate(table: str, project_id: str, data: dict, existing) -> bool:
    """كشف تكرار الإضافة: هل يوجد سجل بنفس كل الحقول غير المهمة؟"""
    if existing is None or existing.empty:
        return False
    keys = [k for k in data if k not in _SKIP_KEYS and k in existing.columns]
    if not keys:
        return False
    for _, row in existing.iterrows():
        if all(_norm(row.get(k)) == _norm(data.get(k)) for k in keys):
            return True
    return False


def _import_queue(project: dict) -> None:
    """يستورد الطابور القادم من صفحة الوضع الميداني إلى قاعدة البيانات."""
    raw = st.query_params.get("cges_queue")
    if not raw:
        return
    if not project.get("id"):
        # لا مشروع مُحدَّد بعد (الصفحة تُفتح قبل اختيار المشروع): نُبقي الطابور
        # محفوظاً في المتصفح حتى نعرف المشروع، فلا تُفقد سجلات ميدانية.
        return
    items = _decode(raw)
    if not items:
        st.error("تعذّر قراءة طابور المزامنة — البيانات تالفة. أعد المحاولة من صفحة الوضع الميداني.")
        st.query_params.clear()
        return

    imported = skipped = 0
    errors: list[str] = []
    for item in items:
        table = str(item.get("table") or "")
        data = item.get("data") or {}
        if table not in records.ALLOWED_TABLES:
            errors.append(f"قسم غير معروف: {table}")
            continue
        try:
            existing = records.fetch_records(table, project["id"])
        except Exception:  # noqa: BLE001
            existing = None
        clean = {k: v for k, v in (data or {}).items() if k and k != "project_id"}
        if _is_duplicate(table, str(project["id"]), clean, existing):
            skipped += 1
            continue
        try:
            row = dict(clean)
            row["project_id"] = str(project["id"])
            records.insert_record(table, row, summary="مزامنة الوضع الميداني")
            imported += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{table}: {exc}")

    if imported:
        st.success(f"تمت مزامنة {imported} سجل من الطابور المحلي بنجاح.")
    if skipped:
        st.info(f"تم تخطي {skipped} سجل مكرر (موجود مسبقاً في قاعدة البيانات).")
    for err in errors[:5]:
        st.error(f"تعذّر إدخال سجل: {err}")
    if errors:
        st.warning("بقي في الطابور المحلي سجلات لم تُدخل — عدّل البيانات ثم أعد المزامنة.")

    # لا نفرّغ الطابور إلا إذا نجحت كل السجلات، حتى لا تُفقد بيانات ميدانية.
    if not errors:
        pwa.clear_queue()
    st.query_params.clear()


def import_from_query(project: dict | None = None) -> None:
    """يستورد الطابور من الرابط ``?cges_queue=`` للمشروع النشط.

    تُستدعى من ``app.py`` بعد تحديد المشروع، فتصل السجلات الميدانية إلى قاعدة
    البيانات أياً كانت الصفحة المفتوحة. تُتجاهل بصمت إن لم يكن هناك طابور.
    """
    raw = st.query_params.get("cges_queue")
    if not raw:
        return
    if project is None:
        try:  # المشروع النشط محفوظ في حالة الجلسة بمفتاح project_id
            project_id = st.session_state.get("project_id")
        except Exception:  # noqa: BLE001
            project_id = None
        project = {"id": project_id} if project_id else {}
    _import_queue(project)


def render(project: dict) -> None:
    """لوحة الوضع الميداني داخل التطبيق."""
    if not project.get("id"):
        st.info("لا يوجد مشروع مُختار. اختر مشروعاً من القائمة أعلاه.")
        return

    pwa.save_schema(_schema())
    _import_queue(project)

    st.markdown("### الوضع الميداني (بدون اتصال)")
    st.caption(
        "افتح صفحة الإدخال الميداني، وسجّل أثناء غياب الشبكة، ثم اضغط «مزامنة الآن» "
        "لتُحفظ السجلات في المشروع تلقائياً."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.link_button("فتح صفحة الوضع الميداني", FIELD_PAGE, use_container_width=True)
    with col_b:
        if st.button("تحديث المخطط المحلي", use_container_width=True):
            pwa.save_schema(_schema())
            st.success("تم تحديث مخطط الحقول في المتصفح.")

    st.markdown(
        """
        **كيف يعمل الطابور المحلي**
        1. تُحفظ السجلات في ذاكرة المتصفح المحلية (`localStorage`) على هذا الجهاز فقط.
        2. عند عودة الاتصال تُرسل عبر رابط آمن إلى التطبيق، فيستوردها إلى قاعدة البيانات.
        3. يُرفض أي سجل مكرر تلقائياً حتى لا تتكرر الإدخالات.
        """,
        unsafe_allow_html=False,
    )
