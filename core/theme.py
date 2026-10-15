"""نظام الألوان والـ CSS (فاتح/داكن). كل الألوان متغيّرات CSS لسهولة التعديل لاحقاً."""
from string import Template

PALETTES = {
    "light": dict(
        bg="#F3F5F8", surface="#FFFFFF", text="#14263D", muted="#5B6B7C", border="#D9DFE7",
        navy="#0F2540", navy_text="#E8EDF3", gold="#B88A2E", gold_soft="#D4AF5A",
        ok="#1F8A5B", warn="#B7740B", bad="#C0392B", hover="#EEF2F7",
    ),
    "dark": dict(
        bg="#0A1626", surface="#12233B", text="#E8EDF3", muted="#9AA9BA", border="#263B57",
        navy="#07111F", navy_text="#E8EDF3", gold="#D4AF5A", gold_soft="#D4AF5A",
        ok="#3DBE8B", warn="#E3A33B", bad="#EF6B5B", hover="#183150",
    ),
}

CSS = Template("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap');
:root{--bg:$bg;--surface:$surface;--text:$text;--muted:$muted;--border:$border;--navy:$navy;
--navy-text:$navy_text;--gold:$gold;--gold-soft:$gold_soft;--ok:$ok;--warn:$warn;--bad:$bad;--hover:$hover;}

html, body, .stApp, [data-testid="stAppViewContainer"], button, input, textarea, select{
  font-family:'IBM Plex Sans Arabic','Segoe UI',Tahoma,Arial,sans-serif !important;}
.stApp{background:var(--bg);color:var(--text);}
[data-testid="stAppViewContainer"]{direction:rtl;}
[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:2rem;padding-bottom:3rem;max-width:1280px;}
h1,h2,h3,h4,p,label,li,span,.stMarkdown{color:var(--text);}
[data-testid="stCaptionContainer"]{color:var(--muted);}

/* ---------- القائمة الجانبية ---------- */
[data-testid="stSidebar"]{background:var(--navy);border-left:3px solid var(--gold);direction:rtl;}
[data-testid="stSidebar"] *{color:var(--navy-text);}
[data-testid="stSidebar"] hr{border-color:rgba(255,255,255,.14);}
[data-testid="stSidebar"] [data-baseweb="select"] > div{
  background:rgba(255,255,255,.07);border-color:rgba(255,255,255,.22);}
[data-testid="stSidebar"] .stRadio label{padding:.55rem .7rem;border-radius:6px;width:100%;}
[data-testid="stSidebar"] .stRadio label:hover{background:rgba(255,255,255,.08);}
[data-testid="stSidebar"] .stRadio label:has(input:checked){
  background:rgba(212,175,90,.16);box-shadow:inset -3px 0 0 var(--gold-soft);}
.side-user{font-size:.85rem;opacity:.85;margin:.4rem 0 1rem;}

/* ---------- عنوان الصفحة: خط أبعاد هندسي ---------- */
.page-head{margin:0 0 1.6rem;}
.page-head h1{font-size:1.7rem;font-weight:700;margin:0 0 .2rem;color:var(--text);}
.page-head p{margin:0;color:var(--muted);font-size:.95rem;}
.dim-line{position:relative;height:1px;background:var(--gold);margin-top:.9rem;max-width:420px;}
.dim-line::before,.dim-line::after{content:"";position:absolute;top:-5px;width:1px;height:11px;background:var(--gold);}
.dim-line::before{right:0;} .dim-line::after{left:0;}

/* ---------- المؤشرات ---------- */
[data-testid="stMetric"]{background:var(--surface);border:1px solid var(--border);
  border-top:3px solid var(--gold);border-radius:4px;padding:1rem 1.1rem;}
[data-testid="stMetricLabel"] *{color:var(--muted) !important;font-weight:500;}
[data-testid="stMetricValue"]{color:var(--text);font-weight:700;}

/* ---------- التبويبات والأزرار والحقول ---------- */
.stTabs [data-baseweb="tab-list"]{gap:.25rem;border-bottom:1px solid var(--border);}
.stTabs [data-baseweb="tab"]{height:2.6rem;color:var(--muted);}
.stTabs [aria-selected="true"]{color:var(--text);font-weight:600;}
.stTabs [data-baseweb="tab-highlight"]{background:var(--gold);}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button,[data-testid="stLinkButton"] a{
  border-radius:4px;border:1px solid var(--navy);font-weight:600;min-height:2.6rem;}
.stFormSubmitButton>button[kind="primary"],.stButton>button[kind="primary"]{
  background:var(--navy);color:#fff;border-color:var(--navy);}
.stFormSubmitButton>button[kind="primary"]:hover,.stButton>button[kind="primary"]:hover{
  background:var(--gold);border-color:var(--gold);color:#fff;}
[data-testid="stForm"]{background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:1.2rem;}
:focus-visible{outline:2px solid var(--gold) !important;outline-offset:2px;}

/* ---------- التنبيهات الذكية ---------- */
.alert{background:var(--surface);border:1px solid var(--border);border-right:4px solid var(--muted);
  border-radius:4px;padding:.7rem 1rem;margin:.4rem 0;font-size:.95rem;}
.alert.bad{border-right-color:var(--bad);} .alert.warn{border-right-color:var(--warn);}
.alert.ok{border-right-color:var(--ok);}
.alert b{margin-left:.4rem;}

/* ---------- شاشة الدخول ---------- */
.login-brand{background:var(--navy);padding:2rem 1.5rem 1.6rem;border-radius:4px 4px 0 0;
  border-bottom:3px solid var(--gold);text-align:center;direction:ltr;}
.login-brand .ar{color:var(--navy-text);margin-top:.9rem;font-size:1rem;font-weight:500;direction:rtl;}
.login-brand .en{color:var(--gold-soft);font-size:.78rem;letter-spacing:.08em;margin-top:.2rem;}
.sidebar-brand{padding:.4rem 0 .8rem;direction:ltr;}

/* ---------- الموبايل ---------- */
@media (max-width:768px){
  .block-container{padding:3.2rem .8rem 2rem;}
  .page-head h1{font-size:1.3rem;}
  [data-testid="stMetricValue"]{font-size:1.5rem;}
  .stButton>button,.stFormSubmitButton>button{width:100%;}
}
@media (prefers-reduced-motion:reduce){*{transition:none !important;animation:none !important;}}
</style>
""")


def build_css(mode: str = "light") -> str:
    return CSS.substitute(PALETTES.get(mode, PALETTES["light"]))
