"""تثبيت التطبيق والعمل بدون اتصال (البندان أ و ب من مرحلة الأوفلاين/PWA).

يُحقَن الكود عبر ``st.html`` (نفس أسلوب ``core/auth.py``) لأن محتوى ``st.html``
يعمل في أصل التطبيق نفسه — وهو شرط تسجيل ``Service Worker`` وكتابة
``localStorage``، بخلاف ``st.components.v1.html`` الذي يعمل داخل iframe.

كل الدوال تعمل بصمت عند أي خطأ: هذه ميزة إضافية لا يجوز أن تُسقط التطبيق.
"""
from __future__ import annotations

import datetime as _dt
import json

import streamlit as st

SNAPSHOT_KEY = "cges_snapshot_v1"
MANIFEST = "/app/static/manifest.webmanifest"
SW = "/app/static/sw.js"
OFFLINE_PAGE = "/app/static/offline.html"
THEME_COLOR = "#0F2540"

_MAX_ROWS = 300     # حد أقصى لكل جدول في اللقطة (حجم localStorage محدود)
_MAX_CELL = 60      # اقتطاع الخلايا الطويلة


def _inject_html(markup: str) -> None:
    """يحقن HTML/JS في أصل التطبيق (بصمت عند الفشل)."""
    try:
        if hasattr(st, "html"):
            st.html(markup, unsafe_allow_javascript=True)
        else:  # توافق مع إصدارات Streamlit الأقدم من 1.33
            from streamlit.components.v1 import html as _legacy
            _legacy(markup, height=0)
    except Exception:  # noqa: BLE001 - ميزة إضافية لا تُسقط التطبيق
        pass


_JS = r"""
(function () {
  var head = document.head;
  function add(tag, name, attrs) {
    if (document.getElementById(name)) { return; }
    var el = document.createElement(tag);
    for (var k in attrs) { el.setAttribute(k, attrs[k]); }
    el.id = name;
    el.setAttribute("data-cges", "1");
    head.appendChild(el);
  }
  add("link", "cges-manifest", { rel: "manifest", href: "__MANIFEST__" });
  add("link", "cges-icon", { rel: "icon", type: "image/png", href: "/app/static/icon-192.png" });
  add("link", "cges-apple-icon", { rel: "apple-touch-icon", href: "/app/static/icon-192.png" });
  add("meta", "cges-theme-color", { name: "theme-color", content: "__THEME__" });
  add("meta", "cges-mobile-capable", { name: "mobile-web-app-capable", content: "yes" });
  add("meta", "cges-apple-capable", { name: "apple-mobile-web-app-capable", content: "yes" });
  add("meta", "cges-apple-title", { name: "apple-mobile-web-app-title", content: "CGES" });

  if ("serviceWorker" in navigator && !window.__cgesSW) {
    window.__cgesSW = true;
    navigator.serviceWorker.register("__SW__").catch(function () {});
  }

  function bar() {
    var el = document.getElementById("cges-offline-bar");
    if (navigator.onLine) { if (el && el.parentNode) { el.parentNode.removeChild(el); } return; }
    if (el) { return; }
    var bar = document.createElement("div");
    bar.id = "cges-offline-bar";
    bar.dir = "rtl";
    bar.style.position = "fixed";
    bar.style.top = "0";
    bar.style.right = "0";
    bar.style.left = "0";
    bar.style.zIndex = "99999";
    bar.style.background = "#B7740B";
    bar.style.color = "#fff";
    bar.style.font = "600 14px sans-serif";
    bar.style.padding = "9px 14px";
    bar.style.textAlign = "center";
    bar.style.boxShadow = "0 2px 10px rgba(0,0,0,.25)";
    bar.appendChild(document.createTextNode("لا يوجد اتصال بالإنترنت — ما يظهر أمامك آخر بيانات محمّلة. "));
    var link = document.createElement("a");
    link.setAttribute("href", "__OFFLINE__");
    link.style.color = "#fff";
    link.style.textDecoration = "underline";
    link.appendChild(document.createTextNode("\u0627\u0644\u0646\u0633\u062e\u0629 \u0627\u0644\u0645\u062d\u0641\u0648\u0638\u0629"));
    bar.appendChild(link);
    document.body.appendChild(bar);
  }
  if (!window.__cgesNet) {
    window.__cgesNet = true;
    window.addEventListener("online", bar);
    window.addEventListener("offline", bar);
  }
  bar();
})();
"""


