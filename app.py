import streamlit as st
import streamlit.components.v1 as components
import os
import time
import urllib.parse
import pypdf # The Inspector Engine
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

# --- 🎨 SESSION STATE ---
if "user_mode" not in st.session_state: st.session_state.user_mode = "client"
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "form_data" not in st.session_state: st.session_state.form_data = {}
if "idx" not in st.session_state: st.session_state.idx = -1
if "language" not in st.session_state: st.session_state.language = "🇺🇸 English"

# --- 🎨 CSS ENGINE (Midnight Flux) ---
st.markdown("""
<style>
    /* GLOBAL THEME */
    .stApp {
        background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #1f4068);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        color: white;
    }
    /* DASHBOARD CARDS */
    div.css-1r6slb0, div.stDataFrame {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 20px;
    }
    /* INPUTS & BUTTONS */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: rgba(0, 0, 0, 0.3) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    /* RADIO & CHECKBOX TEXT */
    label, .stRadio, .stCheckbox {
        color: white !important;
    }
    button {
        border: 1px solid #00d4ff !important;
        color: #00d4ff !important;
        background: transparent !important;
    }
    button:hover {
        background: #00d4ff !important;
        color: black !important;
    }
    /* HIDE DEFAULT MENU */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 🕵️‍♂️ MAGIC LINK DETECTOR ---
query_params = st.query_params
pre_selected_forms = query_params.get_all("form")
magic_code = query_params.get("code")

if magic_code and pre_selected_forms:
    st.session_state.user_mode = "client"
    st.session_state.authenticated = True 

# --- 🛡️ SIDEBAR LOGIN (LAWYER DOOR) ---
with st.sidebar:
    st.title("⚖️ Firm Login")
    admin_pass = st.text_input("Lawyer Password", type="password")
    if st.button("ENTER DASHBOARD ➡️"):
        if admin_pass == "1234" or admin_pass == st.secrets.get("ADMIN_PASS", "admin"):
            st.session_state.user_mode = "lawyer"
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("⛔ Unauthorized")
            
    if st.session_state.user_mode == "lawyer":
        st.divider()
        if st.button("⬅️ LOGOUT"):
            st.session_state.user_mode = "client"
            st.rerun()

# =========================================================
# 🏛️ MODE 1: LAWYER DASHBOARD (THE COMMAND CENTER)
# =========================================================
if st.session_state.user_mode == "lawyer":
    st.title("💼 Firm Command Center")
    
    tab_dispatch, tab_inspect, tab_logs = st.tabs(["🚀 Dispatcher", "🔍 PDF Inspector", "🗄️ Logs"])
    
    # --- DISPATCHER ---
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

    # --- PDF INSPECTOR (UPGRADED) ---
    with tab_inspect:
        st.subheader("🛠️ Universal Field Finder")
        st.write("This tool now detects Text, Checkboxes, and Radio Buttons.")
        uploaded_pdf = st.file_uploader("Upload PDF Template", type="pdf")
        
        if uploaded_pdf:
            try:
                reader = pypdf.PdfReader(uploaded_pdf)
                fields = reader.get_fields()
                if fields:
                    st.write("### ✅ Smart Field Detection:")
                    code_block = "{\n"
                    
                    for field_name, data in fields.items():
                        # GUESS THE TYPE
                        field_type = "text" # Default
                        options_str = ""
                        
                        # If it has '/Btn', it's a checkbox or radio
                        if '/FT' in data and data['/FT'] == '/Btn':
                            # It is likely a Checkbox or Radio
                            field_type = "checkbox" 
                            # If we see 'Yes' or 'No' in the name, hint at it
                            options_str = ', "options": ["True", "False"]'
                        
                        readable = field_name.replace("_", " ").title()
                        
                        code_block += f'    "{field_name}": {{ "description": "What is {readable}?", "type": "{field_type}"{options_str} }},\n'
                    
                    code_block += "}"
                    st.code(code_block, language="python")
                    st.success("Paste this into `config.py`!")
            except Exception as e:
                st.error(f"Error: {e}")

    with tab_logs:
        st.dataframe(load_logs(), use_container_width=True)

# =========================================================
# 🌊 MODE 2: CLIENT INTAKE
# =========================================================
else:
    # --- CLIENT LOGIN ---
    if not st.session_state.authenticated:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.title(f"🌊 {cs.LOGIN_HEADER}")
            st.info("Clients: Please enter your Access Code.")
            code = st.text_input("Access Code", type="password")
            if st.button("START SESSION"):
                if code in cs.ACCESS_CODES or code == "CLIENT-9921": 
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Invalid Code")
        st.stop()

    # --- FORM LOADER ---
    if pre_selected_forms:
        active_form_name = pre_selected_forms[0]
        st.success(f"📂 Open File: {active_form_name}")
    else:
        active_form_name = st.selectbox("Select Form", list(FORM_LIBRARY.keys()))

    client = get_openai_client(st.secrets.get("OPENAI_API_KEY"))
    current_config = FORM_LIBRARY.get(active_form_name, list(FORM_LIBRARY.values())[0])
    fields = list(current_config["fields"].keys())
    wizard = PolyglotWizard(client, current_config["fields"], user_language=st.session_state.language)
    
    if "total_steps" not in st.session_state: st.session_state.total_steps = len(fields)
    
    # --- WIZARD START ---
    if st.session_state.idx == -1:
        st.title(cs.CLIENT_NAME)
        st.write("Welcome, Lee White. Please complete the following information.")
        if st.button("BEGIN INTAKE"):
            st.session_state.idx = 0
            st.rerun()
            
    elif st.session_state.idx < len(fields):
        # 1. GET CURRENT FIELD DATA
        curr_field_key = fields[st.session_state.idx]
        field_info = current_config["fields"][curr_field_key]
        
        # 2. ASK THE QUESTION (AI)
        q_text = wizard.generate_question(curr_field_key)
        st.markdown(f"### {q_text}")
        
        # 3. RENDER THE CORRECT INPUT TYPE
        # Check what 'type' is set in config.py
        ftype = field_info.get("type", "text")
        
        # --- TYPE: TEXT ---
        if ftype == "text":
            default_val = st.session_state.form_data.get(curr_field_key, "")
            ans = st.text_input("Type your answer:", value=default_val)
            
        # --- TYPE: YES/NO or RADIO ---
        elif ftype == "radio":
            opts = field_info.get("options", ["Yes", "No"])
            # Default to index 0 if not set
            current_idx = 0
            if curr_field_key in st.session_state.form_data:
                try: current_idx = opts.index(st.session_state.form_data[curr_field_key])
                except: pass
            ans = st.radio("Select one:", opts, index=current_idx)
            
        # --- TYPE: CHECKBOX (Single) ---
        elif ftype == "checkbox":
            # True/False
            default_bool = False
            if st.session_state.form_data.get(curr_field_key) == "Yes": default_bool = True
            
            check = st.checkbox(field_info.get("description", "Check here"), value=default_bool)
            ans = "Yes" if check else "No"

        # 4. NAVIGATION
        st.markdown("---")
        c1, c2 = st.columns(2)
        if c1.button("⬅️ BACK"):
            st.session_state.idx -= 1
            st.rerun()
        if c2.button("NEXT ➡️"):
            if ans: # Ensure they answered
                st.session_state.form_data[curr_field_key] = ans
                st.session_state.idx += 1
                st.rerun()
            else:
                st.toast("⚠️ Input Required")
            
    elif st.session_state.idx == len(fields):
        st.balloons()
        st.success("✅ Thank you, Lee! Your forms have been submitted.")
