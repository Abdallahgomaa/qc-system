"""نظام الألوان والـ CSS (فاتح/داكن). كل الألوان متغيّرات CSS لسهولة التعديل لاحقاً."""
from string import Template

# هوية e& : الأحمر هو اللون الأساسي (accent)، والكحلي يبقى إطار الهوية الثانوي.
# gold/gold_soft محفوظان كأسماء تاريخية لكنهما يشيران الآن لأحمر e& حتى تتبع
# كل القواعد القديمة (التي تستخدم var(--gold)) اللون الجديد تلقائياً.
PALETTES = {
    "light": dict(
        bg="#F3F5F8", surface="#FFFFFF", text="#1F2937", muted="#6B7280", border="#E5E7EB",
        navy="#0F2540", navy_text="#E8EDF3", gold="#E30613", gold_soft="#C10510",
        ok="#1F8A5B", warn="#B7740B", bad="#C0392B", hover="#F3F4F6",
        accent_tint="rgba(227,6,19,.08)", accent_line="rgba(227,6,19,.25)",
        accent_glow="rgba(227,6,19,.12)", shadow="rgba(0,0,0,.05)",
    ),
    "dark": dict(
        bg="#0A1626", surface="#12233B", text="#E8EDF3", muted="#9AA9BA", border="#263B57",
        navy="#07111F", navy_text="#E8EDF3", gold="#FF3B47", gold_soft="#E30613",
        ok="#3DBE8B", warn="#E3A33B", bad="#EF6B5B", hover="#183150",
        accent_tint="rgba(255,59,71,.16)", accent_line="rgba(255,59,71,.38)",
        accent_glow="rgba(255,59,71,.14)", shadow="rgba(0,0,0,.28)",
    ),
}

CSS = Template("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap');
:root{--bg:$bg;--surface:$surface;--text:$text;--muted:$muted;--border:$border;--navy:$navy;
--navy-text:$navy_text;--gold:$gold;--gold-soft:$gold_soft;--ok:$ok;--warn:$warn;--bad:$bad;--hover:$hover;
--accent:$gold;--accent-soft:$gold_soft;--brand:#E30613;
--accent-tint:$accent_tint;--accent-line:$accent_line;--accent-glow:$accent_glow;
--shadow:$shadow;}

html, body, .stApp, [data-testid="stAppViewContainer"], button, input, textarea, select{
  font-family:'IBM Plex Sans Arabic','Segoe UI',Tahoma,Arial,sans-serif !important;}
.stApp{background:var(--bg);color:var(--text);}
[data-testid="stAppViewContainer"]{direction:rtl;}
[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:2rem;padding-bottom:3rem;max-width:1280px;}
h1,h2,h3,h4,p,label,li,span,.stMarkdown{color:var(--text);}
[data-testid="stCaptionContainer"]{color:var(--muted);}

/* ---------- القائمة الجانبية ---------- */
[data-testid="stSidebar"]{background:var(--surface);border-left:1px solid var(--border);direction:rtl;}
[data-testid="stSidebar"] *{color:var(--text);}
[data-testid="stSidebar"] hr{border-color:var(--border);}
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] .react-aria-ComboBox > div[role="group"],
[data-testid="stSidebar"] [role="group"]:has(> input[role="combobox"]){
  background:var(--bg);border-color:var(--border);}
[data-testid="stSidebar"] .stRadio label{padding:.55rem .7rem;border-radius:10px;width:100%;
  transition:background .18s ease,box-shadow .18s ease;}
[data-testid="stSidebar"] .stRadio label:hover{background:var(--hover);
  box-shadow:inset -3px 0 0 var(--accent-line);}
[data-testid="stSidebar"] .stRadio label:has(input:checked){
  background:var(--accent-tint);box-shadow:inset -3px 0 0 var(--accent);}
/* شريط علوي رفيع بلون التمييز أعلى القائمة الجانبية */
[data-testid="stSidebar"] > div:first-child{border-top:3px solid var(--accent);}
.side-user{font-size:.85rem;color:var(--muted);margin:.4rem 0 1rem;}

