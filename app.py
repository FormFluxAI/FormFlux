import streamlit as st
import streamlit.components.v1 as components
import os
import time
import urllib.parse
import pypdf
from PIL import Image
from openai import OpenAI
from backend import PolyglotWizard, IdentityStamper
from config import FORM_LIBRARY
from dispatcher import send_secure_email
from sms import send_sms_alert
from logger import log_submission, load_logs
from streamlit_drawable_canvas import st_canvas

# --- ⚡ PERFORMANCE CACHE ⚡ ---
@st.cache_resource
def get_openai_client(api_key):
    if api_key and api_key.startswith("sk-") and api_key != "mock":
        try: return OpenAI(api_key=api_key)
        except: return None
    return None

# --- 🔗 IMPORT SETTINGS ---
try:
    import client_settings as cs
except ImportError:
    class cs:
        APP_TITLE = "FormFlux"
        PAGE_ICON = "🌊"
        LOGIN_HEADER = "FormFlux"
        TAGLINE = "Fluid Forms"
        CLIENT_NAME = "FormFlux"
        ACCESS_CODES = ["TEST"]
        LAWYER_EMAIL = "admin@example.com"
        FINAL_SIGNATURE_TEXT = "Sign below."
        CONSENT_TEXT = "I agree."

# --- 🛠️ SETUP PAGE ---
st.set_page_config(
    page_title=cs.APP_TITLE, 
    page_icon=cs.PAGE_ICON, 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- 🗣️ TRANSLATION DICTIONARY ---
UI_LANG = {
    "🇺🇸 English": {
        "welcome": "Welcome to the Secure Client Portal.",
        "start": "START SESSION",
        "next": "NEXT ➡️",
        "back": "⬅️ BACK",
        "submit": "✅ SUBMIT FORM",
        "input_req": "⚠️ Input Required",
        "access_label": "Access Code",
        "firm_login": "⚖️ Firm Login",
        "dashboard_btn": "ENTER DASHBOARD ➡️",
        "logout": "⬅️ LOGOUT",
        "reset": "🔄 RESET / LOGOUT"
    },
    "🇪🇸 Español": {
        "welcome": "Bienvenido al Portal Seguro.",
        "start": "INICIAR SESIÓN",
        "next": "SIGUIENTE ➡️",
        "back": "⬅️ ANTERIOR",
        "submit": "✅ ENVIAR FORMULARIO",
        "input_req": "⚠️ Requerido",
        "access_label": "Código de Acceso",
        "firm_login": "⚖️ Acceso Abogado",
        "dashboard_btn": "ENTRAR AL PANEL ➡️",
        "logout": "⬅️ CERRAR SESIÓN",
        "reset": "🔄 REINICIAR"
    },
    "🇫🇷 Français": { "welcome": "Bienvenue.", "start": "COMMENCER", "next": "SUIVANT ➡️", "back": "⬅️ RETOUR", "submit": "✅ SOUMETTRE", "input_req": "⚠️ Requis", "access_label": "Code d'accès", "firm_login": "⚖️ Accès Avocat", "dashboard_btn": "TABLEAU DE BORD ➡️", "logout": "⬅️ DÉCONNEXION", "reset": "🔄 RÉINITIALISER" },
    "🇩🇪 Deutsch": { "welcome": "Willkommen.", "start": "STARTEN", "next": "WEITER ➡️", "back": "⬅️ ZURÜCK", "submit": "✅ ABSENDEN", "input_req": "⚠️ Erforderlich", "access_label": "Zugangscode", "firm_login": "⚖️ Anwalt Login", "dashboard_btn": "DASHBOARD ➡️", "logout": "⬅️ ABMELDEN", "reset": "🔄 ZURÜCKSETZEN" },
    "🇧🇷 Português": { "welcome": "Bem-vindo.", "start": "INICIAR", "next": "PRÓXIMO ➡️", "back": "⬅️ VOLTAR", "submit": "✅ ENVIAR", "input_req": "⚠️ Obrigatório", "access_label": "Código", "firm_login": "⚖️ Acesso Advogado", "dashboard_btn": "PAINEL ➡️", "logout": "⬅️ SAIR", "reset": "🔄 REINICIAR" },
    "🇨🇳 中文": { "welcome": "欢迎", "start": "开始", "next": "下一步 ➡️", "back": "⬅️ 上一步", "submit": "✅ 提交", "input_req": "⚠️ 必填", "access_label": "访问代码", "firm_login": "⚖️ 律师登录", "dashboard_btn": "进入仪表板 ➡️", "logout": "⬅️ 退出", "reset": "🔄 重置" }
}

# --- 🔄 STATE INITIALIZATION ---
if "user_mode" not in st.session_state: st.session_state.user_mode = "client"
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "form_data" not in st.session_state: st.session_state.form_data = {}
if "idx" not in st.session_state: st.session_state.idx = -1
if "language" not in st.session_state: st.session_state.language = "🇺🇸 English"
if "high_contrast" not in st.session_state: st.session_state.high_contrast = False
if "font_size" not in st.session_state: st.session_state.font_size = "Normal"

# Helper Function for Translations
def t(key):
    lang_dict = UI_LANG.get(st.session_state.language, UI_LANG["🇺🇸 English"])
    return lang_dict.get(key, key)

# --- 🎨 DYNAMIC CSS ENGINE ---
# 1. Font Size Logic
font_css = ""
if st.session_state.font_size == "Large":
    font_css = "html, body, [class*='css'] { font-size: 20px !important; }"
elif st.session_state.font_size == "Extra Large":
    font_css = "html, body, [class*='css'] { font-size: 24px !important; }"

# 2. Theme Logic (Switch between Midnight & High Contrast)
if st.session_state.high_contrast:
    # ⚪ HIGH CONTRAST MODE
    theme_css = """
    .stApp { background-color: #ffffff !important; color: #000000 !important; }
    div.block-container { background: #ffffff; border: 3px solid #000000; color: black; border-radius: 0px; }
    .stButton>button { background: #000000 !important; color: #ffff00 !important; border: 3px solid #000000; border-radius: 0px; font-weight: 900; }
    .stTextInput>div>div>input { background-color: #ffffff; color: black; border: 2px solid black; }
    h1, h2, h3, h4, p, span, div, label { color: #000000 !important; font-family: Arial, sans-serif !important; }
    """
else:
    # 🌑 MIDNIGHT FLUX MODE
    theme_css = """
    .stApp {
        background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #1f4068);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        color: white;
    }
    div.css-1r6slb0, div.stDataFrame {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 20px;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: rgba(0, 0, 0, 0.3) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    label, .stRadio, .stCheckbox { color: white !important; }
    button { border: 1px solid #00d4ff !important; color: #00d4ff !important; background: transparent !important; }
    button:hover { background: #00d4ff !important; color: black !important; }
    """

# Inject CSS
st.markdown(f"<style>{theme_css} {font_css} #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}}</style>", unsafe_allow_html=True)

# --- ⚡ MAGIC LINK AUTO-LOGIN ---
query_params = st.query_params
magic_code = query_params.get("code")

if magic_code:
    if magic_code == "CLIENT-9921" or magic_code in cs.ACCESS_CODES:
        if not st.session_state.authenticated:
            st.session_state.authenticated = True
            st.session_state.user_mode = "client"
            st.success("🔓 Authorized.")
            time.sleep(0.5)
            st.rerun()

# --- 🛡️ SIDEBAR CONTROLS ---
with st.sidebar:
    # 1. DISPLAY SETTINGS (RESTORED!)
    with st.expander("👁️ Display & Language"):
        st.session_state.language = st.selectbox("Language", list(UI_LANG.keys()))
        st.divider()
        st.session_state.high_contrast = st.toggle("High Contrast Mode", value=st.session_state.high_contrast)
        st.session_state.font_size = st.select_slider("Text Size", options=["Normal", "Large", "Extra Large"])
        if st.button("Apply Settings"): st.rerun()
        
    st.divider()

    # 2. RESET BUTTON
    if st.button(t("reset"), type="primary"):
        st.session_state.clear()
        st.rerun()
    
    st.divider()

    # 3. FIRM LOGIN
    st.title(t("firm_login"))
    admin_pass = st.text_input("Password", type="password", label_visibility="collapsed")
    if st.button(t("dashboard_btn")):
        if admin_pass == "1234" or admin_pass == st.secrets.get("ADMIN_PASS", "admin"):
            st.session_state.user_mode = "lawyer"
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("⛔ Unauthorized")
            
    if st.session_state.user_mode == "lawyer":
        st.divider()
        if st.button(t("logout")):
            st.session_state.user_mode = "client"
            st.rerun()

# =========================================================
# 🏛️ MODE 1: LAWYER DASHBOARD
# =========================================================
if st.session_state.user_mode == "lawyer":
    st.title("💼 Firm Command Center")
    
    tab_dispatch, tab_inspect, tab_logs = st.tabs(["🚀 Dispatcher", "🔍 PDF Inspector", "🗄️ Logs"])
    
    with tab_dispatch:
        st.subheader("Send New Invite")
        with st.form("dispatch_form"):
            selected_forms = st.multiselect("Select Forms", options=list(FORM_LIBRARY.keys()))
            client_name = st.text_input("Client Name", value="Lee White")
            submitted = st.form_submit_button("📤 GENERATE LINK")
            if submitted and selected_forms:
                base_url = "https://formflux.streamlit.app" 
                query_string = "&".join([f"form={urllib.parse.quote(f)}" for f in selected_forms])
                magic_link = f"{base_url}/?{query_string}&code=CLIENT-9921"
                st.success(f"Link Created for {client_name}")
                st.code(magic_link)

    with tab_inspect:
        st.subheader("🛠️ Universal Field Finder")
        uploaded_pdf = st.file_uploader("Upload PDF Template", type="pdf")
        if uploaded_pdf:
            try:
                reader = pypdf.PdfReader(uploaded_pdf)
                fields = reader.get_fields()
                if fields:
                    st.write("### ✅ Smart Field Detection:")
                    code_block = "{\n"
                    for field_name, data in fields.items():
                        field_type = "text"
                        options_str = ""
                        if '/FT' in data and data['/FT'] == '/Btn':
                            field_type = "checkbox" 
                            options_str = ', "options": ["True", "False"]'
                        readable = field_name.replace("_", " ").title()
                        code_block += f'    "{field_name}": {{ "description": "What is {readable}?", "type": "{field_type}"{options_str} }},\n'
                    code_block += "}"
                    st.code(code_block, language="python")
            except Exception as e:
                st.error(f"Error: {e}")

    with tab_logs:
        st.dataframe(load_logs(), use_container_width=True)

# =========================================================
# 🌊 MODE 2: CLIENT INTAKE
# =========================================================
else:
    # --- CLIENT LOGIN GATE ---
    if not st.session_state.authenticated:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.title(f"🌊 {cs.LOGIN_HEADER}")
            st.info(f"{t('welcome')} {t('access_label')}:")
            
            code = st.text_input(t("access_label"), type="password")
            if st.button(t("start")):
                if code in cs.ACCESS_CODES or code == "CLIENT-9921": 
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Invalid Code")
        st.stop()

    # --- CLIENT FORM ---
    pre_selected_forms = query_params.get_all("form")
    if pre_selected_forms:
        active_form_name = pre_selected_forms[0]
        st.toast(f"📂 Loaded: {active_form_name}")
    else:
        active_form_name = st.selectbox("Select Form", list(FORM_LIBRARY.keys()))

    client = get_openai_client(st.secrets.get("OPENAI_API_KEY"))
    current_config = FORM_LIBRARY.get(active_form_name, list(FORM_LIBRARY.values())[0])
    fields = list(current_config["fields"].keys())
    # PASS LANGUAGE TO WIZARD
    wizard = PolyglotWizard(client, current_config["fields"], user_language=st.session_state.language)
    
    if "total_steps" not in st.session_state: st.session_state.total_steps = len(fields)
    
    if st.session_state.idx == -1:
        st.title(cs.CLIENT_NAME)
        st.write(t("welcome"))
        if st.button(t("start")):
            st.session_state.idx = 0
            st.rerun()
            
    elif st.session_state.idx < len(fields):
        curr_field_key = fields[st.session_state.idx]
        field_info = current_config["fields"][curr_field_key]
        
        q_text = wizard.generate_question(curr_field_key)
        st.markdown(f"### {q_text}")
        
        ftype = field_info.get("type", "text")
        
        if ftype == "text":
            default_val = st.session_state.form_data.get(curr_field_key, "")
            ans = st.text_input(t("input_req"), value=default_val, label_visibility="collapsed")
            
        elif ftype == "radio":
            opts = field_info.get("options", ["Yes", "No"])
            current_idx = 0
            if curr_field_key in st.session_state.form_data:
                try: current_idx = opts.index(st.session_state.form_data[curr_field_key])
                except: pass
            ans = st.radio("Select:", opts, index=current_idx)
            
        elif ftype == "checkbox":
            default_bool = False
            if st.session_state.form_data.get(curr_field_key) == "Yes": default_bool = True
            check = st.checkbox(field_info.get("description", "Check here"), value=default_bool)
            ans = "Yes" if check else "No"

        st.markdown("---")
        c1, c2 = st.columns(2)
        if c1.button(t("back")):
            st.session_state.idx -= 1
            st.rerun()
        if c2.button(t("next")):
            if ans: 
                st.session_state.form_data[curr_field_key] = ans
                st.session_state.idx += 1
                st.rerun()
            else:
                st.toast(t("input_req"))
            
    elif st.session_state.idx == len(fields):
        st.balloons()
        st.success(t("submit"))
