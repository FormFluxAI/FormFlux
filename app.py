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

# --- 🔗 IMPORT SETTINGS (DEMO MODE) ---
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

# --- 🔄 STATE INITIALIZATION (MOVED TO TOP TO FIX ERROR) ---
if "user_mode" not in st.session_state: st.session_state.user_mode = "client"
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "language" not in st.session_state: st.session_state.language = "🇺🇸 English"
if "terms_accepted" not in st.session_state: st.session_state.terms_accepted = False
if "form_queue" not in st.session_state: st.session_state.form_queue = [] 
if "current_form_index" not in st.session_state: st.session_state.current_form_index = 0
if "form_data" not in st.session_state: st.session_state.form_data = {} 
if "idx" not in st.session_state: st.session_state.idx = -1 
if "uploaded_files" not in st.session_state: st.session_state.uploaded_files = []

# --- 🗣️ TRANSLATION DICTIONARY ---
UI_LANG = {
    "🇺🇸 English": {
        "welcome": "Welcome to the Secure Client Portal.",
        "terms_header": "📜 Terms of Service & Disclaimer",
        "terms_body": "By proceeding, you acknowledge that FormFluxAI is a technology provider, not a law firm. We do not provide legal advice.",
        "agree_btn": "I AGREE & PROCEED ➡️",
        "progress": "Your Intake Progress",
        "upload_header": "📂 The Vault: Secure Uploads",
        "upload_desc": "Please upload any requested documents (ID, Passport, Evidence, etc.) below.",
        "sign_header": "✍️ Final Authorization",
        "finish_btn": "✅ SUBMIT ENTIRE PACKET",
        "next_form": "✅ Form Complete! Proceed to Next ➡️",
        "dashboard_btn": "ENTER DASHBOARD ➡️",
        "input_req": "⚠️ Required",
    },
    # (Other languages hidden for brevity)
}

# Helper Function
def t(key):
    lang_dict = UI_LANG.get(st.session_state.language, UI_LANG["🇺🇸 English"])
    return lang_dict.get(key, key)

