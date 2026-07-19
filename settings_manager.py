"""
settings_manager.py — Dynaaminen sisällönhallinta.
Kaikki dynaamiset sisällöt (mainostoimistot, koulut, kurssit, avainsanat)
tallennetaan settings.json-tiedostoon ja luetaan sieltä ajon aikana.
Session state toimii välimuistina (nopea), levy pysyvänä tallennuksena.
"""
from __future__ import annotations
import base64
from html.parser import HTMLParser
import json
import os
import re
import streamlit as st
import time
from html import unescape
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
LOGO_CACHE_FILE = os.path.join(BASE_DIR, "logo_cache.json")
_CACHE_KEY    = "_settings_cache"
_CACHE_MTIME_KEY = "_settings_cache_mtime"
_LOGO_MAX_BYTES = 1_500_000
_LOGO_TIMEOUT = 4
_logo_cache_memory: dict | None = None


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.casefold() in {"none", "nan", "nat", "<na>", "null"} else text


def _agency_key(value: object) -> str:
    return " ".join(_clean_text(value).split()).casefold()


def _agency_sort_key(agency: dict) -> tuple[str, str]:
    name = _clean_text(agency.get("name"))
    url = _clean_text(agency.get("url"))
    return (_agency_key(name), url.casefold())


_AGENCY_DEFAULT_URLS = {
    "Avidly":           "https://avidly.fi/",
    "Bob the Robot":    "https://www.bobtherobot.fi/",
    "Dagmar":           "https://www.dagmar.fi/",
    "Folk Finland":     "https://folkfinland.fi/",
    "Futurice":         "https://futurice.com/careers",
    "hasan & partners": "https://www.hasanpartners.fi/",
    "Kuulu":            "https://www.kuulu.fi/",
    "Miltton":          "https://miltton.com/fi/",
    "N2 Creative":      "https://n2.fi/",
    "Nitro AIM":        "https://www.nitroaim.fi/",
    "Reaktor":          "https://www.reaktor.com/careers/",
    "Samy":             "https://samy.com/",
    "SEK":              "https://sek.io/careers/",
    "Siili Solutions":  "https://www.siili.com/",
    "TBWA Helsinki":    "https://www.tbwa.fi/",
    "Valve":            "https://valve.fi/",
    "Vapa Media":       "https://vapamedia.fi/",
    "Vincit":           "https://www.vincit.fi/careers/",
}


_OFFICIAL_AGENCY_LOGOS = {
    "Avidly":           "https://avidly.fi/favicons/favicon.svg",
    "Bob the Robot":    "https://www.bobtherobot.fi/static/apple-touch-icon-white.png",
    "Dagmar":           "https://www.dagmar.fi/wp-content/themes/dagmar/dist/images/favicon.svg",
    "Folk Finland":     "https://framerusercontent.com/images/dko2yTEZR6s2MozzKxt3KN5cFxo.png",
    "Futurice":         "https://futurice.com/icon.svg",
    "hasan & partners": "https://cdn.prod.website-files.com/64ddd41212def5051b673f65/6968b03897a047b913a9bf4a_favicon-32x32.png",
    "Kuulu":            "https://www.kuulu.fi/hubfs/raw_assets/public/VideoLandingPage_2025/images/kuulu-logo-lettermark.png",
    "Miltton":          "https://miltton.com/wp-content/themes/miltton42/img/favicon/favicon.svg",
    "N2 Creative":      "https://n2.fi/favicon-32x32.png",
    "Nitro AIM":        "https://images.squarespace-cdn.com/content/v1/693a92467816ab4918026f97/885d9d5e-5f47-42b7-be0b-18324fdcbe54/Nitro+AIM+Logo.png?format=300w",
    "Reaktor":          "https://www.reaktor.com/hubfs/reaktor-favicon-32x32.png",
    "Samy":             "https://samy.com/wp-content/uploads/2025/05/SAMY-white.svg",
    "SEK":              "https://sek.io/wp-content/uploads/fav_icon-300x300.png",
    "Siili Solutions":  "https://www.siili.com/hubfs/Siili_logo_text_8_spikes_Black_RGB_28042020.png",
    "TBWA Helsinki":    "https://www.tbwa.fi/wp-content/themes/tbwa-theme/static/favicon/favicon-32x32.png",
    "Valve":            "https://www.valveone.com/hubfs/raw_assets/public/theme-valve-one/images/favicon.svg",
    "Vapa Media":       "https://vapamedia.fi/wp-content/uploads/2025/04/vapa-logo-white.svg",
    "Vincit":           "https://www.vincit.com/hubfs/favicon-vincit-gradient.png",
}


