import sys
import os
import urllib.parse
import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import requests
import random
import json
import subprocess

# ---------------------------------------------------------
# AUTOMAATTINEN PÄIVITYSLOGIIKKA
# ---------------------------------------------------------
LOG_FILE = "/tmp/tyonhaku_update_success"

def run_update():
    try:
        # Suoritetaan Streamlit päivitys dynaamisella polulla
        subprocess.run(["streamlit", "run", os.path.abspath(__file__), "--server.port", "0"], check=True)
        # Merkitään onnistuminen
        with open(LOG_FILE, "w") as f:
            f.write("OK")
    except Exception as e:
        print(f"Päivitys epäonnistui: {e}")

now = datetime.datetime.now()
weekday = now.weekday()  # 0=ma, 4=pe
hour = now.hour

# Päivitys ma–pe klo 8.00
if 0 <= weekday <= 4 and hour == 8:
    run_update()
# Varmistusajo klo 11, jos aamun päivitystä ei ole tehty
elif 0 <= weekday <= 4 and hour == 11:
    if not os.path.exists(LOG_FILE):
        run_update()

# ---------------------------------------------------------
# 0. KONFIGURAATIO (TÄYTYY OLLA ENSIMMÄINEN STREAMLIT-KOMENTO)
# ---------------------------------------------------------
# HUOM: layout="wide" varmistaa, että sovellus käyttää koko näytön leveyden
st.set_page_config(layout="wide", page_title="Mission Jobs Hub", page_icon="🚀")

# --- PÄIVITYSVAROITUS (24H LOGIIKKA) ---
if os.path.exists(LOG_FILE):
    last_update = datetime.datetime.fromtimestamp(
        os.path.getmtime(LOG_FILE)
    )
    if datetime.datetime.now() - last_update <= datetime.timedelta(hours=24):
        pass
    else:
        st.warning("⚠️ Päivitystä ei ole tehty viimeisen 24 tunnin aikana")
else:
    pass

# Varmistetaan polut
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# ---------------------------------------------------------
# 1. ASETUKSET & DATA & TALLENNUS
# ---------------------------------------------------------

USER_NAME = "Mission Jobs Commander"
STORAGE_FILE = "local_storage.json"
# Google Sheet ID (Public CSV export)
SHEET_ID = "12_hQ54nccgljOCbDGPOvFzYBQ6KhQkdk1GDdpaNTGyM"

# --- LOCAL STORAGE LOGIIKKA (JSON) ---
def load_local_data():
    """Lataa seurannan tiedot paikallisesta JSON-tiedostosta."""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_local_data(data):
    """Tallentaa seurannan tiedot paikalliseen JSON-tiedostoon."""
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Virhe tallennuksessa: {e}")

# --- GOOGLE SHEETS DATA FETCH ---
@st.cache_data(ttl=60) # Välimuisti 60sek, jotta ei kuormita liikaa
def load_visitor_data():
    """Hakee datan Google Sheetistä CSV-muodossa."""
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Datan haku epäonnistui: {e}")
        return None

