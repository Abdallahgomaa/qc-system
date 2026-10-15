"""إشعارات التنبيهات الحرجة (البند 4.2).

يوفّر هذا الملف قناتين **بلا أي مكتبة خارجية**:

1. البريد الإلكتروني عبر SMTP (مكتبة ``smtplib`` القياسية) بإعدادات في
   ``.streamlit/secrets.toml`` تحت القسم ``[smtp]``.
2. رابط واتساب «اضغط للمحادثة» (``wa.me``) لا يحتاج أي API ولا مفاتيح ولا
   موافقة من Meta، ويكفي أن يُرسل النص الجاهز.

كل الدوال آمنة: لا ترفع استثناءات قاتلة، بل تعيد ``(نجاح, رسالة)`` لعرضها في
الواجهة عبر ``st.success``/``st.error``. وإذا غاب الإعداد تُرجع رسالة إرشادية
بدل أن تتعطّل الشاشة.
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

import streamlit as st

from core import config

# اسم القسم المتوقّع في Secrets.
SMTP_SECTION = "smtp"


# ---------------------------------------------------------------------------
# قراءة الإعدادات
# ---------------------------------------------------------------------------
def _secrets():
    """يعيد كائن secrets بأمان حتى خارج سياق Streamlit (للاختبار)."""
    try:
        return st.secrets
    except Exception:  # noqa: BLE001
        return {}


def email_settings() -> dict | None:
    """يعيد قاموس إعدادات SMTP إن توفّرت، وإلا ``None``."""
    secret = _secrets()
    try:
        section = secret[SMTP_SECTION]
    except Exception:  # noqa: BLE001
        return None
    host = section.get("host")
    if not host:
        return None
    return {
        "host": host,
        "port": int(section.get("port", 587)),
        "user": section.get("user"),
        "password": section.get("password"),
        "sender": section.get("sender") or section.get("user"),
        "recipients": section.get("recipients"),
        "use_ssl": bool(section.get("use_ssl", False)),
    }


def email_configured() -> bool:
    """هل يوجد إعداد بريد مكتمل (مرسل + مستلمون)؟"""
    settings = email_settings()
    return bool(settings and settings["sender"] and _as_list(settings["recipients"]))


def _as_list(value) -> list[str]:
    """يحوّل قيمة أسرار (نصّ بفواصل/منقوطة أو قائمة) إلى قائمة عناوين."""
    if not value:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


# ---------------------------------------------------------------------------
# البريد الإلكتروني (SMTP)
# ---------------------------------------------------------------------------
def send_email(subject: str, html: str, *, to=None) -> tuple[bool, str]:
    """يرسل رسالة HTML واحدة. يعيد ``(نجاح, رسالة)``."""
    settings = email_settings()
    if not settings:
        return False, ("لم تُضبط إعدادات البريد. أضف قسم ``[smtp]`` في "
                       "``.streamlit/secrets.toml`` (host/port/user/password/sender/recipients).")
    recipients = _as_list(to or settings["recipients"])
    if not recipients:
        return False, "لا يوجد مستلمون (recipients) في إعدادات البريد."

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings["sender"]
    message["To"] = ", ".join(recipients)
    message.set_content("يرجى عرض هذه الرسالة بصيغة HTML.")
    message.add_alternative(html, subtype="html")

    try:
        if settings["use_ssl"]:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings["host"], settings["port"], context=context,
                                  timeout=20) as server:
                if settings["user"]:
                    server.login(settings["user"], settings["password"] or "")
                server.send_message(message)
        else:
            with smtplib.SMTP(settings["host"], settings["port"], timeout=20) as server:
                server.ehlo()
                try:
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                except smtplib.SMTPException:
                    pass  # خادم داخلي بلا STARTTLS
                if settings["user"]:
                    server.login(settings["user"], settings["password"] or "")
                server.send_message(message)
    except Exception as e:  # noqa: BLE001
        return False, f"تعذّر إرسال البريد: {e}"
    return True, f"تم إرسال الإشعار إلى: {'، '.join(recipients)}"


# ---------------------------------------------------------------------------
# صياغة نصّ التنبيهات
# ---------------------------------------------------------------------------
def critical_alerts(alerts: list[dict]) -> list[dict]:
    """التنبيهات الحرجة فقط (المستوى ``bad``)."""
    return [a for a in (alerts or []) if a.get("level") == "bad"]


def _level_label(level: str) -> str:
    return "حرج" if level == "bad" else "تحذير"


def alerts_text(project: dict, alerts: list[dict]) -> str:
    """نصّ عادي جاهز للمشاركة (واتساب مثلاً)."""
    name = (project or {}).get("name", "")
    code = (project or {}).get("code", "")
    lines = [f"تنبيهات ضبط الجودة — {name} ({code})" if code else f"تنبيهات ضبط الجودة — {name}"]
    for alert in alerts or []:
        lines.append(f"[{_level_label(alert.get('level'))}] {alert.get('text', '')}")
    lines.append(f"— {config.APP_NAME_AR} | {config.APP_SYSTEM_TITLE}")
    return "\n".join(lines)


def build_alerts_html(project: dict, alerts: list[dict]) -> str:
    """نسخة HTML مهيّأة للبريد من التنبيهات."""
    name = (project or {}).get("name", "")
    code = (project or {}).get("code", "")
    rows = []
    for alert in alerts or []:
        color = "#C0392B" if alert.get("level") == "bad" else "#B7740B"
        rows.append(
            f'<li style="color:{color};margin:.3rem 0">'
            f'<b>[{_level_label(alert.get("level"))}]</b> {alert.get("text", "")}</li>'
        )
    items = "".join(rows) or "<li>لا توجد تنبيهات.</li>"
    return (
        '<div dir="rtl" style="font-family:Segoe UI,Tahoma,Arial,sans-serif;color:#14263D">'
        f'<h2 style="color:#0F2540">تنبيهات ضبط الجودة — {name} ({code})</h2>'
        f'<ul>{items}</ul>'
        f'<p style="color:#5B6B7C;font-size:.85rem">— {config.APP_NAME_AR} | '
        f"{config.APP_SYSTEM_TITLE}</p>"
        "</div>"
    )


def send_alerts_email(project: dict, alerts: list[dict]) -> tuple[bool, str]:
    """يرسل التنبيهات بالبريد إلى المستلمين المضبوطين."""
    subject = f"CGES — تنبيهات ضبط الجودة: {(project or {}).get('name', '')}"
    return send_email(subject, build_alerts_html(project, alerts))


# ---------------------------------------------------------------------------
# واتساب (رابط اضغط للمحادثة — بلا API)
# ---------------------------------------------------------------------------
def whatsapp_link(text: str, phone: str | None = None) -> str:
    """رابط ``wa.me`` لنصّ جاهز. بلا ``phone`` يختار المستخدم جهة الاتصال."""
    base = f"https://wa.me/{phone}" if phone else "https://wa.me/"
    return f"{base}?text={quote(text)}"


def alerts_whatsapp_link(project: dict, alerts: list[dict],
                         phone: str | None = None) -> str:
    return whatsapp_link(alerts_text(project, alerts), phone)
