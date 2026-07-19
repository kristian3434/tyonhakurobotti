"""
app.py — Mission Jobs Hub | Julkinen demo + paikallinen Gemma
====================================================
Käynnistä: streamlit run app.py
"""
import streamlit as st

st.set_page_config(layout="wide", page_title="Mission Jobs Hub", page_icon="🚀")

from config import USER_NAME
from storage import load_tracked_items, load_kela_data
from styles import inject_global_styles
from sidebar import render_sidebar, active_api_key
from tabs import (
    render_tab_application, render_tab_analyze, render_tab_links,
    render_tab_search, render_tab_tracking, render_tab_agent,
    render_tab_jobs, render_tab_portfolio, render_tab_recommendations,
    render_tab_ai_courses,
)
from admin_tab import render_tab_admin
from router import call_local


def _init_session_state() -> None:
    defaults = {
        "tracked_items": None,
        "kela_data": None,
        "edit_states": {},
        "ai_engine": "Demo (simuloitu API)",
        "dismissed_suggestions": [],
        "deleted_item": None,
        "presentation_mode": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if st.session_state.tracked_items is None:
        st.session_state.tracked_items = load_tracked_items()

    if st.session_state.kela_data is None:
        st.session_state.kela_data = load_kela_data()


def render_tab_local_cv() -> None:
    """Paikallisen Gemma-mallin CV-generaattorin käyttöliittymä LM Studion kautta."""
    st.header("Automaattinen CV-generaattori (Paikallinen Gemma)")
    st.info("Yhteys: LM Studio (127.0.0.1:1234) | Malli: Gemma 4 12B / LM Studiossa ladattu paikallinen malli")

    job_description = st.text_area("Liitä työpaikkailmoitus tähän:", height=200)

    if st.button("Luo standardoitu CV"):
        if not job_description:
            st.warning("Syötä ilmoitus ensin.")
            return

        with st.spinner("Gemma työstää CV:tä Macillasi..."):
            system_prompt = """Olet mekaaninen ja tarkka CV-generaattori.
SÄÄNNÖT: Ei toistoa. Ei hallusinaatioita. Ei yliopistoviittauksia, vain avoimet kurssit.
KOROSTA: Google Gemini, Nanobanana 2, LinkedIn-sisällöntuotanto, Video-CV.
RAKENNE:
# [Roolin nimi]
## Profiili (Uutiskonsepti, viittaus Video-CV:hen)
## Ydinosaaminen (AI-työkalut, LinkedIn)
## Kokemus (Mission Jobs, kampanjointi)
## Koulutus (Avoimet kurssit ja itsenäinen opiskelu)"""

            prompt = f"{system_prompt}\n\nLuo CV tästä ilmoituksesta:\n{job_description}"
            cv_content, error = call_local(prompt)
            if cv_content:
                st.success("CV luotu paikallisesti Gemmalla!")
                st.markdown("---")
                st.markdown(cv_content)
                st.markdown("---")
            else:
                st.error(error or "Paikallinen malli ei palauttanut vastausta.")


def main() -> None:
    _init_session_state()
    inject_global_styles()
    render_sidebar()

    engine = st.session_state.get("ai_engine", "Demo (simuloitu API)")
    key = active_api_key()
    presentation_mode = st.session_state.get("presentation_mode", False)

    st.title(f"MISSION JOBS // HUB V71 ({engine})")

    tab_labels = [
        "✨ HAKEMUS",
        "📊 ANALYSOI",
        "🏢 LINKIT",
        "⚡️ TEHOHAKU",
        "📌 SEURANTA",
        "🕵️ AGENTTI",
        "🇫🇮 TYÖ",
        "🎨 PORTFOLIO",
        "🧠 SUOSITUKSET",
        "🤖 AI KOULUTUS",
        "💻 PAIKALLINEN CV",
    ]

    if not presentation_mode:
        tab_labels.append("⚙️ HALLINTAPANEELI")

    tabs = st.tabs(tab_labels)

    with tabs[0]:
        render_tab_application(key)
    with tabs[1]:
        render_tab_analyze(key)
    with tabs[2]:
        render_tab_links()
    with tabs[3]:
        render_tab_search()
    with tabs[4]:
        st.session_state.tracked_items = render_tab_tracking(st.session_state.tracked_items)
    with tabs[5]:
        st.session_state.kela_data = render_tab_agent(
            st.session_state.tracked_items,
            st.session_state.kela_data,
            key,
        )
    with tabs[6]:
        render_tab_jobs()
    with tabs[7]:
        render_tab_portfolio()
    with tabs[8]:
        st.session_state.tracked_items = render_tab_recommendations(st.session_state.tracked_items)
    with tabs[9]:
        render_tab_ai_courses()
    with tabs[10]:
        render_tab_local_cv()

    if not presentation_mode:
        with tabs[11]:
            render_tab_admin()


if __name__ == "__main__":
    main()
