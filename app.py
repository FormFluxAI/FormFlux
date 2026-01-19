import streamlit as st
import streamlit.components.v1 as components
import os
import time
import urllib.parse
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

# --- 🛠️ FORCE SIDEBAR OPEN ---
st.set_page_config(
    page_title=cs.APP_TITLE, 
    page_icon=cs.PAGE_ICON, 
    layout="centered", 
    initial_sidebar_state="expanded" 
)

# --- 🛡️ EXIT GUARD ---
components.html("""
<script>
    window.parent.window.onbeforeunload = function() {
        return "Unsaved changes. Leave?";
    };
</script>
""", height=0)

# --- 🗣️ TRANSLATION ENGINE ---
UI_LANG = {
    "🇺🇸 English": { "welcome": "Welcome", "start": "START", "next": "NEXT", "back": "BACK", "submit": "SUBMIT", "legal_warning": "Not a lawyer.", "terms": "I agree." },
}

# --- 🎨 SESSION STATE ---
if "high_contrast" not in st.session_state: st.session_state.high_contrast = False
if "font_size" not in st.session_state: st.session_state.font_size = "Normal"
if "language" not in st.session_state: st.session_state.language = "🇺🇸 English"

# --- 🕵️‍♂️ MAGIC LINK DETECTOR ---
query_params = st.query_params
pre_selected_form = query_params.get("form", None)

def t(key):
    lang_dict = UI_LANG.get(st.session_state.language, UI_LANG["🇺🇸 English"])
    return lang_dict.get(key, key)

# --- 🎨 CONSTRUCTION MODE CSS (HIGH VISIBILITY) ---
st.markdown("""
<style>
    /* MAKE SIDEBAR UGLY BUT VISIBLE */
    section[data-testid="stSidebar"] {
        background-color: #222222 !important; /* Dark Grey */
        border-right: 5px solid #ff0000 !important; /* Red Border to see where it ends */
    }
    
    /* FORCE TEXT COLOR IN SIDEBAR */
    section[data-testid="stSidebar"] * {
        color: #ffffff !important; /* Bright White Text */
    }

    /* MAKE EXPANDERS STAND OUT */
    div[data-testid="stExpander"] {
        background-color: #444444 !important;
        border: 2px solid #00ff00 !important; /* Green Border around the Command Center */
        border-radius: 5px;
    }
    
    /* INPUT BOXES */
    input {
        color: black !important;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIN GATE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title(f"🌊 {cs.LOGIN_HEADER}")
    code = st.text_input("Enter Access Code (Try: TEST)", type="password")
    if st.button("AUTHENTICATE"):
        if code in cs.ACCESS_CODES:
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("⛔ Access Denied")
    st.stop()

client = get_openai_client(st.secrets.get("OPENAI_API_KEY"))

# --- STATE ---
if "form_data" not in st.session_state: st.session_state.form_data = {}
if "idx" not in st.session_state: st.session_state.idx = -1

# --- SIDEBAR & DISPATCHER ---
with st.sidebar:
    st.header("📍 SIDEBAR IS HERE")
    st.info("If you see this, the sidebar is working.")
    
    available_forms = list(FORM_LIBRARY.keys())
    selected_name = st.selectbox("Current File", available_forms)
    
    st.divider()
    st.markdown("### 👇 CLICK BELOW 👇")
    
    # THE COMMAND CENTER
    with st.expander("💼 LAWYER COMMAND CENTER (CLICK ME)"):
        st.write("🔴 Admin Panel Unlocked")
        admin_pass = st.text_input("Admin Password (Try: 1234)", type="password")
        
        if admin_pass == "1234":
            st.success("✅ ACCESS GRANTED")
            st.markdown("### 🚀 Dispatcher")
            st.write("Send a magic link to a client:")
            if st.button("📨 Simulate Sending Link"):
                st.success("Link Sent!")

# --- MAIN LOGIC (Simplified for Visual Test) ---
current_config = FORM_LIBRARY[selected_name]
fields = list(current_config["fields"].keys())
wizard = PolyglotWizard(client, current_config["fields"], user_language=st.session_state.language)

if st.session_state.idx == -1:
    st.title("Main App Area")
    st.write("Look to the left for the sidebar.")
    if st.button("Start Form"):
        st.session_state.idx = 0
        st.rerun()
elif st.session_state.idx < len(fields):
    st.write(f"Question: {fields[st.session_state.idx]}")
    st.text_input("Answer")
    if st.button("Next"):
        st.session_state.idx += 1
        st.rerun()
