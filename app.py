import streamlit as st
import anthropic
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
from datetime import datetime

st.set_page_config(page_title="Chez Wafae Sbai", page_icon="👗", layout="centered")

st.markdown("""
<style>
    .main { background-color: #FFF8F5; }
    .stChatMessage { border-radius: 16px; }
    .header-box {
        background: linear-gradient(135deg, #D4567A, #E8A0B4);
        color: white; padding: 18px 24px; border-radius: 16px;
        text-align: center; margin-bottom: 20px;
    }
    .header-box h2 { margin: 0; font-size: 1.5rem; }
    .header-box p  { margin: 4px 0 0; font-size: 0.85rem; opacity: 0.9; }
    .whatsapp-btn {
        display: inline-block; background: #25D366; color: white !important;
        padding: 10px 20px; border-radius: 24px; text-decoration: none;
        font-weight: 600; font-size: 0.95rem; margin-top: 8px;
    }
    .stock-card {
        background: white; border: 1px solid #F0D0DA;
        border-radius: 12px; padding: 12px 16px; margin: 6px 0;
    }
    div[data-testid="stForm"] {
        border: 2px dashed #E8A0B4;
        border-radius: 16px;
        padding: 16px;
        background: #FFF0F5;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h2>👗 Chez Wafae Sbai</h2>
    <p>14 Rue Mohamed Abdou, Tanger • 11h–22h30 • Livraison Maroc</p>
</div>
""", unsafe_allow_html=True)

# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def get_stock():
    try:
        client = get_gsheet_client()
        sheet = client.open_by_key(st.secrets["SHEET_ID"])
        return sheet.worksheet("Stock").get_all_records()
    except:
        return []

@st.cache_data(ttl=300)
def get_infos_boutique():
    try:
        client = get_gsheet_client()
        sheet = client.open_by_key(st.secrets["SHEET_ID"])
        data = sheet.worksheet("Infos_Boutique").get_all_values()
        return {row[0]: row[1] for row in data if len(row) >= 2}
    except:
        return {"boutique_nom":"Chez Wafae Sbai","adresse":"14 Rue Mohamed Abdou, Tanger 90000",
                "whatsapp":"0777139312","horaires":"11h - 22h30","livraison":"Tout le Maroc","paiement":"Cash"}

def format_stock_for_prompt(stock):
    if not stock:
        return "Stock non disponible."
    lines = []
    for item in stock:
        if str(item.get("Stock_Dispo","")).lower() in ["oui","yes","1","true"]:
            lines.append(f"- {item.get('Nom_Article','?')} | {item.get('Categorie','?')} | Tailles: {item.get('Taille','?')} | Couleurs: {item.get('Couleur','?')} | Prix: {item.get('Prix_MAD','?')} MAD")
    return "\n".join(lines) if lines else "Pas d'articles disponibles."

def whatsapp_link(message, phone="212777139312"):
    encoded = message.replace(" ","%20").replace("\n","%0A")
    return f"https://wa.me/{phone}?text={encoded}"

def build_system_prompt(infos, stock_text):
    return f"""Nti assistante dyal boutique Chez Wafae Sbai f Tanger, boutique dyal l'habillement.
Jawbi bdarija marocaine naturelle — kifma kat7ki nsa Tanger f reality.
Style: chaleureuse, professionnelle, directe. Machi excessive.

Exemples dyal darija marocaine:
- "Salam habibti! Mrhba bik, ash nqderek n3awnek?"
- "Iyeh kayen, zwin bzzaf!"
- "Bghiti tchouf chi haja okhra?"
- "Mzyan, chhal bghiti?"
- "La, hadi machi disponible daba — kayen X bla7a"

== INFOS BOUTIQUE ==
Boutique: {infos.get('boutique_nom','Chez Wafae Sbai')}
Adresse: {infos.get('adresse','14 Rue Mohamed Abdou, Tanger 90000')}
WhatsApp: {infos.get('whatsapp','0777139312')}
Horaires: {infos.get('horaires','11h - 22h30')}
Livraison: {infos.get('livraison','Tout le Maroc')}
Paiement: {infos.get('paiement','Cash')}

== STOCK DISPONIBLE ==
{stock_text}

== RÈGLES ==
1. Jawbi dima bdarija marocaine naturelle, machi robotique
2. Ila bghat article, etih l-info dyal taille, couleur, prix
3. Pour commander, dir lien WhatsApp direct
4. Ila machi disponible, goul b7al hadi w proposiha alternatives
5. livraison n maroc kamel
6. Paiement cash only
7. Horaires: {infos.get('horaires','11h - 22h30')}
8. Max 3-4 lignes — machi tawil
9. Termina b proposer d'aider ou commander via WhatsApp
10. Ila cliente siyftat foto, analyziha w goulha wach kayen chi haja pareille f l-stock
"""

# ── CLAUDE ────────────────────────────────────────────────────────────────────
def call_claude(messages_history, system_prompt):
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-haiku-4-5", max_tokens=600,
        system=system_prompt, messages=messages_history
    )
    return response.content[0].text

