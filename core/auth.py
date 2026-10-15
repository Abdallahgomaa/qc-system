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
            st.session_state["user"] = None
            st.success("تم تسجيل الخروج بنجاح")
            st.rerun()