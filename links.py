"""
links.py — Linkkivalidointi ja koulutustutka.
Agentin avainsanat luetaan settings_managerista dynaamisesti.
"""
from __future__ import annotations
import requests
import streamlit as st
import settings_manager

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fi-FI,fi;q=0.9,en-US;q=0.8,en;q=0.7",
}


@st.cache_data(ttl=3600, show_spinner=False)
def validate_link(url: str) -> bool:
    try:
        h = {"User-Agent": "Mozilla/5.0"}
        r = requests.head(url, headers=h, timeout=2, allow_redirects=True)
        if r.status_code == 200:
            return True
        r = requests.get(url, headers=h, timeout=2)
        return r.status_code == 200
    except Exception:
        return False


@st.cache_data(ttl=300, show_spinner=False)
def check_school_application_status(url: str) -> list[str]:
    """
    Hybriditutka: etsii sivulta aktiivisia hakuindikaattoreita.
    Avainsanat luetaan settings.json:sta (muutettavissa Hallintapaneelista).
    """
    cfg = settings_manager.get_agent_config()
    haku_keywords  = cfg.get("haku_keywords",  [])
    media_keywords = cfg.get("media_keywords", [])
    url_lower = url.lower()

    # Nopea URL-tunnistus
    if "digimarkkinointi" in url_lower or "109191" in url_lower:
        return ["jatkuva haku (tunnistettu osoitteesta)", "digimarkkinoinnin erikoistuminen"]

    try:
        response = requests.get(url, headers=_REQUEST_HEADERS, timeout=10)
        if response.status_code != 200:
            return []
        html = response.text.lower()
        found_haku  = [kw for kw in haku_keywords  if kw in html]
        found_media = [kw for kw in media_keywords if kw in html]
        if found_haku and (found_media or "taitotalo" in url_lower):
            return found_haku
    except Exception:
        pass
    return []
