"""مكوّنات الواجهة المشتركة: الشعار، رأس الصفحة، التنبيهات، شاشة الدخول."""
import streamlit as st

from core import auth, pwa
from core.config import APP_NAME_AR, APP_NAME_EN, APP_SHORT


def logo_svg(fg: str = "#FFFFFF", accent: str = "#D4AF5A", width: int = 220) -> str:
    """شعار CGES: حروف بين عمودين إنشائيين، جمالون (Truss) فوقها، وخط أبعاد (Dimension line) أسفلها."""
    truss = "M8 12 L30 3 L52 12 L74 3 L96 12 L118 3 L140 12 L162 3 L184 12 L206 3 L228 12"
    return f"""
<svg viewBox="0 0 236 90" width="{width}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{APP_SHORT}">
  <path d="M8 3V66M228 3V66" stroke="{accent}" stroke-width="2.4"/>
  <path d="{truss}" fill="none" stroke="{accent}" stroke-width="1.1"/>
  <text x="118" y="58" text-anchor="middle" font-family="'IBM Plex Sans Arabic','Segoe UI',Arial,sans-serif"
        font-size="46" font-weight="700" letter-spacing="9" fill="{fg}">{APP_SHORT}</text>
  <path d="M8 78H66M170 78H228M8 73V83M228 73V83M63 81L69 75M167 81L173 75" stroke="{accent}" stroke-width="1"/>
  <text x="118" y="81" text-anchor="middle" font-family="Arial,sans-serif" font-size="7.5"
        letter-spacing="2.2" fill="{accent}">ENGINEERING SERVICES</text>
</svg>"""


def page_header(title: str, subtitle: str = "") -> None:
    pwa.inject()  # تثبيت التطبيق (PWA) + شريط «لا يوجد اتصال» — البند (أ)
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="page-head"><h1>{title}</h1>{sub}<div class="dim-line"></div></div>',
        unsafe_allow_html=True,
    )


def alert_box(level: str, text: str) -> None:
    label = {"bad": "حرج", "warn": "تنبيه", "ok": "سليم"}.get(level, "")
    st.markdown(f'<div class="alert {level}"><b>{label}</b>{text}</div>', unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.markdown(f'<div class="sidebar-brand">{logo_svg(width=190)}</div>', unsafe_allow_html=True)


def login_screen() -> None:
    pwa.inject()  # تثبيت التطبيق متاح حتى قبل الدخول (وضع مستقل بهوية CGES) — البند (أ)
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(
            f"""<div class="login-brand">{logo_svg(width=280)}
            <div class="ar">{APP_NAME_AR}</div><div class="en">{APP_NAME_EN.upper()}</div></div>""",
            unsafe_allow_html=True,
        )
        with st.form("login", border=True):
            username = st.text_input("اسم المستخدم", autocomplete="username")
            password = st.text_input("كلمة المرور", type="password", autocomplete="current-password")
            if st.form_submit_button("تسجيل الدخول", type="primary"):
                ok, msg = auth.login(username, password)
                if ok:
                    st.rerun()
                else:
                    st.error(msg)


_CLEAN_CSS = """
<style>
/* إخفاء شريط أدوات وسيرفر Streamlit وعلامة التاج والـ Fork بالكامل */
[data-testid="stToolbar"] {visibility: hidden; height: 0%; position: fixed;}
.stDeployButton {display: none !important;}
footer {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}
header {visibility: hidden !important;}

/* إزالة أي خطوط فاصلة مزعجة أو حدود ظاهرة في منتصف الشاشة على الموبايل */
[data-testid="stSidebarNav"] {background-color: transparent;}
[data-testid="collapsedControl"] {display: block;}

/* تحسين الفراغات وتجربة المستخدم (UX) على الشاشات الصغيرة والموبايل */
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        padding-top: 1rem;
    }
}
</style>
"""


def clean_ui() -> None:
    """ينظّف واجهة Streamlit (إخفاء شريط الأدوات والقوائم) ويهيّئ دعم PWA.

    تُستدعى مرة واحدة في كل تشغيل من ``app.py`` (شاشة الدخول والتطبيق)، فتعمل
    كحقن عام: وسوم تثبيت التطبيق + Service Worker + شريط «لا يوجد اتصال»
    (البند أ) مع تنسيقات CSS لإخفاء عناصر Streamlit الافتراضية.

    وتستورد هنا طابور الوضع الميداني القادم عبر الرابط ``?cges_queue=``
    (البند ج)، لتعمل المزامنة عند فتح أي صفحة لا صفحة الوضع الميداني وحدها.
    """
    pwa.inject()
    st.markdown(_CLEAN_CSS, unsafe_allow_html=True)
