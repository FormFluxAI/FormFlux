import os
import zipfile  # <--- NEW: To zip multiple PDFs together
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

class IdentityStamper:
    def __init__(self):
        pass

    # This function stamps ONE single PDF
    def stamp_one_pdf(self, source_pdf, field_data, sig_path, selfie_path, id_path, output_name):
        c = canvas.Canvas(output_name, pagesize=letter)
        width, height = letter
        
        # 1. Header & Metadata
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 30, f"Generated: {datetime.now().strftime('%Y-%m-%d')} | {source_pdf}")

        # 2. Dynamic Mapping (The "Sharpie" Logic)
        # It blindly tries to write EVERY answer. If the PDF needs it, great. If not, it's just hidden text.
        y_pos = height - 100
        for key, value in field_data.items():
            # In a real app, you would have specific coordinates for each key.
            # For this MVP, we list them on a summary page attached to the PDF.
            c.drawString(50, y_pos, f"{key}: {value}")
            y_pos -= 20
        
        # 3. Add Images (Signature, ID)
        if os.path.exists(sig_path):
            c.drawImage(sig_path, 50, 100, width=150, height=50, mask='auto')
        
        c.save()
        return output_name

    # This function handles the BUNDLE
    def compile_bundle(self, file_list, field_data, sig, selfie, gov_id):
        generated_files = []
        
        # Loop through every file in the bundle list
        for i, filename in enumerate(file_list):
            output_name = f"completed_{i}_{os.path.basename(filename)}"
            
            # Stamp this specific file using the SHARED data
            self.stamp_one_pdf(filename, field_data, sig, selfie, gov_id, output_name)
            generated_files.append(output_name)
            
        # Zip them all up into one neat package
        zip_filename = "Client_Bundle.zip"
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in generated_files:
                zipf.write(file)
                
        return zip_filename
