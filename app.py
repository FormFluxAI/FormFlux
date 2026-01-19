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
# 🎨 UI OVERHAUL: THE "FLUX" THEME
# ==========================================
# This CSS hides the framework branding and makes it look like Custom Software.
st.markdown("""
<style>
    /* 1. HIDE STREAMLIT BRANDING */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 2. BACKGROUND & FONTS */
    .stApp {
        background-color: #f8f9fa; /* Light Grey Clean Background */
    }
    
    /* 3. FLUID BUTTONS */
    .stButton>button {
        background: linear-gradient(45deg, #0077b6, #00b4d8);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 10px 25px;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
        color: white;
    }

    /* 4. CARD-LIKE CONTAINERS */
    div.block-container {
        background-color: white;
        padding: 3rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        max-width: 800px;
        margin-top: 2rem;
    }
    
    /* 5. INPUT FIELDS */
    .stTextInput>div>div>input {
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        padding: 10px;
    }
    
    /* 6. PROGRESS BAR FLUX */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #0077b6, #90e0ef);
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIN GATE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title(f"🌊 {cs.LOGIN_HEADER}")
        st.caption(cs.TAGLINE)
        st.divider()
        code = st.text_input("Enter Access Code", type="password")
        if st.button("Secure Login"):
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

# --- SIDEBAR (Hidden Logic) ---
# We keep the sidebar minimalist
with st.sidebar:
    st.markdown("### ⚙️ Control Panel")
    selected_name = st.selectbox("Current File", list(FORM_LIBRARY.keys()))
    
    # Progress Bar
    if "total_steps" in st.session_state and st.session_state.total_steps > 0:
        safe_idx = max(0, st.session_state.idx)
        safe_idx = min(safe_idx, st.session_state.total_steps)
        progress_value = safe_idx / st.session_state.total_steps
        st.progress(progress_value, text=f"{int(progress_value*100)}% Complete")
    
    st.divider()
    with st.expander("🔐 Admin Only"):
        if st.text_input("Admin Password", type="password") == st.secrets.get("ADMIN_PASS", "admin"):
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
    st.image("https://img.icons8.com/clouds/200/overview-pages-3.png", width=150) # Placeholder Flux Icon
    st.title(cs.CLIENT_NAME)
    st.markdown(f"#### {cs.TAGLINE}")
    st.info("Secure Intake Portal • 256-bit Encrypted Session")
    
    st.markdown("""
    **Start your intake process below.** * Please have your ID ready.
    * This session will time out if left inactive.
    """)
    
    if st.button("🚀 Begin Secure Session"):
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

    # UI: Clean Question Header
    st.caption(f"Step {st.session_state.idx + 1} of {len(fields)}")
    st.markdown(f"### {q_text}")
    
    with st.form(key=f"form_{st.session_state.idx}"):
        answer = st.text_input("Type your answer here...", key=f"input_{st.session_state.idx}")
        
        c1, c2 = st.columns([1, 4])
        submitted = c1.form_submit_button("Next Step ➡️")
        
        if submitted and answer:
            st.session_state.form_data[curr_field] = answer
            st.session_state.idx += 1
            st.rerun()
        elif submitted and not answer:
            st.toast("⚠️ Answer required to proceed.")

# ==========================================
# STAGE 2: BIOMETRICS
# ==========================================
elif st.session_state.idx == len(fields):
    st.title("🆔 Biometric Verification")
    st.markdown("We need to verify your identity to prevent fraud.")
    
    tab1, tab2 = st.tabs(["📸 Selfie", "💳 ID Card"])
    
    with tab1:
        selfie = st.camera_input("Take a photo of yourself")
    with tab2:
        gov_id = st.file_uploader("Upload Government ID", type=['jpg', 'png', 'jpeg'])
    
    if selfie and gov_id:
        st.session_state.temp_selfie = selfie
        st.session_state.temp_id = gov_id
        st.success("Verification Data Captured.")
        if st.button("Continue to Review ➡️"):
            st.session_state.idx += 1
            st.rerun()

# ==========================================
# STAGE 3: REVIEW ANSWERS
# ==========================================
elif st.session_state.idx == len(fields) + 1:
    st.title("📋 Final Review")
    st.markdown("Please confirm the details below.")
    
    with st.container():
        for key, value in st.session_state.form_data.items():
            label = current_config["fields"][key]["description"]
            st.text_input(label, value=value, disabled=True)
        
    c1, c2 = st.columns(2)
    if c1.button("✏️ Edit Answers"):
        st.session_state.idx = 0 
        st.rerun()
        
    if c2.button("✅ Confirm & Continue"):
        st.session_state.idx += 1
        st.rerun()

# ==========================================
# STAGE 4: SIGN & SUBMIT
# ==========================================
elif st.session_state.idx == len(fields) + 2:
    st.title("✍️ Digital Signature")
    st.markdown(f"*{cs.FINAL_SIGNATURE_TEXT}*")
    
    # Canvas with a border for better UX
    st.markdown('<div style="border: 2px dashed #ccc; border-radius: 10px;">', unsafe_allow_html=True)
    sig = st_canvas(stroke_width=2, height=150, key="sig")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.caption(f"🔒 {cs.CONSENT_TEXT}")
    
    if st.button("🚀 Finalize & Submit Case"):
        if sig.image_data is not None:
            with st.spinner("Encrypting, Stamping, and Transmitting..."):
                # 1. Save Assets
                with open("temp_selfie.jpg","wb") as f: f.write(st.session_state.temp_selfie.getbuffer())
                with open("temp_id.jpg","wb") as f: f.write(st.session_state.temp_id.getbuffer())
                Image.fromarray(sig.image_data.astype('uint8'),'RGBA').save("temp_sig.png")
                
                # 2. GENERATE PDF (Bundle vs Single)
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
                st.success("✅ Case Filed Successfully!")
                time.sleep(5)
                st.session_state.clear()
                st.rerun()
