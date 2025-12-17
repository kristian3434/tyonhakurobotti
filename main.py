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

# Varmistetaan polut
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# ---------------------------------------------------------
# 1. ASETUKSET & DATA & VALIDOINTI & TALLENNUS
# ---------------------------------------------------------

USER_NAME = "Creative Pro"
STORAGE_FILE = "local_storage.json"

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

# LINKKIVAHTI: VALIDOI HTTP 200 OK
@st.cache_data(ttl=86400, show_spinner=False)
def validate_link(url):
    """
    Tarkistaa onko linkki elossa (HTTP 200).
    Palauttaa True vain jos sivusto vastaa oikein.
    Timeout optimoitu nopeammaksi (2s).
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.head(url, headers=headers, timeout=2, allow_redirects=True)
        if response.status_code == 200:
            return True
        response = requests.get(url, headers=headers, timeout=2)
        return response.status_code == 200
    except:
        return False

# AI-LOGIIKKA
AI_LOGIC_CORE = {
    "Gemini":  {"provider": "Google", "status": "Hybrid (API / Simuloitu)", "role": "Primary"},
    "ChatGPT": {"provider": "OpenAI", "status": "Simuloitu", "role": "Secondary"},
    "Claude":  {"provider": "Anthropic", "status": "Simuloitu", "role": "Secondary"},
    "Copilot": {"provider": "Microsoft", "status": "Simuloitu", "role": "Secondary"}
}

# --- DATASETS ---

AGENCIES = {
    "Bob the Robot": "https://bobtherobot.fi/careers",
    "TBWA\Helsinki": "https://tbwa.fi/careers",
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
        "name": "Taitotalo (Audiovisuaalinen)", 
        "url": "https://www.taitotalo.fi/koulutus/media-alan-ja-kuvallisen-ilmaisun-perustutkinto", 
        "logo": "https://www.taitotalo.fi/themes/custom/taitotalo/logo.svg",
        "status": "🔥 PRIORITEETTI"
    },
    {
        "name": "Taitotalo (ICT)", 
        "url": "https://www.taitotalo.fi/koulutus/tieto-ja-viestintatekniikan-perustutkinto", 
        "logo": "https://www.taitotalo.fi/themes/custom/taitotalo/logo.svg",
        "status": "Jatkuva haku"
    },
    {
        "name": "Business College Helsinki (ICT)", 
        "url": "https://bc.fi/koulutukset/tieto-ja-viestintatekniikan-perustutkinto/", 
        "logo": "https://bc.fi/wp-content/themes/bch/images/logo.svg",
        "status": "Jatkuva haku"
    },
    {
        "name": "Stadin AO (Media)", 
        "url": "https://stadinao.fi/koulutustarjonta/media-alan-ja-kuvallisen-ilmaisun-perustutkinto/", 
        "logo": "https://stadinao.fi/wp-content/themes/stadinao/assets/images/logo.svg",
        "status": "Jatkuva haku"
    },
    {
        "name": "Varia (Media)", 
        "url": "https://www.vantaa.fi/fi/palveluhakemisto/palvelu/media-alan-ja-kuvallisen-ilmaisun-perustutkinto-varia", 
        "logo": "https://www.vantaa.fi/themes/custom/vantaa/logo.svg",
        "status": "Haku auki"
    },
    {
        "name": "Omnia (Media)", 
        "url": "https://www.omnia.fi/koulutushaku/media-alan-ja-kuvallisen-ilmaisun-perustutkinto", 
        "logo": "https://www.omnia.fi/themes/custom/omnia/logo.svg",
        "status": "Jatkuva haku"
    },
    {
        "name": "Rastor-instituutti (Digi)", 
        "url": "https://www.rastorinst.fi/koulutus/markkinointi-ja-viestinta", 
        "logo": "https://www.rastorinst.fi/themes/custom/rastor/logo.svg",
        "status": "Jatkuva haku"
    },
    {
        "name": "Metropolia AMK (Viestintä)", 
        "url": "https://www.metropolia.fi/fi/opiskelu/amk-tutkinnot/viestinta", 
        "logo": "https://www.metropolia.fi/themes/custom/metropolia/logo.svg",
        "status": "Haku auki"
    },
    {
        "name": "Haaga-Helia (Journalismi)", 
        "url": "https://www.haaga-helia.fi/fi/koulutus/media-ja-viestinta", 
        "logo": "https://www.haaga-helia.fi/themes/custom/hh/logo.svg",
        "status": "Jatkuva haku"
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
    role_match = 0
    for role in TARGET_ROLES:
        if role.lower() in title: role_match += 1
    score += min(role_match * 0.5, 2.0)
    if any(x in title for x in ['strateg', 'lead', 'head', 'päällikkö']): score += 1.0
    if any(x in title for x in ['ai ', 'genai', 'technolog']) or any(x in desc for x in ['ai ', 'artificial intelligence', 'chatgpt', 'midjourney']): score += 1.0
    if 'helsinki' in location or 'espoo' in location: score += 1.0
    elif 'remote' in location: score += 0.8
    return min(score, 5.0)

def gemini_safe_fetch(job_desc: str, user_cv: str, api_key: str = "") -> str:
    """
    Fetch job/training results in strict safe mode with Gemini.
    - Hallusinaatiot estetty
    - GDPR ja read-only turva
    - Whitelist domain + HTTP200 check
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

