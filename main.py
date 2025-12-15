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

# Varmistetaan polut
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# ---------------------------------------------------------
# 1. ASETUKSET & DATA & VALIDOINTI
# ---------------------------------------------------------
USER_NAME = "Creative Pro"

# LINKKIVAHTI: VALIDOI HTTP 200 OK
@st.cache_data(ttl=3600, show_spinner=False)
def validate_link(url):
    """
    Tarkistaa onko linkki elossa (HTTP 200).
    Palauttaa True vain jos sivusto vastaa oikein.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        if response.status_code == 200:
            return True
        response = requests.get(url, headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False

# AI-LOGIIKKA
AI_LOGIC_CORE = {
    "Gemini":  {"provider": "Google", "status": "Simuloitu", "role": "Primary"},
    "ChatGPT": {"provider": "OpenAI", "status": "Simuloitu", "role": "Secondary"},
    "Claude":  {"provider": "Anthropic", "status": "Simuloitu", "role": "Secondary"},
    "Copilot": {"provider": "Microsoft", "status": "Simuloitu", "role": "Secondary"}
}

# MAINOSTOIMISTOT
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

# PÄIVITETTY KOULUTUSDATA (PK-SEUTU: MEDIA, DIGI, VIESTINTÄ)
# Vain validoidut linkit.
SCHOOLS_DATA = [
    # AMMATILLINEN & AIKUISKOULUTUS
    {"name": "Stadin AO (Media-alan pt)", "url": "https://stadinao.fi/koulutustarjonta/media-alan-ja-kuvallisen-ilmaisun-perustutkinto/", "status": "Jatkuva haku"},
    {"name": "Varia (Media-ala)", "url": "https://www.sivistysvantaa.fi/varia/fi/hakijalle/koulutustarjonta/media-alan-ja-kuvallisen-ilmaisun-perustutkinto", "status": "Haku auki"},
    {"name": "Omnia (Media-alan pt)", "url": "https://www.omnia.fi/koulutushaku/media-alan-ja-kuvallisen-ilmaisun-perustutkinto", "status": "Jatkuva haku"},
    {"name": "Taitotalo (Audiovisuaalinen)", "url": "https://www.taitotalo.fi/koulutus/media-ala", "status": "Jatkuva haku"},
    {"name": "Rastor-instituutti (Digimarkkinointi)", "url": "https://www.rastorinst.fi/koulutus/markkinointi-ja-viestinta", "status": "Jatkuva haku"},
    
    # KORKEAKOULUT (MEDIA & VIESTINTÄ)
    {"name": "Metropolia AMK (Viestintä)", "url": "https://www.metropolia.fi/fi/opiskelu/amk-tutkinnot/viestinta", "status": "Haku auki"},
    {"name": "Metropolia AMK (Muotoilu/Digi)", "url": "https://www.metropolia.fi/fi/opiskelu/amk-tutkinnot/muotoilu", "status": "Haku auki"},
    {"name": "Haaga-Helia (Journalismi)", "url": "https://www.haaga-helia.fi/fi/koulutus/media-ja-viestinta", "status": "Jatkuva haku"},
    {"name": "Arcada (Media - SWE/EN)", "url": "https://www.arcada.fi/fi/studier/bachelor/media-kultur", "status": "Tulossa"},
    {"name": "Aalto ARTS (Visuaalinen viestintä)", "url": "https://www.aalto.fi/fi/taiteiden-ja-suunnittelun-korkeakoulu", "status": "Haku päättynyt"},
    {"name": "Aalto EE (Design & Creativity)", "url": "https://www.aaltoee.fi/", "status": "Täydennys"}
]

# START-UPIT (PK-SEUTU - AKTIIVISET)
STARTUPS_PK = {
    "Maria 01 (Careers)": "https://maria.io/careers/",
    "The Hub (Helsinki Jobs)": "https://thehub.io/jobs?location=Helsinki",
    "Aalto Startup Center": "https://startupcenter.aalto.fi/",
    "Kiuas Accelerator": "https://www.kiuas.com/",
    "Wolt Careers": "https://careers.wolt.com/en",
    "Supercell Careers": "https://supercell.com/en/careers/"
}

# TARGET_ROLES
TARGET_ROLES = [
    "Graafinen suunnittelija", "Sisällöntuottaja", "Visuaalinen suunnittelija",
    "Projektipäällikkö (luovat sisällöt)", "Viestintäsuunnittelija", "Markkinointisuunnittelija",
    "UI/UX-suunnittelija", "Creative Producer", "Content Manager", "Art Director Assistant",
    "Junior Designer", "Video Editor"
]

# HAKUSANAT
SEARCH_KEYWORDS = [
    "graafinen suunnittelija", "sisällöntuottaja", "visuaalinen suunnittelija",
    "projektipäällikkö", "viestintäsuunnittelija", "markkinointisuunnittelija",
    "UI designer", "UX designer", "creative producer", "content manager", 
    "mainonta", "luova ala", "graafinen suunnittelu", "digitaalinen viestintä"
]

# LINKIT
FUTURE_MAKER_LINK = "https://janmyllymaki.wixsite.com/future-maker/fi"
SITES_INTL = {
    "Krop": "https://www.krop.com/", "Design Jobs Board": "https://www.designjobsboard.com/",
    "If You Could Jobs": "https://ifyoucouldjobs.com/", "Authentic Jobs": "https://authenticjobs.com/",
    "Awwwards Jobs": "https://www.awwwards.com/jobs/", "Coroflot Jobs": "https://www.coroflot.com/design-jobs",
    "ArtStation Jobs": "https://www.artstation.com/jobs", "No Fluff Jobs": "https://nofluffjobs.com/fi/design",
    "Remotive": "https://remotive.com/remote-jobs/design", "Remote OK": "https://remoteok.com/remote-design-jobs",
    "We Work Remotely": "https://weworkremotely.com/", "FlexJobs": "https://www.flexjobs.com/jobs/design",
    "Talenthouse Jobs": "https://www.talenthouse.com/jobs", "Domestika Jobs": "https://www.domestika.org/en/jobs",
    "Smashing Magazine": "https://www.smashingmagazine.com/jobs/", "UX Jobs Board": "https://www.uxjobsboard.com/"
}
SITES_FI_NORDIC = {
    "Journalistiliiton työpaikat": "https://journalistiliitto.fi/fi/tyoelama/avoimet-tyopaikat/",
    "Medialiiton työpaikat": "https://www.medialiitto.fi/tyopaikat",
    "Kulttuurijobs": "https://kulttuurijobs.fi/",
    "Film & TV Finland": "https://www.filmikamari.fi/",
    "Nordic Film Commissions": "https://nordicfilmcommissions.com/",
    "Scandinavian Design Jobs": "https://scandinaviandesign.com/jobs/"
}
SITES_MEDIA = {
    "Stage 32 Jobs": "https://www.stage32.com/find-jobs", "Media Match": "https://www.media-match.com/",
    "ProductionHUB": "https://www.productionhub.com/jobs", "Staff Me Up": "https://staffmeup.com/jobs",
    "ScreenSkills": "https://www.screenskills.com/opportunities/jobs/"
}

# ---------------------------------------------------------
# 2. LOGIIKKA
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
    # ALUSTETAAN SEURANTA TYHJÄKSI JOS EI OLE
    if 'tracked_companies' not in st.session_state:
        st.session_state.tracked_companies = []

    if 'watched_schools' not in st.session_state:
        st.session_state.watched_schools = []

    # API-AVAIN PAKOTETTU TYHJÄKSI (NO API MODE)
    st.session_state.api_key = ''

    with st.sidebar:
        st.title("⚙️ Asetukset")
        
        st.header("🤖 AI-Ydin")
        selected_ai_core = st.radio("Valitse suoritusmalli:", list(AI_LOGIC_CORE.keys()), index=0)
        st.caption(f"Status: {AI_LOGIC_CORE[selected_ai_core]['status']}")
        st.markdown("---")
        
        # API-KENTTÄ POISTETTU KOKONAAN UI:STA
        
        # --- ASETUKSET: KOHDENNETTU HAKU ---
        st.header("🎯 Kohdennettu Haku")
        toggle_edu = st.toggle("🎓 Koulutukset", value=False)
        toggle_startup = st.toggle("🚀 Start-upit", value=False)
        st.markdown("---")
        
        # --- SIVUPALKIN TULOKSET (VALIDOIDUT) ---
        
        # 1. KOULUTUSHAKU (JOS ON)
        if toggle_edu:
            st.markdown("### 🎓 Koulutustarjonta")
            st.caption("✅ Validoidut | PK-seutu | Media/Digi")
            
            valid_count = 0
            for idx, school in enumerate(SCHOOLS_DATA):
                # GLOBAALI LINKKIEN VALIDOINTI
                if validate_link(school['url']):
                    valid_count += 1
                    domain = school['url'].split("/")[2]
                    logo = f"https://www.google.com/s2/favicons?domain={domain}&sz=32"
                    is_watched = school['name'] in st.session_state.watched_schools
                    
                    with st.container():
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.markdown(f"""
                            <div style="display:flex; align-items:center; margin-bottom:5px; background:#262730; padding:6px; border-radius:5px;">
                                <img src="{logo}" style="margin-right:10px; width:20px; height:20px;">
                                <div>
                                    <a href="{school['url']}" target="_blank" style="color:white; text-decoration:none; font-size:0.9em; font-weight:bold;">{school['name']}</a>
                                    <div style="color:#aaa; font-size:0.7em;">{school['status']}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        with c2:
                            # Koulutusvahti (Vain ihminen aktivoi)
                            watch_label = "✅" if is_watched else "👁️"
                            if st.button(watch_label, key=f"w_{idx}", help="Lisää seurantaan"):
                                if is_watched: st.session_state.watched_schools.remove(school['name'])
                                else: st.session_state.watched_schools.append(school['name'])
                                st.rerun()
            
            if valid_count == 0:
                st.warning("Ei aktiivisia koulutuslinkkejä.")

            if st.session_state.watched_schools:
                st.info(f"🕵️ **Koulutusvahti:** {len(st.session_state.watched_schools)} kohdetta seurannassa.")

        # 2. START-UP HAKU (JOS ON)
        if toggle_startup:
            st.markdown("### 🚀 Start-up Hubit")
            st.caption("✅ Aktiiviset sivut (HTTP 200)")
            for name, url in STARTUPS_PK.items():
                # Näytetään vain jos sivu on pystyssä (aktiivinen haku)
                if validate_link(url): 
                    st.markdown(f"- [{name}]({url})")

        st.caption(f"Roolihaku: {len(SEARCH_KEYWORDS)} avainsanaa")

    st.title("FUTURE MAKER // HUB V43.0")
    # TILA ON AINA NO API MODE
    mode_status = "No API Mode"
    st.markdown(f"**User:** {USER_NAME} | **Core:** {selected_ai_core} ({mode_status})")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["✨ AI HAKEMUS", "📊 ANALYSOI", "🏢 LINKIT", "⚡️ TEHOHAKU", "📌 SEURANTA", "🕵️ AGENTTI", "🇫🇮 TYÖ", "🎨 PORTFOLIO"])
    
    # --- TAB 1: AI HAKEMUS ---
    with tab1:
        st.header(f"Kirjoita Hakemus ({selected_ai_core})")
        c1, c2 = st.columns(2)
        with c1: job_desc = st.text_area("1. Työpaikkailmoitus:", height=300)
        with c2: user_cv = st.text_area("2. Oma CV / Tausta:", height=300)
        
        if st.button("🚀 SUORITA (Aktiivinen malli)", type="primary"):
            if job_desc and user_cv:
                # API-avain on aina tyhjä -> Menee suoraan simulaatioon
                if selected_ai_core == "Gemini" and st.session_state.api_key:
                    # TÄNNE EI PÄÄSTÄ KOSKA API_KEY ON PAKOTETTU TYHJÄKSI
                    pass 
                else:
                    st.success(f"Agentti {selected_ai_core} on analysoinut tehtävän (Simulaatio).")
                    constructed_prompt = f"TOIMI SEURAAVASTI ({selected_ai_core}):\nKirjoita erottuva työhakemus tehtävään: {job_desc[:50]}...\nHakijan tausta: {user_cv[:50]}...\nPainotus: Moderni, vakuuttava."
                    st.info("ℹ️ **NO API MODE:** Alla optimoitu kehote (Prompt), jonka voit kopioida.")
                    st.code(constructed_prompt, language="text")
            else: st.warning("Täytä kentät.")

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
                # API-avain on aina tyhjä -> Menee suoraan simulaatioon
                if selected_ai_core == "Gemini" and st.session_state.api_key:
                     pass
                else:
                    st.info(f"💡 **Agentin ({selected_ai_core}) looginen päätelmä (Simulaatio):**")
                    if score >= 4.0: st.write("✅ **Vahva osuma!**")
                    elif score >= 2.5: st.write("⚠️ **Kohtalainen osuma.**")
                    else: st.write("🛑 **Heikko osuma.**")
                    st.caption("Huom: Analyysi tehty paikallisesti ilman API-yhteyttä.")

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
        # EI AUTOMAATTISIA LISÄYKSIÄ - KÄYTTÄJÄ HALLITSEE
        with st.expander("➕ Lisää manuaalisesti", expanded=False):
            with st.form("add"):
                c1, c2 = st.columns(2)
                with c1: cn = st.text_input("Yritys")
                with c2: cr = st.text_input("Rooli")
                cs = st.selectbox("Tila", ["Odottaa", "Keskustelu", "Haastattelu", "Ei vastausta", "Hylätty"])
                if st.form_submit_button("Tallenna") and cn:
                    st.session_state.tracked_companies.append({"company": cn, "role": cr, "status": cs, "date": datetime.datetime.now().strftime("%d.%m.")})
                    st.rerun()
        
        for i, item in enumerate(st.session_state.tracked_companies):
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1: st.write(f"**{item['company']}** ({item['role']})")
                with c2: st.caption(f"{item['status']} | {item['date']}")
                with c3: 
                    if st.button("🗑️", key=f"d{i}"): 
                        st.session_state.tracked_companies.pop(i); st.rerun()
        
        if not st.session_state.tracked_companies:
            st.info("Seurantalista on tyhjä. Lisää kohteita sivupalkin koulutusvahdista tai manuaalisesti.")

    # --- TAB 6: AGENTTI ---
    with tab6:
        st.header("🕵️ Ura-agentti")
        st.write("Agentti tarkkailee taustalla linkkejä ja koulutuksia.")
        st.info("💡 **Vinkki:** Voit lisätä koulutuksia tai työpaikkoja seurantaan 'Seuranta'-välilehdeltä tai sivupalkin silmä-ikonista.")

    # --- TAB 7: TYÖMARKKINATORI ---
    with tab7:
        st.header("🇫🇮 Työmarkkinatori")
        tm_url = f"https://tyomarkkinatori.fi/henkiloasiakkaat/avoimet-tyopaikat/?q={'%20'.join(SEARCH_KEYWORDS)}&region=Uusimaa"
        st.markdown(f"""<div class="cta-container"><a href="{tm_url}" target="_blank" class="cta-button">👉 Avaa Työmarkkinatori</a></div>""", unsafe_allow_html=True)

    # --- TAB 8: PORTFOLIO ---
    with tab8:
        st.header("🎨 Portfolio")
        st.markdown(f"""<div class="cta-container"><a href="{FUTURE_MAKER_LINK}" target="_blank" class="cta-button dark">↗️ AVAA PORTFOLIO & CV</a></div>""", unsafe_allow_html=True)
        st.subheader("🔗 Yhdistä case")
        c1, c2 = st.columns(2)
        with c1: st.selectbox("Osio", ["Video CV", "Showreel", "Case: Brändi"])
        with c2: st.text_area("Perustelu hakemukseen:", height=100)

if __name__ == '__main__':
    main()
