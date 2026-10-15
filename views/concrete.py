"""قسم الخرسانة — جدول ``concrete_pours`` (مطابق لـ schema.sql)."""
from __future__ import annotations

from views._common import render_section

FIELDS = [
    {"key": "station_name", "label": "اسم المحطة", "type": "text", "required": True},
    {"key": "element", "label": "العنصر", "type": "text", "required": True},
    {"key": "pour_date", "label": "تاريخ الصب", "type": "date", "required": True},
    {"key": "cubes_count", "label": "عدد المكعبات", "type": "int", "required": True},
    {"key": "volume_m3", "label": "الكمية (م³)", "type": "number", "required": True, "step": 0.5},
    {"key": "design_strength_mpa", "label": "الإجهاد التصميمي (MPa)", "type": "optnumber", "step": 0.5},
    {"key": "result_7d_mpa", "label": "نتيجة 7 أيام (MPa)", "type": "optnumber", "step": 0.5},
    {"key": "result_28d_mpa", "label": "نتيجة 28 يوم (MPa)", "type": "optnumber", "step": 0.5},
    {"key": "notes", "label": "ملاحظات", "type": "textarea"},
]

FILES = [
    {"key": "report_7d_path", "label": "تقرير 7 أيام"},
    {"key": "report_28d_path", "label": "تقرير 28 يوم"},
]


def render(project: dict) -> None:
    render_section(
        project, table="concrete_pours", section="concrete",
        title="قسم الخرسانة", fields=FIELDS, files=FILES,
        subtitle=f"المشروع النشط: {project.get('name', '')}",
    )