def inject() -> None:
    """يضيف وسوم التثبيت ويسجّل Service Worker وشريط «لا يوجد اتصال» (البند أ)."""
    js = (_JS.replace("__MANIFEST__", MANIFEST)
             .replace("__SW__", SW)
             .replace("__OFFLINE__", OFFLINE_PAGE)
             .replace("__THEME__", THEME_COLOR))
    _inject_html("<script>" + js + "</script>")


def _row_cells(row, columns: list, keys: list | None = None) -> list:
    """يحوّل صفاً (قاموس بمفاتيح ``keys`` أو قائمة قيم) إلى قائمة نصية مقتطعة."""
    if isinstance(row, dict):
        src = [row.get(k) for k in (keys or columns)]
    elif isinstance(row, (list, tuple)):
        src = list(row)
    else:
        src = [row]
    return [("" if v is None else str(v))[:_MAX_CELL] for v in src]


def save_snapshot(*, project: str, metrics: list | None = None,
                  alerts: list | None = None, sections: list | None = None) -> None:
    """يحفظ آخر بيانات قرأها المستخدم في ``localStorage`` (البند ب).

    ``sections`` = قائمة عناصر بالشكل ``{"name": str, "columns": [str], "rows": [dict]}``
    وتُقتطع الصفوف والخلايا حتى لا يتضخّم التخزين المحلي.
    """
    payload = {
        "ts": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "project": str(project or "")[:80],
        "metrics": [
            {"label": str(m.get("label", ""))[:_MAX_CELL],
             "value": str(m.get("value", ""))[:_MAX_CELL]}
            for m in (metrics or [])
        ],
        "alerts": [
            {"level": str(a.get("level", "warn")),
             "text": str(a.get("text", ""))[:300]}
            for a in (alerts or [])
        ],
        "sections": [
            {"name": str(s.get("name", ""))[:80],
             "columns": [str(c)[:_MAX_CELL] for c in (s.get("columns") or [])],
             "rows": [_row_cells(r, s.get("columns") or [], s.get("keys"))
                      for r in (s.get("rows") or [])[:_MAX_ROWS]]}
            for s in (sections or [])
        ],
    }
    try:
        blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
        literal = json.dumps(blob)  # نص جاهز للإدراج كقيمة JS
    except Exception:  # noqa: BLE001
        return
    _inject_html(
        "<script>try{localStorage.setItem(%s,%s);}catch(e){}</script>"
        % (json.dumps(SNAPSHOT_KEY), literal)
    )


# ---------------------------------------------------------------------------
# مخطط الحقول والطابور المحلي (البند ج — الوضع الميداني)
# ---------------------------------------------------------------------------
SCHEMA_KEY = "cges_schema_v1"
QUEUE_KEY = "cges_queue_v1"


def run_js(js: str) -> None:
    """ينفّذ جافاسكربت صغيراً في المتصفح (بصمت عند الفشل)."""
    _inject_html("<script>try{%s}catch(e){}</script>" % js)


def save_schema(schema: dict) -> None:
    """يحفظ مخطط حقول الوضع الميداني في المتصفح لتعمل صفحة الإدخال بدون اتصال."""
    try:
        blob = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
        literal = json.dumps(blob)
    except Exception:  # noqa: BLE001
        return
    run_js("localStorage.setItem(%s,%s);" % (json.dumps(SCHEMA_KEY), literal))


def clear_queue() -> None:
    """يفرّغ طابور الوضع الميداني المحلي بعد نجاح المزامنة."""
    run_js("localStorage.removeItem(%s);" % json.dumps(QUEUE_KEY))
