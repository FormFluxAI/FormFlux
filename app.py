import streamlit as st
import os
import time
from PIL import Image
from openai import OpenAI
from backend import PolyglotWizard, IdentityStamper
from config import FORM_LIBRARY
from dispatcher import send_secure_email
from sms import send_sms_alert
from logger import log_submission, load_logs
from bugs import log_bug
from streamlit_drawable_canvas import st_canvas

# --- 🔗 IMPORT CLIENT SETTINGS ---
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

st.set_page_config(page_title=cs.APP_TITLE, page_icon=cs.PAGE_ICON, layout="centered")

# ==========================================
# 🎨 UI OVERHAUL: "MIDNIGHT FLUX" THEME
# ==========================================
st.markdown("""
<style>
    /* 1. ANIMATED BACKGROUND */
    @keyframes gradient {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    .stApp {
        background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #1f4068);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        color: white;
    }

    /* 2. GLASSMORPHISM CARD */
    div.block-container {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 3rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        max-width: 700px;
        margin-top: 2rem;
    }

    /* 3. NEON BUTTONS */
    .stButton>button {
        background: transparent;
        color: #00d4ff;
        border: 2px solid #00d4ff;
        border-radius: 30px;
        padding: 12px 30px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 2px;
        transition: all 0.3s ease;
        box-shadow: 0 0 10px rgba(0, 212, 255, 0.1);
    }
    .stButton>button:hover {
        background: #00d4ff;
        color: #0f2027;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.6), 0 0 40px rgba(0, 212, 255, 0.4);
        transform: scale(1.05);
        border-color: #00d4ff;
    }

    /* 4. INPUT FIELDS */
    .stTextInput>div>div>input {
        background-color: rgba(0, 0, 0, 0.3);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        padding: 10px;
    }
    .stTextInput>div>div>input:focus {
        border-color: #00d4ff;
        box-shadow: 0 0 10px rgba(0, 212, 255, 0.2);
    }
    
    /* 5. TEXT COLOR OVERRIDE */
    h1, h2, h3, h4, p, span, div, label {
        color: white !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* 6. HIDE BRANDING */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 7. PROGRESS BAR */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #00d4ff, #00ff9d);
        box-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIN GATE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown(f"<h1 style='text-align: center;'>🌊 {cs.LOGIN_HEADER}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; opacity: 0.8;'>{cs.TAGLINE}</p>", unsafe_allow_html=True)
        st.divider()
        code = st.text_input("Enter Access Code", type="password")
        if st.button("AUTHENTICATE"):
            if code in cs.ACCESS_CODES:
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("⛔ Access Denied")
    st.stop()

# --- SAFETY SWITCH FOR OPENAI ---
api_key = st.secrets.get("OPENAI_API_KEY")
client = None
if api_key and api_key.startswith("sk-") and api_key != "mock":
    try:
        client = OpenAI(api_key=api_key)
    except:
        client = None

# --- STATE INITIALIZATION ---
if "form_data" not in st.session_state: st.session_state.form_data = {}
if "idx" not in st.session_state: st.session_state.idx = -1
selected_name_pre = list(FORM_LIBRARY.keys())[0]

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚙️ CONTROL PANEL")
    selected_name = st.selectbox("Current File", list(FORM_LIBRARY.keys()))
    
    if "total_steps" in st.session_state and st.session_state.total_steps > 0:
        safe_idx = max(0, st.session_state.idx)
        safe_idx = min(safe_idx, st.session_state.total_steps)
        progress_value = safe_idx / st.session_state.total_steps
        st.progress(progress_value, text=f"{int(progress_value*100)}% COMPLETE")
    
    st.divider()
    with st.expander("🔐 ADMIN ACCESS"):
        if st.text_input("Password", type="password") == st.secrets.get("ADMIN_PASS", "admin"):
            st.dataframe(load_logs())

# --- MAIN LOGIC ---
current_config = FORM_LIBRARY[selected_name]
fields = list(current_config["fields"].keys())
wizard = PolyglotWizard(client, current_config["fields"])

if "total_steps" not in st.session_state: st.session_state.total_steps = len(fields)

# ==========================================
# STAGE 0: WELCOME SCREEN
# ==========================================
if st.session_state.idx == -1:
    st.markdown(f"<h1 style='text-align: center;'>{cs.CLIENT_NAME}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center; opacity: 0.7; letter-spacing: 2px;'>{cs.TAGLINE}</h4>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # FIXED: Replaced triple quotes with a safer method to prevent SyntaxError
    st.markdown(
        "<div style='text-align: center; padding: 20px;'>"
        "<p style='font-size: 1.2rem;'>Welcome to the Secure Client Portal.</p>"
        "<p style='font-size: 1rem; opacity: 0.6;'>Encrypted • Private • Automated</p>"
        "</div>", 
        unsafe_allow_html=True
    )
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if st.button("INITIALIZE INTAKE"):
            st.session_state.idx = 0
            st.rerun()

# ==========================================
# STAGE 1: QUESTIONS
# ==========================================
elif st.session_state.idx < len(fields):
    curr_field = fields[st.session_state.idx]
    
    if f"q_{st.session_state.idx}" not in st.session_state:
        q_text = wizard.generate_question(curr_field)
        st.session_state[f"q_{st.session_state.idx}"] = q_text
    else:
        q_text = st.session_state[f"q_{st.session_state.idx}"]

    st.caption(f"STEP {st.session_state.idx + 1} / {len(fields)}")
    st.markdown(f"### {q_text}")
    
    with st.form(key=f"form_{st.session_state.idx}"):
        answer = st.text_input("INPUT RESPONSE", key=f"input_{st.session_state.idx}")
        
        c1, c2 = st.columns([1, 1])
        submitted = c1.form_submit_button("NEXT STEP >")
        
        if submitted and answer:
            st.session_state.form_data[curr_field] = answer
            st.session_state.idx += 1
            st.rerun()
        elif submitted and not answer:
            st.toast("⚠️ Input Required")

# ==========================================
# STAGE 2: BIOMETRICS
# ==========================================
elif st.session_state.idx == len(fields):
    st.markdown("### 🆔 IDENTITY VERIFICATION")
    st.markdown("Please provide biometric data for security compliance.")
    
    tab1, tab2 = st.tabs(["📸 SELFIE", "💳 GOV ID"])
    
    with tab1:
        selfie = st.camera_input("CAPTURE FACE")
    with tab2:
        gov_id = st.file_uploader("UPLOAD DOCUMENT", type=['jpg', 'png', 'jpeg'])
    
    if selfie and gov_id:
        st.session_state.temp_selfie = selfie
        st.session_state.temp_id = gov_id
        st.success("✅ BIOMETRICS SECURED")
        if st.button("PROCEED TO REVIEW >"):
            st.session_state.idx += 1
            st.rerun()

# ==========================================
# STAGE 3: REVIEW ANSWERS
# ==========================================
elif st.session_state.idx == len(fields) + 1:
    st.markdown("### 📋 DATA REVIEW")
    st.markdown("Confirm accuracy of captured data points.")
    
    with st.container():
        for key, value in st.session_state.form_data.items():
            label = current_config["fields"][key]["description"]
            st.text_input(label, value=value, disabled=True)
        
    c1, c2 = st.columns(2)
    if c1.button("✏️ EDIT DATA"):
        st.session_state.idx = 0 
        st.rerun()
        
    if c2.button("✅ CONFIRM DATA"):
        st.session_state.idx += 1
        st.rerun()

# ==========================================
# STAGE 4: SIGN & SUBMIT
# ==========================================
elif st.session_state.idx == len(fields) + 2:
    st.markdown("### ✍️ FINAL AUTHORIZATION")
    st.markdown(f"*{cs.FINAL_SIGNATURE_TEXT}*")
    
    st.markdown('<div style="border: 2px solid #00d4ff; border-radius: 10px; background: rgba(255,255,255,0.1);">', unsafe_allow_html=True)
    sig = st_canvas(stroke_width=2, stroke_color="white", background_color="rgba(0,0,0,0)", height=150, key="sig")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.caption(f"🔒 {cs.CONSENT_TEXT}")
    
    if st.button("🚀 EXECUTE FILING"):
        if sig.image_data is not None:
            with st.spinner("ENCRYPTING & TRANSMITTING..."):
                # 1. Save Assets
                with open("temp_selfie.jpg","wb") as f: f.write(st.session_state.temp_selfie.getbuffer())
                with open("temp_id.jpg","wb") as f: f.write(st.session_state.temp_id.getbuffer())
                Image.fromarray(sig.image_data.astype('uint8'),'RGBA').save("temp_sig.png")
                
                # 2. GENERATE PDF
                final_output = None
                if current_config.get("is_bundle"):
                    stamper = IdentityStamper() 
                    final_output = stamper.compile_bundle(
                        current_config['files'], 
                        st.session_state.form_data, 
                        "temp_sig.png", "temp_selfie.jpg", "temp_id.jpg"
                    )
                else:
                    target_file = current_config.get('filename', 'default.pdf')
                    stamper = IdentityStamper(target_file)
                    final_output = stamper.compile_final_doc(
                        st.session_state.form_data, 
                        "temp_sig.png", "temp_selfie.jpg", "temp_id.jpg"
                    )
                
                # 3. Email
                client_name = st.session_state.form_data.get("txt_FirstName", "Client")
                target_email = current_config.get("recipient_email", cs.LAWYER_EMAIL)
                send_secure_email(final_output, client_name, target_email)
                log_submission(client_name, selected_name, "Success")
                
                # 4. SMS
                phone = st.secrets.get("LAWYER_PHONE_NUMBER")
                if phone: 
                    try: send_sms_alert(client_name, selected_name, phone)
                    except: pass
                
                # 5. SUCCESS STATE
                st.balloons()
                st.success("✅ CASE FILED SUCCESSFULLY.")
                time.sleep(5)
                st.session_state.clear()
                st.rerun()