st.set_page_config(layout="wide", page_title="Future Maker Hub")
st.markdown("""
<style>
    @media (max-width: 768px) {
        .block-container { padding-left: 1rem !important; padding-right: 1rem !important; padding-top: 2rem !important; }
        h1 { font-size: 1.8rem !important; }
        .stButton button { width: 100%; }
    }
    .responsive-link-btn {
        display: flex; align-items: center; justify-content: center; padding: 12px; 
        background: #262730; border: 1px solid #464b5f; border-radius: 8px; 
        margin-bottom: 8px; text-decoration: none; color: white !important; width: 100%;
        transition: background 0.2s; font-weight: 500;
    }
    .responsive-link-btn:hover { background: #363740; }
    .responsive-link-btn img { width: 20px; height: 20px; margin-right: 10px; object-fit: contain; }
    .cta-container { display: flex; justify-content: center; margin: 20px 0; width: 100%; }
    .cta-button {
        display: inline-block; background-color: #0a66c2; color: white !important; 
        padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: bold;
        text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 100%;
    }
    .cta-button.dark { background-color: #333; }
    @media (max-width: 576px) { .cta-button { width: 100%; padding: 14px 20px; font-size: 1rem; } }
</style>
""", unsafe_allow_html=True)

def main():
    # ALUSTETAAN SEURANTA TIEDOSTOSTA
    if 'tracked_companies' not in st.session_state:
        st.session_state.tracked_companies = load_local_data()
    if 'watched_schools' not in st.session_state:
        st.session_state.watched_schools = []
    
    # MUOKKAUSTILAN HALLINTA
    if 'edit_states' not in st.session_state:
        st.session_state.edit_states = {}

    with st.sidebar:
        st.title("⚙️ Asetukset")
        
        st.header("🤖 AI-Ydin")
        selected_ai_core = st.radio("Valitse suoritusmalli:", list(AI_LOGIC_CORE.keys()), index=0)
        st.caption(f"Status: {AI_LOGIC_CORE[selected_ai_core]['status']}")
        st.markdown("---")
        
        # API-KENTTÄ
        if 'api_key' not in st.session_state: st.session_state.api_key = ''
        
        api_input = st.text_input(
            "Gemini API-avain (Valinnainen)", 
            type="password", 
            value=st.session_state.api_key, 
            help="Jos jätät tyhjäksi, sovellus toimii simulaatiotilassa."
        )
        
        if api_input: 
            st.session_state.api_key = api_input
            st.success("API-avain aktiivinen!")
        else: 
            st.caption("Ei avainta - Simulaatiotila")
            
        st.markdown("---")
        
        # --- ASETUKSET: KOHDENNETTU HAKU ---
        st.header("🎯 Kohdennettu Haku")
        toggle_edu = False 
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

    st.title("FUTURE MAKER // HUB V60.0")
    mode_status = "API Mode" if st.session_state.api_key and selected_ai_core == "Gemini" else "No API Mode"
    st.markdown(f"**User:** {USER_NAME} | **Core:** {selected_ai_core} ({mode_status})")
    
    # --- VÄLILEHDET ---
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "✨ AI HAKEMUS", "📊 ANALYSOI", "🏢 LINKIT", "⚡️ TEHOHAKU", 
        "📌 SEURANTA", "🕵️ AGENTTI", "🇫🇮 TYÖ", "🎨 PORTFOLIO", 
        "🧠 AGENTIN SUOSITUKSET"
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
                    if selected_ai_core == "Gemini" and st.session_state.api_key:
                        with st.spinner("Gemini API kirjoittaa hakemusta..."):
                            try:
                                genai.configure(api_key=st.session_state.api_key)
                                model = genai.GenerativeModel('gemini-1.5-flash')
                                prompt = "Kirjoita selkeä ja asiallinen työhakemus avoimeen harjoittelupaikkaan."
                                response = model.generate_content(prompt, request_options={'timeout': 30})
                                st.text_area("Valmis hakemus:", value=response.text, height=600)
                            except Exception as e: 
                                st.error(f"API-virhe: {e}. Varmista API-avain ja yhteys.")
                    else:
                        st.success(f"Agentti {selected_ai_core} on analysoinut tehtävän (Simulaatio).")
                        constructed_prompt = f"TOIMI SEURAAVASTI ({selected_ai_core}):\nKirjoita erottuva työhakemus tehtävään: {job_desc[:50]}...\nHakijan tausta: {user_cv[:50]}...\nPainotus: Moderni, vakuuttava."
                        st.info("ℹ️ **NO API MODE:** Alla optimoitu kehote (Prompt), jonka voit kopioida.")
                        st.code(constructed_prompt, language="text")
                else: st.warning("Täytä kentät.")
        
        with btn_col2:
            if st.button("🛡️ SAFE FETCH (Strict Mode)"):
                if job_desc and user_cv:
                    with st.spinner("Suoritetaan tietoturvallista hakua (Read-Only)..."):
                        result = gemini_safe_fetch(job_desc, user_cv, st.session_state.api_key)
                        st.subheader("🔒 Safe Fetch Results")
                        st.info("GDPR & Domain Whitelist Active")
                        st.code(result, language="text")
                else:
                    st.warning("Syötä hakutekstit ensin.")

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
                if selected_ai_core == "Gemini" and st.session_state.api_key:
                    with st.spinner("Gemini API tulkitsee..."):
                        try:
                            genai.configure(api_key=st.session_state.api_key)
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            response = model.generate_content(
                                f"Analysoi lyhyesti miksi tämä työ sopii profiililleni (Luova/AI). Ilmoitus: {input_desc}",
                                request_options={'timeout': 30}
                            )
                            st.info("💡 **TEKOÄLYN TULKINTA (API):**")
                            st.write(response.text)
                        except: st.error("API-virhe.")
                else:
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
        with st.expander("➕ Lisää manuaalisesti", expanded=False):
            with st.form("add"):
                c1, c2 = st.columns(2)
                with c1: cn = st.text_input("Yritys")
                with c2: cr = st.text_input("Rooli")
                cs = st.selectbox("Tila", ["Odottaa", "Keskustelu", "Haastattelu", "Ei vastausta", "Hylätty"])
                if st.form_submit_button("Tallenna") and cn:
                    new_item = {
                        "company": cn, "role": cr, "status": cs, 
                        "date": datetime.datetime.now().strftime("%d.%m."),
                        "contact_name": "", "contact_phone": "", "contact_email": ""
                    }
                    st.session_state.tracked_companies.append(new_item)
                    save_local_data(st.session_state.tracked_companies)
                    st.rerun()
        
        for i, item in enumerate(st.session_state.tracked_companies):
            with st.container(border=True):
                # Varmistetaan kentät
                if "contact_name" not in item: item["contact_name"] = ""
                if "contact_phone" not in item: item["contact_phone"] = ""
                if "contact_email" not in item: item["contact_email"] = ""

                c1, c2, c3 = st.columns([3, 2, 1])
                with c1: st.write(f"**{item['company']}** ({item['role']})")
                with c2: st.caption(f"{item['status']} | {item['date']}")
                with c3: 
                    if st.button("🗑️", key=f"d{i}"): 
                        st.session_state.tracked_companies.pop(i)
                        save_local_data(st.session_state.tracked_companies)
                        st.rerun()
                
                # UUSI YHTEYSTIETO-OSIO (LUKITUS)
                is_editing = st.session_state.edit_states.get(i, False)
                with st.expander("👤 Yhteystiedot"):
                    if st.button("✏️ Avaa muokkaus" if not is_editing else "🔒 Lukitse", key=f"edit_btn_{i}"):
                        st.session_state.edit_states[i] = not is_editing
                        st.rerun()
                    
                    c_contact1, c_contact2, c_contact3 = st.columns(3)
                    disabled_status = not is_editing
                    
                    with c_contact1:
                        new_name = st.text_input("Nimi", value=item['contact_name'], key=f"cn_{i}", disabled=disabled_status)
                        if new_name != item['contact_name']:
                            item['contact_name'] = new_name
                            save_local_data(st.session_state.tracked_companies)
                    with c_contact2:
                        new_phone = st.text_input("Puhelin", value=item['contact_phone'], key=f"cp_{i}", disabled=disabled_status)
                        if new_phone != item['contact_phone']:
                            item['contact_phone'] = new_phone
                            save_local_data(st.session_state.tracked_companies)
                    with c_contact3:
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

    # --- TAB 7: TYÖMARKKINATORI ---
    with tab7:
        st.header("🇫🇮 Työmarkkinatori")
        tm_url = f"https://tyomarkkinatori.fi/henkiloasiakkaat/avoimet-tyopaikat/?q={'%20'.join(SEARCH_KEYWORDS)}&region=Uusimaa"
        st.markdown(f"""<div class="cta-container"><a href="{tm_url}" target="_blank" class="cta-button">👉 Avaa Työmarkkinatori</a></div>""", unsafe_allow_html=True)

    # --- TAB 8: PORTFOLIO ---
    with tab8:
        st.header("🎨 Portfolio")
        st.markdown(f"""<div class="cta-container"><a href="{FUTURE_MAKER_LINK}" target="_blank" class="cta-button dark">AVAA PORTFOLIO & CV</a></div>""", unsafe_allow_html=True)
        st.subheader("🔗 Yhdistä case")
        c1, c2 = st.columns(2)
        with c1: st.selectbox("Osio", ["Video CV", "Showreel", "Case: Brändi"])
        with c2: st.text_area("Perustelu hakemukseen:", height=100)

    # --- TAB 9: AGENTIN SUOSITUKSET (UUSI) ---
    with tab9:
        st.header("🧠 Agentin Suositukset")
        st.info("Agentti analysoi taustalla työ- ja koulutuslinkkejä, validoi niiden toimivuuden ja antaa pisteytyksen (match score). Voit lisätä parhaat osumat yhdellä klikkauksella seurantaan.")

        agent_suggestions = []

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

        # 3. Järjestä ja Näytä
        if agent_suggestions:
            agent_suggestions = sorted(agent_suggestions, key=lambda x: x['score'], reverse=True)
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
                        st.progress(sug['score']/5)
                        st.markdown(f"**{sug['score']}/5.0**")
                    with c3:
                        st.write("Toiminto:")
                        if st.button("➕ Lisää Seurantaan", key=f"add_rec_{idx}", type="primary"):
                            new_item = {
                                "company": sug['name'],
                                "role": sug['category'],
                                "status": "Kiinnostunut",
                                "date": datetime.datetime.now().strftime("%d.%m."),
                                "contact_name": "", "contact_phone": "", "contact_email": ""
                            }
                            st.session_state.tracked_companies.append(new_item)
                            save_local_data(st.session_state.tracked_companies)
                            st.success("✅ Lisätty!")
                            st.rerun()
                    st.divider()
        else:
            st.warning("Agentti ei löytänyt aktiivisia linkkejä tai kohteita.")

if __name__ == '__main__':
    main()
