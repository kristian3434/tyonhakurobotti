import sys
import os
import urllib.parse
import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import requests
import random
import json
import subprocess
import re
from collections import Counter

# Huom: Poistettu aktiivinen riippuvuus google.generativeai -kirjastosta,
# mutta import jätetty varalle, jos ympäristössä on riippuvuuksia.
try:
    import google.generativeai as genai
except ImportError:
    pass

# ---------------------------------------------------------
# AUTOMAATTINEN PÄIVITYSLOGIIKKA
# ---------------------------------------------------------
LOG_FILE = "/tmp/tyonhaku_update_success"

def run_update():
    try:
        subprocess.run(["streamlit", "run", os.path.abspath(__file__), "--server.port", "0"], check=True)
        with open(LOG_FILE, "w") as f:
            f.write("OK")
    except Exception as e:
        print(f"Päivitys epäonnistui: {e}")

now = datetime.datetime.now()
weekday = now.weekday()
hour = now.hour

if 0 <= weekday <= 4 and hour == 8:
    run_update()
elif 0 <= weekday <= 4 and hour == 11:
    if not os.path.exists(LOG_FILE):
        run_update()

# ---------------------------------------------------------
# 0. KONFIGURAATIO
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Mission Jobs Hub", page_icon="🚀")

if os.path.exists(LOG_FILE):
    last_update = datetime.datetime.fromtimestamp(os.path.getmtime(LOG_FILE))
    if datetime.datetime.now() - last_update > datetime.timedelta(hours=24):
        st.warning("⚠️ Päivitystä ei ole tehty viimeisen 24 tunnin aikana")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# ---------------------------------------------------------
# 1. ASETUKSET & DATA
# ---------------------------------------------------------

USER_NAME = "Mission Jobs Commander"
STORAGE_FILE = "local_storage.json"
SHEET_ID = "12_hQ54nccgljOCbDGPOvFzYBQ6KhQkdk1GDdpaNTGyM"

def load_local_data():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_local_data(data):
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Virhe tallennuksessa: {e}")

