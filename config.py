# config.py

FORM_LIBRARY = {
    # -------------------------------------------------
    # 📦 THE BUNDLE: "New Client Packet"
    # -------------------------------------------------
    # instead of one file, we list THREE files
    "New Client Packet": {
        "is_bundle": True,  # <--- New flag to tell the app this is a bundle
        "files": [
            "forms/intake_form.pdf",
            "forms/standard_nda.pdf",
            "forms/fee_agreement.pdf"
        ],
        # The "Master List" of questions for the whole packet
        "fields": {
            # Shared Data (Goes to ALL forms)
            "client_name": {"description": "Full Legal Name"},
            "client_address": {"description": "Current Home Address"},
            
            # Form-Specific Data (Only goes to specific forms)
            "case_description": {"description": "Brief description of legal issue (for Intake)"},
            "retainer_amount": {"description": "Agreed Retainer Amount (for Fee Agreement)"}
        },
        "recipient_email": "admin@smithlegal.com"
    }
}