/* ---------- عنوان الصفحة: خط أبعاد هندسي ---------- */
.page-head{margin:0 0 1.6rem;}
.page-head h1{font-size:1.7rem;font-weight:700;margin:0 0 .2rem;color:var(--text);}
.page-head p{margin:0;color:var(--muted);font-size:.95rem;}
.dim-line{position:relative;height:1px;background:var(--accent);margin-top:.9rem;max-width:420px;}
.dim-line::before,.dim-line::after{content:"";position:absolute;top:-5px;width:1px;height:11px;background:var(--accent);}
.dim-line::before{right:0;} .dim-line::after{left:0;}

/* ---------- المؤشرات ---------- */
[data-testid="stMetric"]{background:var(--surface);border:1px solid var(--border);
  border-radius:14px;padding:1rem 1.1rem;box-shadow:0 2px 10px var(--shadow);
  border-top:3px solid var(--accent);
  transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease;}
[data-testid="stMetric"]:hover{transform:translateY(-2px);
  box-shadow:0 10px 26px var(--accent-glow);border-color:var(--accent-line);}
[data-testid="stMetricLabel"] *{color:var(--muted) !important;font-weight:600;
  font-size:.82rem;letter-spacing:.01em;}
[data-testid="stMetricValue"]{color:var(--text);font-weight:700;font-size:1.65rem;}
[data-testid="stMetric"],[data-testid="stMetricLabel"],[data-testid="stMetricValue"]{
  text-align:center;}
[data-testid="stMetricLabel"]{justify-content:center;}
/* خط تمييز رفيع يمتد من بداية صف المؤشرات */
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"])::before{content:"";display:block;}

/* ---------- الكروت العامة (البطاقات البيضاء العصرية) ---------- */
[data-testid="stForm"],[data-testid="stExpander"],[data-testid="stDataFrame"]{
  background:var(--surface);box-shadow:0 2px 10px var(--shadow);}
[data-testid="stExpander"]{border:1px solid var(--border);border-radius:14px;
  transition:border-color .2s ease;}
[data-testid="stExpander"]:hover{border-color:var(--accent-line);}
[data-testid="stExpander"] summary{border-bottom:1px solid transparent;
  transition:border-color .2s ease;}
[data-testid="stExpander"][open] summary,
[data-testid="stExpander"] details[open] summary{border-bottom-color:var(--accent-tint);}

/* ---------- التبويبات والأزرار والحقول ---------- */
.stTabs [data-baseweb="tab-list"]{gap:.25rem;border-bottom:1px solid var(--border);}
.stTabs [data-baseweb="tab"]{height:2.6rem;color:var(--muted);border-radius:10px 10px 0 0;
  transition:background .18s ease,color .18s ease;}
.stTabs [data-baseweb="tab"]:hover{background:var(--hover);color:var(--text);}
.stTabs [aria-selected="true"]{color:var(--text);font-weight:600;}
.stTabs [data-baseweb="tab-highlight"]{background:var(--accent);height:3px;}
.stTabs [data-baseweb="tab-border"]{background:transparent;}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button,[data-testid="stLinkButton"] a{
  border-radius:10px;border:1px solid var(--border);font-weight:600;min-height:2.6rem;
  transition:transform .18s ease,box-shadow .18s ease,background .18s ease;}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stLinkButton"] a:hover{
  background:var(--hover);box-shadow:0 4px 14px var(--shadow);transform:translateY(-1px);
  border-color:var(--accent-line);}
.stFormSubmitButton>button[kind="primary"],.stButton>button[kind="primary"]{
  background:var(--navy);color:#fff;border-color:var(--navy);
  box-shadow:0 4px 14px rgba(15,37,64,.22);}
.stFormSubmitButton>button[kind="primary"]:hover,.stButton>button[kind="primary"]:hover{
  background:var(--accent);border-color:var(--accent);color:#fff;
  box-shadow:0 6px 20px var(--accent-line);transform:translateY(-1px);}
[data-testid="stForm"]{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:1.2rem;
  box-shadow:0 2px 10px var(--shadow);}
:focus-visible{outline:2px solid var(--accent) !important;outline-offset:2px;}

/* ---------- حقول الإدخال والقوائم المنسدلة (وضوح كامل للألوان) ---------- */
/* خلفية الحقول تتبع اللوحة (var(--surface)) لا لوناً ثابتاً، فتبقى متناسقة
   مع البطاقات والقائمة الجانبية في الوضعين الفاتح والداكن. */
