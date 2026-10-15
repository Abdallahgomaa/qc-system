"""قسم معايرة المحطات — جدول ``station_calibrations`` (مطابق لـ schema.sql)."""
from __future__ import annotations

from views._common import render_section

FIELDS = [
    {"key": "station_name", "label": "المحطة", "type": "text", "required": True},
    {"key": "equipment_type", "label": "نوع الجهاز", "type": "text", "required": True},
    {"key": "serial_no", "label": "الرقم المسلسل", "type": "text"},
    {"key": "last_calibration_date", "label": "تاريخ آخر معايرة", "type": "date", "required": True},
    {"key": "valid_until", "label": "صالحة حتى", "type": "date", "required": True},
    {"key": "notes", "label": "ملاحظات", "type": "textarea"},
]

FILES = [
    {"key": "certificate_path", "label": "شهادة المعايرة"},
]


def render(project: dict) -> None:
    render_section(
        project, table="station_calibrations", section="calibration",
        title="قسم معايرة المحطات", fields=FIELDS, files=FILES,
        subtitle=f"المشروع النشط: {project.get('name', '')}",
    )