@st.cache_data(ttl=60)
def load_visitor_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Datan haku epäonnistui: {e}")
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def validate_link(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.head(url, headers=headers, timeout=2, allow_redirects=True)
        if response.status_code == 200: return True
        response = requests.get(url, headers=headers, timeout=2)
        return response.status_code == 200
    except:
        return False

# --- UUSI FUNKTIO: AIKAEROT ---
def calculate_days_diff(date_str, is_future=False):
    """Laskee päivien erotuksen nykyhetkeen."""
    if not date_str: return 0
    now = datetime.datetime.now()
    try:
        # Jos kyseessä on haastattelu (YYYY-MM-DD)
        if "-" in str(date_str):
            dt = datetime.datetime.strptime(str(date_str), "%Y-%m-%d")
            diff = (dt - now).days + 1 # +1 jotta huominen on 1
            return diff
        
        # Jos kyseessä on hakemus (dd.mm.)
        full_date = f"{date_str}{now.year}"
        dt = datetime.datetime.strptime(full_date, "%d.%m.%Y")
        return (now - dt).days
    except:
        return 0

# --- HYBRID INTELLIGENCE ENGINE (LOCAL ONLY MODE) ---

AI_LOGIC_CORE = {
    "Local Core":  {"provider": "Internal", "status": "Active", "role": "Primary"},
}

def local_text_analysis(text):
    """Analysoi tekstin sisäisellä logiikalla."""
    text = text.lower()
    keywords = {
        "Luova": ["photoshop", "illustrator", "indesign", "figma", "video", "editointi", "visuaalinen", "brändi", "sommittelu", "creative", "art director"],
        "Tekninen/AI": ["ai ", "tekoäly", "chatgpt", "midjourney", "python", "html", "css", "wordpress", "promp", "genai"],
        "Soft Skills": ["tiimityö", "oma-aloitteisuus", "paineensieto", "kommunikointi", "projektinhallinta", "analyyttinen", "koordinoi"]
    }
    
    found_stats = {}
    missing_words = []
    total_score = 0
    
    for category, words in keywords.items():
        count = 0
        for word in words:
            if word in text:
                count += 1
                total_score += 1
            else:
                if random.random() > 0.85: missing_words.append(word)
        found_stats[category] = count

    final_score = min(total_score, 10)
    return found_stats, final_score, missing_words

def generate_template_application(company, role, job_text, user_background):
    """Luo älykkään hakemuspohjan."""
    date_str = datetime.datetime.now().strftime("%d.%m.%Y")
    highlights = []
    if "ai" in job_text.lower(): highlights.append("tekoälyosaamiseni")
    if "visuaalinen" in job_text.lower(): highlights.append("visuaalisen silmäni")
    if "projekti" in job_text.lower(): highlights.append("kokemukseni projektinhallinnasta")
    
    highlight_text = " sekä ".join(highlights) if highlights else "monipuolisen osaamiseni"

    template = f"""
    {USER_NAME}
    Helsinki | {date_str}

    Vastaanottaja: Rekrytointitiimi / {company}

    HAKEMUS: {role.upper()}

    Hei,

    Luin innostuneena ilmoituksenne, jossa haette {role}-osaajaa. Seuraan aktiivisesti {company}:n toimintaa ja uskon, että taustani toisi tiimiinne juuri oikeanlaista lisäarvoa.

    MIKSI MINÄ?
    Olen luovan alan ammattilainen, joka yhdistää visuaalisen suunnittelun ja modernit teknologiat. Ilmoituksessanne korostui tarve ratkaisukeskeiselle tekijälle.
    
    Omaan vahvan taustan, johon kuuluu:
    - {user_background[:150]}... (Täydennä CV:stäsi)
    - Kyky hyödyntää tekoälyä luovassa prosessissa
    - Halu oppia uutta ja kehittää prosesseja

    MITÄ TUON TALOON?
    Uskon, että voisin hyödyntää {highlight_text} heti ensimmäisestä päivästä alkaen. Olen tottunut työskentelemään itsenäisesti, mutta nautin tiimityöstä, jossa sparraillaan ideoita.

    Odotan innolla mahdollisuutta kertoa lisää osaamisestani haastattelussa.

    Ystävällisin terveisin,

    {USER_NAME}
    Portfolio: {FUTURE_MAKER_LINK}
    """
    return template

def calculate_score(title, location, description=""):
    score = 1.0
    title = title.lower(); location = location.lower(); desc = description.lower()
    
    role_match = 0
    for role in TARGET_ROLES:
        if role.lower() in title: role_match += 1
    score += min(role_match * 0.5, 2.0)
    
    if any(x in title for x in ['strateg', 'lead', 'head', 'päällikkö']): score += 1.0
    
    all_keywords = ['ai ', 'genai', 'technolog', 'chatgpt', 'midjourney'] + UNI_KEYWORDS + AMK_KEYWORDS
    if any(kw.lower() in title for kw in all_keywords) or any(kw.lower() in desc for kw in all_keywords):
        score += 1.0

    if 'helsinki' in location or 'espoo' in location: score += 1.0
    elif 'remote' in location: score += 0.8
    
    return min(score, 5.0)

def safe_deadline_block(date_input, is_future_event=False):
    try:
        if not date_input: return ""
        now = datetime.datetime.now()
        if is_future_event and "-" in str(date_input):
            dt = datetime.datetime.strptime(str(date_input), "%Y-%m-%d")
            diff = (dt - now).days + 1
            if diff < 0: return "🔴 Meni jo"
            if diff == 0: return "🔥 TÄNÄÄN"
            if diff <= 2: return f"🔥 {diff} pv"
            return f"📅 {diff} pv"
        full_date = f"{date_input}{now.year}"
        dt = datetime.datetime.strptime(full_date, "%d.%m.%Y")
        diff = (now - dt).days
        if diff > 21: return f"⚠️ {diff} pv (Hiljaista)"
        if diff > 14: return f"🕒 {diff} pv"
        return f"🆕 {diff} pv"
    except: return ""

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
        "name": "3AMK (AI & Future)",
        "provider": "Metropolia, Haaga-Helia, Laurea",
        "url": "https://www.3amk.fi/",
        "desc": "Pääkaupunkiseudun korkeakoulujen yhteiset tulevaisuuskurssit.",
        "type": "AMK (HKI)"
    },
    {
        "name": "DeepLearning.AI: AI for Everyone",
        "provider": "DeepLearning.AI",
        "url": "https://www.deeplearning.ai/courses/ai-for-everyone/",
        "desc": "Andrew Ng:n kurssi bisnespuolelle ja tuottajille. Ei vaadi koodausta.",
        "type": "KV / ETÄ"
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
    "Avidly": "https://www.avidlyagency.com/fi/ura-avidlylla",
    "Bob the Robot": "https://www.bobtherobot.fi/",
    "Futurice": "https://www.futurice.com/careers",
    "hasan & partners": "https://www.hasanpartners.fi/contact",
    "Kuulu": "https://www.kuulu.fi/",
    "Miltton": "https://miltton.com/career",
    "N2 Creative": "https://n2.fi/",
    "Reaktor": "https://www.reaktor.com/careers",
    "SEK": "https://sek.io/en/careers/",
    "Siili Solutions": "https://www.siili.com/join-us",
    "TBWA\Helsinki": "https://www.tbwa.fi/",
    "Valve": "https://www.valve.fi/join-us",
    "Vincit": "https://www.vincit.com/careers",
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
    "Aalto Startup Center": "https://startupcenter.aalto.fi/",
    "Kiuas Accelerator": "https://www.kiuas.com/",
    "Maria 01 (Careers)": "https://maria.io/careers/",
    "Supercell Careers": "https://supercell.com/en/careers/",
    "The Hub (Helsinki Jobs)": "https://thehub.io/jobs?location=Helsinki",
    "Wolt Careers": "https://careers.wolt.com/en"
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
    "ICT"
]

