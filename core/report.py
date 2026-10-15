"""تقرير المشروع (البند 4.1) — يُنتج مستند HTML عربي RTL مكتفياً بذاته.

لماذا HTML وليس PDF مباشرة؟ لا توجد مكتبة توليد PDF عربية مثبَّتة في البيئة، فبدل
إضافة اعتماديات ثقيلة (مثل fpdf2 + arabic_reshaper + python-bidi) نُنتج مستند HTML
مصمّماً للطباعة بمقاس A4، فيفتحه المستخدم ثم يختار «طباعة ▸ حفظ كـ PDF» من المتصفح،
فتكون النتيجة ملف PDF عربي سليم بالكامل. هذا يعمل على أي جهاز ومن أي متصفح.

تُبنى البيانات من نفس طبقة ``core.records``، والتنبيهات من ``core.alerts``، فلا
تكرار لمنطق العمل.
"""
from __future__ import annotations

import html
from datetime import date

import pandas as pd

from core import config

MONTHS_AR = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

# مواصفات كل قسم: (اسم الجدول، العنوان، عمود التاريخ، [(المفتاح، التسمية), ...])
TABLE_SPECS: list[tuple[str, str, str, list[tuple[str, str]]]] = [
    ("concrete_pours", "الخرسانة", "pour_date", [
        ("pour_date", "التاريخ"), ("station_name", "المحطة"), ("element", "العنصر"),
        ("cubes_count", "عدد المكعبات"), ("volume_m3", "الكمية (م³)"),
        ("design_strength_mpa", "تصميمي (MPa)"), ("result_7d_mpa", "7 أيام (MPa)"),
        ("result_28d_mpa", "28 يوم (MPa)"), ("notes", "ملاحظات"),
    ]),
    ("soil_receipts", "التربة", "test_date", [
        ("test_date", "التاريخ"), ("company", "الشركة"), ("zone", "المنطقة"),
        ("layer_no", "رقم الطبقة"), ("level_m", "المنسوب (م)"),
        ("layer_thickness_cm", "السماكة (سم)"), ("test_type", "نوع الاختبار"),
        ("result", "النتيجة"), ("notes", "ملاحظات"),
    ]),
    ("material_tests", "المواد والاختبارات الدورية", "test_date", [
        ("test_date", "التاريخ"), ("material_type", "نوع المادة"), ("supplier", "المورد"),
        ("test_name", "الاختبار"), ("result", "النتيجة"),
        ("next_test_date", "الاختبار القادم"), ("notes", "ملاحظات"),
    ]),
    ("station_calibrations", "معايرة المحطات", "last_calibration_date", [
        ("station_name", "المحطة"), ("equipment_type", "نوع الجهاز"),
        ("serial_no", "الرقم التسلسلي"), ("last_calibration_date", "تاريخ المعايرة"),
        ("valid_until", "صالحة حتى"), ("notes", "ملاحظات"),
    ]),
]

_BADGE = {
    "ناجح": "ok", "مطابق": "ok",
    "ساقط": "bad", "غير مطابق": "bad",
    "قيد الفحص": "warn",
}

_CSS = """
*{box-sizing:border-box;}
body{font-family:'Segoe UI','Tahoma','Arial',sans-serif;direction:rtl;margin:0;
  padding:28px;color:#14263D;background:#fff;font-size:12.5px;}
h1,h2,h3{margin:0;}
.head{display:flex;justify-content:space-between;align-items:flex-start;
  border-bottom:3px solid #0F2540;padding-bottom:12px;margin-bottom:18px;}
.brand{font-size:17px;font-weight:700;color:#0F2540;}
.brand small{display:block;font-size:10.5px;color:#5B6B7C;font-weight:400;margin-top:2px;}
.head .meta{text-align:left;font-size:11px;color:#5B6B7C;line-height:1.7;}
h2.title{font-size:16px;margin:16px 0 8px;color:#0F2540;border-right:5px solid #B88A2E;
  padding-right:8px;}
h3.sec{font-size:13.5px;margin:18px 0 6px;color:#0F2540;}
.cards{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 4px;}
.card{flex:1 1 130px;border:1px solid #D9DFE7;border-radius:6px;padding:8px 10px;background:#F8FAFC;}
.card .k{font-size:10.5px;color:#5B6B7C;}
.card .v{font-size:16px;font-weight:700;color:#0F2540;margin-top:2px;}
table{width:100%;border-collapse:collapse;margin:6px 0 10px;font-size:11.5px;}
th{background:#0F2540;color:#fff;padding:6px 7px;text-align:right;border:1px solid #0F2540;
  font-weight:600;}
td{padding:5px 7px;border:1px solid #D9DFE7;text-align:right;vertical-align:top;}
tr:nth-child(even) td{background:#F2F5F9;}
.empty{color:#5B6B7C;font-style:italic;margin:4px 0 10px;}
.badge{padding:1px 7px;border-radius:10px;font-size:10.5px;font-weight:600;display:inline-block;}
.badge.ok{background:#E4F4EC;color:#1F8A5B;}
.badge.bad{background:#FBE6E3;color:#C0392B;}
.badge.warn{background:#FBF1DC;color:#B7740B;}
.alert{border-right:5px solid #B88A2E;background:#F8FAFC;padding:7px 10px;margin:5px 0;
  border-radius:4px;}
.alert.bad{border-color:#C0392B;background:#FDF2F1;}
.alert.warn{border-color:#B7740B;background:#FDF8EE;}
.alert.ok{border-color:#1F8A5B;background:#F1FAF5;}
.foot{margin-top:22px;border-top:1px solid #D9DFE7;padding-top:8px;font-size:10.5px;color:#5B6B7C;
  display:flex;justify-content:space-between;}
@page{size:A4;margin:14mm;}
@media print{body{padding:0;font-size:11px;} h3.sec{page-break-after:avoid;}
  table{page-break-inside:auto;} tr{page-break-inside:avoid;} .cards{page-break-inside:avoid;}}
"""


