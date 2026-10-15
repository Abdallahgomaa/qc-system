import streamlit as st
from core.db import supabase

def is_logged_in() -> bool:
    """التحقق مما إذا كان المستخدم مسجلاً للدخول أم لا"""
    return st.session_state.get("user") is not None

def is_admin() -> bool:
    """التحقق مما إذا كان المستخدم الحالي هو مدير النظام"""
    user = st.session_state.get("user")
    if not user:
        return False
    email = getattr(user, "email", "")
    return "admin" in email or email == "admin@cges.com"

def profile():
    """إرجاع بيانات الملف الشخصي للمستخدم الحالي متضمنة المفاتيح المطلوبة"""
    user = st.session_state.get("user")
    if not user:
        return {"username": "guest", "full_name": "زائر", "email": "", "role": "guest"}
    
    email = getattr(user, "email", "admin@cges.com")
    username = email.split("@")[0] if email else "admin"
    
    return {
        "username": username,
        "full_name": username.capitalize(),
        "email": email,
        "role": "admin" if is_admin() else "engineer"
    }

def login(email_or_username, password):
    """دالة تسجيل الدخول الأساسية التي تستدعيها واجهات النظام"""
    try:
        login_email = email_or_username if "@" in email_or_username else f"{email_or_username}@cges.com"
        response = supabase.auth.sign_in_with_password({"email": login_email, "password": password})
        st.session_state["user"] = response.user
        return True, "تم تسجيل الدخول بنجاح"
    except Exception as e:
        return False, str(e)

def login_screen():
    """شاشة تسجيل الدخول"""
    if "user" not in st.session_state:
        st.session_state["user"] = None
    
    if not is_logged_in():
        st.subheader("تسجيل الدخول - نظام CGES لإدارة الجودة")
        email_input = st.text_input("اسم المستخدم أو البريد الإلكتروني")
        password = st.text_input("كلمة المرور", type="password")
        
        if st.button("تسجيل الدخول"):
            success, msg = login(email_input, password)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(f"فشل تسجيل الدخول: {msg}")
        return False
    return True

def check_auth():
    """دالة توافقية بديلة"""
    return login_screen()

def logout_ui():
    """واجهة وزر تسجيل الخروج في القائمة الجانبية"""
    if is_logged_in():
        st.sidebar.markdown("---")
        if st.sidebar.button("تسجيل الخروج"):
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
            _forget_session()
            st.session_state["user"] = None
            st.success("تم تسجيل الخروج بنجاح")
            st.rerun()

def logout():
    """تسجيل الخروج: إنهاء جلسة Supabase وتفريغ حالة الجلسة المحلية.

    دالة إضافية غير كاسرة يستدعيها app.py عند الضغط على زر «تسجيل الخروج».
    """
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    _forget_session()
    st.session_state.pop("project_id", None)
    st.session_state["user"] = None
    st.success("تم تسجيل الخروج بنجاح")
    st.rerun()


# ---------------------------------------------------------------------------
# البند 3.1: تثبيت الجلسة بعد تحديث الصفحة (كوكي + إعادة التفويض)
# ---------------------------------------------------------------------------
_COOKIE_NAME = "cges_session"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # ثلاثون يوماً


def _render_cookie_js(js: str) -> None:
    """ينفّذ جافاسكربت صغيراً لكتابة/حذف الكوكي في المتصفح.

    يستخدم ``st.html`` الحديثة مع ``unsafe_allow_javascript=True`` (البديل
    الموصى به عن ``st.components.v1.html`` المهجور). محتوى ``st.html`` غير
    موضوع في iframe، لذلك يُنفَّذ السكربت في أصل التطبيق نفسه وهذا ما يتيح
    كتابة ``document.cookie``.
    """
    script_html = f"<script>{js}</script>"
    try:
        if hasattr(st, "html"):
            st.html(script_html, unsafe_allow_javascript=True)
        else:  # توافق مع إصدارات Streamlit الأقدم من 1.33
            from streamlit.components.v1 import html as _legacy_html
            _legacy_html(script_html, height=0)
    except Exception:  # noqa: BLE001 - الكوكي ميزة إضافية، لا تُسقط التطبيق
        pass


def _remember_session(response) -> None:
    """يحفظ رمز التجديد في كوكي بعد نجاح الدخول."""
    token = getattr(getattr(response, "session", None), "refresh_token", None)
    if token:
        _render_cookie_js(
            f"document.cookie='{_COOKIE_NAME}={token}; path=/; "
            f"max-age={_COOKIE_MAX_AGE}; SameSite=Lax';")


def _forget_session() -> None:
    """يحذف الكوكي عند تسجيل الخروج."""
    _render_cookie_js(f"document.cookie='{_COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax';")


def _read_session_cookie() -> str | None:
    try:
        return st.context.cookies.get(_COOKIE_NAME) or None
    except Exception:  # noqa: BLE001 - غير متاح خارج المتصفح أو في الاختبارات
        return None


def restore_session() -> bool:
    """يستعيد الجلسة من الكوكي بعد تحديث الصفحة. يعيد True إن صار المستخدم مسجّلاً."""
    if is_logged_in():
        return True
    token = _read_session_cookie()
    if not token:
        return False
    try:
        response = supabase.auth.refresh_session(token)
        user = getattr(response, "user", None)
        if not user:
            raise RuntimeError("لا يوجد مستخدم في الجلسة المستعادة.")
        st.session_state["user"] = user
        new_token = getattr(getattr(response, "session", None), "refresh_token", None)
        if new_token and new_token != token:
            _remember_session(response)
        return True
    except Exception:  # noqa: BLE001 - رمز منتهٍ أو غير صالح
        _forget_session()
        return False


def _current_refresh_token() -> str | None:
    try:
        session = supabase.auth.get_session()
        return getattr(session, "refresh_token", None)
    except Exception:  # noqa: BLE001
        return None


def persist_session() -> None:
    """يكتب رمز الجلسة الحالي في الكوكي إن لم يكن مطابقاً (البند 3.1).

    تُستدعى في كل تشغيل بعد التأكد من تسجيل الدخول، على تشغيل مستقر (لا يتبعه
    ``st.rerun`` فوراً) حتى يُنفَّذ سكربت الكوكي فعلاً في المتصفح.
    """
    if not is_logged_in():
        return
    token = _current_refresh_token()
    if not token or _read_session_cookie() == token:
        return
    _render_cookie_js(
        f"document.cookie='{_COOKIE_NAME}={token}; path=/; "
        f"max-age={_COOKIE_MAX_AGE}; SameSite=Lax';")