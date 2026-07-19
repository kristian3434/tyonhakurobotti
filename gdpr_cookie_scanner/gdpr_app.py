"""
gdpr_app.py — Erillinen GDPR/ePrivacy-evästeskanneri.

Käynnistä:
streamlit run gdpr_app.py
"""
import streamlit as st

from gdpr_tab import render_tab_gdpr_scanner


st.set_page_config(
    layout="wide",
    page_title="GDPR Cookie Scanner",
    page_icon="🛡️",
)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp { overflow-x: hidden; }
        .block-container { padding-top: 2rem; max-width: 1440px; }
        @media (max-width: 768px) {
            .block-container { padding: 1rem; }
            .stButton button { width: 100%; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    _inject_styles()
    st.title("GDPR Cookie Scanner")
    render_tab_gdpr_scanner()


if __name__ == "__main__":
    main()
