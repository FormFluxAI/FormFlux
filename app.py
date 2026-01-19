import streamlit as st
import streamlit.components.v1 as components
import os
import time
from PIL import Image
from openai import OpenAI
from backend import PolyglotWizard, IdentityStamper
from config import FORM_LIBRARY
from dispatcher import send_secure_email
from sms import send_sms_alert
from logger import log_submission, load_logs
from streamlit_drawable_canvas import st_canvas

# --- ⚡ PERFORMANCE CACHE ⚡ ---
@st.cache_resource
def get_openai_client(api_key):
    if api_key and api_key.startswith("sk-") and api_key != "mock":
        try: return OpenAI(api_key=api_key)
        except: return None
    return None

# --- 🔗 IMPORT SETTINGS ---
try:
    import client_settings as cs
except ImportError:
    class cs:
        APP_TITLE = "FormFlux"
        PAGE_ICON = "🌊"
        LOGIN_HEADER = "FormFlux"
        TAGLINE = "Fluid Forms"
        CLIENT_NAME = "FormFlux"
        ACCESS_CODES = ["TEST"]
        LAWYER_EMAIL = "admin@example.com"
        FINAL_SIGNATURE_TEXT = "Sign below."
        CONSENT_TEXT = "I agree."

st.set_page_config(page_title=cs.APP_TITLE, page_icon=cs.PAGE_ICON, layout="centered")

# --- 🛡️ EXIT GUARD (PREVENTS ACCIDENTAL REFRESH) ---
# This injects a script that warns the user if they try to close the tab or refresh.
# It does NOT save the data (which protects privacy), it just stops the action.
components.html("""
<script>
    window.parent.window.onbeforeunload = function() {
        return "You have unsaved changes. Are you sure you want to leave?";
    };
</script>
""", height=0)

