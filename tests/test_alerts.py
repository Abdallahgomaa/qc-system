"""اختبارات قواعد التنبيه (البند 3.8).

تعمل بطريقتين:
- مع pytest:  ``pytest tests/test_alerts.py``
- بلا تثبيت أي حزمة:  ``python tests/test_alerts.py``
"""
from __future__ import annotations

import os
import sys
from datetime import date

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.alerts import build_alerts  # noqa: E402

TODAY = date(2026, 3, 1)


def test_empty_returns_no_alerts():
    assert build_alerts() == []


def test_concrete_below_design_is_critical():
    df = pd.DataFrame([{"design_strength_mpa": 30, "result_28d_mpa": 25,
                        "result_7d_mpa": 20, "pour_date": date(2025, 12, 1)}])
    levels = [a["level"] for a in build_alerts(concrete=df, today=TODAY)]
    assert "bad" in levels


def test_missing_28d_is_warning():
    df = pd.DataFrame([{"design_strength_mpa": 30, "result_28d_mpa": None,
                        "result_7d_mpa": 20, "pour_date": date(2025, 12, 1)}])
    items = build_alerts(concrete=df, today=TODAY)
    assert any(a["level"] == "warn" and "28" in a["text"] for a in items)


def test_soil_failing_is_critical():
    df = pd.DataFrame([{"result": "ساقط"}])
    assert any(a["level"] == "bad" for a in build_alerts(soil=df, today=TODAY))


def test_material_nonconforming_is_critical():
    df = pd.DataFrame([{"result": "غير مطابق"}])
    assert any(a["level"] == "bad" for a in build_alerts(materials=df, today=TODAY))


def test_calibration_expired_and_soon():
    df = pd.DataFrame([{"valid_until": date(2026, 1, 1)},
                       {"valid_until": date(2026, 3, 10)}])
    items = build_alerts(calibrations=df, today=TODAY)
    assert any(a["level"] == "bad" for a in items)   # منتهية الصلاحية
    assert any(a["level"] == "warn" for a in items)  # تنتهي خلال 30 يوماً


def test_periodic_test_late_is_warning():
    df = pd.DataFrame([{"result": "مطابق", "next_test_date": date(2026, 2, 1)}])
    assert any(a["level"] == "warn" for a in build_alerts(materials=df, today=TODAY))


def test_healthy_data_no_alerts():
    concrete = pd.DataFrame([{"design_strength_mpa": 30, "result_28d_mpa": 35,
                              "result_7d_mpa": 22, "pour_date": date(2026, 2, 20)}])
    soil = pd.DataFrame([{"result": "ناجح"}])
    materials = pd.DataFrame([{"result": "مطابق", "next_test_date": date(2026, 6, 1)}])
    calibrations = pd.DataFrame([{"valid_until": date(2026, 12, 1)}])
    assert build_alerts(concrete, soil, materials, calibrations, today=TODAY) == []


if __name__ == "__main__":
    tests = [fn for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:  # noqa: PERF203
            failures += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"--- {len(tests) - failures}/{len(tests)} passed ---")
    sys.exit(1 if failures else 0)
