import os
import zipfile
from datetime import datetime
from openai import OpenAI
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# --- CLASS 1: THE WIZARD (Handles AI Questions) ---
class PolyglotWizard:
    def __init__(self, client, field_config, user_language="English"):
        self.client = client
        self.field_config = field_config
        self.language = user_language

    def generate_question(self, field_key):
        # If no OpenAI Key (Mock Mode), return a standard prompt
        if not self.client:
            field_info = self.field_config.get(field_key, {"description": field_key})
            return f"🤖 [MOCK AI] Please enter: {field_info['description']}"
        
        # If AI is active, generate a polite question
        try:
            field_info = self.field_config.get(field_key, {"description": field_key})
            prompt = f"Ask the user for '{field_info['description']}' in {self.language}. Be polite, professional, and brief."
            response = self.client.chat.completions.create(
                model="gpt-4o", messages=[{"role": "system", "content": prompt}]
            )
            return response.choices[0].message.content
        except:
            return f"Please enter {field_key}."

# --- CLASS 2: THE STAMPER (Handles PDF Creation) ---
class IdentityStamper:
    def __init__(self, original_pdf_path=None):
        self.original_pdf_path = original_pdf_path

    # Helper: Stamps ONE single PDF
    def stamp_one_pdf(self, source_pdf, field_data, sig_path, selfie_path, id_path, output_name):
        c = canvas.Canvas(output_name, pagesize=letter)
        width, height = letter
        
        # 1. Header & Metadata
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 30, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        c.drawString(50, height - 45, f"File: {os.path.basename(source_pdf)}")

        # 2. Dynamic Mapping (The "Sharpie" Logic)
        # Lists answers down the page. In a real deployment, you'd use specific X/Y coordinates.
        y_pos = height - 100
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "Client Responses:")
        y_pos -= 20
        c.setFont("Helvetica", 11)
        
        for key, value in field_data.items():
            # Basic text wrapping to prevent cutoff
            text = f"{key}: {value}"
            if len(text) > 80: text = text[:80] + "..."
            c.drawString(50, y_pos, text)
            y_pos -= 20
            
            # Start a new page if we run out of space
            if y_pos < 100:
                c.showPage()
                y_pos = height - 50
        
        # 3. Add Images (Signature, ID) on a new page or at bottom
        if y_pos < 300: c.showPage(); y_pos = height - 50
        
        if os.path.exists(sig_path):
            c.drawString(50, y_pos - 40, "Signature:")
            try:
                c.drawImage(sig_path, 50, y_pos - 100, width=150, height=50, mask='auto')
            except: pass

        c.save()
        return output_name

    # Main Method: Handles Single Files OR Bundles
    def compile_final_doc(self, field_data, sig, selfie, gov_id):
        # Decide if we are making a Bundle (Zip) or Single PDF
        # Note: In a full app, we would check 'is_bundle' from config. 
        # For now, we default to the single file logic unless a list is passed.
        
        # Default single file output
        output_filename = "Final_Submission.pdf"
        
        # Pass the "Sharpie" method to create the PDF
        # We use 'self.original_pdf_path' as the template name
        self.stamp_one_pdf(str(self.original_pdf_path), field_data, sig, selfie, gov_id, output_filename)
        
        return output_filename
        
    # Optional: Bundle Logic (Future Use)
    def compile_bundle(self, file_list, field_data, sig, selfie, gov_id):
        generated_files = []
        for i, filename in enumerate(file_list):
            out_name = f"doc_{i}.pdf"
            self.stamp_one_pdf(filename, field_data, sig, selfie, gov_id, out_name)
            generated_files.append(out_name)
            
        zip_name = "Client_Bundle.zip"
        with zipfile.ZipFile(zip_name, 'w') as z:
            for f in generated_files: z.write(f)
        return zip_name