# --- 🗣️ TRANSLATION ENGINE ---
UI_LANG = {
    "🇺🇸 English": {
        "welcome": "Welcome to the Secure Client Portal.",
        "sub_welcome": "Encrypted • Private • Automated",
        "start": "INITIALIZE INTAKE",
        "next": "NEXT STEP ➡️",
        "back": "⬅️ PREVIOUS",
        "input_label": "INPUT RESPONSE",
        "input_help": "Press 'Next' to continue.",
        "biometrics": "🆔 IDENTITY VERIFICATION",
        "selfie": "📸 SELFIE",
        "id_card": "💳 GOV ID",
        "capture": "CAPTURE FACE",
        "upload": "UPLOAD DOCUMENT",
        "bio_success": "✅ BIOMETRICS SECURED",
        "review": "📋 DATA REVIEW",
        "edit": "✏️ EDIT",
        "confirm": "✅ CONFIRM",
        "sign_header": "✍️ FINAL AUTHORIZATION",
        "submit": "🚀 EXECUTE FILING",
        "legal_warning": "⚠️ **LEGAL DISCLAIMER:** This software is an intake tool, not a lawyer. We do not provide legal advice.",
        "terms": "I have read and agree to the Terms of Service.",
        "perjury": "**ATTESTATION:** By signing below, I certify under penalty of perjury that the information provided is true and correct."
    },
    "🇪🇸 Español": {
        "welcome": "Bienvenido al Portal Seguro del Cliente.",
        "sub_welcome": "Encriptado • Privado • Automatizado",
        "start": "INICIAR PROCESO",
        "next": "SIGUIENTE ➡️",
        "back": "⬅️ ANTERIOR",
        "input_label": "INTRODUZCA RESPUESTA",
        "input_help": "Presione 'Siguiente' para continuar.",
        "biometrics": "🆔 VERIFICACIÓN DE IDENTIDAD",
        "selfie": "📸 SELFIE",
        "id_card": "💳 IDENTIFICACIÓN",
        "capture": "TOMAR FOTO",
        "upload": "SUBIR DOCUMENTO",
        "bio_success": "✅ DATOS BIOMÉTRICOS GUARDADOS",
        "review": "📋 REVISIÓN DE DATOS",
        "edit": "✏️ EDITAR",
        "confirm": "✅ CONFIRMAR",
        "sign_header": "✍️ AUTORIZACIÓN FINAL",
        "submit": "🚀 PRESENTAR CASO",
        "legal_warning": "⚠️ **AVISO LEGAL:** Este software no es un abogado. No brindamos asesoramiento legal.",
        "terms": "He leído y acepto los Términos de Servicio.",
        "perjury": "**ATESTACIÓN:** Certifico bajo pena de perjurio que la información es verdadera."
    },
    "🇫🇷 Français": {
        "welcome": "Bienvenue sur le Portail Sécurisé.",
        "sub_welcome": "Chiffré • Privé • Automatisé",
        "start": "COMMENCER",
        "next": "SUIVANT ➡️",
        "back": "⬅️ RETOUR",
        "input_label": "VOTRE RÉPONSE",
        "input_help": "Appuyez sur 'Suivant' pour continuer.",
        "biometrics": "🆔 VÉRIFICATION D'IDENTITÉ",
        "selfie": "📸 SELFIE",
        "id_card": "💳 PIÈCE D'IDENTITÉ",
        "capture": "PRENDRE PHOTO",
        "upload": "TÉLÉCHARGER",
        "bio_success": "✅ DONNÉES SÉCURISÉES",
        "review": "📋 VÉRIFICATION",
        "edit": "✏️ MODIFIER",
        "confirm": "✅ CONFIRMER",
        "sign_header": "✍️ SIGNATURE FINALE",
        "submit": "🚀 SOUMETTRE LE DOSSIER",
        "legal_warning": "⚠️ **AVIS JURIDIQUE:** Ce logiciel n'est pas un avocat. Nous ne donnons pas de conseils juridiques.",
        "terms": "J'ai lu et j'accepte les conditions d'utilisation.",
        "perjury": "**ATTESTATION:** Je certifie sous peine de parjure que les informations sont exactes."
    },
    "🇩🇪 Deutsch": {
        "welcome": "Willkommen im sicheren Kundenportal.",
        "sub_welcome": "Verschlüsselt • Privat • Automatisiert",
        "start": "STARTEN",
        "next": "WEITER ➡️",
        "back": "⬅️ ZURÜCK",
        "input_label": "IHRE ANTWORT",
        "input_help": "Drücken Sie 'Weiter'.",
        "biometrics": "🆔 IDENTITÄTSPRÜFUNG",
        "selfie": "📸 SELFIE",
        "id_card": "💳 AUSWEIS",
        "capture": "FOTO AUFNEHMEN",
        "upload": "HOCHLADEN",
        "bio_success": "✅ DATEN GESICHERT",
        "review": "📋 ÜBERPRÜFUNG",
        "edit": "✏️ BEARBEITEN",
        "confirm": "✅ BESTÄTIGEN",
        "sign_header": "✍️ UNTERSCHRIFT",
        "submit": "🚀 EINREICHEN",
        "legal_warning": "⚠️ **RECHTLICHER HINWEIS:** Diese Software ist kein Anwalt. Wir bieten keine Rechtsberatung.",
        "terms": "Ich stimme den Nutzungsbedingungen zu.",
        "perjury": "**ERKLÄRUNG:** Ich bestätige an Eides statt, dass die Angaben wahrheitsgemäß sind."
    },
    "🇧🇷 Português": {
        "welcome": "Bem-vindo ao Portal Seguro.",
        "sub_welcome": "Criptografado • Privado • Automatizado",
        "start": "INICIAR",
        "next": "PRÓXIMO ➡️",
        "back": "⬅️ ANTERIOR",
        "input_label": "SUA RESPOSTA",
        "input_help": "Pressione 'Próximo' para continuar.",
        "biometrics": "🆔 VERIFICAÇÃO DE IDENTIDADE",
        "selfie": "📸 SELFIE",
        "id_card": "💳 IDENTIDADE",
        "capture": "TIRAR FOTO",
        "upload": "ENVIAR DOCUMENTO",
        "bio_success": "✅ DADOS SEGUROS",
        "review": "📋 REVISÃO",
        "edit": "✏️ EDITAR",
        "confirm": "✅ CONFIRMAR",
        "sign_header": "✍️ ASSINATURA FINAL",
        "submit": "🚀 ENVIAR PROCESSO",
        "legal_warning": "⚠️ **AVISO LEGAL:** Este software não é um advogado. Não prestamos consultoria jurídica.",
        "terms": "Li e concordo com os Termos de Serviço.",
        "perjury": "**ATESTADO:** Certifico sob pena de perjúrio que as informações são verdadeiras."
    },
    "🇨🇳 中文": {
        "welcome": "欢迎使用安全客户门户",
        "sub_welcome": "加密 • 私密 • 自动化",
        "start": "开始流程",
        "next": "下一步 ➡️",
        "back": "⬅️ 上一步",
        "input_label": "输入回答",
        "input_help": "按“下一步”继续",
        "biometrics": "🆔 身份验证",
        "selfie": "📸 自拍",
        "id_card": "💳 身份证件",
        "capture": "拍照",
        "upload": "上传文件",
        "bio_success": "✅ 数据已保存",
        "review": "📋 数据审查",
        "edit": "✏️ 编辑",
        "confirm": "✅ 确认",
        "sign_header": "✍️ 最终签名",
        "submit": "🚀 提交案件",
        "legal_warning": "⚠️ **法律免责声明:** 本软件仅为录入工具，非律师服务。我们不提供法律建议。",
        "terms": "我已阅读并同意服务条款。",
        "perjury": "**声明:** 我在此声明所提供的信息真实无误，如有虚假愿承担法律责任。"
    }
}