input, textarea,
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input,
.stTextInput [data-baseweb="base-input"], .stNumberInput [data-baseweb="base-input"],
.stDateInput [data-baseweb="base-input"], .stTextArea textarea{
  background-color:var(--surface) !important;color:var(--text) !important;
  border-color:var(--border) !important;border-radius:10px !important;}
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input{
  border:1px solid var(--border) !important;}
/* القوائم المنسدلة (اختيار واحد/متعدد) + النص المختار بداخلها */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div{
  background-color:var(--surface) !important;color:var(--text) !important;
  border-color:var(--border) !important;border-radius:10px !important;}
div[data-baseweb="select"] span, div[data-baseweb="select"] input,
div[data-baseweb="select"] svg{color:var(--text) !important;fill:var(--text) !important;}
/* Streamlit الحديث يرسم حقول الاختيار بـreact-aria (ComboBox) لا baseweb،
   وحاويتها div[role="group"] بيضاء افتراضياً فتظهر كمربع أبيض في الوضع
   الداكن — نربطها باللوحة هنا. */
.react-aria-ComboBox > div[role="group"], [role="group"]:has(> input[role="combobox"]){
  background-color:var(--surface) !important;color:var(--text) !important;
  border:1px solid var(--border) !important;border-radius:10px !important;}
.react-aria-ComboBox > div[role="group"]:focus-within,
[role="group"]:has(> input[role="combobox"]):focus-within{
  border-color:var(--accent) !important;box-shadow:0 0 0 2px var(--accent-tint) !important;}
.react-aria-ComboBox input[role="combobox"], input[role="combobox"]{
  background-color:transparent !important;color:var(--text) !important;}
.react-aria-ComboBox input[role="combobox"]::placeholder{color:var(--muted) !important;opacity:.85;}
/* قائمة الخيارات المنسدلة (react-aria/MUI Popup) */
[role="listbox"], [role="listbox"] [role="option"], ul[data-baseweb="menu"]{
  background-color:var(--surface) !important;color:var(--text) !important;}
[role="option"]:hover, [role="option"][aria-selected="true"]{
  background-color:var(--accent-tint) !important;color:var(--text) !important;}
/* قائمة الخيارات المنسدلة (Popup) — لأنها تُرسم خارج حاوية التطبيق */
ul[data-baseweb="menu"], div[data-baseweb="popover"] ul{
  background-color:var(--surface) !important;}
ul[data-baseweb="menu"] li, div[data-baseweb="popover"] li{color:var(--text) !important;}
ul[data-baseweb="menu"] li:hover, div[data-baseweb="popover"] li[aria-selected="true"]{
  background-color:var(--accent-tint) !important;color:var(--text) !important;}
/* النص المؤقت (Placeholder) أفتح قليلاً من النص العادي */
input::placeholder, textarea::placeholder{color:var(--muted) !important;opacity:.85;}
/* تأثير التركيز بلون هوية e& */
input:focus, textarea:focus, div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="input"] > div:focus-within{
  border-color:var(--accent) !important;
  box-shadow:0 0 0 2px var(--accent-tint) !important;}
/* ملصقات الحقول: واضحة وسميكة */
label, .stTextInput label, .stSelectbox label, .stNumberInput label,
.stDateInput label, .stTextArea label, .stMultiSelect label{
  color:var(--text) !important;font-weight:600 !important;font-size:.95rem !important;}

/* ---------- التنبيهات الذكية ---------- */
.alert{background:var(--surface);border:1px solid var(--border);border-right:4px solid var(--muted);
  border-radius:12px;padding:.7rem 1rem;margin:.4rem 0;font-size:.95rem;
  box-shadow:0 2px 10px var(--shadow);}
.alert.bad{border-right-color:var(--bad);} .alert.warn{border-right-color:var(--warn);}
.alert.ok{border-right-color:var(--ok);}
.alert b{margin-left:.4rem;}

/* ---------- شاشة الدخول ---------- */
.login-brand{background:var(--navy);padding:2rem 1.5rem 1.6rem;border-radius:14px 14px 0 0;
  border-bottom:3px solid var(--accent);text-align:center;direction:ltr;}
