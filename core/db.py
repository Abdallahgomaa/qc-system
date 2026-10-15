import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

def list_projects():
    """جلب قائمة المشاريع من جدول projects في Supabase"""
    try:
        response = supabase.table("projects").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        # لو الجدول مش موجود أو حصل خطأ، نرجع لستة فارغة لتجنب توقف التطبيق
        return []