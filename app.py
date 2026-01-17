import streamlit as st
import os
from PIL import Image
from openai import OpenAI
from backend import PolyglotWizard, IdentityStamper
from config import FORM_LIBRARY
from dispatcher import send_secure_email
from sms import send_sms_alert
from logger import log_submission, load_logs
from bugs import log_bug
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="FormFlux | Justin White", page_icon="🌊")

# --- LOGIN GATE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔒 FormFlux Portal")
    st.caption("Fluid Forms for a Flexible World")
    code = st.text_input("Access Code", type="password")
    if st.button("Enter"):
        if code in ["JUSTIN-ADMIN", "WHITE-LEGAL", "TEST-JW"]:
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
# We do this early so the Sidebar can see the variables
if "form_data" not in st.session_state: st.session_state.form_data = {}
if "idx" not in st.session_state: st.session_state.idx = -1  # -1 = Welcome Screen
selected_name_pre = list(FORM_LIBRARY.keys())[0] # Default

# --- SIDEBAR ---
with st.sidebar:
    st.header("FormFlux Intake")
    st.caption("Owner: Justin White")
    selected_name = st.selectbox("Select Document", list(FORM_LIBRARY.keys()))
    
    # --- FIXED PROGRESS BAR LOGIC ---
    if "total_steps" in st.session_state and st.session_state.total_steps > 0:
        # 1. If on Welcome Screen (-1), treat as 0
        safe_idx = max(0, st.session_state.idx)
        # 2. If we went past the questions (Stages 2,3,4), cap it at 100%
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

# Set Total Steps based on number of questions
if "total_steps" not in st.session_state: st.session_state.total_steps = len(fields)

# ==========================================
# STAGE 0: WELCOME SCREEN
# ==========================================
if st.session_state.idx == -1:
    st.title(f"👋 Welcome to {selected_name}")
    st.info("You are about to begin a secure legal intake process.")
    
    st.markdown("""
    ### 📝 What to Expect:
    1. **Answer a few simple questions** regarding your case.
    2. **Verify your Identity** with a selfie and photo ID.
    3. **Review your answers** for accuracy.
    4. **Sign digitally** to submit your file directly to Justin White.
    
    *This process is encrypted and secure.*
    """)
    
    if st.button("🚀 Start Intake"):
        st.session_state.idx = 0
        st.rerun()

# ==========================================
# STAGE 1: QUESTIONS (One at a time)
# ==========================================
elif st.session_state.idx < len(fields):
    curr_field = fields[st.session_state.idx]
    
    # Generate the AI question (or use cached one)
    if f"q_{st.session_state.idx}" not in st.session_state:
        q_text = wizard.generate_question(curr_field)
        st.session_state[f"q_{st.session_state.idx}"] = q_text
    else:
        q_text = st.session_state[f"q_{st.session_state.idx}"]

    # UI
    st.title(f"Question {st.session_state.idx + 1} of {len(fields)}")
    st.markdown(f"### 🤖 {q_text}")
    
    # Form Input
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
        # Reset to start if they need to change something
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
    st.write("By signing below, you attest that the information provided is true.")
    
    sig = st_canvas(stroke_width=2, height=150, key="sig")
    st.caption("By clicking Submit, I agree to receive SMS updates about my case.")
    
    if st.button("🚀 Finalize & Submit Case"):
        if sig.image_data is not None:
            with st.spinner("Encrypting and submitting..."):
                # Save Assets
                with open("temp_selfie.jpg","wb") as f: f.write(st.session_state.temp_selfie.getbuffer())
                with open("temp_id.jpg","wb") as f: f.write(st.session_state.temp_id.getbuffer())
                Image.fromarray(sig.image_data.astype('uint8'),'RGBA').save("temp_sig.png")
                
                # Generate PDF
                stamper = IdentityStamper(current_config['filename'])
                final_pdf = stamper.compile_final_doc(st.session_state.form_data, "temp_sig.png", "temp_selfie.jpg", "temp_id.jpg")
                
                # Email
                client_name = st.session_state.form_data.get("txt_FirstName", "Client")
                target_email = current_config.get("recipient_email", "admin@example.com")
                send_secure_email(final_pdf, client_name, target_email)
                log_submission(client_name, selected_name, "Success")
                
                # SMS
                phone = st.secrets.get("LAWYER_PHONE_NUMBER")
                if phone: 
                    try:
                        send_sms_alert(client_name, selected_name, phone)
                        st.toast("SMS Alert Sent")
                    except:
                        pass # Ignore SMS failures for user experience
                
                st.success("✅ Case Filed Successfully!")
                st.balloons()