_AGENCY_LOGO_CLASSES = {
    "Dagmar": "logo-on-dark",
    "Reaktor": "logo-invert-on-dark",
    "Siili Solutions": "logo-invert-on-dark",
}


_CANONICAL_AGENCY_NAMES = {
    _agency_key(name): name for name in _AGENCY_DEFAULT_URLS
}


def normalize_agencies(agencies: list[dict]) -> list[dict]:
    """Siivoaa hallintataulukosta tulevat rivit vakaaseen muotoon."""
    rows: list[dict] = []
    seen: set[str] = set()

    for agency in agencies or []:
        if not isinstance(agency, dict):
            continue

        name = _clean_text(agency.get("name"))
        if not name:
            continue

        canonical_name = _CANONICAL_AGENCY_NAMES.get(_agency_key(name), name)
        canonical_key = _agency_key(canonical_name)
        if canonical_key in seen:
            continue

        rows.append({
            "name": canonical_name,
            "url": _clean_text(agency.get("url")) or _AGENCY_DEFAULT_URLS.get(canonical_name, ""),
            "logo_url": _clean_text(agency.get("logo_url")),
        })
        seen.add(canonical_key)

    return sorted(rows, key=_agency_sort_key)


def _default_agencies() -> list[dict]:
    return sorted([
        {"name": name, "url": url, "logo_url": ""}
        for name, url in _AGENCY_DEFAULT_URLS.items()
    ], key=_agency_sort_key)


def normalize_settings(settings: dict) -> dict:
    settings["agencies"] = normalize_agencies(settings.get("agencies", []))
    return settings


def _settings_mtime() -> float | None:
    try:
        return os.path.getmtime(SETTINGS_FILE)
    except OSError:
        return None


