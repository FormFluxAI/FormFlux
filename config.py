FORM_LIBRARY = {
    "Survey Template": {
        "filename": "forms/Survey Questions Template Download in MS Word Doc.pdf", 
        "recipient_email": "justinw1226@gmail.com",
        "fields": {
             # I manually created these so you can test the app NOW
             "Client_Name": { 
                 "description": "What is your full name?", 
                 "type": "text" 
             },
             "Date_of_Birth": { 
                 "description": "What is your date of birth?", 
                 "type": "text" 
             },
             "Service_Rating": { 
                 "description": "How would you rate our service?", 
                 "type": "radio",
                 "options": ["Excellent", "Good", "Average", "Poor"]
             },
             "Recommend_Us": {
                 "description": "Would you recommend us to a friend?",
                 "type": "radio",
                 "options": ["Yes", "No"]
             },
             "Additional_Comments": { 
                 "description": "Any other feedback?", 
                 "type": "text" 
             }
        }
    }
}
