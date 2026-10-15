"""مكوّنات مشتركة لعرض وإدخال وتعديل سجلات أقسام الجودة.

مصمَّمة لتُستعمل مرة واحدة من كل قسم (خرسانة/تربة/مواد/معايرة) اعتماداً على قوائم
حقول (FIELDS) وقوائم ملفات (FILES)، تفادياً لتكرار الكود. تتضمّن:
- معالجة أخطاء كاملة بـ ``try/except`` مع رسائل ``st.error``/``st.warning`` واضحة.
- تحقّقاً من الحقول الإلزامية قبل الحفظ.
- رسائل ``st.success`` تؤكّد نجاح العرض/الحفظ/التعديل/الحذف.
- تبويب «تعديل سجل» (البند 3.3) يتيح تعديل سجل قائم وإضافة/استبدال مرفق (البند 3.4).
"""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Iterable

import pandas as pd
import streamlit as st

from core import auth, records, storage, ui
from core.excel import df_to_excel

try:  # الرسوم ميزة إضافية: إن لم تتوفّر plotly نُكمل بلا رسوم
    import plotly.express as px
except Exception:  # noqa: BLE001
    px = None

_FLASH_KEY = "_cges_flash"


# ---------------------------------------------------------------------------
# رسائل مؤكِّدة تبقى ظاهرة بعد إعادة التحميل
# ---------------------------------------------------------------------------
def flash(message: str, level: str = "success") -> None:
    st.session_state[_FLASH_KEY] = (message, level)


def show_flash() -> None:
    item = st.session_state.pop(_FLASH_KEY, None)
    if not item:
        return
    message, level = item
    {"success": st.success, "warning": st.warning, "error": st.error}.get(level, st.info)(message)


