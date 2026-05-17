import streamlit as st
import anthropic
import gspread
from google.oauth2.service_account import Credentials
import json
import re
from datetime import datetime

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Chez Wafae Sbai",
    page_icon="👗",
    layout="centered"
)

# ── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #FFF8F5; }
    .stChatMessage { border-radius: 16px; }
    .header-box {
        background: linear-gradient(135deg, #D4567A, #E8A0B4);
        color: white;
        padding: 18px 24px;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 20px;
    }
    .header-box h2 { margin: 0; font-size: 1.5rem; }
    .header-box p  { margin: 4px 0 0; font-size: 0.85rem; opacity: 0.9; }
    .whatsapp-btn {
        display: inline-block;
        background: #25D366;
        color: white !important;
        padding: 10px 20px;
        border-radius: 24px;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.95rem;
        margin-top: 8px;
    }
    .stock-card {
        background: white;
        border: 1px solid #F0D0DA;
        border-radius: 12px;
        padding: 12px 16px;
        margin: 6px 0;
    }
</style>
""", unsafe_allow_html=True)

# ── HEADER ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-box">
    <h2>👗 Chez Wafae Sbai</h2>
    <p>14 Rue Mohamed Abdou, Tanger • 11h–22h30 • Livraison Maroc</p>
</div>
""", unsafe_allow_html=True)

# ── GOOGLE SHEETS CONNECTION ──────────────────────────────────────────────────
@st.cache_resource
def get_gsheet_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def get_stock():
    try:
        client = get_gsheet_client()
        sheet = client.open_by_key(st.secrets["SHEET_ID"])
        ws = sheet.worksheet("Stock")
        records = ws.get_all_records()
        return records
    except Exception as e:
        return []

@st.cache_data(ttl=300)
def get_infos_boutique():
    try:
        client = get_gsheet_client()
        sheet = client.open_by_key(st.secrets["SHEET_ID"])
        ws = sheet.worksheet("Infos_Boutique")
        data = ws.get_all_values()
        return {row[0]: row[1] for row in data if len(row) >= 2}
    except Exception:
        return {
            "boutique_nom": "Chez Wafae Sbai",
            "adresse": "14 Rue Mohamed Abdou, Tanger 90000",
            "whatsapp": "0777139312",
            "horaires": "11h - 22h30",
            "livraison": "Tout le Maroc",
            "paiement": "Cash"
        }

def log_commande(nom_client, article, taille, ville):
    try:
        client = get_gsheet_client()
        sheet = client.open_by_key(st.secrets["SHEET_ID"])
        ws = sheet.worksheet("Commandes")
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            nom_client, article, taille, ville
        ])
    except Exception:
        pass

# ── STOCK SUMMARY FOR PROMPT ──────────────────────────────────────────────────
def format_stock_for_prompt(stock):
    if not stock:
        return "Stock non disponible pour l'instant."
    lines = []
    for item in stock:
        dispo = item.get("Stock_Dispo", "")
        if str(dispo).lower() in ["oui", "yes", "1", "true"]:
            lines.append(
                f"- {item.get('Nom_Article','?')} | {item.get('Categorie','?')} | "
                f"Tailles: {item.get('Taille','?')} | Couleurs: {item.get('Couleur','?')} | "
                f"Prix: {item.get('Prix_MAD','?')} MAD"
            )
    return "\n".join(lines) if lines else "Pas d'articles disponibles en ce moment."

# ── WHATSAPP LINK ─────────────────────────────────────────────────────────────
def whatsapp_link(message: str, phone: str = "212777139312") -> str:
    encoded = message.replace(" ", "%20").replace("\n", "%0A")
    return f"https://wa.me/{phone}?text={encoded}"

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
def build_system_prompt(infos, stock_text):
   return f"""Nti assistante dyal boutique Chez Wafae Sbai f Tanger, boutique dyal l'habillement.
Jawbi bdarija marocaine naturelle — kifma kat7ki nsa Tanger f reality.
Style: chaleureuse, professionnelle, directe. Machi excessive.

Exemples dyal darija marocaine:
- "Salam habibti! Mrhba bik, ash nqderek n3awnek?"
- "Iyeh kayen, zwin bzzaf!"
- "Bghiti tchouf chi 7aja okhra?"
- "Mzyan, chhal bghiti?"
- "La, hadi machi disponible daba — kayen X bla7a"

== INFOS BOUTIQUE ==
Boutique: {infos.get('boutique_nom', 'Chez Wafae Sbai')}
Adresse: {infos.get('adresse', '14 Rue Mohamed Abdou, Tanger 90000')}
WhatsApp: {infos.get('whatsapp', '0777139312')}
Horaires: {infos.get('horaires', '11h - 22h30')}
Livraison: {infos.get('livraison', 'Tout le Maroc')}
Paiement: {infos.get('paiement', 'Cash')}

== STOCK DISPONIBLE ==
{stock_text}

== RÈGLES ==
1. Jawbi dima bdarija marocaine naturelle, machi robotique
2. Ila bghat article, 3tiha info dyal taille, couleur, prix
3. Pour commander, dir lien WhatsApp direct
4. Ila machi disponible, goul b7al hadi w proposiha alternatives
5. Livraison l Maroc kamel
6. Paiement cash only
7. Horaires: {infos.get('horaires', '11h - 22h30')}
8. Max 3-4 lignes — machi tawil
9. Termina b proposer d'aider ou commander via WhatsApp
"""

