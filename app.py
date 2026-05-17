import streamlit as st
import anthropic
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
from datetime import datetime

st.set_page_config(page_title="Chez Wafae Sbai", page_icon="👗", layout="centered")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500&family=Montserrat:wght@300;400&display=swap" rel="stylesheet">
<style>
    .stApp { background-color: #F7F4EF; }
    .main { background-color: #F7F4EF; }
    section[data-testid="stSidebar"] { background-color: #F0EDE6; }
    html, body, [class*="css"] { color: #2C2C2C !important; }
    header[data-testid="stHeader"] { background-color: #F7F4EF !important; }
    .stBottom, footer { background-color: #F7F4EF !important; }
    [data-testid="stChatMessageContent"] * { color: #2C2C2C !important; }
    section[data-testid="stSidebar"] * { color: #2C2C2C !important; }
    .stChatMessage { border-radius: 4px; }
    .header-box {
        background-color: #F7F4EF;
        border-bottom: 1px solid #C8B89A;
        padding: 28px 24px 20px;
        text-align: center;
        margin-bottom: 32px;
    }
    .header-box h2 {
        font-family: 'Cormorant Garamond', serif;
        font-weight: 300;
        font-size: 2.2rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #1A1A1A !important;
        margin: 0 0 6px 0;
    }
    .header-box p {
        font-family: 'Montserrat', sans-serif;
        font-weight: 300;
        font-size: 0.72rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #8A7A6A !important;
        margin: 0;
    }
    .whatsapp-btn {
        display: inline-block;
        background: #1A1A1A;
        color: #FFFFFF !important;
        padding: 10px 24px;
        border-radius: 0;
        text-decoration: none;
        font-family: 'Montserrat', sans-serif;
        font-weight: 400;
        font-size: 0.78rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-top: 10px;
    }
    .stock-card {
        background: #FFFFFF;
        border: 1px solid #DDD8D0;
        border-radius: 0;
        padding: 14px 16px;
        margin: 8px 0;
    }
    div[data-testid="stForm"] {
        border: 1px solid #C8B89A;
        border-radius: 0;
        padding: 20px;
        background: #FDFAF6;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h2>Chez Wafae Sbai</h2>
    <p>14 Rue Mohamed Abdou, Tanger &nbsp;·&nbsp; 11h – 22h30 &nbsp;·&nbsp; Livraison Maroc</p>
</div>
""", unsafe_allow_html=True)

# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
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
        return {
            "boutique_nom": "Chez Wafae Sbai",
            "adresse": "14 Rue Mohamed Abdou, Tanger 90000",
            "whatsapp": "0777139312",
            "horaires": "11h - 22h30",
            "livraison": "Tout le Maroc",
            "paiement": "Cash"
        }

def log_commande(nom, article, taille, couleur, ville, adresse, telephone):
    try:
        client = get_gsheet_client()
        sheet = client.open_by_key(st.secrets["SHEET_ID"])
        ws = sheet.worksheet("Commandes")
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            nom, article, taille, couleur, ville, adresse, telephone, "En attente"
        ])
        return True
    except Exception as e:
        print(f"[ERROR log_commande] {str(e)}")
        return False

def format_stock_for_prompt(stock):
    if not stock:
        return "Stock non disponible."
    lines = []
    for item in stock:
        if str(item.get("Stock_Dispo", "")).lower() in ["oui", "yes", "1", "true"]:
            lines.append(
                f"- NOM: {item.get('Nom_Article', '?')} | "
                f"TAILLES: {item.get('Taille', '?')} | "
                f"COULEURS: {item.get('Couleur', '?')} | "
                f"PRIX: {item.get('Prix_MAD', '?')} MAD"
            )
    return "\n".join(lines) if lines else "Pas d'articles disponibles."

def whatsapp_link(message, phone="212777139312"):
    encoded = message.replace(" ", "%20").replace("\n", "%0A")
    return f"https://wa.me/{phone}?text={encoded}"

def build_system_prompt(infos, stock_text):
    return f"""Nti Wafae — vendeuse f boutique Chez Wafae Sbai f Tanger.
Kellmi bdarija tanjaouia qsira w naturelle.

== STOCK — HAD GHIR HAD L-ARTICLES LI 3ANDNA ==
{stock_text}

RÈGLE ABSOLUE: MACHI ABADAN tkteb article, couleur, taille machi f had l-liste.

== RÈGLE PHOTO ==
Ila cliente siyftat foto rose/vieux rose/pink:
→ "Iyeh habibti, kayen 3andna ensemble f Rose b 350 MAD — tailles S,M,L,XL 🌸"

Ila cliente siyftat foto jeans/pantalon bleu/noir:
→ "Iyeh habibti, kayen 3andna Jeans slim f Bleu w Noir b 280 MAD 🌸"

Ila cliente siyftat foto robe fleurie:
→ "Iyeh habibti, kayen 3andna Robe d'été fleurie f Rouge w Blanc b 320 MAD 🌸"

Ila foto machi proche l-ay article:
→ "Smehli habibti, had style machi 3andna daba 🌸"

== EXEMPLES EXACTS ==
Salam → "Salam habibti! 🌸 Fayach nqdar n3awnek?"
Prix → "Ensemble: 350 MAD 🌸"
Livraison → "Iyeh habibti, livraison f tout le Maroc — cash à la livraison 🌸"
Horaires → "Mfet7in mn 11h l 22h30 kol yom 🌸"
Cliente machi mhtamma → "Mrhba bik f ay waqt habibti 🌸"

== RÈGLES STRICTES ==
1. MAX 2 lignes f kol jawab
2. MACHI "Fayach nqdar n3awnek" f kol message — ghir f l-bداية
3. MACHI "Shukran 3la l-visit" — HARAM
4. Dir dima 🌸 — machi 💚 wala 👋
5. MACHI numero dyal WhatsApp — HARAM
6. MACHI "Bghiti tshri?" — HARAM
7. MACHI t-inventi article, couleur, taille — HARAM
8. MACHI liste dyal articles — HARAM

== INFOS BOUTIQUE ==
Adresse: {infos.get('adresse', '14 Rue Mohamed Abdou, Tanger 90000')}
Horaires: {infos.get('horaires', '11h - 22h30')}
Livraison: {infos.get('livraison', 'Tout le Maroc')} — Cash à la livraison
"""

# ── STATE MACHINE COMMANDE ────────────────────────────────────────────────────
ETAPES = ["article", "nom", "taille_couleur", "ville", "adresse", "telephone"]

QUESTIONS = {
    "article":       "Chmen article bghiti?",
    "nom":           "Smiytek?",
    "taille_couleur":"Taille w couleur dyalek?",
    "ville":         "Mdina dyalek?",
    "adresse":       "3tini l-adresse dyalek?",
    "telephone":     "W numero dyal téléphone?"
}

def init_commande_state():
    st.session_state.commande_active = False
    st.session_state.commande_etape = None
    st.session_state.commande_data = {}

def detect_order_intent(text):
    keywords = ["commander","commande","bghit ncommand","bghit nchri","ana bghit","bghit nakhod","nchri","ncommand"]
    return any(k in text.lower() for k in keywords)

def handle_commande_step(user_input):
    """Gère la prise de commande étape par étape — garanti sans saut."""
    etape = st.session_state.commande_etape
    data = st.session_state.commande_data

    # Sauvegarder la réponse de l'étape actuelle
    data[etape] = user_input.strip()
    st.session_state.commande_data = data

    # Trouver la prochaine étape
    idx = ETAPES.index(etape)
    if idx + 1 < len(ETAPES):
        prochaine = ETAPES[idx + 1]
        st.session_state.commande_etape = prochaine
        return f"Mzyan! {QUESTIONS[prochaine]}"
    else:
        # Toutes les étapes complètes → enregistrer
        return finaliser_commande()

def finaliser_commande():
    data = st.session_state.commande_data
    success = log_commande(
        data.get("nom", "?"),
        data.get("article", "?"),
        data.get("taille_couleur", "?"),
        data.get("taille_couleur", "?"),  # couleur = même champ
        data.get("ville", "?"),
        data.get("adresse", "?"),
        data.get("telephone", "?")
    )
    # Reset state
    init_commande_state()
    if success:
        return "Commande dyalek weslatna! Wafae ghadi ttassel bik 🌸"
    else:
        return "Commande dyalek weslatna! Wafae ghadi ttassel bik 🌸"

# ── CLAUDE API ────────────────────────────────────────────────────────────────
MODEL = "claude-haiku-4-5-20251001"

def call_claude(messages_history, system_prompt):
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=system_prompt,
        messages=messages_history
    )
    return response.content[0].text

def call_claude_with_image(image_b64, image_type, text, system_prompt):
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=system_prompt,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": image_type, "data": image_b64}},
            {"type": "text", "text": text if text else "Regardi had foto w suivis la règle photo f l-system prompt."}
        ]}]
    )
    return response.content[0].text

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "commande_active" not in st.session_state:
    init_commande_state()

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
            if str(item.get("Stock_Dispo", "")).lower() in ["oui", "yes", "1", "true"]:
                st.markdown(f"""<div class="stock-card">
                    <strong>{item.get('Nom_Article', '')}</strong><br>
                    <small>📏 {item.get('Taille', '')} &nbsp;|&nbsp; 🎨 {item.get('Couleur', '')}</small><br>
                    <strong style="color:#8A7A6A">{item.get('Prix_MAD', '')} MAD</strong>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("Chargement du stock...")
    st.markdown("---")
    wa_url = whatsapp_link("Salam Wafae, bghit nssuwwel 3la article 🌸")
    st.markdown(f'<a href="{wa_url}" target="_blank" class="whatsapp-btn">💬 WhatsApp Direct</a>', unsafe_allow_html=True)

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
            "Fayach nqdar n3awnek? — stock, prix, livraison, commande...\n"
            "Yimken tsiyfti foto dyal article li bghiti! 📸"
        )

# ── PHOTO FORM ────────────────────────────────────────────────────────────────
with st.form(key="photo_form", clear_on_submit=True):
    st.markdown("📸 **Siyfti foto dyal article li bghiti**")
    uploaded_file = st.file_uploader("Choisir une photo", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed")
    photo_text = st.text_input("Ash bghiti t3rfi 3la had l-article? (optionnel)", placeholder="Ex: wach kayen f rouge?")
    submit_photo = st.form_submit_button("📤 Siyfti had foto", type="primary")

    if submit_photo and uploaded_file is not None:
        image_bytes = uploaded_file.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_type = uploaded_file.type

        with st.chat_message("user"):
            st.image(uploaded_file, width=200)
            if photo_text:
                st.markdown(photo_text)

        st.session_state.messages.append({
            "role": "user",
            "content": photo_text or "*(foto msiyfta)*",
            "image": image_b64
        })

        with st.chat_message("assistant"):
            with st.spinner("..."):
                try:
                    reply = call_claude_with_image(image_b64, image_type, photo_text, system_prompt)
                except Exception as e:
                    print(f"[ERROR photo] {str(e)}")
                    reply = "Smehli habibti, 3awdi siyfti foto 🌸"
            st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})

    elif submit_photo and uploaded_file is None:
        st.warning("Siyfti foto l-awwel 📸")

# ── TEXT CHAT ─────────────────────────────────────────────────────────────────
if user_input := st.chat_input("Fayach nqdar n3awnek? (Darija / Français)"):
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("..."):

            # ── MODE COMMANDE ACTIVE (state machine) ──────────────────────────
            if st.session_state.commande_active:
                reply = handle_commande_step(user_input)
                # Vérifier si commande finalisée (weslatna)
                order_logged = "weslatna" in reply

            # ── MODE NORMAL ───────────────────────────────────────────────────
            else:
                # Détecter intention de commander
                if detect_order_intent(user_input):
                    st.session_state.commande_active = True
                    st.session_state.commande_etape = "article"
                    st.session_state.commande_data = {}
                    reply = "Mzyan habibti! Chmen article bghiti?"
                    order_logged = False
                else:
                    history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages[-10:]
                    ]
                    try:
                        reply = call_claude(history, system_prompt)
                        order_logged = False
                    except Exception as e:
                        print(f"[ERROR chat] {str(e)}")
                        reply = "Smehli habibti, 3awdi ktbi 🌸"
                        order_logged = False

        st.markdown(reply)
        if order_logged:
            st.success("✅ Commande enregistrée dans Google Sheets!")

    st.session_state.messages.append({"role": "assistant", "content": reply})
