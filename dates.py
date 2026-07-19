"""
utils/dates.py — Päivämääräoperaatiot ja laskurit.
"""
from __future__ import annotations
import datetime
from typing import Optional

from config import FUTURE_DATE_BUFFER


def parse_date(date_str: str) -> Optional[datetime.datetime]:
    """
    Muuntaa merkkijonon datetime-objektiksi.

    Tuetut formaatit:
    - "YYYY-MM-DD"
    - "DD.MM."  (vuodenvaihde-bugi korjattu: jos yli FUTURE_DATE_BUFFER päivää
                 tulevaisuudessa → oletetaan edellinen vuosi)
    """
    if not date_str:
        return None
    date_str = str(date_str).strip()
    try:
        if "-" in date_str:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d")
        parts = date_str.rstrip(".").split(".")
        if len(parts) >= 2:
            day, month = int(parts[0]), int(parts[1])
            now = datetime.datetime.now()
            dt = datetime.datetime(now.year, month, day)
            if (dt - now).days > FUTURE_DATE_BUFFER:
                dt = datetime.datetime(now.year - 1, month, day)
            return dt
    except (ValueError, IndexError):
        return None
    return None


def days_since(date_str: str) -> int:
    """Palauttaa kuinka monta päivää sitten annettu päivä oli (positiivinen = menneisyys)."""
    dt = parse_date(date_str)
    if dt is None:
        return 0
    return (datetime.datetime.now() - dt).days


def days_until(date_str: str) -> int:
    """Palauttaa kuinka monta päivää tulevaan päivään (positiivinen = tulevaisuus)."""
    dt = parse_date(date_str)
    if dt is None:
        return 0
    return (dt - datetime.datetime.now()).days + 1


def deadline_badge(date_str: str, is_future: bool = False) -> str:
    """
    Palauttaa ihmisluettavan emoji-merkkijonon päivämäärän tilasta.

    Args:
        date_str:  Päivämäärä merkkijonona.
        is_future: True → lasketaan tulevaan tapahtumaan; False → menneeseen.
    """
    dt = parse_date(str(date_str) if date_str else "")
    if dt is None:
        return ""
    try:
        now = datetime.datetime.now()
        if is_future:
            diff = (dt - now).days + 1
            if diff < 0:   return "🔴 Meni jo"
            if diff == 0:  return "🔥 TÄNÄÄN"
            if diff <= 2:  return f"🔥 {diff} pv"
            return f"📅 {diff} pv"
        else:
            diff = (now - dt).days
            if diff > 21:  return f"⚠️ {diff} pv (Hiljaista)"
            if diff > 14:  return f"🕒 {diff} pv"
            return f"🆕 {diff} pv"
    except Exception:
        return ""
