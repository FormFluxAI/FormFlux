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

# --- 🔄 STATE INITIALIZATION (MUST BE AT TOP) ---
if "user_mode" not in st.session_state: st.session_state.user_mode = "client"
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "language" not in st.session_state: st.session_state.language = "🇺🇸 English"
if "high_contrast" not in st.session_state: st.session_state.high_contrast = False
if "font_size" not in st.session_state: st.session_state.font_size = "Normal"
if "terms_accepted" not in st.session_state: st.session_state.terms_accepted = False
if "intake_method" not in st.session_state: st.session_state.intake_method = None # 'manual' or 'ai'
if "chat_history" not in st.session_state: st.session_state.chat_history = [] 
if "form_queue" not in st.session_state: st.session_state.form_queue = [] 
if "current_form_index" not in st.session_state: st.session_state.current_form_index = 0
if "form_data" not in st.session_state: st.session_state.form_data = {} 
if "idx" not in st.session_state: st.session_state.idx = -1 
if "uploaded_files" not in st.session_state: st.session_state.uploaded_files = []

# --- 🗣️ GLOBAL TRANSLATION ENGINE ---
UI_LANG = {
    "🇺🇸 English": {
        "welcome": "Welcome to the Secure Client Portal.",
        "terms_header": "📜 Terms of Service & Disclaimer",
        "terms_body": "By proceeding, you acknowledge that FormFluxAI is a technology provider, not a law firm. We do not provide legal advice.",
        "agree_btn": "I AGREE & PROCEED ➡️",
        "choose_title": "🤖 Choose Your Assistant",
        "choose_desc": "How would you like to complete your forms today?",
        "mode_manual": "📝 Manual Mode",
        "mode_manual_desc": "Fill out forms step-by-step.",
        "mode_ai": "💬 AI Assistant",
        "mode_ai_desc": "Chat with an AI that fills forms for you.",
        "progress": "Your Intake Progress",
        "upload_header": "📂 The Vault: Secure Uploads",
        "sign_header": "✍️ Final Authorization",
        "finish_btn": "✅ SUBMIT ENTIRE PACKET",
        "next_form": "✅ Form Complete! Proceed to Next ➡️",
        "reset": "🔄 RESET / LOGOUT",
        "input_req": "⚠️ Required"
    },
    "🇪🇸 Español": {
        "welcome": "Bienvenido al Portal Seguro.",
        "terms_header": "📜 Términos de Servicio",
        "terms_body": "Al continuar, reconoce que FormFluxAI es un proveedor de tecnología, no un bufete de abogados.",
        "agree_btn": "ACEPTO Y CONTINÚO ➡️",
        "choose_title": "🤖 Elija su Asistente",
        "choose_desc": "¿Cómo desea completar sus formularios?",
        "mode_manual": "📝 Modo Manual",
        "mode_manual_desc": "Llenar paso a paso.",
        "mode_ai": "💬 Asistente IA",
        "mode_ai_desc": "Chatea con la IA.",
        "progress": "Su Progreso",
        "upload_header": "📂 Bóveda de Documentos",
        "sign_header": "✍️ Autorización Final",
        "finish_btn": "✅ ENVIAR PAQUETE",
        "next_form": "✅ ¡Completado! Siguiente ➡️",
        "reset": "🔄 REINICIAR",
        "input_req": "⚠️ Requerido"
    },
    # Add other languages (French, German, etc.) here as needed
}

def t(key):
    lang_dict = UI_LANG.get(st.session_state.language, UI_LANG["🇺🇸 English"])
    return lang_dict.get(key, key)

# --- 🎨 CSS ENGINE ---
font_css = ""
if st.session_state.font_size == "Large":
    font_css = "html, body, [class*='css'] { font-size: 20px !important; }"
elif st.session_state.font_size == "Extra Large":
    font_css = "html, body, [class*='css'] { font-size: 24px !important; }"

if st.session_state.high_contrast:
    theme_css = """
    .stApp { background-color: #ffffff !important; color: #000000 !important; }
    div.block-container { background: #ffffff; border: 3px solid #000000; color: black; border-radius: 0px; }
    .stButton>button { background: #000000 !important; color: #ffff00 !important; border: 3px solid #000000; border-radius: 0px; font-weight: 900; }
    .stTextInput>div>div>input { background-color: #ffffff; color: black; border: 2px solid black; }
    h1, h2, h3, h4, p, span, div, label { color: #000000 !important; font-family: Arial, sans-serif !important; }
    """
else:
    theme_css = """
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
    """

