"""
================================================================================
  MODULE:       backend.py
  PROJECT:      FormFluxAI
  AUTHOR:       Justin White
  COPYRIGHT:    (c) 2026 FormFluxAI. All Rights Reserved.
  
  DESCRIPTION:
  The "Brain" of the operation. Handles OpenAI integrations, 
  PDF stamping, and Logic Processing.
================================================================================
"""

import os
import json
import pypdf
from datetime import datetime
from PIL import Image
import io

class PolyglotWizard:
    def __init__(self, client, fields_config, user_language="🇺🇸 English"):
        self.client = client
        self.fields = fields_config
        self.language = user_language

    def generate_question(self, field_key):
        """Generates a polite question for a specific field."""
        field_info = self.fields.get(field_key, {})
        description = field_info.get("description", field_key)
        
        # Free Mode (No AI Key)
        if not self.client:
            return f"{description} ({self.language})"

        try:
            prompt = f"Translate this form field question into {self.language}. Make it polite. Field: '{description}'"
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except:
            return description

    def chat_with_assistant(self, history, current_form_data):
        """Analyzes chat history to fill form fields."""
        if not self.client:
            return "AI Error: No API Key found.", current_form_data

        missing_fields = [k for k, v in self.fields.items() if k not in current_form_data or not current_form_data[k]]
        
        system_prompt = f"""
        You are a helpful Legal Intake Assistant for FormFluxAI.
        Current Language: {self.language}
        
        FIELDS TO COLLECT (JSON): {json.dumps(self.fields, indent=2)}
        KNOWN DATA: {json.dumps(current_form_data, indent=2)}
        
        INSTRUCTIONS:
        1. Chat politely.
        2. Extract new info to update JSON.
        3. Do NOT ask for known info.
        
        OUTPUT JSON: {{ "response": "msg", "updated_data": {{...}} }}
        """

        try:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history[-10:])

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0
            )
            result = json.loads(response.choices[0].message.content)
            return result["response"], result.get("updated_data", {})
        except Exception as e:
            return f"Error: {e}", {}

class IdentityStamper:
    def __init__(self, template_path=""):
        self.template_path = template_path

    def compile_final_doc(self, form_data, sig_path, selfie_path, id_path):
        """Stamps answers onto PDF."""
        if not os.path.exists(self.template_path): return None
        reader = pypdf.PdfReader(self.template_path)
        writer = pypdf.PdfWriter()

        for page in reader.pages:
            writer.add_page(page)
            writer.update_page_form_field_values(writer.pages[-1], form_data)

        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        return output_stream.getvalue()