FUTURE_MAKER_LINK = "https://janmyllymaki.wixsite.com/future-maker/fi"

SITES_INTL = {
    "Behance Jobs": "https://www.behance.net/joblist",
    "Design Jobs Board": "https://www.designjobsboard.com/",
    "Krop": "https://www.krop.com/"
}

SITES_FI_NORDIC = {
    "Journalistiliitto (Etusivu)": "https://journalistiliitto.fi/",
    "Kuntarekry (Kulttuuri)": "https://www.kuntarekry.fi/fi/tyopaikat/kulttuuri-ja-museoala/",
    "Medialiitto (Työpaikat)": "https://www.medialiitto.fi/medialiitto/tyopaikat/",
    "TAKU ry": "https://taku.fi/avainsana/tyopaikat/"
}

SITES_MEDIA = {
    "Media Match": "https://www.media-match.com/",
    "ProductionHUB": "https://www.productionhub.com/jobs"
}

# ---------------------------------------------------------
# UI & LOGIIKKA
# ---------------------------------------------------------

st.markdown("""
<style>
    .stApp { overflow-x: hidden; }
    @media (max-width: 768px) {
        .block-container { padding: 1rem; }
        .stButton button { width: 100%; }
        .ai-card, .rec-card { min-height: auto; }
    }
    .responsive-link-btn {
        display: flex; align-items: center; justify-content: center; padding: 12px; 
        background: #262730; border: 1px solid #464b5f; border-radius: 8px; 
        margin-bottom: 8px; text-decoration: none; color: white !important; width: 100%;
        transition: background 0.2s; font-weight: 500;
        box-sizing: border-box;
    }
    .responsive-link-btn:hover { background: #363740; }
    .responsive-link-btn img { width: 20px; height: 20px; margin-right: 10px; object-fit: contain; }
    
    .cta-container { display: flex; justify-content: center; margin: 20px 0; }
    .cta-button {
        background-color: #0a66c2; color: white !important; padding: 16px 32px; 
        border-radius: 8px; font-weight: bold; text-decoration: none; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-block;
    }
    .cta-button.dark { background-color: #333; }
</style>
""", unsafe_allow_html=True)

