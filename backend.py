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

