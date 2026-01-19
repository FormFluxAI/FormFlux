# FORM_LIBRARY
# This file maps the AI Interview Questions to the PDF Fields.

FORM_LIBRARY = {
    # --- FORM 1: THE APOLOGY (Tests Text & Radio Buttons) ---
    "Husband Apology Affidavit": {
        "filename": "forms/apology_v1.pdf", # Ensure this file exists in your forms/ folder
        "recipient_email": "gwendolyn@alwaysright.com",
        "fields": {
            "Husband_Name": { 
                "description": "What is your full name (The Accused)?", 
                "type": "text" 
            },
            "Date_of_Offense": { 
                "description": "On what date did you mess up?", 
                "type": "text" 
            },
            "Offense_Type": { 
                "description": "What is the nature of your crime?", 
                "type": "radio",
                "options": ["Forgot Anniversary", "Left Toilet Seat Up", "Bought Wrong Groceries", "Breathing Too Loud"]
            },
            "Beg_For_Mercy": { 
                "description": "Please type your heartfelt apology here:", 
                "type": "text" 
            }
        }
    },

    # --- FORM 2: MAN CAVE LEASE (Tests Checkboxes & Financials) ---
    "Man Cave Lease Agreement": {
        "filename": "forms/mancave_lease.pdf",
        "recipient_email": "gwendolyn@alwaysright.com",
        "fields": {
            "Tenant_Name": { 
                "description": "Tenant Name (Husband)", 
                "type": "text" 
            },
            "Monthly_Rent": { 
                "description": "Agreed Monthly Rent (in chores or cash)", 
                "type": "text" 
            },
            "Noise_Level": { 
                "description": "Maximum Allowed Volume?", 
                "type": "radio", 
                "options": ["Whisper Mode", "Conversational", "Game Day Screaming"] 
            },
            "Trash_Duty": { 
                "description": "I agree to remove all trash and beer cans daily.", 
                "type": "checkbox" 
            }
        }
    },

    # --- FORM 3: FOOTBALL CONTRACT (Tests Negotiation) ---
    "Sunday Football Contract": {
        "filename": "forms/football_contract.pdf",
        "recipient_email": "gwendolyn@alwaysright.com",
        "fields": {
            "Team_Name": { 
                "description": "Which team will we be watching?", 
                "type": "text" 
            },
            "Snack_Budget": { 
                "description": "Approved Snack Budget ($)", 
                "type": "text" 
            },
            "Chore_Tradeoff": { 
                "description": "Which chore will you perform during halftime?", 
                "type": "radio",
                "options": ["Dishes", "Laundry", "Foot Rub", "Clean Gutters"]
            }
        }
    }
}