== INFOS BOUTIQUE ==
Boutique: {infos.get('boutique_nom', 'Chez Wafae Sbai')}
Adresse: {infos.get('adresse', '14 Rue Mohamed Abdou, Tanger 90000')}
WhatsApp: {infos.get('whatsapp', '0777139312')}
Horaires: {infos.get('horaires', '11h - 22h30')}
Livraison: {infos.get('livraison', 'Tout le Maroc')}
Paiement: {infos.get('paiement', 'Cash')}

== STOCK DISPONIBLE ==
{stock_text}

== RÈGLES ==
1. Si client bghay article, 3tiha l'info dyal taille, couleur, prix min l-stock.
2. Pour commander, dir lien WhatsApp direct.
3. Si article machi disponible, goul bswaha w proposiha alternatives.
4. Pour livraison, goul dima kayna livraison l koll Maroc.
5. Paiement cash only.
6. Ila suwwlek 3la horaires: {infos.get('horaires', '11h - 22h30')}.
7. Jawbi b Darija + un peu de français — naturel, pas robotique.
8. Max 3-4 lignes par réponse — pas trop long.
9. Termina toujours par proposer d'aider davantage ou de commander via WhatsApp si pertinent.

Exemples de réponses naturelles:
- "Wach kayen X?" → "Iyeh ma sœur, kayen X f [couleur] b [prix] MAD 🌸 Bghiti tchoufih?"
- "Bghit ncommand" → "Mzyan! Dir lien ici pour WhatsApp Wafae 👇"
"""

# ── CLAUDE CALL ────────────────────────────────────────────────────────────────
def call_claude(messages_history, system_prompt):
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=system_prompt,
        messages=messages_history
    )
    return response.content[0].text

# ── DETECT COMMAND INTENT ─────────────────────────────────────────────────────
def detect_order_intent(text: str) -> bool:
    keywords = ["commander", "commande", "bghit", "acheter", "achat", "nakhod", "nchri", "howa", "ana bghit"]
    return any(k in text.lower() for k in keywords)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_wa_button" not in st.session_state:
    st.session_state.show_wa_button = False
if "wa_message" not in st.session_state:
    st.session_state.wa_message = ""

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
infos = get_infos_boutique()
stock = get_stock()
stock_text = format_stock_for_prompt(stock)
system_prompt = build_system_prompt(infos, stock_text)

# ── STOCK SIDEBAR ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛍️ Articles disponibles")
    if stock:
        for item in stock:
            dispo = str(item.get("Stock_Dispo", "")).lower()
            if dispo in ["oui", "yes", "1", "true"]:
                st.markdown(f"""
                <div class="stock-card">
                    <strong>{item.get('Nom_Article','')}</strong><br>
                    <small>📏 {item.get('Taille','')} &nbsp;|&nbsp; 🎨 {item.get('Couleur','')}</small><br>
                    <strong style="color:#D4567A">{item.get('Prix_MAD','')} MAD</strong>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Chargement du stock...")

    st.markdown("---")
    wa_url = whatsapp_link("Salam Wafae, bghit nssuwwel 3la article 🌸")
    st.markdown(f'<a href="{wa_url}" target="_blank" class="whatsapp-btn">💬 WhatsApp direct</a>', unsafe_allow_html=True)

# ── CHAT DISPLAY ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── WELCOME MESSAGE ───────────────────────────────────────────────────────────
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Salam ma sœur! 👗 Mrhba bik f **Chez Wafae Sbai** 🌸\n\n"
            "Ana hna bach n3awnek — stock, prix, livraison, commande...\n"
            "Ash bghiti t3rfi? 😊"
        )

# ── CHAT INPUT ────────────────────────────────────────────────────────────────
if user_input := st.chat_input("Ash bghiti t3rfi? (Darija / Français)"):
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Build history for Claude (last 10 messages)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[-10:]
    ]

    # Call Claude
    with st.chat_message("assistant"):
        with st.spinner("..."):
            try:
                reply = call_claude(history, system_prompt)
            except Exception as e:
                reply = "Smehli, kayen mochkil sgheir 🙏 Essayez encore ou contactez Wafae sur WhatsApp."

        st.markdown(reply)

        # Auto WhatsApp button if order intent detected
        if detect_order_intent(user_input) or detect_order_intent(reply):
            wa_msg = f"Salam Wafae 🌸 bghit ncommand — {user_input}"
            wa_url = whatsapp_link(wa_msg)
            st.markdown(
                f'<a href="{wa_url}" target="_blank" class="whatsapp-btn">📲 Commander sur WhatsApp</a>',
                unsafe_allow_html=True
            )

    st.session_state.messages.append({"role": "assistant", "content": reply})