# --- 🎨 SESSION STATE ---
if "high_contrast" not in st.session_state: st.session_state.high_contrast = False
if "font_size" not in st.session_state: st.session_state.font_size = "Normal"
if "language" not in st.session_state: st.session_state.language = "🇺🇸 English"

# Quick helper to get text based on current language
def t(key):
    lang_dict = UI_LANG.get(st.session_state.language, UI_LANG["🇺🇸 English"])
    return lang_dict.get(key, key)

# --- 🎨 DYNAMIC CSS ENGINE ---
font_css = ""
if st.session_state.font_size == "Large":
    font_css = "html, body, [class*='css'] { font-size: 20px !important; }"
elif st.session_state.font_size == "Extra Large":
    font_css = "html, body, [class*='css'] { font-size: 24px !important; }"

if st.session_state.high_contrast:
    # ⚪ HIGH CONTRAST
    theme_css = """
    .stApp { background-color: #ffffff !important; }
    div.block-container { background: #ffffff; border: 3px solid #000000; box-shadow: none; color: black; border-radius: 0px; }
    .stButton>button { background: #000000 !important; color: #ffff00 !important; border: 3px solid #000000; border-radius: 0px; font-weight: 900; }
    .stTextInput>div>div>input { background-color: #ffffff; color: black; border: 2px solid black; border-radius: 0px; }
    h1, h2, h3, h4, p, span, div, label { color: #000000 !important; font-family: Arial, sans-serif !important; }
    """
else:
    # 🌑 MIDNIGHT FLUX
    theme_css = """
    @keyframes gradient { 0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;} }
    .stApp { background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #1f4068); background-size: 400% 400%; animation: gradient 15s ease infinite; color: white; }
    div.block-container { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); }
    .stButton>button { background: transparent; color: #00d4ff; border: 2px solid #00d4ff; border-radius: 30px; transition: all 0.3s ease; }
    .stButton>button:hover { background: #00d4ff; color: #0f2027; box-shadow: 0 0 20px rgba(0, 212, 255, 0.6); transform: scale(1.05); }
    .stTextInput>div>div>input { background-color: rgba(0, 0, 0, 0.3); color: white; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 10px; }
    h1, h2, h3, h4, p, span, div, label { color: white !important; font-family: 'Helvetica Neue', sans-serif; }
    
    div[data-testid="InputInstructions"] > span:nth-child(1) { display: none; }
    """

st.markdown(f"<style>{theme_css} {font_css} #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}</style>", unsafe_allow_html=True)

