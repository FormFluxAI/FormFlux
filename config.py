# FORMFLUX CONFIGURATION
FORM_LIBRARY = {
    "Visa Intake (Standard)": {
        "filename": "immigration.pdf", # Simplified path for cloud
        "description": "Standard intake for new visa applicants.",
        "recipient_email": "justinw1226@gmail.com", 
        "fields": {
            "txt_FirstName": {"description": "Client's First Name", "rule": "Capitalize"},
            "chk_Citizen": {"description": "Are you a US Citizen?", "rule": "Boolean: Yes/No"},
            "txt_Story": {"description": "Brief explanation of the case", "rule": "Summarize in professional English"}
        }
    }
}

