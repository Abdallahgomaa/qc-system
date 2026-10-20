"""مكوّنات الواجهة المشتركة: الشعار، رأس الصفحة، التنبيهات، شاشة الدخول."""
import streamlit as st

from core import auth, pwa
from core.config import APP_NAME_AR, APP_NAME_EN, APP_SHORT, ROLE_LABELS


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


def top_bar(projects: list) -> None:
    """الشريط العلوي: الهوية + أدوات المستخدم (المشروع الحالي وتسجيل الخروج).

    بديل القائمة الجانبية: تُنقل هنا الأدوات الوظيفية الأربع (الهوية، البروفايل،
    المشروع الحالي، تسجيل الخروج) حتى لا تُفقد عند إلغاء ``st.sidebar``.
    """
    p = auth.profile()
    c_brand, c_user, c_proj, c_out = st.columns([1.15, 1.5, 1.5, 0.55], vertical_alignment="center")

    with c_brand:
        st.markdown(f'<div class="topbar-brand">{logo_svg(width=150)}</div>', unsafe_allow_html=True)
    with c_user:
        st.markdown(
            f'<div class="topbar-user">{p.get("full_name") or p["username"]}'
            f' · {ROLE_LABELS.get(p["role"], "")}</div>',
            unsafe_allow_html=True,
        )
    with c_proj:
        project = None
        if projects:
            ids = [x["id"] for x in projects]
            cur = st.session_state.get("project_id")
            default = ids.index(cur) if cur in ids else 0
            project = st.selectbox(
                "المشروع الحالي", projects, index=default, label_visibility="collapsed",
                format_func=lambda x: f"{x['code'] + ' – ' if x.get('code') else ''}{x['name']}",
                key="topbar_project",
            )
            st.session_state["project_id"] = project["id"]
    with c_out:
        if st.button("خروج", use_container_width=True):
            auth.logout()
            st.rerun()


def current_project(projects: list):
    """المشروع النشط كما اختاره المستخدم في الشريط العلوي (أو الأول افتراضياً)."""
    if not projects:
        return None
    ids = [x["id"] for x in projects]
    cur = st.session_state.get("project_id")
    return projects[ids.index(cur)] if cur in ids else projects[0]


def nav_bar_css() -> None:
    """تنسيق شريط التنقل الأفقي العلوي ليكون تبويبات عصرية واضحة على الموبايل والكمبيوتر."""
    st.markdown(
        """
<style>
/* شريط التنقل الأفقي: حاوية تبويبات بألوان اللوحة الداكنة */
[data-testid="stMainBlockContainer"] [role="radiogroup"]{
  background:var(--surface);border:1px solid var(--border);border-radius:14px;
  padding:8px;display:flex !important;flex-wrap:wrap;gap:8px;justify-content:center;
  box-shadow:0 2px 10px var(--shadow);margin-bottom:1.1rem;}
[data-testid="stMainBlockContainer"] [role="radiogroup"] label{
  background:var(--bg);color:var(--muted);border:1px solid var(--border);
  border-radius:10px;padding:8px 16px;font-weight:600;cursor:pointer;margin:0;
  transition:background .22s ease,color .22s ease,border-color .22s ease,box-shadow .22s ease;}
[data-testid="stMainBlockContainer"] [role="radiogroup"] label:hover{
  background:var(--hover);color:var(--text);border-color:var(--accent-line);}
[data-testid="stMainBlockContainer"] [role="radiogroup"] label *{color:inherit !important;}
/* التبويب النشط بلون e& الأحمر */
[data-testid="stMainBlockContainer"] [role="radiogroup"] label:has(input:checked){
  background:var(--accent) !important;color:#FFFFFF !important;border-color:var(--accent) !important;
  box-shadow:0 4px 14px var(--accent-glow);}
[data-testid="stMainBlockContainer"] [role="radiogroup"] input{display:none;}

/* تنسيق الشريط العلوي للهوية والمستخدم */
.topbar-brand svg{max-width:150px;}
.topbar-user{color:var(--muted);font-weight:600;font-size:.9rem;text-align:center;}

@media (max-width:768px){
  [data-testid="stMainBlockContainer"] [role="radiogroup"]{padding:6px;gap:6px;}
  [data-testid="stMainBlockContainer"] [role="radiogroup"] label{
    padding:7px 11px;font-size:.85rem;flex:1 1 auto;text-align:center;}
  .topbar-user{font-size:.8rem;}
}
</style>
""",
        unsafe_allow_html=True,
    )


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
/* القائمة الجانبية ملغاة: التنقل والأدوات في الشريط العلوي الأفقي */
[data-testid="stSidebar"], [data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {display: none !important;}

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