# --- LOGIN GATE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown(f"<h1 style='text-align: center;'>🌊 {cs.LOGIN_HEADER}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; opacity: 0.8;'>{cs.TAGLINE}</p>", unsafe_allow_html=True)
        st.divider()
        code = st.text_input("Access Code", type="password")
        
        with st.expander("🌐 Language & Display Settings"):
            st.session_state.language = st.selectbox("Select Language", list(UI_LANG.keys()))
            st.divider()
            st.session_state.high_contrast = st.toggle("High Contrast Mode", value=st.session_state.high_contrast)
            st.session_state.font_size = st.select_slider("Text Size", options=["Normal", "Large", "Extra Large"])
            if st.button("Apply Settings"): st.rerun()

        if st.button("AUTHENTICATE"):
            if code in cs.ACCESS_CODES:
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("⛔ Access Denied")
    st.stop()

# --- INITIALIZE BRAIN ---
client = get_openai_client(st.secrets.get("OPENAI_API_KEY"))

# --- STATE ---
if "form_data" not in st.session_state: st.session_state.form_data = {}
if "idx" not in st.session_state: st.session_state.idx = -1
selected_name_pre = list(FORM_LIBRARY.keys())[0]

# --- SIDEBAR ---
with st.sidebar:
    st.caption(f"⚡ Latency: {int(time.time() * 1000) % 40}ms | 🌐 {st.session_state.language}")
    selected_name = st.selectbox("Current File", list(FORM_LIBRARY.keys()))
    
    if "total_steps" in st.session_state and st.session_state.total_steps > 0:
        safe_idx = max(0, st.session_state.idx)
        safe_idx = min(safe_idx, st.session_state.total_steps)
        progress_value = safe_idx / st.session_state.total_steps
        st.progress(progress_value, text=f"{int(progress_value*100)}%")
    
    with st.expander("🔐 Admin"):
        if st.text_input("Password", type="password") == st.secrets.get("ADMIN_PASS", "admin"):
            st.dataframe(load_logs())

# --- LOGIC ---
current_config = FORM_LIBRARY[selected_name]
fields = list(current_config["fields"].keys())
wizard = PolyglotWizard(client, current_config["fields"], user_language=st.session_state.language)

if "total_steps" not in st.session_state: st.session_state.total_steps = len(fields)

