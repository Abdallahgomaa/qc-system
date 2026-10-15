"""قواعد التنبيه الذكية (FR-9) — وحدة مستقلة قابلة للاختبار.

تُجمّع منطق التنبيهات خارج الواجهة، فتستدعيها لوحة المؤشرات (وأي شاشة أخرى)
وتُختبر آلياً بسهولة. كل الدوال تتقبّل DataFrames فارغة أو ناقصة الأعمدة بأمان.

مستويات التنبيه: ``bad`` (حرج) و``warn`` (تنبيه) و``ok`` (سليم) وتطابق ألوان
``core.ui.alert_box``.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

# ---- عتبات قابلة للضبط (FR-9) ----
EXPIRY_WARN_DAYS = 30      # معايرة تنتهي خلال هذه المدة => تنبيه
PERIODIC_WARN_DAYS = 14    # اختبار دوري يستحق خلال هذه المدة => تنبيه
SEVEN_DAYS = 7
TWENTY_EIGHT_DAYS = 28


def _num(df: pd.DataFrame, column: str) -> pd.Series:
    """يعيد عموداً رقمياً متوافقاً مع فهرس ``df``، أو سلسلة كلها NaN إن غاب."""
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce")
    return pd.Series(float("nan"), index=df.index, dtype="float64")


def _dates(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return pd.to_datetime(df[column], errors="coerce")
    return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")


def build_alerts(concrete: pd.DataFrame | None = None,
                 soil: pd.DataFrame | None = None,
                 materials: pd.DataFrame | None = None,
                 calibrations: pd.DataFrame | None = None,
                 *, today: date | None = None) -> list[dict]:
    """يبني قائمة التنبيهات للمشروع.

    كل عنصر: ``{"level": "bad"|"warn", "text": str}``. القائمة الفارغة تعني سليم.
    """
    concrete = concrete if concrete is not None else pd.DataFrame()
    soil = soil if soil is not None else pd.DataFrame()
    materials = materials if materials is not None else pd.DataFrame()
    calibrations = calibrations if calibrations is not None else pd.DataFrame()
    now = pd.Timestamp(today or date.today())

    alerts: list[dict] = []

    def add(level: str, text: str) -> None:
        alerts.append({"level": level, "text": text})

    # ---- الخرسانة ----
    if not concrete.empty:
        design = _num(concrete, "design_strength_mpa")
        r28 = _num(concrete, "result_28d_mpa")
        r7 = _num(concrete, "result_7d_mpa")

        bad = int((r28.notna() & design.notna() & (r28 < design)).sum())
        if bad:
            add("bad", f"{bad} صبّة بنتيجة 28 يوم أقل من الإجهاد التصميمي.")

        age = (now - _dates(concrete, "pour_date")).dt.days
        miss7 = int(((age >= SEVEN_DAYS) & r7.isna()).sum())
        miss28 = int(((age >= TWENTY_EIGHT_DAYS) & r28.isna()).sum())
        if miss7:
            add("warn", f"{miss7} صبّة مضى عليها {SEVEN_DAYS} أيام دون تسجيل نتيجة 7 أيام.")
        if miss28:
            add("warn", f"{miss28} صبّة مضى عليها {TWENTY_EIGHT_DAYS} يوماً دون تسجيل نتيجة 28 يوم.")

    # ---- التربة ----
    if not soil.empty and "result" in soil.columns:
        failed = int((soil["result"] == "ساقط").sum())
        if failed:
            add("bad", f"{failed} اختبار تربة «ساقط».")

    # ---- المواد والاختبارات الدورية ----
    if not materials.empty:
        if "result" in materials.columns:
            nonconforming = int((materials["result"] == "غير مطابق").sum())
            if nonconforming:
                add("bad", f"{nonconforming} مادة «غير مطابقة».")
        if "next_test_date" in materials.columns:
            nxt = _dates(materials, "next_test_date")
            late = int((nxt < now).sum())
            due = int(((nxt >= now) & (nxt <= now + pd.Timedelta(days=PERIODIC_WARN_DAYS))).sum())
            if late:
                add("warn", f"{late} اختبار دوري متأخر.")
            if due:
                add("warn", f"{due} اختبار دوري خلال {PERIODIC_WARN_DAYS} يوماً.")

    # ---- المعايرة ----
    if not calibrations.empty and "valid_until" in calibrations.columns:
        valid = _dates(calibrations, "valid_until")
        expired = int((valid < now).sum())
        soon = int(((valid >= now) & (valid <= now + pd.Timedelta(days=EXPIRY_WARN_DAYS))).sum())
        if expired:
            add("bad", f"{expired} معايرة منتهية الصلاحية.")
        if soon:
            add("warn", f"{soon} معايرة تنتهي خلال {EXPIRY_WARN_DAYS} يوماً.")

    return alerts
