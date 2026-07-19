"""
data/models.py — Sovelluksen tietomallit (dataclass).
Selkeyttää tyypit ja estää kirjoitusvirheitä sanakirjaavaimissa.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TrackedItem:
    """Yksittäinen seurantakohde (hakemus tai koulutus)."""
    company:        str
    role:           str
    status:         str
    date:           str          # "DD.MM." -formaatti
    contact_name:   str = ""
    contact_phone:  str = ""
    contact_email:  str = ""
    interview_date: str = ""
    interview_time: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "TrackedItem":
        return cls(
            company        = d.get("company", ""),
            role           = d.get("role", ""),
            status         = d.get("status", "Odottaa"),
            date           = d.get("date", ""),
            contact_name   = d.get("contact_name", ""),
            contact_phone  = d.get("contact_phone", ""),
            contact_email  = d.get("contact_email", ""),
            interview_date = d.get("interview_date", ""),
            interview_time = d.get("interview_time", ""),
        )


@dataclass
class Suggestion:
    """Suositeltu kohde (koulu tai startup)."""
    name:  str
    url:   str
    cat:   str
    score: float


@dataclass
class Course:
    """Tekoälykoulutus."""
    name:     str
    provider: str
    url:      str
    desc:     str
    type:     str


@dataclass
class KelaData:
    last_date: Optional[str] = None

    def to_dict(self) -> dict:
        return {"last_date": self.last_date}

    @classmethod
    def from_dict(cls, d: dict) -> "KelaData":
        return cls(last_date=d.get("last_date"))
