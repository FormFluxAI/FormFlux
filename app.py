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

# --- SIDEBAR ---
with st.sidebar:
    st.header("FormFlux Intake")
    st.caption("Owner: Justin White")
    if client:
        st.success("🟢 AI Connected")
    else:
        st.info("🟡 Mock Mode Active")
        
    selected_name = st.selectbox("Select Document", list(FORM_LIBRARY.keys()))
    current_config = FORM_LIBRARY[selected_name]
    
    with st.expander("💼 Admin Dashboard"):
        admin_pass = st.secrets.get("ADMIN_PASS", "admin")
        if st.text_input("Admin Pass", type="password") == admin_pass:
            st.dataframe(load_logs())
            
    with st.expander("🐞 Report Bug"):
        with st.form("bug"):
            if st.form_submit_button("Submit"): log_bug("User", "Issue Reported", "Med")

# --- CHAT LOGIC ---
st.title(f"✍️ {selected_name}")
wizard = PolyglotWizard(client, current_config["fields"])
fields = list(current_config["fields"].keys())

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": wizard.generate_question(fields[0])}]
if "form_data" not in st.session_state: st.session_state.form_data = {}
if "idx" not in st.session_state: st.session_state.idx = 0

# Display Chat History
for msg in st.session_state.messages: st.chat_message(msg["role"]).write(msg["content"])

# ONLY show chat input if we still have questions left
if st.session_state.idx < len(fields):
    if prompt := st.chat_input("Answer here..."):
        # Save User Answer
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        curr_field = fields[st.session_state.idx]
        st.session_state.form_data[curr_field] = prompt 
        
        # Move to Next Question
        st.session_state.idx += 1
        
        # If there are more questions, generate the next one
        if st.session_state.idx < len(fields):
            q = wizard.generate_question(fields[st.session_state.idx])
            st.session_state.messages.append({"role": "assistant", "content": q})
            st.rerun()
        else:
            # We are done! Refresh to hide chat and show Identity section
            st.rerun()

# --- FINALIZATION (IDENTITY) ---
# This section only appears when index >= len(fields)
if st.session_state.idx >= len(fields):
    st.divider()
    st.header("🆔 Identity Verification")
    c1, c2 = st.columns(2)
    selfie = c1.camera_input("Selfie")
    gov_id = c2.file_uploader("ID", type=['jpg','png'])
    
    st.write("Sign Below:")
    sig = st_canvas(stroke_width=2, height=150, key="sig")
    
    if st.button("Finalize & Submit"):
        if selfie and gov_id and sig.image_data is not None:
            with st.spinner("Processing with FormFlux..."):
                # Save Assets
                with open("temp_selfie.jpg","wb") as f: f.write(selfie.getbuffer())
                with open("temp_id.jpg","wb") as f: f.write(gov_id.getbuffer())
                Image.fromarray(sig.image_data.astype('uint8'),'RGBA').save("temp_sig.png")
                
                # Create PDF
                stamper = IdentityStamper(current_config['filename'])
                final_pdf = stamper.compile_final_doc(st.session_state.form_data, "temp_sig.png", "temp_selfie.jpg", "temp_id.jpg")
                
                # Dispatch Email
                client_name = st.session_state.form_data.get("txt_FirstName", "Client")
                target_email = current_config.get("recipient_email", "admin@example.com")
                
                email_status = send_secure_email(final_pdf, client_name, target_email)
                log_submission(client_name, selected_name, "Success")
                
                # --- TWILIO DEBUGGER ---
                phone = st.secrets.get("LAWYER_PHONE_NUMBER")
                if phone: 
                    sms_success, sms_msg = send_sms_alert(client_name, selected_name, phone)
                    if sms_success:
                        st.toast(f"📱 SMS Sent to {phone}!")
                    else:
                        st.error(f"❌ SMS Failed: {sms_msg}")
                else:
                    st.warning("⚠️ No Lawyer Phone Number found in Secrets.")
                
                st.success("✅ Submission Sent via FormFlux!")
                st.balloons()
                
