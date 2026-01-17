import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

class PolyglotWizard:
    def __init__(self, client, field_config, user_language="English"):
        self.client = client
        self.field_config = field_config
        self.language = user_language

    def generate_question(self, field_key):
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

    def compile_final_doc(self, field_data, sig_path, selfie_path, id_path, final_output="filed_case.pdf"):
        # --- THE SHARPIE METHOD: Write directly on the page ---
        c = canvas.Canvas(final_output, pagesize=letter)
        width, height = letter

        # 1. Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "OFFICIAL FORMFLUX INTAKE")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 70, f"Filed: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # 2. The Answers
        # First Name
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 120, "Client Name:")
        c.setFont("Helvetica-Bold", 14)
        # Pull the answer from the data. If missing, print a blank line.
        answer_name = field_data.get("txt_FirstName", "_________________")
        c.drawString(150, height - 120, answer_name)

        # US Citizen
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 160, "US Citizen:")
        answer_citizen = field_data.get("chk_Citizen", "No")
        c.setFont("Helvetica-Bold", 14)
        c.drawString(150, height - 160, f"[{answer_citizen}]")

        # Case Story
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 200, "Case Details:")
        c.setFont("Helvetica-Oblique", 11)
        answer_story = field_data.get("txt_Story", "No details provided.")
        
        # Wrap text so it doesn't run off the page
        text_obj = c.beginText(50, height - 230)
        # Simple text wrapping logic
        import textwrap
        lines = textwrap.wrap(answer_story, width=80)
        for line in lines:
            text_obj.textLine(line)
        c.drawText(text_obj)

        # 3. The Images (Identity Section)
        y_pos = height - 400
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_pos, "Identity Verification Exhibit")
        
        # Signature
        if os.path.exists(sig_path):
            c.drawString(50, y_pos - 30, "Signature:")
            c.drawImage(sig_path, 50, y_pos - 100, width=150, height=60, mask='auto')

        # Selfie
        if os.path.exists(selfie_path):
            c.drawString(50, y_pos - 250, "Biometric Selfie:")
            try:
                c.drawImage(selfie_path, 50, y_pos - 420, width=150, height=150, preserveAspectRatio=True)
            except:
                c.drawString(50, y_pos - 350, "[Image Error]")

        # ID
        if os.path.exists(id_path):
            c.drawString(300, y_pos - 250, "Gov ID:")
            try:
                c.drawImage(id_path, 300, y_pos - 420, width=200, height=150, preserveAspectRatio=True)
            except:
                c.drawString(300, y_pos - 350, "[Image Error]")

        c.save()
        return final_output
        