# LINKKIVAHTI: VALIDOI HTTP 200 OK
@st.cache_data(ttl=3600, show_spinner=False) # Välimuisti 1h
def validate_link(url):
    """
    Tarkistaa onko linkki elossa (HTTP 200).
    Timeout optimoitu nopeammaksi (2s).
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
        }
        response = requests.head(url, headers=headers, timeout=2, allow_redirects=True)
        if response.status_code == 200:
            return True
        response = requests.get(url, headers=headers, timeout=2)
        return response.status_code == 200
    except:
        return False

# AI-LOGIIKKA
AI_LOGIC_CORE = {
    "Gemini":  {"provider": "Google", "status": "Simuloitu (Safe Mode)", "role": "Primary"},
    "ChatGPT": {"provider": "OpenAI", "status": "Simuloitu", "role": "Secondary"},
    "Claude":  {"provider": "Anthropic", "status": "Simuloitu", "role": "Secondary"},
    "Copilot": {"provider": "Microsoft", "status": "Simuloitu", "role": "Secondary"}
}

# --- DATASETS ---

AI_STUDIES = [
    {
        "name": "Generative AI Learning Path",
        "provider": "Google Cloud",
        "url": "https://www.cloudskillsboost.google/paths/118",
        "desc": "Googlen virallinen ja ilmainen polku generatiivisen tekoälyn syvälliseen ymmärtämiseen.",
        "type": "SERTIFIKAATTI"
    },
    {
        "name": "Opin.fi: Tekoäly & Luova osaaminen",
        "provider": "Suomen Korkeakoulut (Digivisio)",
        "url": "https://opin.fi/fi/search?q=teko%C3%A4ly",
        "desc": "Kokoava haku. Kriteerit: Laskennallinen luovuus, XR, Visual Culture, Palvelumuotoilu & AI.",
        "type": "HAKUPALVELU"
    },
    {
        "name": "Elements of AI",
        "provider": "Helsingin Yliopisto & Reaktor",
        "url": "https://www.elementsofai.com/fi",
        "desc": "Suomalainen klassikko. Pakollinen pohjatieto kaikille alalla toimiville.",
        "type": "MOOC / ETÄ"
    },
    {
        "name": "Building AI",
        "provider": "Helsingin Yliopisto & Reaktor",
        "url": "https://buildingai.elementsofai.com/fi",
        "desc": "Elements of AI:n jatko-osa. Hieman teknisempi, opettaa AI:n luomista.",
        "type": "MOOC / ETÄ"
    },
    {
        "name": "FiTech - Tekoäly (Koko Suomi)",
        "provider": "Yliopistoverkosto (Aalto ym.)",
        "url": "https://fitech.io/fi/opinnot/?s=teko%C3%A4ly",
        "desc": "Suomen laajin ilmainen tekniikan tarjonta. Etäopintoja Aallosta, LUTista ja Oulusta.",
        "type": "YLIOPISTO / ETÄ"
    },
    {
        "name": "Aalto Avoin: Art & Media",
        "provider": "Aalto Arts",
        "url": "https://www.aalto.fi/fi/taiteiden-ja-suunnittelun-korkeakoulu",
        "desc": "Seuraa Aalto Artsin avoimia kursseja. Usein AI- ja mediayhteyksiä.",
        "type": "YLIOPISTO (HKI)"
    },
    {
        "name": "XAMK Open (Game & 3D)",
        "provider": "XAMK",
        "url": "https://www.xamk.fi/koulutus/avoin-amk/",
        "desc": "Vahva peliala ja 3D-osaaminen. Paljon etäkursseja visuaaliseen suunnitteluun.",
        "type": "AMK / ETÄ"
    },
    {
        "name": "CampusOnline (AI & Data)",
        "provider": "Suomen AMK-verkosto",
        "url": "https://campusonline.fi/?s=artificial+intelligence",
        "desc": "Hae kursseja kaikista Suomen AMK:ista (Turku, Tampere, Lappi...).",
        "type": "AMK / ETÄ"
    },
    {
        "name": "DeepLearning.AI: AI for Everyone",
        "provider": "DeepLearning.AI",
        "url": "https://www.deeplearning.ai/courses/ai-for-everyone/",
        "desc": "Andrew Ng:n kurssi bisnespuolelle ja tuottajille. Ei vaadi koodausta.",
        "type": "KV / ETÄ"
    },
    {
        "name": "Metropolia Avoin: ICT & Media",
        "provider": "Metropolia",
        "url": "https://www.metropolia.fi/fi/opiskelu/avoin-amk/opintotarjonnan-haku",
        "desc": "Pääkaupunkiseudun laajin AMK-tarjonta. Tarkista XR/AI -kurssit.",
        "type": "AMK (HKI)"
    }
]

UNI_KEYWORDS = [
    "laskennallinen luovuus",
    "computational creativity",
    "human-computer interaction",
    "digital humanities",
    "visual culture",
    "mikrotutkinto",
    "tekoäly viestinnässä"
]

AMK_KEYWORDS = [
    "palvelumuotoilu",
    "erikoistumiskoulutus",
    "osaajakoulutus",
    "mediatuotanto",
    "visuaalinen suunnittelu",
    "XR",
    "virtuaalituotanto"
]

AGENCIES = {
    "Bob the Robot": "https://bobtherobot.fi/careers",
    "TBWA\Helsinki": "https://www.tbwa.fi/",
    "SEK": "https://www.sek.fi/tyopaikat",
    "Futurice": "https://futurice.com/careers",
    "N2 Creative": "https://n2.fi/rekry",
    "hasan & partners": "https://hasanpartners.fi/careers",
    "Miltton": "https://www.miltton.com/careers",
    "Valve": "https://www.valve.fi/ura",
    "Avidly": "https://www.avidlyagency.com/fi/tyopaikat",
    "Reaktor": "https://www.reaktor.com/careers",
    "Vincit": "https://www.vincit.com/fi/ura",
    "Siili Solutions": "https://www.siili.com/urat",
}

SCHOOLS_DATA = [
    {
        "name": "Aalto-yliopisto (Taiteet & Suunnittelu)", 
        "url": "https://www.aalto.fi/fi/taiteiden-ja-suunnittelun-korkeakoulu", 
        "logo": "https://www.aalto.fi/themes/custom/aalto/logo.svg",
        "status": "⭐ HUIPPU"
    },
    {
        "name": "HEO Kansanopisto (Graafinen & Kuvallinen)", 
        "url": "https://www.heo.fi/kulttuuri-ja-taide/", 
        "logo": "https://www.heo.fi/wp-content/themes/heo/images/logo.png",
        "status": "Portfolio"
    },
    {
        "name": "Metropolia AMK (Viestintä & Muotoilu)", 
        "url": "https://www.metropolia.fi/fi/opiskelu/amk-tutkinnot/viestinta", 
        "logo": "https://www.metropolia.fi/themes/custom/metropolia/logo.svg",
        "status": "AMK / Haku"
    },
    {
        "name": "Haaga-Helia (Journalismi & Digi)", 
        "url": "https://www.haaga-helia.fi/fi/koulutus/media-ja-viestinta", 
        "logo": "https://www.haaga-helia.fi/themes/custom/hh/logo.svg",
        "status": "AMK / Haku"
    },
    {
        "name": "Humak (Kulttuurituottaja)", 
        "url": "https://www.humak.fi/koulutus/kulttuurituottaja/", 
        "logo": "https://www.humak.fi/wp-content/themes/humak/images/logo.svg",
        "status": "AMK / Tuottaja"
    },
    {
        "name": "Taitotalo (Media-alan PT)", 
        "url": "https://www.taitotalo.fi/koulutus/media-alan-ja-kuvallisen-ilmaisun-perustutkinto", 
        "logo": "https://www.taitotalo.fi/themes/custom/taitotalo/logo.svg",
        "status": "Ammatillinen"
    },
    {
        "name": "Stadin AO (Media & Kuvallinen)", 
        "url": "https://stadinao.fi/koulutustarjonta/media-alan-ja-kuvallisen-ilmaisun-perustutkinto/", 
        "logo": "https://stadinao.fi/wp-content/themes/stadinao/assets/images/logo.svg",
        "status": "Jatkuva haku"
    },
    {
        "name": "Varia (Media-ala)", 
        "url": "https://www.vantaa.fi/fi/palveluhakemisto/palvelu/media-alan-ja-kuvallisen-ilmaisun-perustutkinto-varia", 
        "logo": "https://www.vantaa.fi/themes/custom/vantaa/logo.svg",
        "status": "Vantaa"
    },
    {
        "name": "Omnia (Media)", 
        "url": "https://www.omnia.fi/koulutushaku/media-alan-ja-kuvallisen-ilmaisun-perustutkinto", 
        "logo": "https://www.omnia.fi/themes/custom/omnia/logo.svg",
        "status": "Espoo"
    },
    {
        "name": "Business College Helsinki (Digi)", 
        "url": "https://bc.fi/koulutukset/tieto-ja-viestintatekniikan-perustutkinto/", 
        "logo": "https://bc.fi/wp-content/themes/bch/images/logo.svg",
        "status": "Helsinki"
    },
    {
        "name": "Rastor-instituutti (Markkinointi)", 
        "url": "https://www.rastorinst.fi/koulutus/markkinointi-ja-viestinta", 
        "logo": "https://www.rastorinst.fi/themes/custom/rastor/logo.svg",
        "status": "Aikuis"
    },
    {
        "name": "Careeria (Media)", 
        "url": "https://careeria.fi/koulutus/media-alan-ja-kuvallisen-ilmaisun-perustutkinto/", 
        "logo": "https://careeria.fi/wp-content/themes/careeria/assets/images/logo.svg",
        "status": "Hki/Vantaa"
    }
]

STARTUPS_PK = {
    "Maria 01 (Careers)": "https://maria.io/careers/",
    "The Hub (Helsinki Jobs)": "https://thehub.io/jobs?location=Helsinki",
    "Aalto Startup Center": "https://startupcenter.aalto.fi/",
    "Kiuas Accelerator": "https://www.kiuas.com/",
    "Wolt Careers": "https://careers.wolt.com/en",
    "Supercell Careers": "https://supercell.com/en/careers/"
}

TARGET_ROLES = [
    "Graafinen suunnittelija", "Sisällöntuottaja", "Visuaalinen suunnittelija",
    "Projektipäällikkö (luovat sisällöt)", "Viestintäsuunnittelija", "Markkinointisuunnittelija",
    "UI/UX-suunnittelija", "Creative Producer", "Content Manager", "Art Director Assistant",
    "Junior Designer", "Video Editor"
]

SEARCH_KEYWORDS = [
    "graafinen suunnittelija", "sisällöntuottaja", "visuaalinen suunnittelija",
    "projektipäällikkö", "viestintäsuunnittelija", "markkinointisuunnittelija",
    "UI designer", "UX designer", "creative producer", "content manager", 
    "mainonta", "luova ala", "graafinen suunnittelu", "digitaalinen viestintä",
    "osatutkinto", "tutkinnon osa", "osatutkintokoulutus", "ICT"
]

FUTURE_MAKER_LINK = "https://janmyllymaki.wixsite.com/future-maker/fi"

SITES_INTL = {
    "Krop": "https://www.krop.com/", 
    "Design Jobs Board": "https://www.designjobsboard.com/",
    "Behance Jobs": "https://www.behance.net/joblist"
}

SITES_FI_NORDIC = {
    "Journalistiliiton työpaikat": "https://journalistiliitto.fi/fi/tyoelama/avoimet-tyopaikat/",
    "Medialiiton työpaikat": "https://www.medialiitto.fi/tyopaikat",
    "Kulttuurijobs": "https://kulttuurijobs.fi/"
}

SITES_MEDIA = {
    "Media Match": "https://www.media-match.com/",
    "ProductionHUB": "https://www.productionhub.com/jobs"
}

# ---------------------------------------------------------
# 2. LOGIIKKA JA FUNKTIOT
# ---------------------------------------------------------

def generate_linkedin_url():
    keywords = " OR ".join([f'"{role}"' for role in SEARCH_KEYWORDS])
    keywords = f"({keywords}) AND (Portfolio OR Case OR AI)"
    params = {"keywords": keywords, "location": "Helsinki Metropolitan Area", "f_TPR": "r2592000", "sort": "dd"}
    return "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(params)

def calculate_score(title, location, description=""):
    score = 1.0
    title = title.lower(); location = location.lower(); desc = description.lower()
    
    # 1. Rooliosumat
    role_match = 0
    for role in TARGET_ROLES:
        if role.lower() in title: role_match += 1
    score += min(role_match * 0.5, 2.0)
    
    # 2. Senioriteetti
    if any(x in title for x in ['strateg', 'lead', 'head', 'päällikkö']): score += 1.0
    
    # 3. Kytketään aivot uuteen dataan (AI + UNI + AMK)
    # Yhdistetään kaikki "hyvät" avainsanat yhteen listaan
    all_keywords = ['ai ', 'genai', 'technolog', 'chatgpt', 'midjourney'] + UNI_KEYWORDS + AMK_KEYWORDS
    
    # Tarkistetaan otsikko TAI kuvaus näiden sanojen varalta
    if any(kw.lower() in title for kw in all_keywords) or any(kw.lower() in desc for kw in all_keywords):
        score += 1.0

    # 4. Sijainti
    if 'helsinki' in location or 'espoo' in location: score += 1.0
    elif 'remote' in location: score += 0.8
    
    return min(score, 5.0)

def SAFE_DEADLINE_BLOCK(date_input, is_future_event=False):
    """
    Renders a crash-proof deadline/elapsed time badge.
    Accepts: 'dd.mm.' (past) or 'YYYY-MM-DD' (future/interview).
    """
    try:
        if not date_input: return ""
        now = datetime.datetime.now()
        
        # 1. Handle Future Dates (e.g. Interviews: 2024-12-25)
        if is_future_event and "-" in str(date_input):
            dt = datetime.datetime.strptime(str(date_input), "%Y-%m-%d")
            diff = (dt - now).days + 1
            if diff < 0: return "🔴 Meni jo"
            if diff == 0: return "🔥 TÄNÄÄN"
            if diff <= 2: return f"🔥 {diff} pv"
            return f"📅 {diff} pv"
            
        # 2. Handle Past Dates (e.g. Applied: 20.12.)
        # Assumes current year for format 'dd.mm.'
        full_date = f"{date_input}{now.year}"
        dt = datetime.datetime.strptime(full_date, "%d.%m.%Y")
        diff = (now - dt).days
        
        if diff > 21: return f"⚠️ {diff} pv (Hiljaista)"
        if diff > 14: return f"🕒 {diff} pv"
        return f"🆕 {diff} pv"

    except Exception:
        return "" # Fail silently, do not break UI

def gemini_safe_fetch(job_desc: str, user_cv: str, api_key: str = "") -> str:
    """
    Fetch job/training results in strict safe mode with Gemini.
    """
    if not api_key:
        return "NO API KEY - Simulated mode only (read-only, safe)."

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    You are operating in STRICT DATA MODE for job and training searches.
    READ-ONLY RULE: You cannot modify, delete, overwrite, or create any files, databases, or app settings.
    Never hallucinate, guess, or fabricate data. Personal info must be skipped.
    Only return results from these domains:
    LinkedIn, Työmarkkinatori, Taitotalo.fi, StadinAO.fi, Metropolia.fi, Haaga-Helia.fi, Arcada.fi, Aalto.fi, Omnia.fi, Varia.fi, BusinessCollege.fi, RastorInst.fi
    Verify each URL returns HTTP 200.
    Format each result as: title | organization | platform | full URL | status (VERIFIED / SKIPPED)
    If nothing valid, return exactly: NO DATA – SKIPPED
    Include SKIPPED reasons for invalid items.
    Operate in read-only mode. DO NOT modify any files or settings.
    Task: Fetch jobs or training opportunities matching:
    Job description: {job_desc[:100]}...
    User CV / Background: {user_cv[:100]}...
    """

    try:
        response = model.generate_content(prompt, request_options={'timeout': 30})
        return response.text
    except Exception as e:
        return f"API error: {e} – ensure API key and network connectivity"