# ---------------------------------------------------------------------------
# أدوات مساعدة
# ---------------------------------------------------------------------------
def _num(series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _esc(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("nan", "nat", "none") else html.escape(text)


def _cell(key: str, value) -> str:
    """يُنسّق قيمة خلية واحدة (شارة ملوّنة للنتائج، وحذف الكسور الصفرية)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    text = str(value).strip()
    if text.lower() in ("nan", "nat", "none", ""):
        return "—"
    if key == "result" and text in _BADGE:
        return f'<span class="badge {_BADGE[text]}">{html.escape(text)}</span>'
    if isinstance(value, float) and value.is_integer():
        return html.escape(str(int(value)))
    return html.escape(text)


def month_options(tables: dict[str, pd.DataFrame]) -> list[str]:
    """يعيد قائمة الأشهر (YYYY-MM) المتوفّرة في البيانات، الأحدث أولاً."""
    months: set[str] = set()
    for table, (_, _, datecol, _) in zip(tables, TABLE_SPECS):
        df = tables.get(table)
        if df is None or df.empty or datecol not in df.columns:
            continue
        parsed = pd.to_datetime(df[datecol], errors="coerce").dropna()
        months.update(parsed.dt.strftime("%Y-%m").tolist())
    return sorted(months, reverse=True)


def month_label(month: str) -> str:
    try:
        year, mon = month.split("-")
        return f"{MONTHS_AR[int(mon) - 1]} {year}"
    except Exception:  # noqa: BLE001
        return month


def _filter_month(df: pd.DataFrame, datecol: str, month: str | None) -> pd.DataFrame:
    if df is None or df.empty or not month or datecol not in df.columns:
        return df if df is not None else pd.DataFrame()
    parsed = pd.to_datetime(df[datecol], errors="coerce")
    return df[parsed.dt.strftime("%Y-%m") == month]


# ---------------------------------------------------------------------------
# بناء التقرير
# ---------------------------------------------------------------------------
def _kpi_cards(tables: dict[str, pd.DataFrame], alerts: list[dict]) -> str:
    concrete = tables.get("concrete_pours", pd.DataFrame())
    soil = tables.get("soil_receipts", pd.DataFrame())
    materials = tables.get("material_tests", pd.DataFrame())
    calib = tables.get("station_calibrations", pd.DataFrame())

    volume = float(_num(concrete.get("volume_m3", pd.Series(dtype=float))).sum()) if not concrete.empty else 0.0
    design = _num(concrete.get("design_strength_mpa", pd.Series(dtype=float)))
    r28 = _num(concrete.get("result_28d_mpa", pd.Series(dtype=float)))
    mask = design.notna() & r28.notna() & (design > 0)
    conform = int((r28[mask] / design[mask] >= 1).sum()) if mask.any() else 0
    avg28 = float(r28.mean()) if r28.notna().any() else 0.0

    soil_pass = float((soil["result"] == "ناجح").mean() * 100) if (
        not soil.empty and "result" in soil.columns) else None
    mat_conf = float((materials["result"] == "مطابق").mean() * 100) if (
        not materials.empty and "result" in materials.columns) else None
    expired = 0
    if not calib.empty and "valid_until" in calib.columns:
        valid = pd.to_datetime(calib["valid_until"], errors="coerce")
        expired = int((valid < pd.Timestamp(date.today())).sum())

    cards = [
        ("إجمالي الخرسانة (م³)", f"{volume:,.1f}"),
        ("عدد صبّات الخرسانة", f"{len(concrete)}"),
        ("متوسط مقاومة 28 يوم (MPa)", f"{avg28:,.1f}" if avg28 else "—"),
        ("صبّات مستوفية (28 ≥ تصميمي)", f"{conform}/{int(mask.sum())}" if mask.any() else "—"),
        ("اختبارات التربة", f"{len(soil)}"),
        ("نسبة نجاح التربة", f"{soil_pass:.1f}%" if soil_pass is not None else "—"),
        ("سجلات المواد", f"{len(materials)}"),
        ("نسبة مطابقة المواد", f"{mat_conf:.1f}%" if mat_conf is not None else "—"),
        ("معايرات منتهية", f"{expired}"),
        ("عدد التنبيهات", f"{len(alerts)}"),
    ]
    inner = "".join(
        f'<div class="card"><div class="k">{html.escape(k)}</div><div class="v">{v}</div></div>'
        for k, v in cards
    )
    return f'<div class="cards">{inner}</div>'


def _alerts_html(alerts: list[dict]) -> str:
    if not alerts:
        return '<div class="alert ok">لا توجد تنبيهات — جميع المؤشرات سليمة.</div>'
    return "".join(
        f'<div class="alert {html.escape(str(a.get("level", "warn")))}">'
        f'{html.escape(str(a.get("text", "")))}</div>'
        for a in alerts
    )


def _table_html(title: str, df: pd.DataFrame, columns: list[tuple[str, str]]) -> str:
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    if df is None or df.empty:
        return f'<h3 class="sec">{html.escape(title)}</h3><p class="empty">لا توجد سجلات في هذه الفترة.</p>'
    body = []
    for _, row in df.iterrows():
        cells = "".join(f"<td>{_cell(key, row.get(key))}</td>" for key, _ in columns)
        body.append(f"<tr>{cells}</tr>")
    return (
        f'<h3 class="sec">{html.escape(title)} <span class="empty">({len(df)} سجل)</span></h3>'
        f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"
    )


def build_report(project: dict, tables: dict[str, pd.DataFrame], alerts: list[dict],
                 *, month: str | None = None) -> str:
    """يبني مستند HTML كاملاً لتقرير المشروع.

    project: صف المشروع. tables: قاموس «اسم الجدول -> DataFrame». alerts: قائمة
    ``core.alerts.build_alerts``. month: ``YYYY-MM`` لتصفية السجلات، أو None للكل.
    """
    generated = date.today().strftime("%Y-%m-%d")
    period = month_label(month) if month else "جميع الفترات"
    filtered = {
        table: _filter_month(tables.get(table, pd.DataFrame()), datecol, month)
        for table, _, datecol, _ in TABLE_SPECS
    }

    sections = "".join(
        _table_html(title, filtered[table], columns)
        for table, title, _datecol, columns in TABLE_SPECS
    )

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>تقرير {_esc(project.get('name'))} — {html.escape(period)}</title>
<style>{_CSS}</style>
</head>
<body>
  <div class="head">
    <div class="brand">{config.APP_NAME_AR}<small>{config.APP_NAME_EN} — {config.APP_SYSTEM_TITLE}</small></div>
    <div class="meta">
      تاريخ الإصدار: {generated}<br>
      الفترة: {html.escape(period)}
    </div>
  </div>

  <h2 class="title">تقرير ضبط الجودة — {_esc(project.get('name'))}</h2>
  <div class="meta">
    الكود: {_esc(project.get('code'))} &nbsp;|&nbsp; العميل: {_esc(project.get('client'))}
    &nbsp;|&nbsp; الموقع: {_esc(project.get('location'))}
  </div>

  <h3 class="sec">الملخّص التنفيذي</h3>
  {_kpi_cards(filtered, alerts)}

  <h3 class="sec">التنبيهات</h3>
  {_alerts_html(alerts)}

  <h2 class="title">سجلات الجودة</h2>
  {sections}

  <div class="foot">
    <span>{config.APP_SHORT} — تقرير مُولَّد آلياً من النظام</span>
    <span>للطباعة كـ PDF: Ctrl+P ثم «حفظ كـ PDF»</span>
  </div>
</body>
</html>"""


def suggested_filename(project: dict, month: str | None) -> str:
    code = str(project.get("code") or "report").replace(" ", "_")
    return f"CGES_{code}_{month or 'all'}.html"
