"""قسم المواد والاختبارات الدورية — جدول ``material_tests`` (مطابق لـ schema.sql)."""
from __future__ import annotations

from views._common import render_section

FIELDS = [
    {"key": "material_type", "label": "نوع المادة", "type": "select", "required": True,
     "options": ["ممبرين", "حديد", "طوب", "أسمنت", "ركام", "أخرى"]},
    {"key": "supplier", "label": "المورّد", "type": "text"},
    {"key": "test_name", "label": "اسم الاختبار", "type": "text", "required": True},
    {"key": "test_date", "label": "تاريخ الاختبار", "type": "date", "required": True},
    {"key": "next_test_date", "label": "موعد الاختبار الدوري القادم", "type": "optdate"},
    {"key": "result", "label": "النتيجة", "type": "select", "required": True,
     "options": ["مطابق", "غير مطابق", "قيد الفحص"], "default": "قيد الفحص"},
    {"key": "notes", "label": "ملاحظات", "type": "textarea"},
]

FILES = [
    {"key": "report_path", "label": "تقرير الاختبار"},
]


def render(project: dict) -> None:
    render_section(
        project, table="material_tests", section="materials",
        title="المواد والاختبارات الدورية", fields=FIELDS, files=FILES,
        subtitle=f"المشروع النشط: {project.get('name', '')}",
    )
