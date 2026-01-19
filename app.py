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

# --- 🛠️ SETUP PAGE ---
st.set_page_config(
    page_title=cs.APP_TITLE, 
    page_icon=cs.PAGE_ICON, 
    layout="wide", # <--- WIDE MODE FOR DASHBOARD
    initial_sidebar_state="collapsed"
)

# --- 🎨 SESSION STATE ---
if "user_mode" not in st.session_state: st.session_state.user_mode = "client" # or 'lawyer'
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
    @keyframes gradient { 0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;} }
    
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
# If URL has ?form=..., force Client Mode
query_params = st.query_params
pre_selected_forms = query_params.get_all("form") # Can now accept multiple!

if pre_selected_forms:
    st.session_state.user_mode = "client"

# --- 🛡️ SIDEBAR LOGIN (LAWYER DOOR) ---
with st.sidebar:
    st.title("⚖️ Firm Login")
    admin_pass = st.text_input("Lawyer Password", type="password")
    
    # 🔴 LOGIN LOGIC
    if st.button("ENTER DASHBOARD ➡️"):
        # ACCEPT '1234' OR REAL PASSWORD
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
    st.caption(f"Logged in as: {cs.LAWYER_EMAIL}")
    
    # --- TOP ROW: METRICS ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Active Forms", len(FORM_LIBRARY))
    c2.metric("Pending Intakes", "3") # Placeholder for DB connection
    c3.metric("System Status", "🟢 Online")
    
    st.divider()
    
    # --- MAIN ACTION: CREATE PACKET ---
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("🚀 Send New Invite")
        st.markdown("Select one or multiple forms for the client.")
        
        with st.form("dispatch_form"):
            # MULTI-SELECT FOR FORMS
            selected_forms = st.multiselect(
                "Select Forms to Include", 
                options=list(FORM_LIBRARY.keys())
            )
            
            st.markdown("---")
            client_phone = st.text_input("Client Phone (+1...)")
            client_email = st.text_input("Client Email")
            method = st.radio("Send via:", ["SMS", "Email", "Generate Link Only"])
            
            submitted = st.form_submit_button("📤 SEND PACKET")
            
            if submitted and selected_forms:
                # 1. BUILD MAGIC LINK
                base_url = "https://formflux.streamlit.app"
                
                # Create query string: ?form=Divorce&form=NDA
                query_string = "&".join([f"form={urllib.parse.quote(f)}" for f in selected_forms])
                magic_link = f"{base_url}/?{query_string}"
                
                # 2. EXECUTE
                st.success("✅ Intake Packet Created!")
                
                if method == "Generate Link Only":
                    st.code(magic_link)
                else:
                    st.info(f"Simulating {method} to {client_phone or client_email}...")
                    st.code(magic_link, language="text")
                    # Here is where you would call send_sms_alert(magic_link)
    
    with col_right:
        st.subheader("🗄️ Recent Activity")
        # Load the logs
        logs = load_logs()
        st.dataframe(logs, use_container_width=True)

# =========================================================
# 🌊 MODE 2: CLIENT INTAKE (THE FLUID FORM)
# =========================================================
else:
    # --- CLIENT LOGIN GATE ---
    if not st.session_state.authenticated and not pre_selected_forms:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.title(f"🌊 {cs.LOGIN_HEADER}")
            st.info("Clients: Please enter your Access Code. Lawyers: Use sidebar.")
            code = st.text_input("Client Access Code", type="password")
            if st.button("START SESSION"):
                if code in cs.ACCESS_CODES:
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Invalid Code")
        st.stop()

    # --- CLIENT FORM LOGIC ---
    # Determine which form to show
    if pre_selected_forms:
        # If magic link used, lock to those forms
        active_form_name = pre_selected_forms[0] # Handle first form for now (Multi-form wizard logic comes next)
        st.success(f"📂 Open File: {active_form_name}")
    else:
        # Fallback to selector if logged in manually
        active_form_name = st.selectbox("Select Form", list(FORM_LIBRARY.keys()))

    # Load Form
    client = get_openai_client(st.secrets.get("OPENAI_API_KEY"))
    current_config = FORM_LIBRARY.get(active_form_name, list(FORM_LIBRARY.values())[0])
    fields = list(current_config["fields"].keys())
    wizard = PolyglotWizard(client, current_config["fields"], user_language=st.session_state.language)

    # ... (STANDARD WIZARD LOGIC CONTINUES BELOW) ...
    # This is the same wizard logic as before, just wrapped in the "else" block.
    
    if "total_steps" not in st.session_state: st.session_state.total_steps = len(fields)
    
    # WIZARD UI (Simplified for this pasted block to fit)
    if st.session_state.idx == -1:
        st.title(cs.CLIENT_NAME)
        st.write("Welcome to your secure intake.")
        if st.button("BEGIN"):
            st.session_state.idx = 0
            st.rerun()
            
    elif st.session_state.idx < len(fields):
        curr_field = fields[st.session_state.idx]
        q_text = wizard.generate_question(curr_field)
        st.markdown(f"### {q_text}")
        ans = st.text_input("Your Answer")
        if st.button("NEXT ➡️"):
            st.session_state.form_data[curr_field] = ans
            st.session_state.idx += 1
            st.rerun()
            
    elif st.session_state.idx == len(fields):
        st.success("Form Complete. (Biometrics/Signing logic here)")
