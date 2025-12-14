
import sys
import os
import urllib.parse
import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import random

# Varmistetaan polut
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# ---------------------------------------------------------
# 1. ASETUKSET & DATA
# ---------------------------------------------------------
USER_NAME = "Creative Pro"

# ===============================================
# AI-KÄYTTÖPERIAATE & PAKOTUS (LOGIC LAYER)
# ===============================================
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

# TARGET_ROLES
TARGET_ROLES = [
    "Graafinen suunnittelija",        # Graphic Designer
    "Sisällöntuottaja",               # Content Creator
    "Visuaalinen suunnittelija",      # Visual Designer
    "Projektipäällikkö (luovat sisällöt)", # Project Manager (Creative Content)
    "Viestintäsuunnittelija",         # Communications Planner
    "Markkinointisuunnittelija",      # Marketing Planner
    "UI/UX-suunnittelija",            # UI/UX Designer
    "Creative Producer",
    "Content Manager",
    "Art Director Assistant"
]

# Hakusanat
SEARCH_KEYWORDS = [
    "graafinen suunnittelija",
    "sisällöntuottaja",
    "visuaalinen suunnittelija",
    "projektipäällikkö",
    "viestintäsuunnittelija",
    "markkinointisuunnittelija",
    "UI designer",
    "UX designer",
    "creative producer",
    "content manager",
    "art director assistant"
]

# Linkit
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
    title = title.lower()
    location = location.lower()
    desc = description.lower()
    
    role_match = 0
    for role in TARGET_ROLES:
        if role.lower() in title:
            role_match += 1
    score += min(role_match * 0.5, 2.0)
    
    if any(x in title for x in ['strateg', 'lead', 'head', 'päällikkö']): score += 1.0
    
    if any(x in title for x in ['ai ', 'genai', 'technolog']) or any(x in desc for x in ['ai ', 'artificial intelligence', 'chatgpt', 'midjourney']):
        score += 1.0
        
    if 'helsinki' in location or 'espoo' in location: score += 1.0
    elif 'remote' in location: score += 0.8
    
    return min(score, 5.0)

# ---------------------------------------------------------
# 3. KÄYTTÖLIITTYMÄ
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Future Maker Hub")