.login-brand .ar{color:var(--navy-text);margin-top:.9rem;font-size:1rem;font-weight:500;direction:rtl;}
.login-brand .en{color:var(--gold-soft);font-size:.78rem;letter-spacing:.08em;margin-top:.2rem;}
.sidebar-brand{padding:.4rem 0 .8rem;direction:ltr;}

/* ---------- جداول السجلات (البند 3.2: تتبع الثيم فاتح/داكن + RTL) ---------- */
.cges-table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:4px;margin:.4rem 0;}
table.cges-table{width:100%;border-collapse:collapse;direction:rtl;font-size:.9rem;background:var(--surface);}
table.cges-table thead th{background:var(--navy);color:var(--navy-text) !important;padding:.55rem .7rem;
  text-align:right;font-weight:600;border:1px solid var(--border);white-space:nowrap;}
table.cges-table tbody td{padding:.45rem .7rem;border:1px solid var(--border);color:var(--text) !important;
  text-align:right;background:var(--surface);}
table.cges-table tbody tr:nth-child(even) td{background:var(--hover);}
table.cges-table tbody tr:hover td{background:var(--hover);}

/* ---------- الشاشات المتوسطة والضيقة (البند 2.4) ---------- */
/* بطاقات المؤشرات: بطاقتان في الصف بدل أربع بطاقات مضغوطة (لوحة/تابلت/موبايل). */
@media (max-width:1024px){
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"]{
    flex:1 1 45% !important;min-width:45% !important;}
}

/* ---------- الموبايل (البند 2.4: عرض نظيف على شاشة الهاتف) ---------- */
@media (max-width:768px){
  .block-container{padding:3.2rem .5rem 2rem;}
  /* منع أي تداخل/قطع للنصوص في منتصف الشاشة */
  .block-container,[data-testid="stAppViewContainer"]{overflow-x:hidden;}
  .page-head h1{font-size:1.3rem;}
  .page-head p{font-size:.85rem;}
  .dim-line{max-width:100%;}
  [data-testid="stMetric"]{padding:.7rem .85rem;margin-bottom:10px;}
  [data-testid="stMetricValue"]{font-size:1.5rem;}
  [data-testid="stMetricLabel"]{font-size:.8rem;}
  .stButton>button,.stFormSubmitButton>button,.stDownloadButton>button,
  [data-testid="stLinkButton"] a{width:100%;}
  /* منطقة الإبهام: أزرار أعلى وأوضح للمس باليد الواحدة */
  .stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{height:50px;font-size:16px;}
  [data-testid="stForm"]{padding:.9rem;}
  /* حقول النماذج: كل حقل في سطر كامل لسهولة اللمس */
  [data-testid="stForm"] [data-testid="stHorizontalBlock"]{flex-wrap:wrap;}
  [data-testid="stForm"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{
    flex:1 1 100% !important;min-width:100% !important;}
  /* الجداول العريضة: تمرير أفقي داخل حاويتها بلا كسر عرض الصفحة */
  .cges-table-wrap{max-width:100%;}
  table.cges-table{font-size:.78rem;}
  table.cges-table thead th,table.cges-table tbody td{padding:.38rem .45rem;}
  table.cges-table thead th{white-space:normal;}
  .alert{font-size:.88rem;}
  /* لا تنكسر الصفحة بسبب نص طويل (أسماء ملفات، بريد…) */
  [data-testid="stMarkdownContainer"],table.cges-table td{overflow-wrap:anywhere;}
  /* شاشة الدخول: النموذج بعرض كامل بدل أعمدة ضيقة (الأعمدة الفارغة تنطبق) */
  [data-testid="stHorizontalBlock"]:has(.login-brand) > [data-testid="stColumn"]{
    flex:1 1 100% !important;min-width:100% !important;}
  .login-brand{padding:1.4rem 1rem 1.2rem;}
}
@media (prefers-reduced-motion:reduce){*{transition:none !important;animation:none !important;}}
</style>
""")


def build_css(mode: str = "light") -> str:
    return CSS.substitute(PALETTES.get(mode, PALETTES["light"]))
