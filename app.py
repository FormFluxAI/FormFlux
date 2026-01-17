import streamlit as st
import os
from PIL import Image
from openai import OpenAI
from backend import PolyglotWizard, IdentityStamper
from config import FORM_LIBRARY
from dispatcher import send_secure_email
from sms import send_sms_alert
from logger import log_submission, load_logs
from bugs import log_bug
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="FormFlux | Justin White", page_icon="🌊")

# --- LOGIN GATE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔒 FormFlux Portal")
    st.caption("Fluid Forms for a Flexible World")
    code = st.text_input("Access Code", type="password")
    if st.button("Enter"):
        if code in ["JUSTIN-ADMIN", "WHITE-LEGAL", "TEST-JW"]:
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("Invalid Access Code")
    st.stop()

# --- SAFETY SWITCH FOR OPENAI ---
api_key = st.secrets.get("OPENAI_API_KEY")
client = None
if api_key and api_key.startswith("sk-") and api_key != "mock":
    try:
        client = OpenAI(api_key=api_key)
    except:
        client = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("FormFlux Intake")
    st.caption("Owner: Justin White")
    if client:
        st.success("🟢 AI Connected")
    else:
        st.info("🟡 Mock Mode Active")
        
    selected_name = st.selectbox("Select Document", list(FORM_LIBRARY.keys()))
    current_config = FORM_LIBRARY[selected_name]
    
    with st.expander("💼 Admin Dashboard"):
        if st.
        st.balloons()
                                 
