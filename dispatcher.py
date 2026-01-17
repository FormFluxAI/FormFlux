import smtplib
import ssl
import os
import streamlit as st
from email.message import EmailMessage

def send_secure_email(pdf_path, client_name, recipient_email):
    sender_email = st.secrets["EMAIL_USER"]
    sender_pass = st.secrets["EMAIL_PASS"]
    
    msg = EmailMessage()
    msg['Subject'] = f"FormFlux Submission: {client_name}"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg.set_content(f"New secure submission attached for {client_name}.\\n\\nSent via FormFlux for Justin White.")

    with open(pdf_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(pdf_path))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_pass)
            server.send_message(msg)
        return True, "Sent"
    except Exception as e:
        return False, str(e)
      