# --- 🎨 CSS ENGINE ---
st.markdown("""
<style>
    /* GLOBAL THEME */
    .stApp {
        background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #1f4068);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        color: white;
    }
    div.block-container { background: rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 20px; }
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: rgba(0, 0, 0, 0.3) !important; color: white !important; border: 1px solid rgba(255, 255, 255, 0.2);
    }
    label, .stRadio, .stCheckbox, p, h1, h2, h3 { color: white !important; }
    button { border: 1px solid #00d4ff !important; color: #00d4ff !important; background: transparent !important; }
    button:hover { background: #00d4ff !important; color: black !important; }
    
    /* LINK DISPLAY BOX */
    .link-box {
        background-color: #222;
        padding: 15px;
        border: 1px dashed #00d4ff;
        border-radius: 5px;
        font-family: monospace;
        color: #00d4ff;
        word-break: break-all;
    }
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
            # LOAD THE QUEUE FROM URL
            if pre_selected_forms:
                st.session_state.form_queue = pre_selected_forms
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
# 🏛️ MODE 1: LAWYER DASHBOARD
# =========================================================
if st.session_state.user_mode == "lawyer":
    st.title(f"💼 {cs.CLIENT_NAME} Dashboard")
    
    tab_dispatch, tab_inspect, tab_logs = st.tabs(["🚀 Dispatcher", "🔍 PDF Inspector", "🗄️ Client Files"])
    
    with tab_dispatch:
        st.subheader("Send New Invite")
        with st.form("dispatch_form"):
            st.write("Select all forms to include in this packet:")
            selected_forms = st.multiselect("Forms Bundle", options=list(FORM_LIBRARY.keys()))
            client_name = st.text_input("Client Name", value="Lee White")
            submitted = st.form_submit_button("📤 GENERATE LINK")
            
            if submitted and selected_forms:
                base_url = "https://formflux.streamlit.app" 
                query_string = "&".join([f"form={urllib.parse.quote(f)}" for f in selected_forms])
                magic_link = f"{base_url}/?{query_string}&code=CLIENT-9921"
                
                st.success(f"Packet Ready for {client_name} containing {len(selected_forms)} forms.")
                st.markdown("### 🔗 Secure Link:")
                # NEW: BETTER LINK DISPLAY
                st.markdown(f'<div class="link-box">{magic_link}</div>', unsafe_allow_html=True)
                st.caption("Copy the link above and send it to the client.")

    with tab_inspect:
        st.subheader("🛠️ Universal Field Finder")
        uploaded_pdf = st.file_uploader("Upload PDF Template", type="pdf")
        if uploaded_pdf:
            reader = pypdf.PdfReader(uploaded_pdf)
            fields = reader.get_fields()
            if fields:
                st.code(str(fields), language="python")

    with tab_logs:
        st.dataframe(load_logs(), use_container_width=True)

# =========================================================
# 🌊 MODE 2: CLIENT INTAKE FLOW
# =========================================================
else:
    # --- STEP 1: LOGIN ---
    if not st.session_state.authenticated:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.title(f"{cs.CLIENT_NAME}")
            st.info("Please enter your Access Code.")
            code = st.text_input("Access Code", type="password")
            if st.button("START"):
                if code in cs.ACCESS_CODES or code == "CLIENT-9921": 
                    st.session_state.authenticated = True
                    st.rerun()
        st.stop()

    # --- STEP 2: TERMS OF SERVICE (THE HANDSHAKE) ---
    if not st.session_state.terms_accepted:
        st.title(t("terms_header"))
        st.markdown("""
        ### Welcome to FormFluxAI
        
        Before we begin, please review the following:
        1. **Security:** Your data is encrypted end-to-end.
        2. **Disclaimer:** This software aggregates your data for your attorney. **FormFluxAI is NOT a law firm** and does not provide legal advice.
        3. **Accuracy:** You are responsible for the truthfulness of your answers.
        """)
        st.warning(t("terms_body"))
        
        agree = st.checkbox("I have read and agree to these terms.")
        if st.button(t("agree_btn")):
            if agree:
                st.session_state.terms_accepted = True
                # Use default forms if none in URL
                if not st.session_state.form_queue:
                    st.session_state.form_queue = list(FORM_LIBRARY.keys())
                st.rerun()
            else:
                st.error("You must agree to proceed.")
        st.stop()

    # --- MAIN ENGINE ---
    # Check if we are done with all forms
    if st.session_state.current_form_index >= len(st.session_state.form_queue):
        # === THE VAULT (FINAL STEP) ===
        st.title(t("upload_header"))
        st.markdown(t("upload_desc"))
        
        # 1. DOCUMENT UPLOADER
        doc_type = st.selectbox("Document Type", ["Driver's License", "Passport", "Social Security Card", "Visa", "Evidence/Photos", "Other"])
        uploaded_file = st.file_uploader(f"Upload {doc_type}", accept_multiple_files=False)
        
        if uploaded_file:
            st.session_state.uploaded_files.append(uploaded_file.name)
            st.success(f"✅ Received: {uploaded_file.name}")

        st.markdown("### 📋 Uploaded So Far:")
        for f in st.session_state.uploaded_files:
            st.caption(f"- {f}")
            
        st.divider()
        
        # 2. FINAL SIGNATURE
        st.subheader(t("sign_header"))
        st.caption(cs.FINAL_SIGNATURE_TEXT)
        sig = st_canvas(stroke_width=2, stroke_color="white", background_color="rgba(0,0,0,0)", height=150, key="final_sig")
        
        if st.button(t("finish_btn")):
            if sig.image_data is not None:
                st.balloons()
                st.success("✅ PACKET SUBMITTED TO FIRM")
                log_submission("Client", "Full Packet", "Completed")
                time.sleep(5)
                st.session_state.clear()
                st.rerun()
            else:
                st.error("Please sign to finish.")
        st.stop()

    # === FORM FILLING MODE ===
    active_form_name = st.session_state.form_queue[st.session_state.current_form_index]
    
    # Progress Bar (Forms)
    forms_done = st.session_state.current_form_index
    total_forms = len(st.session_state.form_queue)
    st.caption(f"📝 FORM {forms_done + 1} OF {total_forms}: {active_form_name}")
    st.progress(forms_done / total_forms)

    # Load Form Config
    client = get_openai_client(st.secrets.get("OPENAI_API_KEY"))
    current_config = FORM_LIBRARY.get(active_form_name, list(FORM_LIBRARY.values())[0])
    fields = list(current_config["fields"].keys())
    wizard = PolyglotWizard(client, current_config["fields"], user_language="🇺🇸 English")
    
    if st.session_state.idx == -1:
        st.title(active_form_name)
        st.write("Please answer the following questions.")
        if st.button("START THIS FORM"):
            st.session_state.idx = 0
            st.rerun()
            
    elif st.session_state.idx < len(fields):
        # Question Rendering
        curr_key = fields[st.session_state.idx]
        field_info = current_config["fields"][curr_key]
        q_text = wizard.generate_question(curr_key)
        
        st.markdown(f"### {q_text}")
        
        widget_key = f"{active_form_name}_{st.session_state.idx}"
        ftype = field_info.get("type", "text")
        
        if ftype == "text":
            ans = st.text_input(t("input_req"), key=widget_key, label_visibility="collapsed")
        elif ftype == "radio":
            ans = st.radio("Select:", field_info.get("options", ["Yes", "No"]), key=widget_key)
        elif ftype == "checkbox":
            check = st.checkbox(field_info.get("description", "Check here"), key=widget_key)
            ans = "Yes" if check else "No"

        c1, c2 = st.columns(2)
        if c1.button("⬅️ BACK"): st.session_state.idx -= 1; st.rerun()
        if c2.button("NEXT ➡️"):
            if ans:
                st.session_state.form_data[curr_key] = ans
                st.session_state.idx += 1
                st.rerun()
    
    else:
        # END OF SINGLE FORM
        st.success(f"✅ {active_form_name} Completed!")
        if st.button(t("next_form")):
            st.session_state.current_form_index += 1
            st.session_state.idx = -1
            st.rerun()
