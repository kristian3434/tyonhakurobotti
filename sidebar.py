"""
sidebar.py — Sivupalkki: simuloitu demo, paikallinen AI ja Esitystila-kytkin.
"""
import streamlit as st
import settings_manager
from config import SIMULATED_API_KEY
from links import validate_link
from router import local_server_status

_DEMO_ENGINE = "Demo (simuloitu API)"
_LOCAL_ENGINE = "Gemma 4 12B (Paikallinen)"
_ENGINE_OPTIONS = [_DEMO_ENGINE, _LOCAL_ENGINE]


def render_sidebar() -> None:
    with st.sidebar:
        st.title("⚙️ Asetukset")

        presentation_mode = st.toggle(
            "🎬 Esitystila",
            value=st.session_state.get("presentation_mode", False),
            key="presentation_mode_toggle",
            help="Piilottaa Hallintapaneelin — aktivoi ennen video-CV:tä tai LinkedIn-esittelyä.",
        )
        st.session_state.presentation_mode = presentation_mode
        if presentation_mode:
            st.caption("✅ Hallintapaneeli piilotettu")
        else:
            st.caption("🔧 Hallintapaneeli näkyvissä")

        st.markdown("---")
        st.header("🧠 Äly")
        _render_engine_selector()

        st.markdown("---")
        st.header("🎯 Tavoitteet")

        if "target_count" not in st.session_state:
            st.session_state.target_count = settings_manager.get_monthly_target_count()

        target_count = st.radio(
            "Haettavien työpaikkojen määrä / kk:",
            options=[2, 4],
            index=1 if st.session_state.get("target_count", 4) == 4 else 0,
            horizontal=True,
            help="Valitse kuukausittainen työnhakuvelvoite."
        )
        st.session_state.target_count = target_count
        settings_manager.set_monthly_target_count(target_count)

        st.markdown("---")
        if not presentation_mode:
            if st.toggle("🚀 Start-upit", value=False):
                st.markdown("### Hubit")
                for item in settings_manager.get_startups():
                    if validate_link(item["url"]):
                        st.markdown(f"- [{item['name']}]({item['url']})")


def _render_engine_selector() -> None:
    current_engine = st.session_state.get("ai_engine", _DEMO_ENGINE)

    if current_engine == "lamal 3.1-8b (Paikallinen)":
        current_engine = _LOCAL_ENGINE
        st.session_state.ai_engine = current_engine

    if current_engine not in _ENGINE_OPTIONS:
        current_engine = _DEMO_ENGINE
        st.session_state.ai_engine = current_engine

    engine = st.radio(
        "Valitse tekoälymoottori:",
        _ENGINE_OPTIONS,
        index=_ENGINE_OPTIONS.index(current_engine),
        horizontal=True,
    )
    st.session_state.ai_engine = engine

    if engine == _DEMO_ENGINE:
        st.success("🧪 Simuloitu API käytössä")
        st.caption("Oikeita avaimia tai ulkoisia AI-palveluja ei käytetä.")

    elif engine == _LOCAL_ENGINE:
        available, model, message = local_server_status()
        st.session_state.local_ai_available = available
        if available:
            st.success("🤖 Paikallinen Gemma yhdistetty")
            st.caption(f"LM Studio • {model}")
        else:
            st.error("🔴 Paikallinen Gemma ei ole yhteydessä")
            st.info(message)


def active_api_key() -> str:
    engine = st.session_state.get("ai_engine", _DEMO_ENGINE)

    if engine in (_LOCAL_ENGINE, "lamal 3.1-8b (Paikallinen)"):
        return "LOCAL_GEMMA_ACTIVE" if st.session_state.get("local_ai_available", False) else ""

    return SIMULATED_API_KEY