def main():
    if 'tracked_companies' not in st.session_state: st.session_state.tracked_companies = load_local_data()
    if 'edit_states' not in st.session_state: st.session_state.edit_states = {}
    if 'dismissed_suggestions' not in st.session_state: st.session_state.dismissed_suggestions = []
    
    # Pakotetaan API tyhjäksi, varmuuden vuoksi
    st.session_state.api_key = ""

    with st.sidebar:
        st.title("⚙️ Asetukset")
        st.header("🧠 Äly")
        
        # Vain Local Mode käytössä
        selected_ai_core = st.radio("Malli:", ["Local Core"], index=0)
        
        st.info("ℹ️ Local Mode: Sovellus toimii itsenäisesti sisäisellä logiikalla. Ulkoinen tekoäly on poistettu käytöstä.")

        st.markdown("---")
        toggle_startup = st.toggle("🚀 Start-upit", value=False)
        if toggle_startup:
            st.markdown("### Hubit")
            for name, url in STARTUPS_PK.items():
                if validate_link(url): st.markdown(f"- [{name}]({url})")

    st.title("MISSION JOBS // HUB V68.3 (Local)")
    status_text = "🟢 ONLINE (LOCAL)"
    st.markdown(f"**Tila:** {status_text} | **Käyttäjä:** {USER_NAME} | **Core:** {selected_ai_core}")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "✨ HAKEMUS", "📊 ANALYSOI", "🏢 LINKIT", "⚡️ TEHOHAKU", 
        "📌 SEURANTA", "🕵️ AGENTTI", "🇫🇮 TYÖ", "🎨 PORTFOLIO", 
        "🧠 SUOSITUKSET", "🤖 AI KOULUTUS"
    ])

    # --- TAB 1: HAKEMUS ---
    with tab1:
        st.header("📝 Hakemusgeneraattori")
        c1, c2 = st.columns(2)
        with c1: 
            company_name = st.text_input("Yrityksen nimi (Generointia varten):")
            role_name = st.text_input("Haettava rooli:")
            job_desc = st.text_area("Liitä työpaikkailmoitus tähän:", height=250)
        with c2: 
            user_cv = st.text_area("Oma tausta / CV tiivistelmä:", height=380)
        
        if st.button("🚀 LUO HAKEMUS", type="primary"):
            if job_desc and user_cv:
                # LOCAL LOGIC ONLY
                with st.spinner("Luodaan älykästä hakemuspohjaa..."):
                    draft = generate_template_application(company_name if company_name else "[YRITYS]", role_name if role_name else "[ROOLI]", job_desc, user_cv)
                    st.subheader("📄 Hakemuspohja:")
                    st.info("💡 Tässä on valmis pohja, johon on upotettu avainsanat ja rakenne. Viimeistele tiedot itse.")
                    st.text_area("", value=draft, height=600)
            else:
                st.warning("Täytä ainakin ilmoitus ja oma tausta.")

    # --- TAB 2: ANALYSOI ---
    with tab2:
        st.header("📊 Analysoi Ilmoitus")
        col1, col2 = st.columns(2)
        with col1: input_title = st.text_input("Työnimike")
        with col2: input_loc = st.text_input("Sijainti")
        input_desc_analysis = st.text_area("Liitä ilmoitusteksti tähän analyysiä varten:", height=200)
        
        if st.button("🔍 ANALYSOI TEKSTI"):
            # Pisteytys (Aina toiminnassa)
            score = calculate_score(input_title, input_loc, input_desc_analysis)
            st.subheader(f"Match Score: {score}/5.0")
            st.progress(min(score/5, 1.0))

            if input_desc_analysis:
                # LOCAL ANALYSIS
                stats, keyword_score, missing = local_text_analysis(input_desc_analysis)
                c1, c2 = st.columns(2)
                with c1:
                    st.write("✅ **Löydetyt avainsanat:**")
                    st.json(stats)
                with c2:
                    if missing:
                        st.write("⚠️ **Harkitse näiden mainitsemista:**")
                        for m in missing[:5]: st.markdown(f"- {m.capitalize()}")
                    st.info("💡 Tämä on automaattinen avainsana-analyysi.")

    # --- TAB 3: LINKIT (FULL LIST RESTORED) ---
    with tab3:
        st.header("🏢 Linkkikirjasto")
        with st.expander("Mainostoimistot", expanded=True):
            cols = st.columns(3)
            for i, (name, url) in enumerate(AGENCIES.items()):
                logo = f"https://www.google.com/s2/favicons?domain={url.split('/')[2]}&sz=64"
                with cols[i % 3]: 
                    st.markdown(f"""<a href="{url}" target="_blank" class="responsive-link-btn"><img src="{logo}">{name}</a>""", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.subheader("🌍 Intl")
            for n,u in SITES_INTL.items(): st.markdown(f"[{n}]({u})")
        with c2: 
            st.subheader("🇫🇮 Suomi")
            for n,u in SITES_FI_NORDIC.items(): st.markdown(f"[{n}]({u})")
        with c3: 
            st.subheader("🎬 Media")
            for n,u in SITES_MEDIA.items(): st.markdown(f"[{n}]({u})")

    # --- TAB 4: TEHOHAKU ---
    with tab4:
        st.header("⚡️ Tehohaku")
        def generate_linkedin_url_full():
            q = " OR ".join([f'"{r}"' for r in SEARCH_KEYWORDS])
            params = {"keywords": f"({q})", "location": "Helsinki Metropolitan Area", "f_TPR": "r2592000", "sort": "dd"}
            return "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(params)
        
        st.markdown(f"""<div class="cta-container"><a href="{generate_linkedin_url_full()}" target="_blank" class="cta-button">👉 LINKEDIN (HELSINKI + CREATIVE)</a></div>""", unsafe_allow_html=True)

    # --- TAB 5: SEURANTA (FULL FEATURES) ---
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
                    "company": cn, "role": cr, "status": cs,
                    "date": datetime.datetime.now().strftime("%d.%m."),
                    "contact_name": "", "contact_phone": "", "contact_email": "",
                    "interview_date": str(interview_date) if cs == "Haastattelu" else "",
                    "interview_time": str(interview_time) if cs == "Haastattelu" else ""
                }
                st.session_state.tracked_companies.append(new_item)
                save_local_data(st.session_state.tracked_companies)
                st.success("✅ Hakemus tallennettu!")
                st.rerun()

        for i, item in enumerate(st.session_state.tracked_companies):
            with st.container():
                for k in ["contact_name", "contact_phone", "contact_email", "interview_date", "interview_time"]:
                    if k not in item: item[k] = ""

                time_badge = safe_deadline_block(item.get('date', ''))
                status_color = STATUS_COLORS.get(item['status'], {"bg": "#FFFFFF", "text": "#000000"})
                
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1: st.markdown(f"**{item['company']}** ({item['role']})")
                with c2: st.markdown(f"<span style='background-color:{status_color['bg']}; color:{status_color['text']}; padding:4px 8px; border-radius:6px;'>{item['status']}</span> <span style='margin-left:8px; font-size:0.9em;'>{time_badge}</span>", unsafe_allow_html=True)
                with c3:
                    if st.button("🗑️", key=f"d{i}"): 
                        st.session_state.tracked_companies.pop(i)
                        save_local_data(st.session_state.tracked_companies)
                        st.rerun()

                if item['status'] == "Haastattelu" and item['interview_date']:
                    countdown_badge = safe_deadline_block(item['interview_date'], is_future_event=True)
                    st.markdown(f"🗓️ **Haastattelu:** {item['interview_date']} klo {item['interview_time']} → <span style='color:#d9534f; font-weight:bold;'>{countdown_badge}</span>", unsafe_allow_html=True)

                is_editing = st.session_state.edit_states.get(i, False)
                with st.expander("👤 Yhteystiedot"):
                    if st.button("✏️ Avaa muokkaus" if not is_editing else "🔒 Lukitse", key=f"edit_btn_{i}"):
                        st.session_state.edit_states[i] = not is_editing
                        st.rerun()
                    
                    c1, c2, c3 = st.columns(3)
                    disabled_status = not is_editing
                    with c1:
                        new_name = st.text_input("Nimi", value=item['contact_name'], key=f"cn_{i}", disabled=disabled_status)
                        if new_name != item['contact_name']: item['contact_name'] = new_name; save_local_data(st.session_state.tracked_companies)
                    with c2:
                        new_phone = st.text_input("Puhelin", value=item['contact_phone'], key=f"cp_{i}", disabled=disabled_status)
                        if new_phone != item['contact_phone']: item['contact_phone'] = new_phone; save_local_data(st.session_state.tracked_companies)
                    with c3:
                        new_email = st.text_input("Sähköposti", value=item['contact_email'], key=f"ce_{i}", disabled=disabled_status)
                        if new_email != item['contact_email']: item['contact_email'] = new_email; save_local_data(st.session_state.tracked_companies)

    if not st.session_state.tracked_companies:
        st.info("Seurantalista on tyhjä.")

    # --- TAB 6: AGENTTI (SMART QUOTA - LOCAL ONLY) ---
    with tab6:
        st.header("🕵️ Ura-agentti")
        st.info("Agentti valvoo työnhakuvelvoitetta ja aikatauluja.")
        
        # --- VELVOITELASKURI ---
        MONTHLY_QUOTA = 4
        current_month = datetime.datetime.now().month
        apps_this_month = 0
        
        for item in st.session_state.tracked_companies:
            if item['status'] == "Kiinnostunut": continue 
            
            try:
                date_parts = item.get('date', '').split('.')
                if len(date_parts) >= 2:
                    month_num = int(date_parts[1])
                    if month_num == current_month:
                        apps_this_month += 1
            except:
                pass 

        quota_progress = min(apps_this_month / MONTHLY_QUOTA, 1.0)
        remaining_quota = MONTHLY_QUOTA - apps_this_month

        st.subheader("📉 Työnhakuvelvoite (Tämä kuu)")
        if remaining_quota > 0:
            st.warning(f"⚠️ Olet lähettänyt **{apps_this_month} / {MONTHLY_QUOTA}** hakemusta. Vielä {remaining_quota} puuttuu!")
            st.progress(quota_progress, text=f"Valmiina: {int(quota_progress*100)}%")
        else:
            st.balloons()
            st.success(f"✅ **MAHTAVAA!** Olet täyttänyt kuukauden kiintiön ({apps_this_month} / {MONTHLY_QUOTA}).")
            st.progress(1.0, text="Velvoite täytetty 100%")

        st.divider()
        st.subheader("🔔 Ilmoitukset")

        agent_actions_found = False
        
        # LOOPATAAN LÄPI SEURATTAVAT YRITYKSET
        if st.session_state.tracked_companies:
            for i, item in enumerate(st.session_state.tracked_companies):
                
                # --- LOGIIKKA A: FOLLOW-UP (14 PÄIVÄÄ) ---
                days_since_applied = calculate_days_diff(item.get('date', ''))
                
                if item['status'] == "Odottaa" and days_since_applied >= 14:
                    agent_actions_found = True
                    with st.container():
                        st.warning(f"⏳ **{item['company']}**: Hakemuksesta on kulunut {days_since_applied} päivää. Hiljaista?")
                        
                        col_a, col_b = st.columns([1, 4])
                        with col_a:
                            if st.button("📧 Kirjoita viesti", key=f"agent_email_{i}"):
                                st.session_state[f"show_email_{i}"] = True
                        
                        with col_b:
                            if st.session_state.get(f"show_email_{i}", False):
                                st.markdown("### 📝 Luonnos:")
                                
                                # LOCAL FALLBACK ONLY
                                contact = item.get('contact_name', 'Rekrytointitiimi')
                                draft_email = f"""
Hei {contact},

Toivottavasti viikkone on sujunut hyvin!

Laitoin teille hakemuksen {item['role']} -tehtävään {item['date']} ({days_since_applied} päivää sitten). 
Olen edelleen erittäin kiinnostunut mahdollisuudesta liittyä {item['company']}:n tiimiin ja halusin tiedustella, missä vaiheessa rekrytointiprosessi etenee?

Vastaan mielelläni mahdollisiin lisäkysymyksiin.

Ystävällisin terveisin,
{USER_NAME}
"""
                                st.text_area("Kopioi tästä:", value=draft_email, height=200)
                                if st.button("Sulje", key=f"close_email_{i}"):
                                    st.session_state[f"show_email_{i}"] = False
                                    st.rerun()

                # --- LOGIIKKA B: HAASTATTELU PREP (0-2 PÄIVÄÄ) ---
                if item['status'] == "Haastattelu" and item.get('interview_date'):
                    days_until = calculate_days_diff(item['interview_date'], is_future=True)
                    
                    if 0 <= days_until <= 2:
                        agent_actions_found = True
                        with st.container():
                            st.error(f"🔥 **{item['company']}**: Haastattelu {days_until} pv päästä! Valmistaudutaanko?")
                            
                            col_c, col_d = st.columns([1, 4])
                            with col_c:
                                if st.button("🧠 Luo muistilista", key=f"agent_prep_{i}"):
                                    st.session_state[f"show_prep_{i}"] = True
                            
                            with col_d:
                                if st.session_state.get(f"show_prep_{i}", False):
                                    st.markdown("### 📋 Prep-lista:")
                                    prep_text = f"""
1. **Tutustu yrityksen viimeisimpiin uutisiin** (LinkedIn, Verkkosivut).
2. **Kertaa hakemuksesi:** Mitä lupasit osaavasi?
3. **Valmistele kysymyksiä heille:** Esim. "Miltä tyypillinen työpäivä näyttää?"
4. **Pitch:** Harjoittele 2 minuutin hissipuhe itsestäsi.
                                    """
                                    st.markdown(prep_text)
                                    if st.button("Sulje", key=f"close_prep_{i}"):
                                        st.session_state[f"show_prep_{i}"] = False
                                        st.rerun()

        if not agent_actions_found:
            st.success("✅ Kaikki ajan tasalla. Ei akuutteja toimenpiteitä.")

    # --- TAB 7: TYÖMARKKINATORI ---
    with tab7:
        st.header("🇫🇮 Työmarkkinatori: Mission Jobs -haku")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("💼 Työpaikat")
            job_options = ["Kaikki luovat alat"] + SEARCH_KEYWORDS
            selected_job_role = st.selectbox("Valitse ammattinimike:", job_options)
            q_jobs = "%20".join(SEARCH_KEYWORDS) if selected_job_role == "Kaikki luovat alat" else selected_job_role
            tm_jobs_url = f"https://tyomarkkinatori.fi/henkiloasiakkaat/avoimet-tyopaikat?q={q_jobs}&location=Uusimaa"
            st.markdown(f"""<div class="cta-container"><a href="{tm_jobs_url}" target="_blank" class="cta-button">👉 HAE: {selected_job_role.upper()}</a></div>""", unsafe_allow_html=True)

        with c2:
            st.subheader("🎓 Koulutus")
            training_topics = {
                "Kaikki aiheet": "media viestintä", 
                "Viestintä": "viestintä", 
                "Graafinen": "graafinen",
                "Osatutkinnot": "osatutkinto",
                "Tutkinnon osat": "tutkinnon osa",
                "Osatutkintokoulutus": "osatutkintokoulutus"
            }
            selected_topic = st.selectbox("Valitse ala:", list(training_topics.keys()))
            q_training = training_topics[selected_topic]
            tm_train_url = f"https://tyomarkkinatori.fi/henkiloasiakkaat/koulutukset-ja-palvelut?q={q_training}"
            st.markdown(f"""<div class="cta-container"><a href="{tm_train_url}" target="_blank" class="cta-button dark">👉 HAE: {selected_topic.upper()}</a></div>""", unsafe_allow_html=True)

    # --- TAB 8: PORTFOLIO ---
    with tab8:
        st.header("🎨 Portfolio & Data")
        st.markdown(f"""<div class="cta-container"><a href="{FUTURE_MAKER_LINK}" target="_blank" class="cta-button dark">🚀 AVAA PORTFOLIO & CV</a></div>""", unsafe_allow_html=True)
        st.markdown("---")
        df_visitors = load_visitor_data()
        if df_visitors is not None and not df_visitors.empty:
            cols = df_visitors.columns.tolist()
            col_time, col_company = cols[0], cols[2] if len(cols) > 2 else cols[0]
            st.markdown("""<style>.metric-card { background: linear-gradient(135deg, #2b2d42 0%, #1e1e24 100%); border: 1px solid #464b5f; border-radius: 10px; padding: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); } .metric-value { font-size: 1.8rem; font-weight: bold; color: #4DA6FF; margin: 0; } .metric-label { font-size: 0.9rem; color: #b0b0b0; text-transform: uppercase; letter-spacing: 1px; }</style>""", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            with m1: st.markdown(f"""<div class="metric-card"><div class="metric-value">{len(df_visitors)}</div><div class="metric-label">Vierailijat</div></div>""", unsafe_allow_html=True)
            with m2: st.markdown(f"""<div class="metric-card"><div class="metric-value">{df_visitors.iloc[-1][col_company]}</div><div class="metric-label">Viimeisin</div></div>""", unsafe_allow_html=True)
            with m3: st.markdown(f"""<div class="metric-card"><div class="metric-value">{str(df_visitors.iloc[-1][col_time]).split(' ')[0]}</div><div class="metric-label">Päivämäärä</div></div>""", unsafe_allow_html=True)
            st.write("")
            c1, c2 = st.columns([2, 1])
            with c1: 
                st.subheader("📊 Top Vierailijat")
                if len(cols) > 2:
                    st.bar_chart(df_visitors[col_company].value_counts().head(7), color="#4DA6FF")
            with c2: st.subheader("📋 Lokitiedot"); st.dataframe(df_visitors.iloc[::-1], use_container_width=True, height=300)
        else: st.warning("⚠️ Dataa ei saatavilla...")

    # --- TAB 9: SUOSITUKSET ---
    with tab9:
        st.header("🧠 Suositukset")
        st.markdown("""<style>.rec-card { background-color: #262730; border: 1px solid #464b5f; border-radius: 10px; padding: 15px; margin-bottom: 10px; transition: box-shadow 0.3s; } .rec-card:hover { box-shadow: 0 4px 15px rgba(0,0,0,0.3); border-color: #777; } .rec-title { font-size: 1.1rem; font-weight: bold; color: white; margin-bottom: 5px; } .rec-cat { font-size: 0.8rem; text-transform: uppercase; color: #aaa; letter-spacing: 1px; } .rec-badge { background-color: #0a66c2; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }</style>""", unsafe_allow_html=True)
        with st.spinner("Analysoidaan kohteita..."):
            agent_suggestions = []
            tracked_names = {item['company'] for item in st.session_state.tracked_companies}
            for school in SCHOOLS_DATA:
                if validate_link(school['url']):
                    score = calculate_score(school['name'], "Helsinki")
                    agent_suggestions.append({"name": school['name'], "url": school['url'], "cat": "🎓 Koulutus", "score": score})
            for name, url in STARTUPS_PK.items():
                if validate_link(url):
                    score = calculate_score(name, "Helsinki")
                    agent_suggestions.append({"name": name, "url": url, "cat": "💼 Työ / Hub", "score": score})
            agent_suggestions = [s for s in agent_suggestions if s['name'] not in tracked_names and s['name'] not in st.session_state.dismissed_suggestions]
            agent_suggestions.sort(key=lambda x: x['score'], reverse=True)

            if agent_suggestions:
                for idx, sug in enumerate(agent_suggestions):
                    with st.container():
                        c1, c2 = st.columns([4, 1])
                        with c1: st.markdown(f"""<div class="rec-card"><div class="rec-cat">{sug['cat']}</div><div class="rec-title">{sug['name']} <span class="rec-badge">{sug['score']}/5</span></div><a href="{sug['url']}" target="_blank" style="color:#4da6ff; text-decoration:none;">🔗 Avaa sivu</a></div>""", unsafe_allow_html=True)
                        with c2:
                            st.write("")
                            if st.button("➕ Lisää", key=f"add_{idx}", use_container_width=True):
                                st.session_state.tracked_companies.append({"company": sug['name'], "role": sug['cat'], "status": "Kiinnostunut", "date": datetime.datetime.now().strftime("%d.%m."), "contact_name": "", "contact_phone": "", "contact_email": "", "interview_date": "", "interview_time": ""})
                                save_local_data(st.session_state.tracked_companies)
                                st.rerun()
                            if st.button("❌ Piilota", key=f"dis_{idx}", use_container_width=True):
                                st.session_state.dismissed_suggestions.append(sug['name'])
                                st.rerun()
            else: st.success("Kaikki suositukset on jo käsitelty! 🚀")

    # --- TAB 10: AI KOULUTUS ---
    with tab10:
        st.header("🤖 Tekoälykoulutukset")
        st.markdown("""<style>.ai-card { background: linear-gradient(135deg, #2b2d42 0%, #1e1e24 100%); border: 1px solid #4DA6FF; border-radius: 12px; padding: 20px; min-height: 300px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 4px 6px rgba(0,0,0,0.3); } .ai-type { color: #00d4ff !important; font-size: 0.75em; font-weight: bold; text-transform: uppercase; } .ai-title { color: white !important; font-size: 1.2rem; font-weight: bold; margin: 5px 0; } .ai-provider { color: #b0b0b0 !important; font-size: 0.9rem; font-style: italic; margin-bottom: 10px; } .ai-desc { color: #e0e0e0 !important; font-size: 0.9rem; flex-grow: 1; } .ai-link { background: #4DA6FF; color: white !important; padding: 8px 16px; border-radius: 20px; text-decoration: none; font-weight: bold; display: inline-block; white-space: nowrap; font-size: 0.9rem; } .ai-link:hover { background: #008cff; } </style>""", unsafe_allow_html=True)
        cols = st.columns(3)
        for i, course in enumerate(AI_STUDIES):
            with cols[i % 3]:
                st.markdown(f"""<div class="ai-card"><div><div class="ai-type">{course['type']}</div><div class="ai-title">{course['name']}</div><div class="ai-provider">{course['provider']}</div><div class="ai-desc">{course['desc']}</div></div><div style="text-align:right; margin-top:20px;"><a href="{course['url']}" target="_blank" class="ai-link">Tutustu ➜</a></div></div><div style="margin-bottom:20px;"></div>""", unsafe_allow_html=True)

if __name__ == '__main__':
    main()