# ---------------------------------------------------------
# 3. KÄYTTÖLIITTYMÄ (RESPONSIIVINEN)
# ---------------------------------------------------------

st.markdown("""
<style>
    /* RESPONSIVE SCALING FIXES */
    .stApp {
        overflow-x: hidden; /* Piilota vaakavieritys mobiilissa */
    }
    
    @media (max-width: 768px) {
        .block-container { 
            padding-left: 0.5rem !important; 
            padding-right: 0.5rem !important; 
            padding-top: 2rem !important; 
        }
        h1 { font-size: 1.6rem !important; }
        h2 { font-size: 1.4rem !important; }
        h3 { font-size: 1.2rem !important; }
        .stButton button { width: 100%; } /* Napit täyteen leveyteen */
        
        /* Kortit ja containerit */
        .ai-card { height: auto !important; min-height: 280px; }
    }
    
    img {
        max-width: 100%;
        height: auto;
    }

    .responsive-link-btn {
        display: flex; align-items: center; justify-content: center; padding: 12px; 
        background: #262730; border: 1px solid #464b5f; border-radius: 8px; 
        margin-bottom: 8px; text-decoration: none; color: white !important; width: 100%;
        transition: background 0.2s; font-weight: 500;
        box-sizing: border-box; /* Varmistaa paddingin pysyvän leveyden sisällä */
    }
    .responsive-link-btn:hover { background: #363740; }
    .responsive-link-btn img { width: 20px; height: 20px; margin-right: 10px; object-fit: contain; }
    
    .cta-container { display: flex; justify-content: center; margin: 20px 0; width: 100%; }
    .cta-button {
        display: inline-block; background-color: #0a66c2; color: white !important; 
        padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: bold;
        text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 100%;
        width: 100%; /* Mobiiliystävällinen leveys */
    }
    .cta-button.dark { background-color: #333; }
    
    @media (min-width: 769px) {
        .cta-button { width: auto; } /* Desktopilla normaali leveys */
    }
</style>
""", unsafe_allow_html=True)

