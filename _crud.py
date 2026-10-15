"""مولّد واجهة السجلات (عرض + بحث + تصدير Excel + إضافة + مرفقات) معتمد على تعريف الحقول."""
from __future__ import annotations

from datetime import date

import streamlit as st

from core import auth, db, storage
from core.config import UPLOAD_TYPES
from core.excel import df_to_excel


def _input(f: dict, key: str):
    t, label = f["type"], f["label"]
    if t == "text":
        return st.text_input(label, key=key)
    if t == "textarea":
        return st.text_area(label, key=key, height=90)
    if t == "number" and f.get("int"):
        return st.number_input(label, min_value=0, step=1, value=int(f.get("default", 0)), key=key)
    if t == "number":
        return st.number_input(label, min_value=f.get("min", 0.0), step=f.get("step", 1.0),
                               value=f.get("default", 0.0), format=f.get("format", "%.2f"), key=key)
    if t == "optnumber":  # رقم اختياري: 0 تعني "لا يوجد"
        v = st.number_input(label + " (اتركه 0 إن لم يتوفر)", min_value=0.0, step=f.get("step", 0.5),
                            value=0.0, format="%.1f", key=key)
        return v if v > 0 else None
    if t == "select":
        return st.selectbox(label, f["options"], key=key)
    if t == "date":
        return st.date_input(label, value=f.get("default", date.today()), key=key)
    if t == "optdate":
        use = st.checkbox(f"تحديد {label}", key=key + "_on")
        return st.date_input(label, value=date.today(), key=key, disabled=not use) if use else None
    raise ValueError(t)


def render_crud(project: dict, *, table: str, section: str, fields: list[dict],
                files: list[dict], hidden_cols: tuple = ()) -> None:
    labels = {f["key"]: f["label"] for f in fields} | {x["key"]: x["label"] for x in files}
    tab_log, tab_add = st.tabs(["السجل", "إضافة سجل جديد"])

    # ---------------- السجل ----------------
    with tab_log:
        df = db.fetch(table, project["id"])
        if df.empty:
            st.info("لا توجد سجلات بعد. أضف أول سجل من تبويب «إضافة سجل جديد».")
        else:
            q = st.text_input("بحث في السجل", placeholder="اكتب أي كلمة…", key=f"q_{table}")
            view = df
            if q:
                mask = df.astype(str).apply(lambda s: s.str.contains(q, case=False, na=False)).any(axis=1)
                view = df[mask]
            shown = view[[c for c in labels if c in view.columns and c not in hidden_cols]].copy()
            for fcol in files:  # نعرض ✔ بدل المسار الطويل
                if fcol["key"] in shown:
                    shown[fcol["key"]] = shown[fcol["key"]].map(lambda p: "✔" if p else "—")
            st.dataframe(shown.rename(columns=labels), hide_index=True)
            st.caption(f"عدد السجلات: {len(view)}")

            c1, c2 = st.columns(2)
            c1.download_button(
                "تصدير Excel", df_to_excel(shown.rename(columns=labels), section),
                file_name=f"CGES_{project.get('code') or 'project'}_{section}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            # عرض المرفقات + الحذف
            st.markdown("##### مرفقات سجل")
            ids = view["id"].tolist()
            main = fields[0]["key"]
            pick = st.selectbox(
                "اختر سجلاً", ids, key=f"pick_{table}",
                format_func=lambda i: " | ".join(
                    str(view.loc[view["id"] == i, f["key"]].iloc[0]) for f in fields[:3]))
            row = view[view["id"] == pick].iloc[0]
            has_any = False
            for fcol in files:
                path = row.get(fcol["key"])
                if path:
                    has_any = True
                    url = storage.signed_url(path)
                    if url:
                        st.link_button(f"فتح: {fcol['label']}", url)
            if not has_any:
                st.caption("لا توجد مرفقات لهذا السجل.")
            if auth.is_admin():
                if st.button("حذف هذا السجل", key=f"del_{table}"):
                    db.delete(table, pick)
                    st.rerun()

    # ---------------- إضافة ----------------
    with tab_add:
        with st.form(f"add_{table}", clear_on_submit=True):
            values = {}
            cols = st.columns(2)
            for i, f in enumerate(fields):
                with cols[i % 2]:
                    values[f["key"]] = _input(f, f"{table}_{f['key']}")
            st.markdown("**المرفقات** (الصور تُضغط تلقائياً قبل الرفع)")
            uploads = {x["key"]: st.file_uploader(x["label"], type=UPLOAD_TYPES, key=f"{table}_{x['key']}")
                       for x in files}
            submitted = st.form_submit_button("حفظ السجل", type="primary")

        if submitted:
            missing = [f["label"] for f in fields if f.get("required") and not values[f["key"]]]
            if missing:
                st.error("أكمل الحقول المطلوبة: " + "، ".join(missing))
                return
            row = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in values.items()}
            row["project_id"] = project["id"]
            for key, up in uploads.items():
                if up is not None:
                    row[key] = storage.upload_attachment(project["id"], section, up)
            try:
                db.insert(table, row)
                st.success("تم حفظ السجل.")
            except Exception as e:
                st.error(f"تعذّر الحفظ: {e}")