st.markdown(f"""
<style>
    {theme_css} 
    {font_css}
    
    /* LINK DISPLAY BOX */
    .link-box {{
        background-color: #222;
        padding: 15px;
        border: 1px dashed #00d4ff;
        border-radius: 5px;
        font-family: monospace;
        color: #00d4ff;
        word-break: break-all;
    }}
    
    /* CHAT BUBBLES */
    .chat-user {{ background-color: #00d4ff; color: black; padding: 10px; border-radius: 10px; margin: 5px; text-align: right; }}
    .chat-ai {{ background-color: #333; color: white; border: 1px solid #555; padding: 10px; border-radius: 10px; margin: 5px; text-align: left; }}
    
    /* HIDE 'PRESS ENTER TO APPLY' TEXT */
    div[data-testid="InputInstructions"] {{
        display: none !important;
    }}
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
            if pre_selected_forms:
                st.session_state.form_queue = pre_selected_forms
            st.rerun()

# --- 🛡️ SIDEBAR ---
with st.sidebar:
    # 1. ACCESSIBILITY RESTORED
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
    # --- PHASE 1: LOGIN ---
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

    # --- PHASE 2: TERMS OF SERVICE ---
    if not st.session_state.terms_accepted:
        st.title(t("terms_header"))
        st.markdown(t("terms_body"))
        agree = st.checkbox("I have read and agree to these terms.")
        if st.button(t("agree_btn")):
            if agree:
                st.session_state.terms_accepted = True
                if not st.session_state.form_queue:
                    st.session_state.form_queue = list(FORM_LIBRARY.keys())
                st.rerun()
            else:
                st.error("You must agree to proceed.")
        st.stop()

    # --- PHASE 3: CHOOSE YOUR PATH (AI vs MANUAL) ---
    if st.session_state.intake_method is None:
        st.title(t("choose_title"))
        st.markdown(t("choose_desc"))
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.info(f"### {t('mode_manual')}")
            st.write(t('mode_manual_desc'))
            if st.button("USE MANUAL MODE"):
                st.session_state.intake_method = "manual"
                st.rerun()
                
        with col_b:
            st.success(f"### {t('mode_ai')}")
            st.write(t('mode_ai_desc'))
            if st.button("CHAT WITH ASSISTANT"):
                st.session_state.intake_method = "ai"
                st.session_state.chat_history.append({"role": "ai", "content": f"Hello! I see you have {len(st.session_state.form_queue)} forms to complete. I can help you fill them all out just by chatting. What is your full legal name?"})
                st.rerun()
        st.stop()

    # --- PHASE 4A: AI CHAT MODE ---
    if st.session_state.intake_method == "ai":
        st.title(t("mode_ai"))
        
        # Chat History
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                role_class = "chat-ai" if msg["role"] == "ai" else "chat-user"
                st.markdown(f"<div class='{role_class}'>{msg['content']}</div>", unsafe_allow_html=True)

        # Chat Input
        user_input = st.chat_input("Type your answer here...")
        
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # SIMULATED LOGIC (Placeholder for Real AI)
            response = "Got it. I've updated that on all your forms. Next: What is your current address?"
            if len(user_input) > 0:
                # Update background data
                st.session_state.form_data["Client_Name"] = user_input
            
            time.sleep(1) 
            st.session_state.chat_history.append({"role": "ai", "content": response})
            st.rerun()
            
        with st.expander("🕵️ Debug: See What The AI Is Filling"):
            st.json(st.session_state.form_data)
            
        if st.button("✅ I'M DONE CHATTING - REVIEW FORMS"):
             # Switch back to manual to review/sign
             st.session_state.intake_method = "manual"
             st.session_state.current_form_index = 0
             st.rerun()

    # --- PHASE 4B: MANUAL TURBO-FLOW MODE ---
    elif st.session_state.intake_method == "manual":
        
        # CHECK IF QUEUE DONE -> GO TO VAULT
        if st.session_state.current_form_index >= len(st.session_state.form_queue):
            # === THE VAULT (FINAL STEP) ===
            st.title(t("upload_header"))
            
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

        # === FORM FILLING ===
        active_form_name = st.session_state.form_queue[st.session_state.current_form_index]
        
        # Progress Bar
        forms_done = st.session_state.current_form_index
        total_forms = len(st.session_state.form_queue)
        st.caption(f"📝 FORM {forms_done + 1} OF {total_forms}: {active_form_name}")
        st.progress(forms_done / total_forms)

        # Load Form Config
        client = get_openai_client(st.secrets.get("OPENAI_API_KEY"))
        current_config = FORM_LIBRARY.get(active_form_name, list(FORM_LIBRARY.values())[0])
        fields = list(current_config["fields"].keys())
        wizard = PolyglotWizard(client, current_config["fields"], user_language=st.session_state.language)
        
        if st.session_state.idx == -1:
            st.title(active_form_name)
            st.write("Please answer the following questions.")
            if st.button("START THIS FORM"):
                st.session_state.idx = 0
                st.rerun()
                
        elif st.session_state.idx < len(fields):
            curr_key = fields[st.session_state.idx]
            field_info = current_config["fields"][curr_key]
            q_text = wizard.generate_question(curr_key)
            
            st.markdown(f"### {q_text}")
            
            widget_key = f"{active_form_name}_{st.session_state.idx}"
            ftype = field_info.get("type", "text")
            
            # PRE-FILL IF DATA EXISTS (FROM AI CHAT OR PREVIOUS)
            default_val = st.session_state.form_data.get(curr_key, "")
            
            if ftype == "text":
                ans = st.text_input(t("input_req"), value=default_val, key=widget_key, label_visibility="collapsed")
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
