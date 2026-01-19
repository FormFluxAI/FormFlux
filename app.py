import streamlit as st
import streamlit.components.v1 as components
import os
import time
import urllib.parse
import pandas as pd
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
        APP_TITLE = "She's Always Right, Esq."
        PAGE_ICON = "⚖️"
        LOGIN_HEADER = "The Boss is In"
        TAGLINE = "Just ask her husband."
        CLIENT_NAME = "She's Always Right, Esq."
        ACCESS_CODES = ["TEST", "GWEN-RULES"]
        LAWYER_EMAIL = "gwendolyn@alwaysright.com"
        FINAL_SIGNATURE_TEXT = "I certify the above is true."
        CONSENT_TEXT = "I officially agree."

# --- 🛠️ SETUP PAGE ---
st.set_page_config(
    page_title=cs.APP_TITLE, 
    page_icon=cs.PAGE_ICON, 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- 🔄 STATE INITIALIZATION ---
if "user_mode" not in st.session_state: st.session_state.user_mode = "client"
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "language" not in st.session_state: st.session_state.language = "🇺🇸 English"
if "terms_accepted" not in st.session_state: st.session_state.terms_accepted = False
if "intake_method" not in st.session_state: st.session_state.intake_method = None # 'manual' or 'ai'
if "chat_history" not in st.session_state: st.session_state.chat_history = [] # For AI Chat
if "form_queue" not in st.session_state: st.session_state.form_queue = [] 
if "current_form_index" not in st.session_state: st.session_state.current_form_index = 0
if "form_data" not in st.session_state: st.session_state.form_data = {} 
if "idx" not in st.session_state: st.session_state.idx = -1 
if "uploaded_files" not in st.session_state: st.session_state.uploaded_files = []

# --- 🗣️ TRANSLATION & CSS (Condensed for brevity) ---
UI_LANG = { "🇺🇸 English": { "welcome": "Welcome", "reset": "🔄 RESET" } } # (Keep full list in real app)
def t(key): return UI_LANG.get("🇺🇸 English", {}).get(key, key)

st.markdown("""
<style>
    /* THEME CSS */
    .stApp { background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #1f4068); color: white; background-size: 400% 400%; animation: gradient 15s ease infinite; }
    div.block-container { background: rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 20px; }
    .stTextInput>div>div>input, .stSelectbox>div>div>div { background-color: rgba(0, 0, 0, 0.3) !important; color: white !important; border: 1px solid rgba(255, 255, 255, 0.2); }
    label, p, h1, h2, h3 { color: white !important; }
    button { border: 1px solid #00d4ff !important; color: #00d4ff !important; background: transparent !important; }
    div[data-testid="InputInstructions"] { display: none !important; }
    
    /* CHAT BUBBLES */
    .chat-user { background-color: #00d4ff; color: black; padding: 10px; border-radius: 10px; margin: 5px; text-align: right; }
    .chat-ai { background-color: #333; color: white; border: 1px solid #555; padding: 10px; border-radius: 10px; margin: 5px; text-align: left; }
</style>
""", unsafe_allow_html=True)

# --- ⚡ MAGIC LINK AUTO-LOGIN ---
query_params = st.query_params
magic_code = query_params.get("code")
pre_selected_forms = query_params.get_all("form")

if magic_code:
    if magic_code == "CLIENT-9921" or magic_code in cs.ACCESS_CODES:
        if not st.session_state.authenticated:
            st.session_state.authenticated = True
            st.session_state.user_mode = "client"
            if pre_selected_forms: st.session_state.form_queue = pre_selected_forms
            st.rerun()

# --- 🛡️ SIDEBAR ---
with st.sidebar:
    if st.button("🔄 RESET / LOGOUT", type="primary"):
        st.session_state.clear()
        st.rerun()
    st.divider()
    st.title("⚖️ Firm Login")
    admin_pass = st.text_input("Password", type="password", label_visibility="collapsed")
    if st.button("ENTER DASHBOARD ➡️"):
        if admin_pass == "1234":
            st.session_state.user_mode = "lawyer"
            st.session_state.authenticated = True
            st.rerun()

# =========================================================
# 🏛️ LAWYER DASHBOARD
# =========================================================
if st.session_state.user_mode == "lawyer":
    st.title(f"💼 {cs.CLIENT_NAME} Dashboard")
    tab1, tab2 = st.tabs(["🚀 Dispatcher", "🗄️ Files"])
    with tab1:
        with st.form("dispatch"):
            sel = st.multiselect("Select Forms", list(FORM_LIBRARY.keys()))
            if st.form_submit_button("GENERATE LINK") and sel:
                q = "&".join([f"form={urllib.parse.quote(f)}" for f in sel])
                st.code(f"https://formflux.streamlit.app/?{q}&code=CLIENT-9921")
    with tab2:
        st.dataframe(load_logs(), use_container_width=True)

# =========================================================
# 🌊 CLIENT EXPERIENCE
# =========================================================
else:
    # 1. LOGIN
    if not st.session_state.authenticated:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.title(cs.CLIENT_NAME)
            code = st.text_input("Access Code", type="password")
            if st.button("START"): 
                if code in cs.ACCESS_CODES or code == "CLIENT-9921": 
                    st.session_state.authenticated = True; st.rerun()
        st.stop()

    # 2. TERMS
    if not st.session_state.terms_accepted:
        st.title("📜 Terms of Service")
        st.warning("FormFluxAI is a technology provider, not a law firm.")
        if st.checkbox("I Agree") and st.button("PROCEED"):
            st.session_state.terms_accepted = True
            if not st.session_state.form_queue: st.session_state.form_queue = list(FORM_LIBRARY.keys())
            st.rerun()
        st.stop()

    # 3. CHOOSE YOUR PATH (NEW!)
    if st.session_state.intake_method is None:
        st.title("🤖 Choose Your Assistant")
        st.markdown("How would you like to complete your forms today?")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.info("### 📝 Manual Mode")
            st.write("Fill out the forms step-by-step using standard text boxes.")
            if st.button("Use Manual Mode"):
                st.session_state.intake_method = "manual"
                st.rerun()
                
        with col_b:
            st.success("### 💬 AI Assistant (BETA)")
            st.write("Chat with our AI. It asks you questions and fills ALL forms at once.")
            if st.button("Chat with Assistant"):
                st.session_state.intake_method = "ai"
                # Seed the chat with a welcome message
                st.session_state.chat_history.append({"role": "ai", "content": f"Hello! I see you need to complete {len(st.session_state.form_queue)} forms today. I can help you fill them all out just by chatting. What is your full legal name?"})
                st.rerun()
        st.stop()

    # 4a. AI CHAT MODE (THE NEW FEATURE)
    if st.session_state.intake_method == "ai":
        st.title("💬 AI Legal Assistant")
        
        # Display Chat History
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                role_class = "chat-ai" if msg["role"] == "ai" else "chat-user"
                st.markdown(f"<div class='{role_class}'>{msg['content']}</div>", unsafe_allow_html=True)

        # Chat Input
        user_input = st.chat_input("Type your answer here...")
        
        if user_input:
            # 1. Show User Message
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # 2. SIMULATED AI BRAIN (This is where the OpenAI Code will go later)
            # For now, we simulate the "Ask Once, Fill Everywhere" logic
            response = "Got it. I've updated that on all your forms. Next question: What is your current address?"
            
            # Simulated Logic: If they type "Justin", we update the 'form_data' in the background
            if "name" in user_input.lower() or len(user_input) > 0:
                # Update the invisible master data
                st.session_state.form_data["Client_Name"] = user_input
                st.session_state.form_data["Husband_Name"] = user_input
                st.session_state.form_data["Tenant_Name"] = user_input
            
            time.sleep(1) # Fake thinking time
            st.session_state.chat_history.append({"role": "ai", "content": response})
            st.rerun()
            
        with st.expander("🕵️ Debug: See What The AI Is Filling"):
            st.json(st.session_state.form_data)

    # 4b. MANUAL MODE (OLD LOGIC)
    elif st.session_state.intake_method == "manual":
        # ... (Previous Manual Code Logic Goes Here) ...
        # For brevity in this paste, I'll put a simplified version so you can test the toggle.
        
        active_form = st.session_state.form_queue[st.session_state.current_form_index]
        st.title(f"📝 {active_form}")
        st.text_input("Manual Input Example")
        if st.button("Next Form"):
            if st.session_state.current_form_index < len(st.session_state.form_queue) - 1:
                st.session_state.current_form_index += 1
                st.rerun()
            else:
                st.success("All Done!")
