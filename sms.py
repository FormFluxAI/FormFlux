import streamlit as st
from twilio.rest import Client

def send_sms_alert(client_name, form_name, recipient_phone):
    try:
        client = Client(st.secrets["TWILIO_SID"], st.secrets["TWILIO_TOKEN"])
        message = client.messages.create(
            body=f"FormFlux Alert: New submission from {client_name}.",
            from_=st.secrets["TWILIO_PHONE_NUMBER"],
            to=recipient_phone
        )
        return True, message.sid
    except Exception as e:
        return False, str(e)
      
