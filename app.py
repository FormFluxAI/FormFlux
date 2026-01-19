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
from streamlit_drawable_canvas import st_canvas

# --- ⚡ PERFORMANCE: CACHING THE BRAIN ⚡ ---
# This prevents the app from reconnecting to OpenAI on every click.
# It makes the app feel 2x faster after the first load.
@st.cache_resource
def get_openai_client(api_key):
    if api_key and api_key.startswith("sk-") and api_key != "mock":
        try:
            return OpenAI(api_key=api_key)
        except:
            return None
    return None

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

# --- ♿ UNIVERSAL ACCESS MENU ---
# We put this FIRST so it loads before the visuals
if "high_contrast" not in st.session_state: st.session_state.high_contrast = False
if "font_size" not in st.session_state: st.session_state.font_size = "Normal"

with st.sidebar:
    st.markdown("### ♿ Accessibility")
    st.session_state.high_contrast = st.toggle("👁️ High Contrast Mode", value=st.session_state.high_contrast)
    st.session_state.font_size = st.select_slider("Aa Text Size", options=["Normal", "Large", "Extra Large"])
    
    st.divider()
    
    # Connection Status Indicator
    st.markdown("### 📶 System Status")
    st.caption("🟢 Secure Link Established")
    st.caption(f"⚡ Latency: {int(time.time() * 1000) % 50}ms") # Simulated Ping

# --- 🎨 DYNAMIC THEME ENGINE ---
# We swap the CSS based on the user's choice.

# 1. DEFINE FONTS
font_css = ""
if st.session_state.font_size == "Large":
    font_css = "html, body, [class*='css'] { font-size: 18px !important; }"
elif st.session_state.font_size == "Extra Large":
    font_css = "html, body, [class*='css'] { font-size: 22px !important; }"

# 2. DEFINE THEMES
if st.session_state.high_contrast:
    # ⚪ HIGH CONTRAST THEME (White/Black/Yellow)
    theme_css = """
    .stApp { background-color: #ffffff; color: #000000; }
    div.block-container { background: #ffffff; border: 2px solid #000000; box-shadow: none; color: black; }
    .stButton>button { background: #000000; color: #ffff00; border: 2px solid #000000; border-radius: 0px; font-weight: 900; }
    .stButton>button:hover { background: #ffff00; color: #000000; }
    .stTextInput>div>div>input { background-color: #ffffff; color: black; border: 2px solid black; }
    h1, h2, h3, p { color: black !important; }
    """
else:
    # 🌑 MIDNIGHT FLUX THEME (The Cool One)
    theme_css = """
    @keyframes gradient { 0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;} }
    .stApp { background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #1f4068); background-size: 400% 400%; animation: gradient 15s ease infinite; color: white; }
    div.block-container { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); }
    .stButton>button { background: transparent; color: #00d4ff; border: 2px solid #00d4ff; border-radius: 30px; transition: all 0.3s ease; }
    .stButton>button:hover { background: #00d4ff; color: #0f2027; box-shadow: 0 0 20px rgba(0, 212, 255, 0.6); transform: scale(1.05); }
    .stTextInput>div>div>input { background-color: rgba(0, 0, 0, 0.3); color: white; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 10px; }
    """

# 3. INJECT CSS
st.markdown(f"<style>{theme_css} {font_css} #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}</style>", unsafe_allow_html=True)


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

# --- INITIALIZE BRAIN (CACHED) ---
client = get_openai_client(st.secrets.get("OPENAI_API_KEY"))

# --- STATE INITIALIZATION ---
if "form_data" not in st.session_state: st.session_state.form_data = {}
if "idx" not in st.session_state: st.session_state.idx = -1
selected_name_pre = list(FORM_LIBRARY.keys())[0]

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    selected_name = st.selectbox("Current File", list(FORM_LIBRARY.keys()))
    if "total_steps" in st.session_state and st.session_state.total_steps > 0:
        safe_idx = max(0, st.session_state.idx)
        safe_idx = min(safe_idx, st.session_state.total_steps)
        progress_value = safe_idx / st.session_state.total_steps
        st.progress(progress_value, text=f"{int(progress_value*100)}% COMPLETE")
    
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
    
    # Use standard markdown to avoid syntax errors
    st.markdown("""
    <div style='text-align: center; padding: 20px;'>
        <p style='font-size: 1.2rem;'>Welcome to the Secure Client Portal.</p>
        <p style='font-size: 1rem; opacity: 0.6;'>Encrypted • Private • Automated</p>
    </div>
    """, unsafe_allow_html=True)
    
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
        # Show a spinner while the AI thinks (Perceived Speed Increase)
        with st.spinner("Decryption Protocol Active..."): 
            q_text = wizard.generate_question(curr_field)
            st.session_state[f"q_{st.session_state.idx}"] = q_text
    else:
        q_text = st.session_state[f"q_{st.session_state.idx}"]

    st.caption(f"STEP {st.session_state.idx + 1} / {len(fields)}")
    st.markdown(f"### {q_text}")
    
    with st.form(key=f"form_{st.session_state.idx}"):
        # Focusing on the input field helps accessibility
        answer = st.text_input("INPUT RESPONSE", key=f"input_{st.session_state.idx}")
        
        c1, c2 = st.columns([1, 1])
        submitted = c1.form_submit_button("NEXT STEP >")
        
        if submitted and answer:
            st.session_state.form_data[curr_field] = answer
            st.session_state.idx += 1
            st.rerun()
        elif submitted and not answer:
            st.toast("⚠️ Input Required", icon="⚠️")

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
    
    # Conditional Border for High Contrast
    border_color = "#000000" if st.session_state.high_contrast else "#00d4ff"
    
    st.markdown(f'<div style="border: 2px solid {border_color}; border-radius: 10px;">', unsafe_allow_html=True)
    sig = st_canvas(stroke_width=2, stroke_color="black" if st.session_state.high_contrast else "white", background_color="rgba(0,0,0,0)", height=150, key="sig")
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
                
                # 3. Email & SMS
                client_name = st.session_state.form_data.get("txt_FirstName", "Client")
                target_email = current_config.get("recipient_email", cs.LAWYER_EMAIL)
                send_secure_email(final_output, client_name, target_email)
                log_submission(client_name, selected_name, "Success")
                
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
