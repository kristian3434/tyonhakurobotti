"""
data/storage.py — Paikallinen JSON-tallennus.
Kaikki tiedostoluku/-kirjoitus tapahtuu tässä moduulissa.
"""
from __future__ import annotations
import json
import os
import streamlit as st

from config import STORAGE_FILE, KELA_FILE
from models import TrackedItem, KelaData


# ── Tracked items ─────────────────────────────────────────────────────────────

def load_tracked_items() -> list[TrackedItem]:
    """Lataa seurantakohteet levyltä. Palauttaa tyhjän listan virhetilanteessa."""
    if not os.path.exists(STORAGE_FILE):
        return []
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            raw: list[dict] = json.load(f)
        return [TrackedItem.from_dict(d) for d in raw]
    except (json.JSONDecodeError, OSError) as exc:
        st.error(f"Virhe ladattaessa seurantadataa: {exc}")
        return []


def save_tracked_items(items: list[TrackedItem]) -> None:
    """Tallentaa seurantakohteet levylle."""
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump([item.to_dict() for item in items], f, ensure_ascii=False, indent=4)
    except OSError as exc:
        st.error(f"Virhe tallennuksessa: {exc}")


# ── Kela data ─────────────────────────────────────────────────────────────────

def load_kela_data() -> KelaData:
    """Lataa Kela-ilmoituksen viimeisimmän päivämäärän."""
    if not os.path.exists(KELA_FILE):
        return KelaData()
    try:
        with open(KELA_FILE, "r", encoding="utf-8") as f:
            return KelaData.from_dict(json.load(f))
    except (json.JSONDecodeError, OSError):
        return KelaData()


def save_kela_data(data: KelaData) -> None:
    """Tallentaa Kela-datan levylle."""
    try:
        with open(KELA_FILE, "w", encoding="utf-8") as f:
            json.dump(data.to_dict(), f, ensure_ascii=False, indent=4)
    except OSError as exc:
        st.error(f"Virhe Kela-datan tallennuksessa: {exc}")