# CSS INJEKTIO RESPONSIIVISUUDELLE
st.markdown("""
<style>
    /* Responsiivinen kontainerin padding */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 2rem !important;
        }
        h1 {
            font-size: 1.8rem !important;
        }
        .stButton button {
            width: 100%;
        }
    }

    /* Linkkipainikkeiden tyyli */
    .responsive-link-btn {
        display: flex; 
        align-items: center; 
        justify-content: center;
        padding: 12px; 
        background: #262730; 
        border: 1px solid #464b5f;
        border-radius: 8px; 
        margin-bottom: 8px; 
        text-decoration: none; 
        color: white !important; 
        width: 100%;
        box-sizing: border-box;
        transition: background 0.2s, transform 0.1s;
        font-weight: 500;
    }
    .responsive-link-btn:hover {
        background: #363740;
        border-color: #6c7080;
    }
    .responsive-link-btn:active {
        transform: scale(0.98);
    }
    .responsive-link-btn img {
        width: 20px; 
        height: 20px;
        margin-right: 10px;
        object-fit: contain;
    }

    /* CTA-painikkeet (Tehohaku, Portfolio) */
    .cta-container {
        display: flex;
        justify-content: center;
        margin-top: 20px;
        margin-bottom: 20px;
        width: 100%;
    }
    .cta-button {
        display: inline-block;
        background-color: #0a66c2; 
        color: white !important; 
        padding: 16px 32px; 
        text-decoration: none; 
        border-radius: 8px; 
        font-weight: bold;
        font-size: 1.1em;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.1s;
        max-width: 100%;
    }
    .cta-button.dark {
        background-color: #333;
    }
    .cta-button:active {
        transform: scale(0.98);
    }
    
    /* Mobiilisovitus CTA-napille */
    @media (max-width: 576px) {
        .cta-button {
            width: 100%;
            padding: 14px 20px;
            font-size: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

def main():
    # --- SIVUPALKKI ---
    with st.sidebar:
        st.title("⚙️ Asetukset")
        
        # --- AI-YDIN ---
        st.header("🤖 AI-Ydin")
        selected_ai_core = st.radio(
            "Valitse suoritusmalli:",
            list(AI_LOGIC_CORE.keys()),
            index=0,
            help="Vain valittu malli on aktiivinen. Toimii loogisena agenttina."
        )
        st.caption(f"Versio: {AI_LOGIC_CORE[selected_ai_core]['provider']} (Simuloitu)")
        st.markdown("---")

        if 'api_key' not in st.session_state: st.session_state.api_key = ''
        api_input = st.text_input("API-avain (Ei aktiivinen)", type="password", value=st.session_state.api_key, disabled=True, help="NO API MODE aktivoitu.")
        st.markdown("---")
        st.caption(f"Roolihaku: {len(SEARCH_KEYWORDS)} avainsanaa")

    # --- OTSIKKO ---
    st.title("FUTURE MAKER // HUB V33.0")
    st.markdown(f"**User:** {USER_NAME} | **Active Core:** {selected_ai_core} (No API Mode)")
    
    # --- VÄLILEHDET ---
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "✨ AI HAKEMUS", 
        "📊 ANALYSOI", 
        "🏢 LINKIT", 
        "⚡️ TEHOHAKU", 
        "📌 SEURANTA", 
        "🕵️ AGENTTI",
        "🇫🇮 TYÖ",
        "🎨 PORTFOLIO"
    ])
    
    # ---------------------------------------------------------
    # TAB 1: AI HAKEMUS
    # ---------------------------------------------------------
    with tab1:
        st.header(f"Kirjoita Hakemus ({selected_ai_core})")
        c1, c2 = st.columns(2)
        with c1: job_desc = st.text_area("1. Työpaikkailmoitus:", height=300, key="app_job")
        with c2: user_cv = st.text_area("2. Oma CV / Tausta:", height=300, key="app_cv")
        
        if st.button("🚀 SUORITA (Aktiivinen malli)", type="primary"):
            if job_desc and user_cv:
                st.success(f"Agentti {selected_ai_core} on analysoinut tehtävän.")
                
                constructed_prompt = f"""
                TOIMI SEURAAVASTI ({selected_ai_core}):
                Kirjoita erottuva työhakemus tehtävään: {job_desc[:50]}...
                Hakijan tausta: {user_cv[:50]}...
                Painotus: Moderni, vakuuttava, AI-osaaminen.
                """
                
                st.info(f"ℹ️ **NO API MODE:** Sovellus ei ota yhteyttä ulkoiseen palvelimeen.")
                st.markdown("**Agentti on valmistellut optimoidun kehotteen (Prompt), jota voit käyttää:**")
                st.code(constructed_prompt, language="text")
                st.markdown("*Kopioi yllä oleva teksti ja syötä se haluamaasi AI-palveluun.*")
            else: 
                st.warning("Täytä kentät analyysia varten.")

    # ---------------------------------------------------------
    # TAB 2: ANALYSOI LÖYDÖS
    # ---------------------------------------------------------
    with tab2:
        st.header(f"Analysoi Löydös ({selected_ai_core})")
        col_input1, col_input2 = st.columns(2)
        with col_input1: input_title = st.text_input("Työnimike", placeholder="esim. Creative Strategist")
        with col_input2: input_loc = st.text_input("Sijainti", placeholder="esim. Helsinki")
        input_desc = st.text_area("Liitä ilmoitusteksti tähän (Analyysia varten):", height=150)
        
        if st.button("🔍 ANALYSOI (Aktiivinen malli)"):
            score = calculate_score(input_title, input_loc, input_desc)
            st.markdown("---")
            st.subheader(f"Match Score: {score}/5.0")
            st.progress(score/5)
            
            if input_desc:
                st.info(f"💡 **Agentin ({selected_ai_core}) looginen päätelmä:**")
                if score >= 4.0:
                    st.write("✅ **Vahva osuma!** Tämä rooli vastaa erinomaisesti määriteltyjä tavoitteita ja avainsanoja.")
                elif score >= 2.5:
                    st.write("⚠️ **Kohtalainen osuma.** Rooli sisältää oikeita elementtejä, mutta vaatii tarkempaa tarkastelua.")
                else:
                    st.write("🛑 **Heikko osuma.** Rooli ei näytä vastaavan ydinosaamisalueita.")
                st.caption("Huom: Tämä analyysi perustuu paikalliseen avainsanavertailuun ilman ulkoista API-kutsua.")
            else:
                st.warning("Syötä ilmoitusteksti.")

    # ---------------------------------------------------------
    # TAB 3: LINKKIKIRJASTO (RESPONSIIVINEN)
    # ---------------------------------------------------------
    with tab3:
        st.header("🏢 Linkkikirjasto")
        with st.expander("Mainostoimistot", expanded=True):
            cols = st.columns(4)
            for i, (name, url) in enumerate(AGENCIES.items()):
                try: domain = url.split("/")[2]; logo = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
                except: logo = ""
                with cols[i % 4]:
                    # Käytetään CSS-luokkaa 'responsive-link-btn'
                    st.markdown(f"""<a href="{url}" target="_blank" class="responsive-link-btn"><img src="{logo}">{name}</a>""", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.subheader("🌍 Kansainväliset")
            for n, u in SITES_INTL.items(): 
                st.markdown(f"[{n}]({u})")
        with c2: 
            st.subheader("🇫🇮 Suomi")
            for n, u in SITES_FI_NORDIC.items(): 
                st.markdown(f"[{n}]({u})")
        with c3: 
            st.subheader("🎬 Media")
            for n, u in SITES_MEDIA.items(): 
                st.markdown(f"[{n}]({u})")

    # ---------------------------------------------------------
    # TAB 4: TEHOHAKU (RESPONSIIVINEN)
    # ---------------------------------------------------------
    with tab4:
        st.header("⚡️ Tehohaku")
        url = generate_linkedin_url()
        # Käytetään CSS-luokkia 'cta-container' ja 'cta-button'
        st.markdown(f"""
        <div class="cta-container">
            <a href="{url}" target="_blank" class="cta-button">
                👉 AVAA LINKEDIN (HELSINKI + CREATIVE ROLES)
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("ℹ️ Mitä hakusanoja käytetään?"):
            st.write(", ".join(SEARCH_KEYWORDS))

    # ---------------------------------------------------------
    # TAB 5: SEURANTA
    # ---------------------------------------------------------
    with tab5:
        st.header("📌 Hakemusten Seuranta")
        if 'tracked_companies' not in st.session_state:
            st.session_state.tracked_companies = []
            
        with st.expander("➕ Lisää uusi seurattava yritys", expanded=False):
            with st.form("add_company_form"):
                c_name = st.text_input("Yritys")
                c_role = st.text_input("Rooli / Tehtävä")
                c_status = st.selectbox("Tila", ["Odottaa vastausta", "Aktiivinen keskustelu", "Haastattelu sovittu", "Ei vastausta", "Tarjous saatu", "Hylätty"])
                c_source = st.selectbox("Lähde", ["LinkedIn", "Suorahaku", "Verkosto", "Muu", "Työmarkkinatori"])
                submitted = st.form_submit_button("Tallenna seurantaan")
                
                if submitted and c_name:
                    new_item = {
                        "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                        "company": c_name, "role": c_role, "status": c_status, "source": c_source,
                        "date_added": datetime.datetime.now().strftime("%d.%m.%Y"),
                        "timeline": [{"date": datetime.datetime.now().strftime("%d.%m."), "event": "Lisätty seurantaan", "note": ""}],
                        "notes": ""
                    }
                    st.session_state.tracked_companies.append(new_item)
                    st.success(f"{c_name} lisätty!")
                    st.rerun()

        st.markdown("---")
        if not st.session_state.tracked_companies: st.info("Ei vielä seurattavia yrityksiä.")
        else:
            for i, item in enumerate(st.session_state.tracked_companies):
                status_color = "gray"
                if "Aktiivinen" in item['status'] or "Haastattelu" in item['status']: status_color = "green"
                elif "Ei vastausta" in item['status'] or "Hylätty" in item['status']: status_color = "red"
                elif "Tarjous" in item['status']: status_color = "gold"
                
                with st.container(border=True):
                    # Tässä st.columns skaalautuu automaattisesti, mutta sisältö voi mennä päällekkäin mobiilissa.
                    # CSS-korjaukset block-containerissa auttavat.
                    col_main, col_status, col_action = st.columns([3, 2, 1])
                    with col_main:
                        st.subheader(f"{item['company']}")
                        st.caption(f"**{item['role']}** | Lisätty: {item['date_added']}")
                    with col_status:
                        st.markdown(f"<span style='color:{status_color}; font-weight:bold; font-size:1.2em;'>● {item['status']}</span>", unsafe_allow_html=True)
                    with col_action:
                        if st.button("🗑️", key=f"del_{i}"):
                            st.session_state.tracked_companies.pop(i)
                            st.rerun()

                    with st.expander(f"📜 Aikajana ({len(item['timeline'])})"):
                        t_col1, t_col2 = st.columns([2, 1])
                        with t_col1:
                            for event in item['timeline']: st.text(f"{event['date']} - {event['event']}")
                            with st.form(key=f"add_event_{i}"):
                                new_event_type = st.selectbox("Tapahtuma", ["Sähköposti lähetetty", "Vastaus saatu", "Haastattelu", "Follow-up", "Muu"], key=f"type_{i}")
                                new_event_note = st.text_input("Info", key=f"note_{i}")
                                if st.form_submit_button("Lisää"):
                                    item['timeline'].append({"date": datetime.datetime.now().strftime("%d.%m."), "event": new_event_type, "note": new_event_note})
                                    st.rerun()
                        with t_col2:
                            new_status = st.selectbox("Päivitä tila", ["Odottaa vastausta", "Aktiivinen keskustelu", "Haastattelu sovittu", "Ei vastausta", "Tarjous saatu", "Hylätty"], key=f"stat_{i}", index=["Odottaa vastausta", "Aktiivinen keskustelu", "Haastattelu sovittu", "Ei vastausta", "Tarjous saatu", "Hylätty"].index(item['status']))
                            if new_status != item['status']:
                                item['status'] = new_status
                                st.rerun()

    # ---------------------------------------------------------
    # TAB 6: AGENTTI
    # ---------------------------------------------------------
    with tab6:
        st.header("🕵️ Ura-agentti (Ehdottaja)")
        st.markdown("""Tämä agentti analysoi taustalla tilannettasi (Seuranta, Roolit, Aikajänteet) ja antaa kevyitä ehdotuksia. **Se ei tee päätöksiä tai lähetä viestejä.**""")
        st.markdown("---")
        
        suggestions = []
        if 'tracked_companies' in st.session_state and st.session_state.tracked_companies:
            found_follow_up = False
            for item in st.session_state.tracked_companies:
                try:
                    added_date = datetime.datetime.strptime(item['date_added'], "%d.%m.%Y")
                    days_diff = (datetime.datetime.now() - added_date).days
                    if item['status'] == "Odottaa vastausta" and days_diff > 14:
                        suggestions.append(f"📬 **Follow-up:** Hakemuksesta yritykseen **{item['company']}** on kulunut {days_diff} päivää ilman merkintöjä. Kevyt kysely voisi olla paikallaan.")
                        found_follow_up = True
                    elif item['status'] == "Odottaa vastausta" and days_diff > 7:
                         suggestions.append(f"⏳ **Seuranta:** **{item['company']}** on ollut 'Odottaa'-tilassa viikon. Hyvä aika valmistella follow-up viestiä.")
                         found_follow_up = True
                except: pass
            if not found_follow_up: suggestions.append("✅ **Seuranta kunnossa:** Ei myöhässä olevia vastauksia juuri nyt.")
        else:
            suggestions.append("ℹ️ **Seuranta:** Lisää yrityksiä 'Seuranta'-välilehdelle, niin voin muistuttaa follow-upeista.")

        highlight_role = random.choice(TARGET_ROLES)
        suggestions.append(f"🚀 **Fokus-ehdotus:** Rooli **{highlight_role}** on nyt kysytty markkinalla. Oletko tarkistanut LinkedIn-tehohaun tälle roolille tällä viikolla?")
        tips = ["Muista, että portfolio painaa enemmän kuin CV luovissa rooleissa.", "Oletko jo kokeillut syöttää 'Analysoi'-työkaluun roolia, joka on hieman mukavuusalueesi ulkopuolella?", "AI-osaaminen on nyt valtava valttikortti. Muista mainita se jokaisessa hakemuksessa."]
        suggestions.append(f"💡 **Vinkki:** {random.choice(tips)}")

        for s in suggestions:
            if "Follow-up" in s: st.warning(s)
            elif "Fokus" in s: st.info(s)
            elif "Vinkki" in s: st.success(s)
            else: st.markdown(s)

    # ---------------------------------------------------------
    # TAB 7: TYÖMARKKINATORI (RESPONSIIVINEN)
    # ---------------------------------------------------------
    with tab7:
        st.header("🇫🇮 Työmarkkinatori - Luovat Alat")
        st.markdown("""
        Tämä näkymä hakee rooleja Suomen suurimmasta julkisesta työpaikkaportaalista.
        Haku on kohdistettu: **Uusimaa** ja **Luovat alat**.
        """)
        
        tm_base = "https://tyomarkkinatori.fi/henkiloasiakkaat/avoimet-tyopaikat/"
        tm_keywords = "%20".join(SEARCH_KEYWORDS) 
        tm_query = f"q={tm_keywords}&region=Uusimaa"
        tm_url = f"{tm_base}?{tm_query}"

        # Käytetään CSS-luokkia 'cta-container' ja 'cta-button'
        st.markdown(f"""
        <div class="cta-container">
            <a href="{tm_url}" target="_blank" class="cta-button">
                👉 Avaa Työmarkkinatori (Live-haku)
            </a>
        </div>
        """, unsafe_allow_html=True)
    
    # ---------------------------------------------------------
    # TAB 8: PORTFOLIO (RESPONSIIVINEN)
    # ---------------------------------------------------------
    with tab8:
        st.header("🎨 Future Maker // Portfolio")
        st.markdown("Klikkaa alla olevaa linkkiä avataksesi portfolion ja CV:n.")
        
        # Käytetään CSS-luokkia 'cta-container' ja 'cta-button dark'
        st.markdown(f"""
        <div class="cta-container">
            <a href="{FUTURE_MAKER_LINK}" target="_blank" class="cta-button dark">
                ↗️ AVAA PORTFOLIO & CV
            </a>
        </div>
        """, unsafe_allow_html=True)

        st.info("ℹ️ Sivu aukeaa uuteen välilehteen, jotta se skaalautuu oikein kaikilla laitteilla.")
        st.markdown("---")
        
        # 3. Yhdistäjä-työkalu
        st.subheader("🔗 Yhdistä työnäyte hakemukseen")
        st.markdown("Kun löydät portfoliosta hyvän casen, kirjoita tähän muistiin, miten se liittyy nykyiseen hakuusi.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Valitse osio portfoliosta:**")
            st.selectbox("Osio", ["Video CV", "Showreel", "Case: Brändiuudistus", "Case: Some-kampanja", "Muu"], key="port_section")
        with c2:
            st.markdown("**Miten tämä liittyy hakemukseen?**")
            note = st.text_area("Perustelu (Kopioi tämä sitten hakemukseen)", placeholder="Esim: Tämä case osoittaa kykyni hallita laajoja brändikokonaisuuksia...", height=100)

if __name__ == '__main__':
    main()