def call_claude_with_image(image_b64, image_type, text, system_prompt):
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-haiku-4-5", max_tokens=600,
        system=system_prompt,
        messages=[{"role":"user","content":[
            {"type":"image","source":{"type":"base64","media_type":image_type,"data":image_b64}},
            {"type":"text","text": text if text else "Wach kayen had l-article f boutique? Etih l-info dyal taille, couleur, prix."}
        ]}]
    )
    return response.content[0].text

def detect_order_intent(text):
    keywords = ["commander","commande","bghit","acheter","achat","nakhod","nchri","howa","ana bghit"]
    return any(k in text.lower() for k in keywords)

def show_whatsapp_btn(text=""):
    wa_msg = f"Salam Wafae, bghit ncommand — {text} 🌸" if text else "Salam Wafae, bghit ncommand 🌸"
    wa_url = whatsapp_link(wa_msg)
    st.markdown(f'<a href="{wa_url}" target="_blank" class="whatsapp-btn">📲 Commander sur WhatsApp</a>', unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
infos = get_infos_boutique()
stock = get_stock()
stock_text = format_stock_for_prompt(stock)
system_prompt = build_system_prompt(infos, stock_text)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛍️ Articles disponibles")
    if stock:
        for item in stock:
            if str(item.get("Stock_Dispo","")).lower() in ["oui","yes","1","true"]:
                st.markdown(f"""<div class="stock-card">
                    <strong>{item.get('Nom_Article','')}</strong><br>
                    <small>📏 {item.get('Taille','')} &nbsp;|&nbsp; 🎨 {item.get('Couleur','')}</small><br>
                    <strong style="color:#D4567A">{item.get('Prix_MAD','')} MAD</strong>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("Chargement du stock...")
    st.markdown("---")
    wa_url = whatsapp_link("Salam Wafae, bghit nssuwwel 3la article 🌸")
    st.markdown(f'<a href="{wa_url}" target="_blank" class="whatsapp-btn">💬 WhatsApp direct</a>', unsafe_allow_html=True)

# ── CHAT HISTORY ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("image"):
            st.image(base64.b64decode(msg["image"]), width=200)
        st.markdown(msg["content"])

# ── WELCOME ───────────────────────────────────────────────────────────────────
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Salam habibti! 👗 Mrhba bik f **Chez Wafae Sbai** 🌸\n\n"
            "Ash nqderek n3awnek? — stock, prix, livraison, commande...\n"
            "Yimken tsiyfti foto dyal article li bghiti! 📸"
        )

# ── PHOTO FORM — uses st.form to avoid rerun issues ──────────────────────────
with st.form(key="photo_form", clear_on_submit=True):
    st.markdown("📸 **Siyfti foto dyal article li bghiti**")
    uploaded_file = st.file_uploader("Choisir une photo", type=["jpg","jpeg","png","webp"], label_visibility="collapsed")
    photo_text = st.text_input("Ash bghiti t3rfi 3la had l-article? (optionnel)", placeholder="Ex: wach kayen f rouge?")
    submit_photo = st.form_submit_button("📤 Siyfti had foto", type="primary")

    if submit_photo and uploaded_file is not None:
        image_bytes = uploaded_file.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_type = uploaded_file.type

        # Show user message
        with st.chat_message("user"):
            st.image(uploaded_file, width=200)
            if photo_text:
                st.markdown(photo_text)
            else:
                st.markdown("*(foto msiyfta)*")

        st.session_state.messages.append({
            "role": "user",
            "content": photo_text or "*(foto msiyfta)*",
            "image": image_b64
        })

        # Get Claude response
        with st.chat_message("assistant"):
            with st.spinner("..."):
                try:
                    reply = call_claude_with_image(image_b64, image_type, photo_text, system_prompt)
                except Exception:
                    reply = "Smehli, kayen mochkil sgheir 🙏 Essayez encore ou contactez Wafae sur WhatsApp."
            st.markdown(reply)
            if detect_order_intent(reply) or detect_order_intent(photo_text):
                show_whatsapp_btn(photo_text)

        st.session_state.messages.append({"role":"assistant","content":reply})

    elif submit_photo and uploaded_file is None:
        st.warning("Siyfti foto l-awwel 📸")

# ── TEXT CHAT ─────────────────────────────────────────────────────────────────
if user_input := st.chat_input("Ash bghiti t3rfi? (Darija / Français)"):
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role":"user","content":user_input})

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[-10:]
    ]

    with st.chat_message("assistant"):
        with st.spinner("..."):
            try:
                reply = call_claude(history, system_prompt)
            except Exception:
                reply = "Smehli, kayen mochkil sgheir 🙏 Essayez encore ou contactez Wafae sur WhatsApp."
        st.markdown(reply)
        if detect_order_intent(user_input) or detect_order_intent(reply):
            show_whatsapp_btn(user_input)

    st.session_state.messages.append({"role":"assistant","content":reply})