# ---------------------------------------------------------------------------
# تحويلات مساعدة للقيم القادمة من قاعدة البيانات
# ---------------------------------------------------------------------------
def _as_date(value) -> date | None:
    """يحوّل قيمة (نص/تاريخ/Timestamp/NaT) إلى ``date`` أو ``None``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip() and value != "NaT":
        try:
            return datetime.fromisoformat(value[:10]).date()
        except ValueError:
            return None
    return None


def _as_num(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        number = float(value)
        return default if math.isnan(number) else number
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# عناصر الإدخال
# ---------------------------------------------------------------------------
_UNSET = object()


def _widget(field: dict, key: str, value=_UNSET):
    """ينشئ عنصر الإدخال المناسب لنوع الحقل.

    ``value`` قيمة ابتدائية صريحة (تُستخدم في التعديل)؛ عند تركها ترجع للافتراضي.
    """
    ftype, label = field["type"], field["label"]
    cur = field.get("default") if value is _UNSET else value

    if ftype == "text":
        return st.text_input(label, value="" if cur in (None, _UNSET) else str(cur),
                             key=key, placeholder=field.get("placeholder", ""))
    if ftype == "textarea":
        return st.text_area(label, value="" if cur in (None, _UNSET) else str(cur),
                            key=key, height=90)
    if ftype == "select":
        options = field["options"]
        if cur in options:
            index = options.index(cur)
        elif field.get("default") in options:
            index = options.index(field["default"])
        else:
            index = 0
        return st.selectbox(label, options, index=index, key=key)
    if ftype == "date":
        return st.date_input(label, value=_as_date(cur) or date.today(), key=key)
    if ftype == "optdate":
        existing = _as_date(cur)
        enabled = st.checkbox(f"تحديد {label}", value=existing is not None, key=key + "_on")
        return st.date_input(label, value=existing or date.today(), key=key) if enabled else None
    if ftype == "int":
        return int(st.number_input(label, min_value=0, step=1,
                                   value=int(_as_num(cur)), key=key))
    if ftype == "number":
        return float(st.number_input(label, min_value=0.0, step=field.get("step", 0.5),
                                     value=float(_as_num(cur)),
                                     format=field.get("format", "%.1f"), key=key))
    if ftype == "optnumber":
        number = float(st.number_input(label + " (اتركه 0 إن لم يتوفر)",
                                       min_value=0.0, step=field.get("step", 0.5),
                                       value=float(_as_num(cur)),
                                       format=field.get("format", "%.1f"), key=key))
        return number if number > 0 else None
    raise ValueError(f"نوع حقل غير مدعوم: {ftype}")


def validate(fields: Iterable[dict], values: dict) -> list[str]:
    """يعيد قائمة بتسميات الحقول الإلزامية الناقصة (فارغة إن كان كل شيء سليماً)."""
    missing: list[str] = []
    for field in fields:
        if not field.get("required"):
            continue
        value = values.get(field["key"])
        if field["type"] in ("int", "number", "optnumber"):
            if value in (None, 0, 0.0):
                missing.append(field["label"])
        elif value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field["label"])
    return missing


def _labels(fields: list[dict], files: list[dict]) -> dict:
    return {f["key"]: f["label"] for f in fields} | {x["key"]: x["label"] for x in files}


def _row_label(fields: list[dict], view, record_id) -> str:
    preview = [f["key"] for f in fields[:2] if f["key"] in view.columns]
    values = [str(view.loc[view["id"] == record_id, k].iloc[0]) for k in preview]
    return " | ".join(values) or str(record_id)


def _render_table(frame) -> None:
    """يعرض الجدول كـ HTML ليتبع ثيم التطبيق (فاتح/داكن) واتجاه RTL — البند 3.2."""
    try:
        html = frame.to_html(index=False, escape=True, border=0, classes="cges-table")
    except Exception as e:  # noqa: BLE001
        st.warning(f"تعذّر عرض الجدول: {e}")
        return
    st.markdown(f'<div class="cges-table-wrap">{html}</div>', unsafe_allow_html=True)


# حقول المقاومة المستخدمة في التحليل (البند 4.3)
_STRENGTH_KEYS = ("design_strength_mpa", "result_7d_mpa", "result_28d_mpa")


def _has_analytics(fields: list[dict]) -> bool:
    return bool({f["key"] for f in fields} & set(_STRENGTH_KEYS))


def _record_title(fields: list[dict], row) -> str:
    parts = [str(row.get(f["key"])) for f in fields[:2]
             if row.get(f["key"]) not in (None, "")]
    return " | ".join(parts) or "سجل"


# ---------------------------------------------------------------------------
# تبويب السجل (عرض + بحث + تصدير + مرفقات + حذف)
# ---------------------------------------------------------------------------
def _render_log(project: dict, *, table: str, section: str, fields: list[dict], files: list[dict]) -> None:
    try:
        df = records.fetch_records(table, project["id"])
    except Exception as e:  # noqa: BLE001
        st.error(str(e))
        return

    if df.empty:
        st.info("لا توجد سجلات بعد لهذا المشروع. أضف أول سجل من تبويب «إضافة سجل جديد».")
        return

    st.success(f"تم جلب البيانات بنجاح — عدد السجلات: {len(df)}.")
    labels = _labels(fields, files)

    query = st.text_input("بحث في السجل", placeholder="اكتب أي كلمة…", key=f"q_{table}")
    view = df
    if query:
        needle = query.casefold()
        mask = df.map(lambda v: needle in str(v).casefold()).any(axis=1)
        view = df[mask]
        if view.empty:
            st.warning("لا توجد نتائج مطابقة لبحثك.")

    shown = view[[c for c in labels if c in view.columns]].copy()
    for fcol in files:  # نعرض علامة ✔ بدل المسار الطويل
        if fcol["key"] in shown:
            shown[fcol["key"]] = shown[fcol["key"]].map(lambda p: "✔" if p else "—")
    _render_table(shown.rename(columns=labels))
    st.caption(f"عدد السجلات المعروضة: {len(view)} من {len(df)}")

    try:
        data = df_to_excel(shown.rename(columns=labels), section)
        st.download_button(
            "تصدير Excel", data,
            file_name=f"CGES_{project.get('code') or 'project'}_{section}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:  # noqa: BLE001
        st.warning(f"تعذّر تجهيز ملف Excel: {e}")

    _render_attachments(project, table=table, fields=fields, files=files, view=view)


def _render_attachments(project: dict, *, table: str, fields: list[dict],
                        files: list[dict], view) -> None:
    if not files:
        return
    st.markdown("##### مرفقات السجل")
    ids = view["id"].tolist() if "id" in view.columns else []
    if not ids:
        st.caption("لا توجد سجلات لها معرّفات لعرض المرفقات.")
        return

    pick = st.selectbox("اختر سجلاً لعرض مرفقاته", ids, key=f"pick_{table}",
                        format_func=lambda i: _row_label(fields, view, i))
    row = view[view["id"] == pick].iloc[0]

    any_attachment = False
    for fcol in files:
        path = row.get(fcol["key"])
        if path:
            any_attachment = True
            url = storage.signed_url(path)
            if url:
                st.link_button(f"فتح: {fcol['label']}", url)
            else:
                st.warning(f"تعذّر توليد رابط لـ «{fcol['label']}».")
    if not any_attachment:
        st.caption("لا توجد مرفقات لهذا السجل.")

    if auth.is_admin():
        if st.button("حذف هذا السجل", key=f"del_{table}"):
            old_paths = [row.get(f["key"]) for f in files]
            try:
                records.delete_record(table, pick, summary=_record_title(fields, row))
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
            else:
                # احذف مرفقات السجل المحذوف حتى لا تبقى ملفات يتيمة في الـ Bucket.
                storage.delete_uploaded(old_paths)
                flash("تم حذف السجل بنجاح.")
                st.rerun()


# ---------------------------------------------------------------------------
# البند 2.5: التقاط الصور بكاميرا الموبايل + التحقّق من وضوح الأرقام بعد الضغط
# ---------------------------------------------------------------------------
_NOTES_KEY = "_cges_upload_notes"


class _CameraUpload:
    """غلاف لصورة الكاميرا ليحمل اسماً بامتداد صورة صالح لطبقة التخزين."""

    def __init__(self, raw: bytes, name: str = "camera.png") -> None:
        self.name = name
        self._raw = raw

    def getvalue(self) -> bytes:
        return self._raw


def _attachment_widget(field: dict, key: str, camera: bool):
    """يعرض حقل مرفق: التقاط بالكاميرا (للموبايل) أو اختيار ملف — البند 2.5."""
    if camera:
        shot = st.camera_input(f"كاميرا: {field['label']}", key=f"{key}_cam")
        return _CameraUpload(shot.getvalue()) if shot is not None else None
    return st.file_uploader(
        field["label"], type=list(storage.UPLOAD_TYPES), key=key,
        help="الصور تُضغط تلقائياً وتُحفظ WebP، والمستندات حتى 10 ميجابايت.",
    )


def _push_upload_notes(notes: list[tuple[str, dict]]) -> None:
    """يحفظ ملخّصات الرفع لعرضها بعد إعادة التحميل (مثل رسائل flash)."""
    if notes:
        st.session_state[_NOTES_KEY] = notes


def _show_upload_notes() -> None:
    """يعرض معاينة المرفقات المرفوعة للتوّ مع تحذير إن كانت الأرقام غير واضحة."""
    notes = st.session_state.pop(_NOTES_KEY, None) or []
    for label, meta in notes:
        st.markdown(f"**معاينة المرفق: {label}**")
        left, right = st.columns([1, 2])
        with left:
            if meta.get("data"):
                st.image(meta["data"], caption=f"{label} (بعد الضغط)", width=220)
        with right:
            st.caption(meta.get("summary", ""))
            warning = meta.get("warning")
            if warning:
                st.warning(warning + " — إن كانت المعاينة غير واضحة فأعد الرفع بصورة أوضح.")
            else:
                st.success("الأرقام واضحة في المعاينة، وتم ضغط الصورة بنجاح.")


# ---------------------------------------------------------------------------
# تبويب الإضافة (نموذج + تحقّق + رفع مرفقات + حفظ)
# ---------------------------------------------------------------------------
def _render_add(project: dict, *, table: str, section: str, fields: list[dict], files: list[dict]) -> None:
    # مفتاح دوّار: يُعاد إنشاء حقول النموذج بعد كل حفظ ناجح، لأن
    # ``st.form(clear_on_submit=True)`` لا يُفرّغ ``st.file_uploader``، فقد يبقى
    # مرفق قديم معلّقاً ويُرفع خطأً مع السجل التالي.
    nonce = st.session_state.get(f"_addn_{table}", 0)
    _show_upload_notes()

    # البند 2.5: خيار التقاط الصور بكاميرا الموبايل (خارج النموذج ليُعيد التحميل فوراً).
    camera = False
    if files:
        camera = st.checkbox(
            "📷 التقاط الصور بالكاميرا (مناسب للموبايل)",
            key=f"{table}_{nonce}_camera",
            help="فعّله لالتقاط صورة مباشرة من كاميرا الجهاز بدل اختيار ملف، مع ضغط تلقائي ومعاينة للتحقّق من وضوح الأرقام.",
        )

    with st.form(f"add_{table}_{nonce}", clear_on_submit=True):
        values: dict = {}
        cols = st.columns(2)
        for i, field in enumerate(fields):
            with cols[i % 2]:
                values[field["key"]] = _widget(field, f"{table}_{nonce}_{field['key']}")

        uploads: dict = {}
        if files:
            st.markdown("**المرفقات** (الصور تُضغط تلقائياً قبل الرفع)")
            uploads = {
                x["key"]: _attachment_widget(x, f"{table}_{nonce}_{x['key']}", camera)
                for x in files
            }

        submitted = st.form_submit_button("حفظ السجل", type="primary")

    if not submitted:
        return

    missing = validate(fields, values)
    if missing:
        st.error("أكمل الحقول الإلزامية التالية: " + "، ".join(missing))
        return

    row = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in values.items()}
    row["project_id"] = project["id"]

    labels = {x["key"]: x["label"] for x in (files or [])}
    saved_paths: list[str] = []
    notes: list[tuple[str, dict]] = []
    for key, uploaded in uploads.items():
        if uploaded is None:
            continue
        try:
            path, meta = storage.upload_attachment_info(project["id"], section, uploaded)
            row[key] = path
            saved_paths.append(path)
            if meta.get("is_image"):
                notes.append((labels.get(key, key), meta))
        except Exception as e:  # noqa: BLE001
            storage.delete_uploaded(saved_paths)
            st.error(f"تعذّر رفع المرفق «{getattr(uploaded, 'name', key)}»: {e}")
            st.warning("لم يتم حفظ السجل. أعد المحاولة بعد معالجة المرفق.")
            return

    try:
        records.insert_record(table, row, summary=_record_title(fields, row))
    except Exception as e:  # noqa: BLE001
        storage.delete_uploaded(saved_paths)  # لا نُبقي مرفقات بلا سجل
        st.error(str(e))
    else:
        _push_upload_notes(notes)
        st.session_state[f"_addn_{table}"] = nonce + 1  # يُفرّغ النموذج والمرفقات
        flash("تم حفظ السجل بنجاح.")
        st.rerun()


# ---------------------------------------------------------------------------
# تبويب التعديل (3.3 تعديل سجل قائم + 3.4 إضافة/استبدال مرفق)
# ---------------------------------------------------------------------------
def _render_edit(project: dict, *, table: str, section: str, fields: list[dict], files: list[dict]) -> None:
    try:
        df = records.fetch_records(table, project["id"])
    except Exception as e:  # noqa: BLE001
        st.error(str(e))
        return

    if df.empty:
        st.info("لا توجد سجلات لتعديلها بعد.")
        return

    ids = df["id"].tolist()
    pick = st.selectbox("اختر السجل المطلوب تعديله", ids, key=f"edit_pick_{table}",
                        format_func=lambda i: _row_label(fields, df, i))
    row = df[df["id"] == pick].iloc[0]
    _show_upload_notes()

    # البند 2.5: خيار التقاط الصور بكاميرا الموبايل (خارج النموذج ليُعيد التحميل فوراً).
    camera = False
    if files:
        camera = st.checkbox(
            "📷 التقاط الصور بالكاميرا (مناسب للموبايل)",
            key=f"{table}_edit_{pick}_camera",
            help="فعّله لالتقاط صورة مباشرة من كاميرا الجهاز بدل اختيار ملف، مع ضغط تلقائي ومعاينة للتحقّق من وضوح الأرقام.",
        )

    with st.form(f"edit_{table}_{pick}"):
        values: dict = {}
        cols = st.columns(2)
        for i, field in enumerate(fields):
            with cols[i % 2]:
                values[field["key"]] = _widget(
                    field, f"{table}_edit_{pick}_{field['key']}", row.get(field["key"]))

        uploads: dict = {}
        if files:
            st.markdown("**المرفقات** (ارفع ملفاً جديداً لإضافة/استبدال المرفق — البند 3.4)")
            for x in files:
                current = row.get(x["key"])
                st.caption(f"{x['label']}: {'يوجد مرفق حالياً ✔' if current else 'لا يوجد مرفق'}")
                uploads[x["key"]] = _attachment_widget(
                    x, f"{table}_edit_{pick}_{x['key']}", camera)

        submitted = st.form_submit_button("حفظ التعديلات", type="primary")

    if not submitted:
        return

    missing = validate(fields, values)
    if missing:
        st.error("أكمل الحقول الإلزامية التالية: " + "، ".join(missing))
        return

    payload = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in values.items()}
    labels = {x["key"]: x["label"] for x in (files or [])}
    saved_paths: list[str] = []
    replaced_paths: list[str] = []  # مرفقات قديمة استُبدلت بمرفقات جديدة
    notes: list[tuple[str, dict]] = []
    for key, uploaded in uploads.items():
        if uploaded is None:
            continue
        try:
            path, meta = storage.upload_attachment_info(project["id"], section, uploaded)
            payload[key] = path
            saved_paths.append(path)
            old = row.get(key)
            if old and old != path:
                replaced_paths.append(old)
            if meta.get("is_image"):
                notes.append((labels.get(key, key), meta))
        except Exception as e:  # noqa: BLE001
            storage.delete_uploaded(saved_paths)
            st.error(f"تعذّر رفع المرفق «{getattr(uploaded, 'name', key)}»: {e}")
            st.warning("لم يتم حفظ التعديلات. أعد المحاولة بعد معالجة المرفق.")
            return

    try:
        records.update_record(table, pick, payload, summary=_record_title(fields, payload))
    except Exception as e:  # noqa: BLE001
        storage.delete_uploaded(saved_paths)  # لا نُبقي مرفقاً بلا سجل
        st.error(str(e))
    else:
        # احذف المرفقات القديمة التي استُبدلت حتى لا تبقى ملفات يتيمة.
        storage.delete_uploaded(replaced_paths)
        for field in fields:
            st.session_state.pop(f"{table}_edit_{pick}_{field['key']}", None)
        for x in (files or []):  # يُفرّغ حقول المرفقات بعد الحفظ
            st.session_state.pop(f"{table}_edit_{pick}_{x['key']}", None)
        _push_upload_notes(notes)
        flash("تم تعديل السجل بنجاح.")
        st.rerun()


# ---------------------------------------------------------------------------
# تبويب الاستيراد من Excel (البند 4.4)
# ---------------------------------------------------------------------------
def coerce_import_row(fields: list[dict], raw) -> tuple[dict, list[str]]:
    """يحوّل صفاً من DataFrame إلى قاموس بقيم صالحة للإدراج (دالة نقية قابلة للاختبار).

    يعيد ``(row, errors)``؛ أخطاء القيم بلا بادئة رقم الصف، ويضيفها المستدعي.
    """
    labels = {f["label"]: f["key"] for f in fields}
    types = {f["key"]: f["type"] for f in fields}
    row: dict = {}
    errors: list[str] = []
    for col in getattr(raw, "index", []):
        if col not in labels:
            continue
        value = raw[col]
        if pd.isna(value) or (isinstance(value, str) and not value.strip()):
            continue
        key = labels[col]
        ftype = types.get(key)
        if ftype == "int":
            try:
                value = int(round(float(value)))
            except (TypeError, ValueError):
                errors.append(f"قيمة غير رقمية في «{col}»")
                continue
        elif ftype in ("number", "optnumber"):
            try:
                value = float(value)
            except (TypeError, ValueError):
                errors.append(f"قيمة غير رقمية في «{col}»")
                continue
            if ftype == "optnumber" and value == 0:
                value = None
        elif ftype in ("date", "optdate"):
            value = _as_date(value)
            value = value.isoformat() if value else None
        else:
            value = str(value).strip()
        if value is not None:
            row[key] = value
    return row, errors


def _render_import(project: dict, *, table: str, section: str, fields: list[dict]) -> None:
    """يستورد سجلات من ملف Excel/CSV بأعمدة عربية مطابقة لتسميات الحقول."""
    labels = {f["label"]: f["key"] for f in fields}
    types = {f["key"]: f["type"] for f in fields}
    try:
        template = df_to_excel(pd.DataFrame([{f["label"]: "" for f in fields}]), section)
        st.download_button(
            "تنزيل نموذج فارغ", template,
            file_name=f"CGES_{section}_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"tpl_{table}",
        )
    except Exception as e:  # noqa: BLE001
        st.warning(f"تعذّر تجهيز النموذج: {e}")
    st.caption("ارفع ملفاً بأعمدة عربية مطابقة لتسميات الحقول (نزّل النموذج أعلاه للبدء). "
               "الأعمدة غير المعروفة تُتجاهل، والمرفقات لا تُستورد.")

    uploaded = st.file_uploader("ملف Excel/CSV", type=["xlsx", "xls", "csv"], key=f"imp_{table}")
    if uploaded is None:
        return

    try:
        frame = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
    except Exception as e:  # noqa: BLE001
        st.error(f"تعذّر قراءة الملف «{getattr(uploaded, 'name', '')}»: {e}")
        return

    frame.columns = [str(c).strip() for c in frame.columns]
    unknown = [c for c in frame.columns if c not in labels]
    if unknown:
        st.warning("أعمدة غير معروفة ستُتجاهل: " + "، ".join(unknown))
    known = [c for c in frame.columns if c in labels]
    if not known:
        st.error("لم يُعثر على أي عمود مطابق لتسميات الحقول.")
        return

    st.info(f"عدد الصفوف في الملف: {len(frame)}")
    _render_table(frame[known].head(20))

    if not st.button("تأكيد الاستيراد", key=f"imp_go_{table}", type="primary"):
        return

    imported, errors = 0, []
    for pos, (_, raw) in enumerate(frame.iterrows(), start=2):
        row, row_errors = coerce_import_row(fields, raw)
        errors.extend(f"الصف {pos}: {msg}" for msg in row_errors)
        if row_errors:
            continue
        row["project_id"] = project["id"]
        missing = validate(fields, row)
        if missing:
            errors.append(f"الصف {pos}: حقول إلزامية ناقصة ({'، '.join(missing)})")
            continue
        try:
            records.insert_record(table, row, summary=_record_title(fields, row))
            imported += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"الصف {pos}: {e}")

    if errors:
        st.error("تعذّر استيراد بعض الصفوف:\n- " + "\n- ".join(errors[:15]))
    if imported:
        flash(f"تم استيراد {imported} سجلاً بنجاح.")
        st.rerun()


# ---------------------------------------------------------------------------
# تبويب تحليل النتائج (البند 4.3: مقارنة 7 و28 يوم بالإجهاد التصميمي)
# ---------------------------------------------------------------------------
def _render_analytics(project: dict, *, table: str, fields: list[dict]) -> None:
    try:
        df = records.fetch_records(table, project["id"])
    except Exception as e:  # noqa: BLE001
        st.error(str(e))
        return
    if df.empty:
        st.info("لا توجد سجلات لتحليلها بعد.")
        return
    if px is None:
        st.warning("مكتبة الرسوم البيانية (plotly) غير متوفرة.")
        return

    label_of = {f["key"]: f["label"] for f in fields}
    keys = [k for k in _STRENGTH_KEYS if k in df.columns]
    if not keys:
        st.info("لا توجد حقول مقاومة قابلة للتحليل لهذا القسم.")
        return

    work = df.copy()
    work["السجل"] = work.apply(lambda r: _record_title(fields, r), axis=1)
    long = work.melt(id_vars="السجل", value_vars=keys, var_name="السلسلة", value_name="MPa")
    long["MPa"] = pd.to_numeric(long["MPa"], errors="coerce")
    long = long.dropna(subset=["MPa"])
    if long.empty:
        st.info("لا توجد نتائج مقاومة مدخلة بعد.")
        return
    long["السلسلة"] = long["السلسلة"].map(lambda k: label_of.get(k, k))

    fig = px.bar(long, x="السجل", y="MPa", color="السلسلة", barmode="group",
                 title="نتائج المقاومة (MPa) مقابل الإجهاد التصميمي")
    st.plotly_chart(fig, width="stretch")

    design = pd.to_numeric(work.get("design_strength_mpa"), errors="coerce")
    d28 = pd.to_numeric(work.get("result_28d_mpa"), errors="coerce")
    mask = design.notna() & d28.notna() & (design > 0)
    if mask.any():
        passed = int((d28[mask] / design[mask] >= 1).sum())
        st.metric("السجلات المستوفية (28 يوم ≥ التصميمي)", f"{passed}/{int(mask.sum())}")


# ---------------------------------------------------------------------------
# نقطة الدخول الموحّدة لكل قسم
# ---------------------------------------------------------------------------
def render_section(project: dict, *, table: str, section: str, title: str,
                   fields: list[dict], files: list[dict] | None = None,
                   subtitle: str = "") -> None:
    """يعرض قسم جودة كامل (سجل + إضافة + تعديل) للمشروع النشط."""
    if not project or not project.get("id"):
        st.warning("لا يوجد مشروع نشط. اختر مشروعاً من القائمة الجانبية أولاً.")
        return

    files = files or []
    ui.page_header(title, subtitle or f"المشروع النشط: {project.get('name', '')}")
    show_flash()

    names = ["السجل", "إضافة سجل جديد", "تعديل سجل", "استيراد من Excel"]
    if _has_analytics(fields):
        names.append("تحليل النتائج")
    panels = st.tabs(names)
    with panels[0]:
        _render_log(project, table=table, section=section, fields=fields, files=files)
    with panels[1]:
        _render_add(project, table=table, section=section, fields=fields, files=files)
    with panels[2]:
        _render_edit(project, table=table, section=section, fields=fields, files=files)
    with panels[3]:
        _render_import(project, table=table, section=section, fields=fields)
    if len(panels) > 4:
        with panels[4]:
            _render_analytics(project, table=table, fields=fields)