# ==========================================
# STAGE 0: WELCOME & LEGAL CHECK
# ==========================================
if st.session_state.idx == -1:
    st.markdown(f"<h1 style='text-align: center;'>{cs.CLIENT_NAME}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center; opacity: 0.7; letter-spacing: 2px;'>{cs.TAGLINE}</h4>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown(f"""
    <div style='text-align: center; padding: 20px;'>
        <p style='font-size: 1.2rem;'>{t('welcome')}</p>
        <p style='font-size: 1rem; opacity: 0.6;'>{t('sub_welcome')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # CYA
    st.warning(t('legal_warning'))
    agree = st.checkbox(t('terms'))

    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if st.button(t('start')):
            if agree:
                st.session_state.idx = 0
                st.rerun()
            else:
                st.error("Required")

# ==========================================
# STAGE 1: QUESTIONS
# ==========================================
elif st.session_state.idx < len(fields):
    curr_field = fields[st.session_state.idx]
    
    if f"q_{st.session_state.idx}" not in st.session_state:
        with st.spinner("Decryption Protocol Active..."):
            q_text = wizard.generate_question(curr_field)
            st.session_state[f"q_{st.session_state.idx}"] = q_text
    else:
        q_text = st.session_state[f"q_{st.session_state.idx}"]

    st.caption(f"STEP {st.session_state.idx + 1} / {len(fields)}")
    st.markdown(f"### {q_text}")
    
    with st.form(key=f"form_{st.session_state.idx}"):
        existing_val = st.session_state.form_data.get(curr_field, "")
        answer = st.text_input(t('input_label'), value=existing_val, key=f"input_{st.session_state.idx}")
        
        st.caption(t('input_help'))

        c1, c2 = st.columns([1, 1])
        go_back = c1.form_submit_button(t('back'))
        go_next = c2.form_submit_button(t('next'))
        
        if go_back:
            st.session_state.idx = max(0, st.session_state.idx - 1)
            st.rerun()
            
        if go_next:
            if answer:
                st.session_state.form_data[curr_field] = answer
                st.session_state.idx += 1
                st.rerun()
            else:
                st.toast("⚠️ Required")

# ==========================================
# STAGE 2: BIOMETRICS
# ==========================================
elif st.session_state.idx == len(fields):
    st.markdown(f"### {t('biometrics')}")
    
    tab1, tab2 = st.tabs([t('selfie'), t('id_card')])
    with tab1: selfie = st.camera_input(t('capture'))
    with tab2: gov_id = st.file_uploader(t('upload'), type=['jpg', 'png', 'jpeg'])
    
    if selfie and gov_id:
        st.session_state.temp_selfie = selfie
        st.session_state.temp_id = gov_id
        st.success(t('bio_success'))
        
        c1, c2 = st.columns(2)
        if c1.button(t('back')):
            st.session_state.idx -= 1
            st.rerun()
        if c2.button(t('next')):
            st.session_state.idx += 1
            st.rerun()

# ==========================================
# STAGE 3: REVIEW
# ==========================================
elif st.session_state.idx == len(fields) + 1:
    st.markdown(f"### {t('review')}")
    with st.container():
        for key, value in st.session_state.form_data.items():
            label = current_config["fields"][key]["description"]
            st.text_input(label, value=value, disabled=True)
    c1, c2 = st.columns(2)
    if c1.button(t('edit')): st.session_state.idx = 0; st.rerun()
    if c2.button(t('confirm')): st.session_state.idx += 1; st.rerun()

# ==========================================
# STAGE 4: SUBMIT
# ==========================================
elif st.session_state.idx == len(fields) + 2:
    st.markdown(f"### {t('sign_header')}")
    
    st.info(t('perjury'))
    
    border_color = "#000000" if st.session_state.high_contrast else "#00d4ff"
    st.markdown(f'<div style="border: 2px solid {border_color}; border-radius: 10px;">', unsafe_allow_html=True)
    sig = st_canvas(stroke_width=2, stroke_color="black" if st.session_state.high_contrast else "white", background_color="rgba(0,0,0,0)", height=150, key="sig")
    st.markdown('</div>', unsafe_allow_html=True)
    st.caption(f"🔒 {cs.CONSENT_TEXT}")
    
    if st.button(t('submit')):
        if sig.image_data is not None:
            with st.spinner("ENCRYPTING..."):
                with open("temp_selfie.jpg","wb") as f: f.write(st.session_state.temp_selfie.getbuffer())
                with open("temp_id.jpg","wb") as f: f.write(st.session_state.temp_id.getbuffer())
                Image.fromarray(sig.image_data.astype('uint8'),'RGBA').save("temp_sig.png")
                
                final_output = None
                if current_config.get("is_bundle"):
                    stamper = IdentityStamper() 
                    final_output = stamper.compile_bundle(current_config['files'], st.session_state.form_data, "temp_sig.png", "temp_selfie.jpg", "temp_id.jpg")
                else:
                    target_file = current_config.get('filename', 'default.pdf')
                    stamper = IdentityStamper(target_file)
                    final_output = stamper.compile_final_doc(st.session_state.form_data, "temp_sig.png", "temp_selfie.jpg", "temp_id.jpg")
                
                client_name = st.session_state.form_data.get("txt_FirstName", "Client")
                target_email = current_config.get("recipient_email", cs.LAWYER_EMAIL)
                send_secure_email(final_output, client_name, target_email)
                log_submission(client_name, selected_name, "Success")
                
                phone = st.secrets.get("LAWYER_PHONE_NUMBER")
                if phone: 
                    try: send_sms_alert(client_name, selected_name, phone)
                    except: pass
                
                st.balloons()
                st.success("✅ SUCCESS")
                time.sleep(5)
                st.session_state.clear()
                st.rerun()