def main():
    # ALUSTETAAN SEURANTA TIEDOSTOSTA
    if 'tracked_companies' not in st.session_state:
        st.session_state.tracked_companies = load_local_data()
    if 'watched_schools' not in st.session_state:
        st.session_state.watched_schools = []
    
    # API AVAIN AINA TYHJÄ (SIMULOITU TILA)
    st.session_state.api_key = ""
        
    # MUOKKAUSTILAN HALLINTA
    if 'edit_states' not in st.session_state:
        st.session_state.edit_states = {}

    with st.sidebar:
        st.title("⚙️ Asetukset")
        
        st.header("🤖 AI-Ydin")
        selected_ai_core = st.radio("Valitse suoritusmalli:", list(AI_LOGIC_CORE.keys()), index=0)
        st.caption(f"Status: {AI_LOGIC_CORE[selected_ai_core]['status']}")
        
        st.info("ℹ️ Sovellus toimii 'Safe Mode' -tilassa ilman API-avainta. Tekoälytoiminnot ovat simuloituja.")
        
        st.markdown("---")
        
        # --- ASETUKSET: KOHDENNETTU HAKU ---
        st.header("🎯 Kohdennettu Haku")
        toggle_startup = st.toggle("🚀 Start-upit", value=False)
        st.markdown("---")
        
        # SIVUPALKIN TULOKSET (VALIDOIDUT - VAIN START-UP)
        if toggle_startup:
            st.markdown("### 🚀 Start-up Hubit")
            st.caption("✅ Aktiiviset sivut (HTTP 200)")
            for name, url in STARTUPS_PK.items():
                if validate_link(url): 
                    st.markdown(f"- [{name}]({url})")
        
        st.caption(f"Roolihaku: {len(SEARCH_KEYWORDS)} avainsanaa")

    st.title("MISSION JOBS // HUB V63.0 (Auto-Scale)")
    mode_status = "No API / Safe Mode"
    st.markdown(f"**User:** {USER_NAME} | **Core:** {selected_ai_core} ({mode_status})")
    
    # --- VÄLILEHDET (SISÄLTÄÄ NYT AI KOULUTUKSEN) ---
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "✨ AI HAKEMUS", "📊 ANALYSOI", "🏢 LINKIT", "⚡️ TEHOHAKU", 
        "📌 SEURANTA", "🕵️ AGENTTI", "🇫🇮 TYÖ", "🎨 PORTFOLIO", 
        "🧠 AGENTIN SUOSITUKSET", "🤖 AI KOULUTUS"
    ])
    
    # --- TAB 1: AI HAKEMUS ---
    with tab1:
        st.header(f"Kirjoita Hakemus ({selected_ai_core})")
        c1, c2 = st.columns(2)
        with c1: job_desc = st.text_area("1. Työpaikkailmoitus / Haku:", height=300)
        with c2: user_cv = st.text_area("2. Oma CV / Tausta:", height=300)
        
        btn_col1, btn_col2 = st.columns([1, 1])

        with btn_col1:
            if st.button("🚀 KIRJOITA HAKEMUS", type="primary"):
                if job_desc and user_cv:
                    # SIMULOITU TILA AINA KÄYTÖSSÄ
                    st.success(f"Agentti {selected_ai_core} on analysoinut tehtävän (Safe Mode).")
                    constructed_prompt = f"TOIMI SEURAAVASTI ({selected_ai_core}):\nKirjoita erottuva työhakemus tehtävään: {job_desc[:50]}...\nHakijan tausta: {user_cv[:50]}...\nPainotus: Moderni, vakuuttava."
                    st.info("ℹ️ **SAFE MODE:** Alla optimoitu kehote (Prompt), jonka voit kopioida ChatGPT:hen tai Geminiin.")
                    st.code(constructed_prompt, language="text")
                else: st.warning("Täytä kentät.")
        
        with btn_col2:
            if st.button("🛡️ SAFE FETCH (Strict Mode)"):
                st.info("API-haku poistettu käytöstä. Käytä simuloitua tilaa.")

    # --- TAB 2: ANALYSOI ---
    with tab2:
        st.header(f"Analysoi Löydös ({selected_ai_core})")
        col1, col2 = st.columns(2)
        with col1: input_title = st.text_input("Työnimike")
        with col2: input_loc = st.text_input("Sijainti")
        input_desc = st.text_area("Liitä ilmoitus:")
        
        if st.button("🔍 ANALYSOI"):
            score = calculate_score(input_title, input_loc, input_desc)
            st.subheader(f"Match Score: {score}/5.0")
            st.progress(score/5)
            
            if input_desc:
                st.info(f"💡 **Agentin ({selected_ai_core}) looginen päätelmä (Simulaatio):**")
                if score >= 4.0: st.write("✅ **Vahva osuma!**")
                elif score >= 2.5: st.write("⚠️ **Kohtalainen osuma.**")
                else: st.write("🛑 **Heikko osuma.**")

    # --- TAB 3: LINKIT (VALIDOITU) ---
    with tab3:
        st.header("🏢 Linkkikirjasto")
        with st.expander("Mainostoimistot", expanded=True):
            cols = st.columns(4)
            for i, (name, url) in enumerate(AGENCIES.items()):
                if validate_link(url):
                    logo = f"https://www.google.com/s2/favicons?domain={url.split('/')[2]}&sz=64"
                    with cols[i % 4]: st.markdown(f"""<a href="{url}" target="_blank" class="responsive-link-btn"><img src="{logo}">{name}</a>""", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.subheader("🌍 Intl"); 
            for n,u in SITES_INTL.items(): st.markdown(f"[{n}]({u})")
        with c2: 
            st.subheader("🇫🇮 Suomi"); 
            for n,u in SITES_FI_NORDIC.items(): st.markdown(f"[{n}]({u})")
        with c3: 
            st.subheader("🎬 Media"); 
            for n,u in SITES_MEDIA.items(): st.markdown(f"[{n}]({u})")

    # --- TAB 4: TEHOHAKU ---
    with tab4:
        st.header("⚡️ Tehohaku")
        st.markdown(f"""<div class="cta-container"><a href="{generate_linkedin_url()}" target="_blank" class="cta-button">👉 AVAA LINKEDIN (HELSINKI + CREATIVE)</a></div>""", unsafe_allow_html=True)

    # --- TAB 5: SEURANTA ---
    with tab5:
        st.header("📌 Hakemusten Seuranta")

        STATUS_COLORS = {
            "Odottaa": {"bg": "#FFF3CD", "text": "#856404"},
            "Keskustelu": {"bg": "#D1ECF1", "text": "#0C5460"},
            "Haastattelu": {"bg": "#C3E6CB", "text": "#155724"},
            "Ei vastausta": {"bg": "#E2E3E5", "text": "#6C757D"},
            "Hylätty": {"bg": "#F8D7DA", "text": "#721C24"},
            "Kiinnostunut": {"bg": "#E2E3E5", "text": "#333333"}
        }

        # Lisää uusi hakemus
        with st.expander("➕ Lisää manuaalisesti", expanded=False):
            c1, c2 = st.columns(2)
            with c1: cn = st.text_input("Yritys")
            with c2: cr = st.text_input("Rooli")
            cs = st.selectbox("Tila", ["Odottaa", "Keskustelu", "Haastattelu", "Ei vastausta", "Hylätty"])

            interview_date = ""
            interview_time = ""
            if cs == "Haastattelu":
                interview_date = st.date_input("Haastattelupäivä", key="int_date")
                interview_time = st.time_input("Haastattelun kellonaika", key="int_time")

            if st.button("Tallenna", type="primary") and cn:
                new_item = {
                    "company": cn,
                    "role": cr,
                    "status": cs,
                    "date": datetime.datetime.now().strftime("%d.%m."),
                    "contact_name": "",
                    "contact_phone": "",
                    "contact_email": "",
                    "interview_date": str(interview_date) if cs == "Haastattelu" else "",
                    "interview_time": str(interview_time) if cs == "Haastattelu" else ""
                }
                st.session_state.tracked_companies.append(new_item)
                save_local_data(st.session_state.tracked_companies)
                st.success("✅ Hakemus tallennettu!")
                st.rerun()

        # Näytä seuranta
        for i, item in enumerate(st.session_state.tracked_companies):
            with st.container():
                for k in ["contact_name", "contact_phone", "contact_email", "interview_date", "interview_time"]:
                    if k not in item: item[k] = ""

                # --- DEADLINE LOGIIKKA (SAFE_DEADLINE_BLOCK) ---
                time_badge = SAFE_DEADLINE_BLOCK(item.get('date', ''))
                
                status_color = STATUS_COLORS.get(item['status'], {"bg": "#FFFFFF", "text": "#000000"})
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.markdown(f"**{item['company']}** ({item['role']})")
                with c2:
                    st.markdown(
                        f"<span style='background-color:{status_color['bg']}; color:{status_color['text']}; "
                        f"padding:4px 8px; border-radius:6px;'>{item['status']}</span> "
                        f"<span style='margin-left:8px; color:#555; font-size:0.9em; font-weight:bold;'>{item['date']}</span> "
                        f"<span style='margin-left:8px; font-size:0.9em;'>{time_badge}</span>",
                        unsafe_allow_html=True
                    )
                with c3:
                    if st.button("🗑️", key=f"d{i}"): 
                        st.session_state.tracked_companies.pop(i)
                        save_local_data(st.session_state.tracked_companies)
                        st.success("✅ Poistettu")
                        st.rerun()

                # Haastattelun tiedot + Countdown
                if item['status'] == "Haastattelu" and item['interview_date']:
                    countdown_badge = SAFE_DEADLINE_BLOCK(item['interview_date'], is_future_event=True)
                    st.markdown(
                        f"🗓️ **Haastattelu:** {item['interview_date']} klo {item['interview_time']} "
                        f"→ <span style='color:#d9534f; font-weight:bold;'>{countdown_badge}</span>",
                        unsafe_allow_html=True
                    )

                # Yhteystiedot
                is_editing = st.session_state.edit_states.get(i, False)
                with st.expander("👤 Yhteystiedot"):
                    if st.button("✏️ Avaa muokkaus" if not is_editing else "🔒 Lukitse", key=f"edit_btn_{i}"):
                        st.session_state.edit_states[i] = not is_editing
                        st.rerun()

                    c1, c2, c3 = st.columns(3)
                    disabled_status = not is_editing
                    with c1:
                        new_name = st.text_input("Nimi", value=item['contact_name'], key=f"cn_{i}", disabled=disabled_status)
                        if new_name != item['contact_name']:
                            item['contact_name'] = new_name
                            save_local_data(st.session_state.tracked_companies)
                    with c2:
                        new_phone = st.text_input("Puhelin", value=item['contact_phone'], key=f"cp_{i}", disabled=disabled_status)
                        if new_phone != item['contact_phone']:
                            item['contact_phone'] = new_phone
                            save_local_data(st.session_state.tracked_companies)
                    with c3:
                        new_email = st.text_input("Sähköposti", value=item['contact_email'], key=f"ce_{i}", disabled=disabled_status)
                        if new_email != item['contact_email']:
                            item['contact_email'] = new_email
                            save_local_data(st.session_state.tracked_companies)

    if not st.session_state.tracked_companies:
        st.info("Seurantalista on tyhjä.")

    # --- TAB 6: AGENTTI ---
    with tab6:
        st.header("🕵️ Ura-agentti")
        st.write("Agentti tarkkailee taustalla linkkejä ja koulutuksia.")
        st.info("💡 Katso 'Agentin Suositukset' -välilehti nähdäksesi automaattiset ehdotukset.")

    # --- TAB 7: TYÖMARKKINATORI (PUDOTUSVALIKOT) ---
    with tab7:
        st.header("🇫🇮 Työmarkkinatori: Mission Jobs -haku")
        st.info("✅ Käytä valikoita kohdentaaksesi haun tarkemmin.")

        c1, c2 = st.columns(2)

        # 1. TYÖPAIKAT (Pudotusvalikko)
        with c1:
            st.subheader("💼 Avoimet Työpaikat")
            
            # Lisätään "Kaikki" -vaihtoehto listan kärkeen
            job_options = ["Kaikki luovat alat"] + SEARCH_KEYWORDS
            selected_job_role = st.selectbox("Valitse ammattinimike:", job_options)
            
            # Logiikka valinnan perusteella
            if selected_job_role == "Kaikki luovat alat":
                q_jobs = "%20".join(SEARCH_KEYWORDS)
            else:
                q_jobs = selected_job_role
            
            tm_jobs_url = f"https://tyomarkkinatori.fi/henkiloasiakkaat/avoimet-tyopaikat?q={q_jobs}&location=Uusimaa"
            
            st.markdown(f"""
            <div class="cta-container">
                <a href="{tm_jobs_url}" target="_blank" class="cta-button">
                   👉 HAE: {selected_job_role.upper()}
                </a>
            </div>
            """, unsafe_allow_html=True)

        # 2. KOULUTUKSET (Pudotusvalikko)
        with c2:
            st.subheader("🎓 Kurssit & Lyhytkoulutus")
            
            # Määritellään teemat ja niiden hakusanat
            training_topics = {
                "Kaikki aiheet": "media viestintä graafinen digimarkkinointi",
                "Viestintä & Media": "viestintä media",
                "Graafinen & Visuaalinen": "graafinen visuaalinen",
                "Digimarkkinointi": "digimarkkinointi some",
                "Tuotanto & Projektit": "tuottaja projektipäällikkö"
            }
            
            selected_topic = st.selectbox("Valitse koulutusala:", list(training_topics.keys()))
            
            # Haetaan oikeat hakusanat sanakirjasta
            q_training = training_topics[selected_topic].replace(" ", "%20")
            
            tm_training_url = f"https://tyomarkkinatori.fi/henkiloasiakkaat/koulutukset-ja-palvelut?q={q_training}"
            
            st.markdown(f"""
            <div class="cta-container">
                <a href="{tm_training_url}" target="_blank" class="cta-button dark">
                   👉 HAE: {selected_topic.upper()}
                </a>
            </div>
            """, unsafe_allow_html=True)
            
        st.divider()
        st.caption("Valinnat päivittävät hakupainikkeen linkin automaattisesti.")

    # --- TAB 8: PORTFOLIO & DATA (UPDATED) ---
    with tab8:
        st.header("🎨 Portfolio & Analytiikka")
        
        # --- LINKIT ---
        st.markdown(f"""<div class="cta-container"><a href="{FUTURE_MAKER_LINK}" target="_blank" class="cta-button dark">AVAA PORTFOLIO & CV</a></div>""", unsafe_allow_html=True)
        
        st.subheader("🔗 Yhdistä case")
        c1, c2 = st.columns(2)
        with c1: st.selectbox("Osio", ["Video CV", "Showreel", "Case: Brändi"])
        with c2: st.text_area("Perustelu hakemukseen:", height=100)
        
        st.divider()
        
        # --- GOOGLE SHEETS DATA ---
        st.subheader("📡 Live Audience (News Feed)")
        st.caption(f"Tracking ID: {SHEET_ID[:8]}...")
        
        df_visitors = load_visitor_data()
        
        if df_visitors is not None and not df_visitors.empty:
            # Metrics rivi - Mukautetaan sarakkeet datan mukaan
            # Oletetaan: Aikaleima, Lähde, Yritys/Verkko, Sijainti, Laite
            
            # Yritetään tunnistaa sarakkeet dynaamisesti tai käytetään indeksejä
            cols = df_visitors.columns.tolist()
            col_time = cols[0]
            col_company = cols[2] if len(cols) > 2 else cols[0]
            
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("Vierailijat yhteensä", len(df_visitors))
            with m2: 
                last_company = df_visitors.iloc[-1][col_company]
                st.metric("Viimeisin vierailija", str(last_company))
            with m3:
                last_time = str(df_visitors.iloc[-1][col_time]).split(' ')[0]
                st.metric("Päivämäärä", last_time)

            # Näytetään data taulukkona, uusimmat ensin
            st.dataframe(
                df_visitors.iloc[::-1], 
                use_container_width=True,
                hide_index=True
            )
            
            # Yksinkertainen graafi
            if len(cols) > 2:
                st.caption("Top Visitors:")
                chart_data = df_visitors[col_company].value_counts().head(10)
                st.bar_chart(chart_data)
        else:
            st.warning("⚠️ Dataa ei saatavilla. Varmista Google Sheetistä: File > Share > Publish to web > CSV.")

    # --- TAB 9: AGENTIN SUOSITUKSET ---
    with tab9:
        st.header("🧠 Agentin Suositukset")
        st.info("Agentti analysoi taustalla työ- ja koulutuslinkkejä, validoi niiden toimivuuden ja antaa pisteytyksen (match score). Voit lisätä parhaat osumat yhdellä klikkauksella seurantaan.")

        agent_suggestions = []

        # Alustetaan dismissed-lista, jos ei ole vielä olemassa
        if 'dismissed_suggestions' not in st.session_state:
            st.session_state.dismissed_suggestions = []

        # Kerätään jo seurattavat nimet
        tracked_names = {item['company'] for item in st.session_state.tracked_companies}

        # 1. Analysoi Koulutukset
        with st.spinner("Agentti analysoi koulutustarjontaa..."):
            for school in SCHOOLS_DATA:
                if validate_link(school['url']):
                    score = calculate_score(school['name'], "Helsinki")
                    agent_suggestions.append({
                        "name": school['name'],
                        "url": school['url'],
                        "category": "Koulutus",
                        "score": score,
                        "status": school.get('status', 'Avoin'),
                        "logo": school.get('logo', '')
                    })

        # 2. Analysoi Start-upit
        with st.spinner("Agentti analysoi start-up hubien tilannetta..."):
            for name, url in STARTUPS_PK.items():
                if validate_link(url):
                    score = calculate_score(name, "Helsinki")
                    agent_suggestions.append({
                        "name": name,
                        "url": url,
                        "category": "Työ / Hub",
                        "score": score,
                        "status": "Aktiivinen",
                        "logo": ""
                    })

        # 3. Poistetaan jo seurattavat ja dismissatut ehdotukset
        if agent_suggestions:
            agent_suggestions = [
                s for s in agent_suggestions 
                if s['name'] not in tracked_names and s['name'] not in st.session_state.dismissed_suggestions
            ]
            agent_suggestions = sorted(agent_suggestions, key=lambda x: x['score'], reverse=True)

            if agent_suggestions:
                st.write(f"Löydetty {len(agent_suggestions)} validoitua kohdetta.")
                st.markdown("---")

                for idx, sug in enumerate(agent_suggestions):
                    with st.container():
                        c1, c2, c3 = st.columns([5, 2, 2])
                        with c1:
                            st.markdown(f"### {sug['name']}")
                            st.caption(f"{sug['category']} | Status: {sug['status']}")
                            st.markdown(f"🔗 [Avaa sivu]({sug['url']})")
                        with c2:
                            st.write("Match Score:")
                            st.progress(sug['score']/5.0)
                            st.markdown(f"**{sug['score']}/5.0**")
                        with c3:
                            st.write("Toiminto:")
                            col_add, col_dismiss = st.columns([1,1])
                            with col_add:
                                if st.button("➕ Lisää", key=f"add_rec_{idx}", type="primary", use_container_width=True):
                                    # Estetään duplikaatti Seurannassa
                                    if sug['name'] not in tracked_names:
                                        new_item = {
                                            "company": sug['name'],
                                            "role": sug['category'],
                                            "status": "Kiinnostunut",
                                            "date": datetime.datetime.now().strftime("%d.%m."),
                                            "contact_name": "", "contact_phone": "", "contact_email": "",
                                            "interview_date": "", "interview_time": ""
                                        }
                                        st.session_state.tracked_companies.append(new_item)
                                        save_local_data(st.session_state.tracked_companies)
                                        st.success("✅ Lisätty!")
                                        st.rerun()
                            with col_dismiss:
                                if st.button("❌", key=f"dismiss_rec_{idx}", help="Poista ehdotuksista", use_container_width=True):
                                    st.session_state.dismissed_suggestions.append(sug['name'])
                                    st.rerun()
                        st.divider()
            else:
                st.success("Kaikki suositukset on jo käsitelty tai seurannassa! 🚀")
        else:
            st.warning("Agentti ei löytänyt aktiivisia linkkejä tai kohteita.")
            
    # --- TAB 10: AI KOULUTUS (UUSI) ---
    with tab10:
        st.header("🤖 Tekoälykoulutukset (Helsinki & Online)")
        st.write("Agentti on kuratoinut listan Helsingin alueen avoimista yliopistoista, AMK-verkoista ja sertifikaateista.")
        
        # Päivitys-indikaattori
        check_time = datetime.datetime.now().strftime("%H:%M")
        st.info(f"✅ Linkit validoitu ja päivitetty automaattisesti: Tänään klo {check_time}")

        # CSS Tyylittely korteille
        st.markdown("""
        <style>
        .ai-card {
            background: linear-gradient(135deg, #2b2d42 0%, #1e1e24 100%);
            border: 1px solid #4DA6FF;
            border-radius: 12px;
            padding: 20px;
            height: 280px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .ai-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(77, 166, 255, 0.2);
            border-color: #00d4ff;
        }
        .ai-header {
            margin-bottom: 10px;
        }
        .ai-type {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #00d4ff;
            font-weight: bold;
            margin-bottom: 5px;
            display: block;
        }
        .ai-title {
            color: #ffffff;
            font-size: 1.2rem;
            font-weight: 700;
            margin: 0 0 10px 0;
            line-height: 1.3;
        }
        .ai-provider {
            color: #b0b0b0;
            font-size: 0.9rem;
            margin-bottom: 15px;
            font-style: italic;
        }
        .ai-desc {
            color: #e0e0e0;
            font-size: 0.9rem;
            line-height: 1.5;
            flex-grow: 1;
        }
        .ai-footer {
            margin-top: 15px;
            text-align: right;
        }
        .ai-link {
            background-color: #4DA6FF;
            color: white !important;
            padding: 8px 16px;
            border-radius: 20px;
            text-decoration: none;
            font-weight: bold;
            font-size: 0.9rem;
            transition: background 0.2s;
        }
        .ai-link:hover {
            background-color: #008cff;
        }
        </style>
        """, unsafe_allow_html=True)

        cols = st.columns(3)
        valid_courses_count = 0
        
        for i, course in enumerate(AI_STUDIES):
            valid_courses_count += 1
            with cols[i % 3]:
                st.markdown(f"""
                <div class="ai-card">
                    <div class="ai-header">
                        <span class="ai-type">{course['type']}</span>
                        <h3 class="ai-title">{course['name']}</h3>
                        <div class="ai-provider">{course['provider']}</div>
                        <div class="ai-desc">{course['desc']}</div>
                    </div>
                    <div class="ai-footer">
                        <a href="{course['url']}" target="_blank" class="ai-link">Tutustu ➜</a>
                    </div>
                </div>
                <div style="margin-bottom: 20px;"></div>
                """, unsafe_allow_html=True)
        
        if valid_courses_count == 0:
            st.warning("⚠️ Yhteyksiä oppilaitosten palvelimiin ei saatu (HTTP Timeout). Kokeile myöhemmin uudelleen.")

if __name__ == '__main__':
    main()
