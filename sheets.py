"""
data/sheets.py — Google Sheets -integraatio (portfolio-vierailijadata).
"""
from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from config import (
    SHEET_ID,
    VISITOR_DATA_ENABLED,
    VISITOR_DATA_ENDPOINT,
    VISITOR_DATA_TOKEN,
)

_HEADERS = {
    "User-Agent": "MissionJobs/portfolio-data",
    "Accept": "application/json",
}

_COLUMNS = [
    "timestamp",
    "date",
    "time",
    "event_type",
    "session_id",
    "page_path",
    "device_type",
    "browser",
    "os",
    "language",
    "referrer_type",
    "button_label",
    "button_href",
    "visit_duration_seconds",
    "scroll_depth_percent",
    "connection_type",
    "connection_operator",
]

_ALIASES = {
    "Saapumisaika": "timestamp",
    "Aika": "timestamp",
    "timestamp": "timestamp",
    "Päivämäärä": "date",
    "date": "date",
    "Kellonaika": "time",
    "time": "time",
    "Tapahtuma": "event_type",
    "Klikkaus": "event_type",
    "event_type": "event_type",
    "Istunto": "session_id",
    "session_id": "session_id",
    "Sivu": "page_path",
    "page_path": "page_path",
    "Saapuva laite": "device_type",
    "Laite": "device_type",
    "device_type": "device_type",
    "Selain": "browser",
    "browser": "browser",
    "Käyttöjärjestelmä": "os",
    "os": "os",
    "Kieli": "language",
    "language": "language",
    "Tulotapa": "referrer_type",
    "referrer_type": "referrer_type",
    "Painike": "button_label",
    "button_label": "button_label",
    "Kohde": "button_href",
    "button_href": "button_href",
    "Vierailun kesto (s)": "visit_duration_seconds",
    "visit_duration_seconds": "visit_duration_seconds",
    "Scroll (%)": "scroll_depth_percent",
    "scroll_depth_percent": "scroll_depth_percent",
    "Yhteystyyppi": "connection_type",
    "connection_type": "connection_type",
    "Operaattori": "connection_operator",
    "connection_operator": "connection_operator",
}

_EVENTS = {
    "Sivun avaus": "visit_start",
    "Painikkeen klikkaus": "button_click",
    "Vierailu päättyi": "visit_end",
    "page_view": "visit_start",
    "visit_start": "visit_start",
    "button_click": "button_click",
    "visit_end": "visit_end",
}

_DEVICES = {
    "desktop": "Tietokone",
    "computer": "Tietokone",
    "tietokone": "Tietokone",
    "mobile": "Mobiili",
    "mobiili": "Mobiili",
    "tablet": "Tabletti",
    "tabletti": "Tabletti",
}


def _endpoint_params() -> dict[str, str]:
    params: dict[str, str] = {"limit": "5000"}

    if not VISITOR_DATA_ENABLED:
        return params

    if "mode=" not in VISITOR_DATA_ENDPOINT:
        params["mode"] = "read"

    if "token=" in VISITOR_DATA_ENDPOINT:
        return params

    params["token"] = VISITOR_DATA_TOKEN
    return params


@st.cache_data(ttl=60)
def load_visitor_data() -> pd.DataFrame | None:
    """
    Lataa vierailijadata yksityisestä Google Sheetistä Apps Script -read endpointin kautta.
    Palauttaa DataFrame:n tai None virhetilanteessa.
    """
    if not VISITOR_DATA_ENABLED:
        return pd.DataFrame(columns=_COLUMNS)

    try:
        response = requests.get(
            VISITOR_DATA_ENDPOINT,
            params=_endpoint_params(),
            headers=_HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()

        if not payload.get("ok"):
            error = payload.get("error", "tuntematon endpoint-virhe")
            raise RuntimeError(f"Apps Script read endpoint: {error}")

        df = _normalise_payload(payload)
        return df
    except Exception as exc:
        st.error(
            "Vierailijadata-virhe: "
            f"{exc}. Tarkista Apps Script -endpoint, token ja käyttöoikeudet. "
            "Google Sheetin ei pidä olla julkinen."
        )
        st.caption(f"Sheet ID: {SHEET_ID}")
        return None


def _normalise_payload(payload: dict) -> pd.DataFrame:
    rows = payload.get("rows") or []
    source_columns = payload.get("columns") or []

    if not rows:
        return pd.DataFrame(columns=_COLUMNS)

    if isinstance(rows[0], dict):
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame(rows, columns=source_columns[: len(rows[0])] if source_columns else None)

    clean = pd.DataFrame()
    for source in df.columns:
        canonical = _canonical_column(source)
        if canonical and canonical not in clean.columns:
            clean[canonical] = df[source].fillna("").astype(str).str.strip()

    for column in _COLUMNS:
        if column not in clean.columns:
            clean[column] = ""

    clean["event_type"] = clean["event_type"].map(_normalise_event)
    clean["device_type"] = clean["device_type"].map(_normalise_device)
    clean["page_path"] = clean["page_path"].replace("", "/")
    clean["connection_type"] = clean["connection_type"].replace("", "not_available")
    clean["connection_operator"] = clean["connection_operator"].replace("", "not_available")

    valid_events = {"visit_start", "button_click", "visit_end"}
    clean = clean[clean["event_type"].isin(valid_events)].copy()
    clean = clean[~clean.apply(_looks_like_old_header_row, axis=1)].copy()

    return clean[_COLUMNS].reset_index(drop=True)


def _canonical_column(name) -> str | None:
    text = str(name or "").strip()
    if text in _ALIASES:
        return _ALIASES[text]

    if text.startswith("Column "):
        return None

    return _ALIASES.get(text.lower())


def _normalise_event(value: str) -> str:
    return _EVENTS.get(str(value or "").strip(), "")


def _normalise_device(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "Tuntematon"

    return _DEVICES.get(text.lower(), text)


def _looks_like_old_header_row(row: pd.Series) -> bool:
    values = [str(value or "").strip() for value in row.values]
    return any(value.startswith("Column ") for value in values)
