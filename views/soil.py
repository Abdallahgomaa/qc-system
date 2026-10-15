"""قسم التربة — جدول ``soil_receipts`` (مطابق لـ schema.sql)."""
from __future__ import annotations

from views._common import render_section

FIELDS = [
    {"key": "company", "label": "الشركة", "type": "text", "required": True},
    {"key": "zone", "label": "الزونة", "type": "text", "required": True},
    {"key": "layer_no", "label": "رقم الطبقة", "type": "int", "required": True},
    {"key": "level_m", "label": "المنسوب (م)", "type": "optnumber", "step": 0.001, "format": "%.3f"},
    {"key": "test_date", "label": "التاريخ", "type": "date", "required": True},
    {"key": "layer_thickness_cm", "label": "سمك الطبقة (سم)", "type": "optnumber", "step": 0.5},
    {"key": "test_type", "label": "نوع الاختبار", "type": "select",
     "options": ["Dynamic", "Sand Cone", "Plate Load"], "required": True},
    {"key": "result", "label": "النتيجة", "type": "select",
     "options": ["ناجح", "ساقط"], "required": True},
    {"key": "notes", "label": "ملاحظات", "type": "textarea"},
]

FILES = [
    {"key": "report_path", "label": "تقرير الاختبار"},
]


def render(project: dict) -> None:
    render_section(
        project, table="soil_receipts", section="soil",
        title="قسم التربة", fields=FIELDS, files=FILES,
        subtitle=f"المشروع النشط: {project.get('name', '')}",
    )