def _load_logo_cache() -> dict:
    global _logo_cache_memory
    if _logo_cache_memory is not None:
        return _logo_cache_memory

    try:
        with open(LOGO_CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except (OSError, json.JSONDecodeError):
        cache = {}

    _logo_cache_memory = cache
    return cache


def _save_logo_cache(cache: dict) -> None:
    global _logo_cache_memory
    _logo_cache_memory = cache
    try:
        with open(LOGO_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _mime_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if path.endswith(".svg"):
        return "image/svg+xml"
    if path.endswith(".png"):
        return "image/png"
    if path.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if path.endswith(".gif"):
        return "image/gif"
    if path.endswith(".webp"):
        return "image/webp"
    if path.endswith(".ico"):
        return "image/x-icon"
    return ""


def _image_data_uri(url: str) -> str:
    url = _clean_text(url)
    if url.startswith("data:image/"):
        return url
    if not url.startswith(("http://", "https://")):
        return ""

    try:
        req = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
                ),
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "fi-FI,fi;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        with urlopen(req, timeout=_LOGO_TIMEOUT) as response:
            data = response.read(_LOGO_MAX_BYTES + 1)
            content_type = response.headers.get("content-type", "").split(";")[0].lower()
    except (OSError, URLError, TimeoutError, ValueError):
        return ""

    if len(data) > _LOGO_MAX_BYTES:
        return ""
    if not data:
        return ""

    mime = content_type if content_type.startswith("image/") else _mime_from_url(url)
    if not mime:
        return ""

    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _cached_image_data_uri(url: str, cache_key: str) -> str:
    cache = _load_logo_cache()
    entry = cache.get(cache_key, {})
    if entry.get("data_uri") and entry.get("source_url") == url:
        return entry["data_uri"]

    failed_at = entry.get("failed_at", 0) if entry.get("source_url") == url else 0
    if failed_at and time.time() - failed_at < 24 * 60 * 60:
        return ""

    data_uri = _image_data_uri(url)
    if data_uri:
        cache[cache_key] = {
            "source_url": url,
            "data_uri": data_uri,
            "updated_at": int(time.time()),
        }
    else:
        cache[cache_key] = {
            "source_url": url,
            "failed_at": int(time.time()),
        }

    _save_logo_cache(cache)
    return data_uri


class _LogoParser(HTMLParser):
    def __init__(self, base_url: str, name: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.name_tokens = [p for p in re.split(r"\W+", name.lower()) if len(p) > 2]
        self.candidates: list[tuple[str, str, str]] = []

    def _add(self, kind: str, label: str, url: str) -> None:
        url = _clean_text(unescape(url))
        if url:
            self.candidates.append((kind, label, urljoin(self.base_url, url)))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()

        if tag == "link":
            rel = attrs_dict.get("rel", "").lower()
            href = attrs_dict.get("href", "")
            if href and "apple-touch-icon" in rel:
                self._add("apple-icon", rel, href)
            elif href and "icon" in rel:
                self._add("icon", rel, href)
            return

        if tag == "meta":
            prop = (attrs_dict.get("property") or attrs_dict.get("name") or "").lower()
            content = attrs_dict.get("content", "")
            if content and prop in {"og:image", "twitter:image", "twitter:image:src"}:
                self._add("meta-image", prop, content)
            return

        if tag == "img":
            src = attrs_dict.get("src") or attrs_dict.get("data-src") or attrs_dict.get("data-lazy-src")
            label = " ".join([
                attrs_dict.get("alt", ""),
                attrs_dict.get("class", ""),
                attrs_dict.get("id", ""),
                src or "",
            ])
            label_l = label.lower()
            if src and ("logo" in label_l or any(token in label_l for token in self.name_tokens)):
                self._add("img", label, src)
            return

        if tag == "source":
            srcset = attrs_dict.get("srcset", "")
            src = srcset.split(",")[0].strip().split(" ")[0]
            if src and "logo" in src.lower():
                self._add("source", "srcset", src)


def _json_logo_candidates(html: str, base_url: str) -> list[tuple[str, str, str]]:
    candidates = []
    patterns = [
        r'"logo"\s*:\s*"([^"]+)"',
        r'"logo"\s*:\s*\{[^{}]*"url"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, html, flags=re.IGNORECASE):
            raw = unescape(match.group(1).replace("\\/", "/"))
            if raw:
                candidates.append(("json-logo", "structured logo", urljoin(base_url, raw)))
    return candidates


def _score_logo_candidate(name: str, kind: str, label: str, url: str) -> int:
    haystack = f"{label} {url}".lower()
    score = {
        "json-logo": 95,
        "img": 80,
        "source": 70,
        "apple-icon": 55,
        "icon": 50,
        "meta-image": 20,
        "direct": 35,
    }.get(kind, 0)

    if "logo" in haystack:
        score += 30
    if "white" in haystack or "valk" in haystack:
        score += 12
    if "black" in haystack:
        score -= 8
    if "favicon" in haystack:
        score -= 3
    if urlparse(url).path.lower().endswith(".svg"):
        score += 8

    for token in re.split(r"\W+", name.lower()):
        if len(token) > 2 and token in haystack:
            score += 5

    return score


def _direct_icon_candidates(url: str) -> list[tuple[str, str, str]]:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return []

    origin = f"{parsed.scheme}://{parsed.netloc}"
    return [
        ("direct", "apple-touch-icon", f"{origin}/apple-touch-icon.png"),
        ("direct", "favicon svg", f"{origin}/favicon.svg"),
        ("direct", "favicon 32", f"{origin}/favicon-32x32.png"),
        ("direct", "favicon", f"{origin}/favicon.ico"),
    ]


def _discover_agency_logo(agency: dict) -> str:
    name = _clean_text(agency.get("name"))
    url = _clean_text(agency.get("url"))
    if not url:
        return ""

    cache_key = f"auto:{_agency_key(name)}:{url}"
    cache = _load_logo_cache()
    entry = cache.get(cache_key, {})
    if entry.get("data_uri"):
        return entry["data_uri"]
    if entry.get("failed_at") and time.time() - entry["failed_at"] < 24 * 60 * 60:
        return ""

    candidates: list[tuple[str, str, str]] = []
    try:
        req = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "fi-FI,fi;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        with urlopen(req, timeout=_LOGO_TIMEOUT) as response:
            html = response.read(500_000).decode("utf-8", "ignore")
        parser = _LogoParser(url, name)
        parser.feed(html)
        candidates.extend(_json_logo_candidates(html, url))
        candidates.extend(parser.candidates)
    except (OSError, URLError, TimeoutError, ValueError):
        pass

    candidates.extend(_direct_icon_candidates(url))
    candidates = sorted(
        list(dict.fromkeys(candidates)),
        key=lambda c: _score_logo_candidate(name, c[0], c[1], c[2]),
        reverse=True,
    )

    for _kind, _label, candidate_url in candidates[:20]:
        data_uri = _image_data_uri(candidate_url)
        if data_uri:
            cache[cache_key] = {
                "source_url": candidate_url,
                "data_uri": data_uri,
                "updated_at": int(time.time()),
            }
            _save_logo_cache(cache)
            return data_uri

    cache[cache_key] = {"failed_at": int(time.time())}
    _save_logo_cache(cache)
    return ""


def _initials_logo(name: str) -> str:
    initials = "".join(part[0] for part in re.split(r"\W+", name) if part)[:2].upper()
    initials = initials or "?"
    hue = sum(ord(ch) for ch in name) % 360
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 40">'
        f'<rect width="64" height="40" rx="8" fill="hsl({hue},65%,38%)"/>'
        f'<text x="32" y="26" text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-size="18" font-weight="700" fill="#fff">{initials}</text>'
        f'</svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def agency_logo_fallback(agency: dict) -> str:
    return _initials_logo(_clean_text(agency.get("name")))


def agency_logo_class(agency: dict) -> str:
    name = _clean_text(agency.get("name"))
    canonical_name = _CANONICAL_AGENCY_NAMES.get(_agency_key(name), name)
    return _AGENCY_LOGO_CLASSES.get(canonical_name, "")


# ── Oletusarvot ───────────────────────────────────────────────────────────────

def _build_defaults() -> dict:
    return {
        "portfolio_url": "",
        "monthly_target_count": 4,
        "user_education": {
            "degree": "",
            "year": None,
            "level": "",
            "is_higher_education": False,
            "has_amk_degree": False,
            "has_university_degree": False,
        },

        "agencies": _default_agencies(),

        "schools": [
            {"name": "Aalto-yliopisto (Taiteet & Suunnittelu)",  "url": "https://www.aalto.fi/fi/taiteiden-ja-suunnittelun-korkeakoulu",                                                                                                                                                                          "status": "⭐ HUIPPU"},
            {"name": "HEO Kansanopisto (Graafinen & Kuvallinen)","url": "https://www.heo.fi/",                                                                                                                                                                                                                     "status": "Portfolio"},
            {"name": "Metropolia AMK (Viestintä & Muotoilu)",    "url": "https://www.metropolia.fi/fi/opiskelu-metropoliassa/amk-tutkinnot/",                                                                                                                                                                      "status": "AMK / Haku"},
            {"name": "Haaga-Helia (Journalismi & Digi)",         "url": "https://www.haaga-helia.fi/fi/viestinta-ja-journalismi",                                                                                                                                                                                  "status": "AMK / Haku"},
            {"name": "Humak (Kulttuurituottaja)",                 "url": "https://www.humak.fi/opiskelu/amk-tutkinnot/kulttuurituottaja/",                                                                                                                                                                         "status": "AMK / Tuottaja"},
            {"name": "Taitotalo (Digimarkkinointi)",             "url": "https://www.taitotalo.fi/koulutukset/ict-ja-media/109191-6279-6315-digimarkkinoinnin-asiantuntija-verkko-opiskelu-media-alan-ja-kuvallisen-ilmaisun-perustutkinnon-osa",                                                                  "status": "Erikoistuminen"},
            {"name": "Stadin AO (Media & Kuvallinen)",           "url": "https://stadinao.fi/koulutustarjonta/media-ja-visuaalinen-ala/",                                                                                                                                                                          "status": "Jatkuva haku"},
            {"name": "Varia (Media-ala)",                         "url": "https://www.varia.fi/koulutukset/media-ala/",                                                                                                                                                                                            "status": "Vantaa"},
            {"name": "Omnia (Media & Kuvallinen ilmaisu)",        "url": "https://www.omnia.fi/koulutukset/mediapalvelujen-toteuttaja",                                                                                                                                                                            "status": "Espoo"},
            {"name": "Business College Helsinki (Digi)",          "url": "https://bc.fi/koulutukset/",                                                                                                                                                                                                             "status": "Helsinki"},
            {"name": "Rastor-instituutti (Markkinointi)",         "url": "https://www.rastor.fi/koulutukset/",                                                                                                                                                                                                    "status": "Aikuis"},
            {"name": "Careeria (Media)",                          "url": "https://careeria.fi/koulutukset/",                                                                                                                                                                                                      "status": "Hki/Vantaa"},
        ],

        "ai_courses": [
            {"name": "Generative AI Learning Path",    "provider": "Google Cloud",                    "url": "https://www.cloudskillsboost.google/paths/118",                                                                                                             "type": "SERTIFIKAATTI",    "desc": "Googlen virallinen ja ilmainen polku generatiivisen tekoälyn syvälliseen ymmärtämiseen."},
            {"name": "Opin.fi: Tekoäly & Luova",       "provider": "Suomen Korkeakoulut (Digivisio)", "url": "https://opin.fi/fi/search?q=teko%C3%A4ly",                                                                                                                  "type": "HAKUPALVELU",      "desc": "Kokoava haku. Kriteerit: Laskennallinen luovuus, XR, Visual Culture, Palvelumuotoilu & AI."},
            {"name": "Elements of AI",                 "provider": "Helsingin Yliopisto & Reaktor",   "url": "https://www.elementsofai.com/fi",                                                                                                                            "type": "MOOC / ETÄ",       "desc": "Suomalainen klassikko. Pakollinen pohjatieto kaikille alalla toimiville."},
            {"name": "HY Avoin: Tekoäly & Data",       "provider": "Helsingin Yliopisto",             "url": "https://www.helsinki.fi/fi/hakeminen-ja-opetus/etsi-koulutuksia-ja-kursseja?s_format=mooc%2Cdistance_or_online_teaching&s_itg=open_university&s_q=ai",      "type": "YLIOPISTO / MOOC", "desc": "Helsingin yliopiston avoimet tekoälykurssit. MOOC-toteutuksia ja etäopintoja joustavasti."},
            {"name": "FiTech – Tekoäly",               "provider": "Yliopistoverkosto (Aalto ym.)",   "url": "https://fitech.io/fi/opinnot/?s=teko%C3%A4ly",                                                                                                              "type": "YLIOPISTO / ETÄ",  "desc": "Suomen laajin ilmainen tekniikan tarjonta. Etäopintoja Aallosta, LUTista ja Oulusta."},
            {"name": "Aalto Avoin: Art & Media",       "provider": "Aalto Arts",                      "url": "https://www.aalto.fi/fi/taiteiden-ja-suunnittelun-korkeakoulu",                                                                                             "type": "YLIOPISTO (HKI)",  "desc": "Seuraa Aalto Artsin avoimia kursseja. Usein AI- ja mediayhteyksiä."},
            {"name": "3AMK (AI & Future)",             "provider": "Metropolia, Haaga-Helia, Laurea", "url": "https://www.3amk.fi/",                                                                                                                                       "type": "AMK (HKI)",        "desc": "Pääkaupunkiseudun korkeakoulujen yhteiset tulevaisuuskurssit."},
            {"name": "DeepLearning.AI: AI for Everyone","provider": "DeepLearning.AI",                "url": "https://www.deeplearning.ai/courses/ai-for-everyone/",                                                                                                       "type": "KV / ETÄ",         "desc": "Andrew Ng:n kurssi bisnespuolelle ja tuottajille. Ei vaadi koodausta."},
        ],

        "startups": [
            {"name": "Aalto Startup Center",    "url": "https://startupcenter.aalto.fi/"},
            {"name": "Kiuas Accelerator",        "url": "https://www.kiuas.com/"},
            {"name": "Kurio (Mainostoimisto)",   "url": "https://www.kurio.fi/"},
            {"name": "Maria 01 (Yritykset)",     "url": "https://maria.io/"},
            {"name": "Supercell Careers",        "url": "https://supercell.com/en/careers/"},
            {"name": "The Hub (Helsinki Jobs)",  "url": "https://thehub.io/jobs?location=Helsinki"},
            {"name": "Wolt Careers",             "url": "https://careers.wolt.com/en"},
        ],

        "sites_intl": [
            {"name": "Behance Jobs",       "url": "https://www.behance.net/joblist"},
            {"name": "Design Jobs Board",  "url": "https://www.designjobsboard.com/"},
            {"name": "Krop",               "url": "https://www.krop.com/"},
        ],

        "sites_fi": [
            {"name": "Grafia ry",              "url": "https://www.grafia.fi/"},
            {"name": "Journalistiliitto",       "url": "https://journalistiliitto.fi/"},
            {"name": "Kuntarekry (Kulttuuri)", "url": "https://www.kuntarekry.fi/fi/tyopaikat/kulttuuri-ja-museoala/"},
            {"name": "TAKU ry",                "url": "https://taku.fi/avainsana/tyopaikat/"},
            {"name": "Valtiolle.fi",           "url": "https://valtiolle.fi/"},
            {"name": "Viesti ry",              "url": "https://viesti.fi/tyoelama/avoimet-tyopaikat/"},
        ],

        "sites_media": [
            {"name": "Alma Media Urat",  "url": "https://www.almamedia.fi/tyopaikat/"},
            {"name": "Duunitori (Media)","url": "https://duunitori.fi/tyopaikat/ala/media-ala"},
            {"name": "Kelaamo (AV-ala)", "url": "https://www.kelaamo.fi/"},
            {"name": "Sanoma Urat",      "url": "https://www.sanoma.com/fi/keita-olemme/toihin-sanomalle/"},
            {"name": "Yle Rekry",        "url": "https://yle.fi/rekry"},
        ],

        "training_topics": [
            {"label": "Kaikki aiheet",       "query": "media viestintä"},
            {"label": "Viestintä",            "query": "viestintä"},
            {"label": "Graafinen",            "query": "graafinen"},
            {"label": "Osatutkinnot",         "query": "osatutkinto"},
            {"label": "Tutkinnon osat",       "query": "tutkinnon osa"},
            {"label": "Osatutkintokoulutus",  "query": "osatutkintokoulutus"},
        ],

        "agent_taitotalo_url": (
            "https://www.taitotalo.fi/koulutukset/ict-ja-media/109191-6279-6315-"
            "digimarkkinoinnin-asiantuntija-verkko-opiskelu-media-alan-ja-kuvallisen-"
            "ilmaisun-perustutkinnon-osa"
        ),
        "agent_haku_keywords": [
            "hae tähän koulutukseen", "hae nyt", "ilmoittaudu nyt",
            "jatkuva haku", "täytä hakemus", "lisää ostoskoriin", "ilmoittaudu",
        ],
        "agent_media_keywords": [
            "digimarkkinointi", "media-ala", "kuvallisen ilmaisun", "viestintä", "verkko-opiskelu",
        ],

        "target_roles": [
            "Graafinen suunnittelija", "Sisällöntuottaja", "Visuaalinen suunnittelija",
            "Projektipäällikkö (luovat sisällöt)", "Viestintäsuunnittelija",
            "Markkinointisuunnittelija", "UI/UX-suunnittelija", "Creative Producer",
            "Content Manager", "Art Director Assistant", "Junior Designer", "Video Editor",
        ],

        "search_keywords": [
            "graafinen suunnittelija", "sisällöntuottaja", "visuaalinen suunnittelija",
            "projektipäällikkö", "viestintäsuunnittelija", "markkinointisuunnittelija",
            "UI designer", "UX designer", "creative producer", "content manager",
            "mainonta", "luova ala", "graafinen suunnittelu", "digitaalinen viestintä", "ICT",
        ],
    }


# ── Lataus & tallennus ────────────────────────────────────────────────────────

def load_settings() -> dict:
    """Lataa settings.json. Jos puuttuu, luo oletusasetuksilla."""
    if not os.path.exists(SETTINGS_FILE):
        defaults = _build_defaults()
        _write_to_disk(defaults)
        return defaults
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Täydennä mahdolliset uudet avaimet oletusarvoilla
        for key, val in _build_defaults().items():
            if key not in data:
                data[key] = val
        return normalize_settings(data)
    except Exception as exc:
        st.warning(f"⚠️ settings.json vioittunut, käytetään oletuksia: {exc}")
        return _build_defaults()


def save_settings(settings: dict) -> None:
    """Tallentaa asetukset levylle ja päivittää session state -välimuistin."""
    settings = normalize_settings(settings)
    _write_to_disk(settings)
    st.session_state[_CACHE_KEY] = settings
    st.session_state[_CACHE_MTIME_KEY] = _settings_mtime()


def _write_to_disk(settings: dict) -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        st.error(f"🔴 Virhe tallennuksessa: {exc}")


def get_settings() -> dict:
    """Palauttaa asetukset välimuistista tai levyltä."""
    disk_mtime = _settings_mtime()
    if (
        _CACHE_KEY not in st.session_state
        or st.session_state.get(_CACHE_MTIME_KEY) != disk_mtime
    ):
        st.session_state[_CACHE_KEY] = load_settings()
        st.session_state[_CACHE_MTIME_KEY] = _settings_mtime()
    else:
        st.session_state[_CACHE_KEY] = normalize_settings(st.session_state[_CACHE_KEY])
    return st.session_state[_CACHE_KEY]


def reset_section(key: str) -> None:
    """Palauttaa yksittäisen osion oletusarvoihin."""
    s = get_settings()
    s[key] = _build_defaults()[key]
    save_settings(s)


# ── Getter-apufunktiot ────────────────────────────────────────────────────────

def get_agencies() -> list[dict]:
    return get_settings().get("agencies", [])

def get_schools() -> list[dict]:
    return get_settings().get("schools", [])

def get_ai_courses() -> list[dict]:
    return get_settings().get("ai_courses", [])

def get_startups() -> list[dict]:
    return get_settings().get("startups", [])

def get_sites_intl() -> list[dict]:
    return get_settings().get("sites_intl", [])

def get_sites_fi() -> list[dict]:
    return get_settings().get("sites_fi", [])

def get_sites_media() -> list[dict]:
    return get_settings().get("sites_media", [])

def get_training_topics() -> dict[str, str]:
    """Palauttaa {label: query} -sanakirjan Työmarkkinatorille."""
    return {row["label"]: row["query"]
            for row in get_settings().get("training_topics", [])
            if row.get("label") and row.get("query")}

def get_portfolio_url() -> str:
    return get_settings().get("portfolio_url", "")

def get_user_education() -> dict:
    return get_settings().get("user_education", {})

def get_monthly_target_count() -> int:
    value = get_settings().get("monthly_target_count", 4)
    try:
        target = int(value)
    except (TypeError, ValueError):
        return 4
    return target if target in (2, 4) else 4

def set_monthly_target_count(target_count: int) -> None:
    try:
        target = int(target_count)
    except (TypeError, ValueError):
        target = 4

    if target not in (2, 4):
        target = 4

    settings = get_settings()
    if settings.get("monthly_target_count") == target:
        return

    settings["monthly_target_count"] = target
    save_settings(settings)

def get_target_roles() -> list[str]:
    return get_settings().get("target_roles", [])

def get_search_keywords() -> list[str]:
    return get_settings().get("search_keywords", [])

def get_agent_config() -> dict:
    s = get_settings()
    return {
        "taitotalo_url":    s.get("agent_taitotalo_url", ""),
        "haku_keywords":    s.get("agent_haku_keywords", []),
        "media_keywords":   s.get("agent_media_keywords", []),
    }

def agency_logo(agency: dict) -> str:
    """
    Palauttaa logon URL:n.
    Jos logo_url on asetettu, käytetään sitä. Tunnetuille toimistoille käytetään
    viralliselta sivulta tarkistettua logoa. Muut lisäykset yrittävät hakea
    aidon logon automaattisesti sivun metatiedoista ja tallentavat sen välimuistiin.
    """
    logo_url = _clean_text(agency.get("logo_url"))
    if logo_url:
        return _cached_image_data_uri(logo_url, f"manual:{logo_url}") or logo_url

    name = _clean_text(agency.get("name"))
    canonical_name = _CANONICAL_AGENCY_NAMES.get(_agency_key(name), name)
    if canonical_name in _OFFICIAL_AGENCY_LOGOS:
        logo_url = _OFFICIAL_AGENCY_LOGOS[canonical_name]
        return _cached_image_data_uri(logo_url, f"official:{canonical_name}") or logo_url

    discovered = _discover_agency_logo(agency)
    if discovered:
        return discovered

    return _initials_logo(name)
