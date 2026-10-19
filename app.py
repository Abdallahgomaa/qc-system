"""CGES – نظام إدارة المكتب الاستشاري الهندسي. نقطة التشغيل: streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="CGES | المجموعة الاستشارية", page_icon="🏗️",
                   layout="wide", initial_sidebar_state="auto")

from core import auth, db, theme, ui  # noqa: E402
from core.config import ROLE_LABELS  # noqa: E402

dark = st.session_state.get("dark_mode", False)
st.markdown(theme.build_css("dark" if dark else "light"), unsafe_allow_html=True)

# تنظيف واجهة Streamlit (إخفاء شريط الأدوات/القوائم) + تهيئة PWA والوضع بدون اتصال
ui.clean_ui()

auth.restore_session()   # البند 3.1: استعادة الجلسة من الكوكي بعد تحديث الصفحة
auth.persist_session()   # البند 3.1: كتابة/تحديث الكوكي على تشغيل مستقر

if not auth.is_logged_in():
    ui.login_screen()
    st.stop()

NAV = {
    "dashboard": (":material/dashboard: لوحة المؤشرات", "views.dashboard"),
    "field": (":material/agriculture: الوضع الميداني", "views.field"),
    "concrete": (":material/foundation: الخرسانة", "views.concrete"),
    "soil": (":material/layers: التربة", "views.soil"),
    "materials": (":material/science: المواد والاختبارات", "views.materials"),
    "calibration": (":material/tune: معايرة المحطات", "views.calibration"),
}
if auth.is_admin():
    NAV["admin"] = (":material/admin_panel_settings: الإدارة", "views.admin")

# البند (ج): استيراد طابور الوضع الميداني القادم عبر الرابط ?cges_queue=
# (بعد التحقق من الدخول حتى لا تُكتب بيانات بدون مستخدم مُصرَّح).
projects = db.list_projects()

with st.sidebar:
    ui.sidebar_brand()
    p = auth.profile()
    st.markdown(f'<div class="side-user">{p.get("full_name") or p["username"]}'
                f' · {ROLE_LABELS.get(p["role"], "")}</div>', unsafe_allow_html=True)

    project = None
    if projects:
        ids = [x["id"] for x in projects]
        default = ids.index(st.session_state["project_id"]) if st.session_state.get("project_id") in ids else 0
        project = st.selectbox("المشروع الحالي", projects, index=default,
                               format_func=lambda x: f"{x['code'] + ' – ' if x.get('code') else ''}{x['name']}")
        st.session_state["project_id"] = project["id"]
    st.divider()
    page = st.radio("القائمة", list(NAV), format_func=lambda k: NAV[k][0], label_visibility="collapsed")
    st.divider()
    st.toggle("الوضع الداكن", key="dark_mode")
    if st.button("تسجيل الخروج"):
        auth.logout()
        st.rerun()

if page == "admin":
    from views import admin
    admin.render()
elif project is None:
    st.info("لا توجد مشاريع متاحة لحسابك. اطلب من المدير العام إسناد مشروع لك.")
else:
    # البند (ج): مزامنة طابور الوضع الميداني القادم عبر ?cges_queue= بعد
    # تحديد المشروع النشط، حتى تُنسب السجلات للمشروع الصحيح.
    from views import field as _field  # noqa: E402
    _field.import_from_query(project)

    import importlib
    importlib.import_module(NAV[page][1]).render(project)
