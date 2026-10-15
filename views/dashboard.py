"""لوحة المؤشرات — ملخّص المشروع النشط مع تنبيهات (FR-9)."""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core import alerts, notify, records, report, ui
from views._common import show_flash

try:  # الرسوم ميزة إضافية: إن لم تتوفر plotly نُكمل بلا رسوم
    import plotly.express as px
except Exception:  # noqa: BLE001
    px = None


def _load(table: str, project_id: str):
    """يحمّل جدولاً ويعيد (DataFrame, رسالة خطأ أو None)."""
    try:
        return records.fetch_records(table, project_id), None
    except Exception as e:  # noqa: BLE001
        return pd.DataFrame(), str(e)


def _num(series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def render(project: dict) -> None:
    if not project or not project.get("id"):
        st.warning("لا يوجد مشروع نشط. اختر مشروعاً من القائمة الجانبية.")
        return

    ui.page_header("لوحة المؤشرات", f"المشروع النشط: {project.get('name', '')}")
    show_flash()

    concrete, err_c = _load("concrete_pours", project["id"])
    soil, err_s = _load("soil_receipts", project["id"])
    materials, err_m = _load("material_tests", project["id"])
    calib, err_k = _load("station_calibrations", project["id"])
    for err in (err_c, err_s, err_m, err_k):
        if err:
            st.warning(err)

    total_volume = float(_num(concrete.get("volume_m3", pd.Series(dtype=float))).sum()) if not concrete.empty else 0.0
    soil_pass = 0.0
    if not soil.empty and "result" in soil:
        soil_pass = round((soil["result"] == "ناجح").mean() * 100, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي الخرسانة (م³)", f"{total_volume:,.1f}")
    c2.metric("اختبارات التربة", f"{len(soil)}")
    c3.metric("نسبة نجاح التربة", f"{soil_pass}%")
    c4.metric("سجلات المواد", f"{len(materials)}")

    alert_items = alerts.build_alerts(concrete=concrete, soil=soil,
                                      materials=materials, calibrations=calib)
    _render_alerts(alert_items)
    _render_notify(project, alert_items)
    _render_charts(concrete, soil)
    _render_report(project, {"concrete_pours": concrete, "soil_receipts": soil,
                             "material_tests": materials,
                             "station_calibrations": calib}, alert_items)


def _render_alerts(items: list[dict]) -> None:
    st.markdown("##### التنبيهات")
    if not items:
        st.success("لا توجد تنبيهات حالياً لهذا المشروع.")
        return
    for item in items:
        ui.alert_box(item["level"], item["text"])


def _render_notify(project: dict, items: list[dict]) -> None:
    """إشعارات التنبيهات الحرجة: بريد (SMTP) + واتساب (رابط جاهز) — البند 4.2."""
    if not items:
        return
    st.markdown("##### إشعارات التنبيهات")
    critical = notify.critical_alerts(items)
    if critical:
        st.caption(f"يوجد {len(critical)} تنبيه حرج — يمكن إبلاغ المسؤول فوراً.")
    else:
        st.caption("لا توجد تنبيهات حرجة، لكن يمكن مشاركة التنبيهات الحالية.")

    left, right = st.columns(2)
    with left:
        if notify.email_configured():
            if st.button("إرسال التنبيهات بالبريد", key="notify_email", type="primary"):
                try:
                    ok, message = notify.send_alerts_email(project, items)
                except Exception as e:  # noqa: BLE001
                    ok, message = False, f"تعذّر إرسال البريد: {e}"
                (st.success if ok else st.error)(message)
        else:
            st.info("لتفعيل إرسال البريد أضف قسم «[smtp]» في «.streamlit/secrets.toml» "
                    "(host / port / user / password / sender / recipients).")
    with right:
        st.link_button("مشاركة التنبيهات على واتساب",
                       notify.alerts_whatsapp_link(project, items))


def _render_report(project: dict, tables: dict, alert_items: list[dict]) -> None:
    """تقرير المشروع القابل للطباعة/الحفظ كـ PDF (البند 4.1)."""
    st.markdown("##### تقرير المشروع")
    st.caption("يُنتَج مستند HTML مصمَّم للطباعة (A4). افتحه ثم Ctrl+P ▸ «حفظ كـ PDF» للحصول على تقرير عربي كامل.")
    months = report.month_options(tables)
    options = ["كل الفترات"] + [report.month_label(m) for m in months]
    choice = st.selectbox("الفترة المطلوبة", options, key="report_month")
    idx = options.index(choice)
    month = months[idx - 1] if idx > 0 else None
    try:
        html_doc = report.build_report(project, tables, alert_items, month=month)
    except Exception as e:  # noqa: BLE001
        st.error(f"تعذّر تجهيز التقرير: {e}")
        return
    st.download_button(
        "تنزيل التقرير (HTML قابل للطباعة كـ PDF)",
        html_doc.encode("utf-8"),
        file_name=report.suggested_filename(project, month),
        mime="text/html",
        key="report_dl",
    )
    with st.expander("معاينة التقرير"):
        # ``st.iframe`` هي البديل الحديث لـ ``st.components.v1.html`` المهجورة.
        if hasattr(st, "iframe"):
            st.iframe(html_doc, height=620, alt="معاينة تقرير المشروع")
        else:  # احتياط لإصدارات Streamlit الأقدم من 1.66
            components.html(html_doc, height=620, scrolling=True)


def _render_charts(concrete, soil) -> None:
    if px is None:
        return
    if not concrete.empty and "pour_date" in concrete and "volume_m3" in concrete:
        df = concrete.copy()
        df["الشهر"] = pd.to_datetime(df["pour_date"], errors="coerce").dt.to_period("M").astype(str)
        df["الكمية"] = _num(df["volume_m3"])
        monthly = df.groupby("الشهر", as_index=False)["الكمية"].sum()
        fig = px.bar(monthly, x="الشهر", y="الكمية", title="كميات الخرسانة الشهرية (م³)")
        st.plotly_chart(fig, width="stretch")

    if not soil.empty and "result" in soil:
        counts = soil["result"].value_counts().rename_axis("النتيجة").reset_index(name="العدد")
        fig = px.pie(counts, names="النتيجة", values="العدد", title="نتائج اختبارات التربة")
        st.plotly_chart(fig, width="stretch")
