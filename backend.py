import os
from datetime import datetime
from openai import OpenAI
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

class PolyglotWizard:
    def __init__(self, client, field_config, user_language="English"):
        self.client = client
        self.field_config = field_config
        self.language = user_language

    def generate_question(self, field_key):
        # MOCK MODE CHECK
        if not self.client:
            field_info = self.field_config.get(field_key, {"description": field_key})
            return f"🤖 [MOCK AI] Please enter: {field_info['description']}"
        try:
            field_info = self.field_config.get(field_key, {"description": field_key})
            prompt = f"Ask the user for '{field_info['description']}' in {self.language}. Be polite and brief."
            response = self.client.chat.completions.create(
                model="gpt-4o", messages=[{"role": "system", "content": prompt}]
            )
            return response.choices[0].message.content
        except:
            return f"Please enter {field_key}."

class IdentityStamper:
    def __init__(self, original_pdf_path):
        self.original_pdf_path = original_pdf_path

    def create_identity_page(self, signature_path, selfie_path, id_path):
        output_filename = "temp_identity_page.pdf"
        c = canvas.Canvas(output_filename, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, "Identity Verification Exhibit")
        c.setFont("Helvetica", 10)
        c.drawString(50, 730, f"Generated: {datetime.now()} | FormFlux AI")
        c.drawString(50, 715, "Verified for: Justin White Legal Services")

        if signature_path and os.path.exists(signature_path):
            c.drawString(50, 680, "1. Digital Signature:")
            c.drawImage(signature_path, 50, 600, width=200, height=60, mask='auto')

        if selfie_path and os.path.exists(selfie_path):
            c.drawString(50, 550, "2. Biometric Capture:")
            c.drawImage(selfie_path, 50, 340, width=200, height=200, preserveAspectRatio=True)

        if id_path and os.path.exists(id_path):
            c.drawString(300, 550, "3. Gov ID:")
            c.drawImage(id_path, 300, 340, width=250, height=200, preserveAspectRatio=True)

        c.save()
        return output_filename

    def compile_final_doc(self, field_data, sig, selfie, gov_id, final_output="filed_case.pdf"):
        # Auto-generate dummy PDF if missing (Critical for Cloud deployment)
        if not os.path.exists(self.original_pdf_path):
            c = canvas.Canvas(self.original_pdf_path, pagesize=letter)
            c.drawString(100, 750, "MOCK FORM - AUTO GENERATED")
            c.save()

        reader = PdfReader(self.original_pdf_path)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)
        try:
            writer.update_page_form_field_values(writer.pages[0], field_data)
        except:
            pass # Ignore field errors on mock pdf
        
        id_page = self.create_identity_page(sig, selfie, gov_id)
        id_reader = PdfReader(id_page)
        writer.add_page(id_reader.pages[0])
        
        with open(final_output, "wb") as f:
            writer.write(f)
        if os.path.exists(id_page): os.remove(id_page)
        return final_output
"""

---

### 📄 File 4: `app.py`
*The main application interface.*

```python
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
        if st.text_input("Admin Pass", type="password") == st.secrets.get("ADMIN_PASS", "admin"):
            st.dataframe(load_logs())
    with st.expander("🐞 Report Bug"):
        with st.form("bug"):
            if st.form_submit_button("Submit"): log_bug("User", "Issue Reported", "Med")

# --- CHAT ---
st.title(f"✍️ {selected_name}")
wizard = PolyglotWizard(client, current_config["fields"])
fields = list(current_config["fields"].keys())

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": wizard.generate_question(fields[0])}]
if "form_data" not in st.session_state: st.session_state.form_data = {}
if "idx" not in st.session_state: st.session_state.idx = 0

for msg in st.session_state.messages: st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Answer here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    curr_field = fields[st.session_state.idx]
    st.session_state.form_data[curr_field] = prompt 
    st.session_state.idx += 1
    if st.session_state.idx < len(fields):
        q = wizard.generate_question(fields[st.session_state.idx])
        st.session_state.messages.append({"role": "assistant", "content": q})
        st.rerun()
    else:
        st.rerun()

# --- FINALIZATION ---
if st.session_state.idx >= len(fields):
    st.divider()
    st.header("🆔 Identity Verification")
    c1, c2 = st.columns(2)
    selfie = c1.camera_input("Selfie")
    gov_id = c2.file_uploader("ID", type=['jpg','png'])
    
    from streamlit_drawable_canvas import st_canvas
    st.write("Sign Below:")
    sig = st_canvas(stroke_width=2, height=150, key="sig")
    
    if st.button("Finalize & Submit"):
        if selfie and gov_id and sig.image_data is not None:
            with st.spinner("Processing with FormFlux..."):
                with open("temp_selfie.jpg","wb") as f: f.write(selfie.getbuffer())
                with open("temp_id.jpg","wb") as f: f.write(gov_id.getbuffer())
                Image.fromarray(sig.image_data.astype('uint8'),'RGBA').save("temp_sig.png")
                
                stamper = IdentityStamper(current_config['filename'])
                final_pdf = stamper.compile_final_doc(st.session_state.form_data, "temp_sig.png", "temp_selfie.jpg", "temp_id.jpg")
                
                client_name = st.session_state.form_data.get("txt_FirstName", "Client")
                target_email = current_config.get("recipient_email", "admin@example.com")
                
                send_secure_email(final_pdf, client_name, target_email)
                log_submission(client_name, selected_name, "Success")
                
                phone = st.secrets.get("LAWYER_PHONE_NUMBER")
                if phone: send_sms_alert(client_name, selected_name, phone)
                
                st.success("✅ Submission Sent via FormFlux!")
                st.balloons()

