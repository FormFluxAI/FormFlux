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
import client_settings as cs 

st.set_page_config(page_title=cs.APP_TITLE, page_icon=cs.PAGE_ICON)

# --- LOGIN GATE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title(f"🔒 {cs.LOGIN_HEADER}")
    st.caption(cs.TAGLINE)
    code = st.text_input("Access Code", type="password")
    if st.button("Enter"):
        # Check against the list in client_settings
        if code in cs.ACCESS_CODES:
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("Invalid Access Code")
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
    st.header(cs.CLIENT_NAME)
    st.caption(cs.TAGLINE)
    selected_name = st.selectbox("Select Document", list(FORM_LIBRARY.keys()))
    
    # Progress Bar
    if "total_steps" in st.session_state and st.session_state.total_steps > 0:
        safe_idx = max(0, st.session_state.idx)
        safe_idx = min(safe_idx, st.session_state.total_steps)
        progress_value = safe_idx / st.session_state.total_steps
        st.progress(progress_value, text=f"Progress: {int(progress_value*100)}%")

    with st.expander("💼 Admin Dashboard"):
        if st.text_input("Admin Pass", type="password") == st.secrets.get("ADMIN_PASS", "admin"):
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
    st.title(f"👋 Welcome to {cs.CLIENT_NAME}")
    st.info(f"You are about to begin a secure legal intake process for {cs.CLIENT_NAME}.")
    
    st.markdown("""
    ### 📝 What to Expect:
    1. **Answer a few simple questions** regarding your case.
    2. **Verify your Identity** with a selfie and photo ID.
    3. **Review your answers** for accuracy.
    4. **Sign digitally** to submit your file.
    """)
    
    if st.button("🚀 Start Intake"):
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

    st.title(f"Question {st.session_state.idx + 1} of {len(fields)}")
    st.markdown(f"### 🤖 {q_text}")
    
    with st.form(key=f"form_{st.session_state.idx}"):
        answer = st.text_input("Your Answer:", key=f"input_{st.session_state.idx}")
        
        c1, c2 = st.columns([1, 5])
        submitted = c1.form_submit_button("Next ➡️")
        
        if submitted and answer:
            st.session_state.form_data[curr_field] = answer
            st.session_state.idx += 1
            st.rerun()
        elif submitted and not answer:
            st.warning("Please provide an answer to continue.")

# ==========================================
# STAGE 2: BIOMETRICS
# ==========================================
elif st.session_state.idx == len(fields):
    st.title("🆔 Identity Verification")
    st.info("Please provide the following to verify your identity.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**1. Take a Selfie**")
        selfie = st.camera_input("Selfie")
    with c2:
        st.markdown("**2. Upload Gov ID**")
        gov_id = st.file_uploader("Upload ID", type=['jpg', 'png', 'jpeg'])
    
    if selfie and gov_id:
        st.session_state.temp_selfie = selfie
        st.session_state.temp_id = gov_id
        if st.button("Continue to Review ➡️"):
            st.session_state.idx += 1
            st.rerun()

# ==========================================
# STAGE 3: REVIEW ANSWERS
# ==========================================
elif st.session_state.idx == len(fields) + 1:
    st.title("📋 Review Your Info")
    st.write("Please verify that all information below is correct.")
    
    for key, value in st.session_state.form_data.items():
        label = current_config["fields"][key]["description"]
        st.text_input(label, value=value, disabled=True)
        
    c1, c2 = st.columns(2)
    if c1.button("✏️ Revise Answers"):
        st.session_state.idx = 0 
        st.rerun()
        
    if c2.button("✅ Information is Correct"):
        st.session_state.idx += 1
        st.rerun()

# ==========================================
# STAGE 4: SIGN & SUBMIT
# ==========================================
elif st.session_state.idx == len(fields) + 2:
    st.title("✍️ Final Signature")
    st.write(cs.FINAL_SIGNATURE_TEXT)
    
    sig = st_canvas(stroke_width=2, height=150, key="sig")
    st.caption(cs.CONSENT_TEXT)
    
    if st.button("🚀 Finalize & Submit Case"):
        if sig.image_data is not None:
            with st.spinner("Encrypting and submitting..."):
                # 1. Save Assets
                with open("temp_selfie.jpg","wb") as f: f.write(st.session_state.temp_selfie.getbuffer())
                with open("temp_id.jpg","wb") as f: f.write(st.session_state.temp_id.getbuffer())
                Image.fromarray(sig.image_data.astype('uint8'),'RGBA').save("temp_sig.png")
                
                # 2. Generate PDF
                stamper = IdentityStamper(current_config['filename'])
                final_pdf = stamper.compile_final_doc(st.session_state.form_data, "temp_sig.png", "temp_selfie.jpg", "temp_id.jpg")
                
                # 3. Email (Uses Config Email)
                client_name = st.session_state.form_data.get("txt_FirstName", "Client")
                target_email = cs.LAWYER_EMAIL # <--- Pulls from client_settings
                send_secure_email(final_pdf, client_name, target_email)
                log_submission(client_name, selected_name, "Success")
                
                # 4. SMS
                phone = st.secrets.get("LAWYER_PHONE_NUMBER")
                if phone: 
                    try:
                        send_sms_alert(client_name, selected_name, phone)
                    except:
                        pass
                
                # 5. END SESSION LOGIC
                st.balloons()
                st.success("✅ Case Filed! This session will close in 5 seconds...")
                time.sleep(5)
                st.session_state.clear()
                st.rerun()
