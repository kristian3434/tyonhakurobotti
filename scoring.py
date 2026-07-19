"""
scoring.py — Pisteytys ja paikallinen teksti-analyysi.
TARGET_ROLES luetaan ajon aikana settings_managerista (dynaaminen).

Korjattu versio:
- poistaa satunnaisuuden puuttuvista avainsanoista
- deduplikoi työpaikkailmoituksen avainsanat
- tekee keyword-matchista deterministisen
- lisää apufunktion Match Score -> prosentti, jotta AI ei keksi omaa sopivuutta
"""
from __future__ import annotations

import re
import settings_manager
from config import UNI_KEYWORDS, AMK_KEYWORDS, USER_EDUCATION


_KEYWORD_CATEGORIES: dict[str, list[str]] = {
    "Luova": [
        "photoshop", "illustrator", "indesign", "figma", "video", "editointi",
        "visuaalinen", "brändi", "sommittelu", "creative", "art director",
    ],
    "Tekninen/AI": [
        "ai", "tekoäly", "chatgpt", "midjourney", "python", "html",
        "css", "wordpress", "prompt", "genai",
    ],
    "Soft Skills": [
        "tiimityö", "oma-aloitteisuus", "paineensieto", "kommunikointi",
        "projektinhallinta", "analyyttinen", "koordinoi",
    ],
}

# Mahdollistaa sen, että työkalu tunnistaa samaan osaamiseen liittyviä muotoja.
# Ensimmäinen arvo on käyttöliittymässä näytettävä kanoninen avainsana.
_KEYWORD_ALIASES: dict[str, list[str]] = {
    "ai": ["ai", "tekoäly", "artificial intelligence", "generatiivinen tekoäly"],
    "prompt": ["prompt", "promptaus", "prompt engineering"],
    "video": ["video", "videotuotanto", "liikkuva kuva", "motion"],
    "editointi": ["editointi", "videoeditointi", "leikkaus", "editing"],
    "brändi": ["brändi", "brandi", "brand", "branding", "brand identity"],
    "visuaalinen": ["visuaalinen", "visual", "visual design", "graafinen"],
    "projektinhallinta": ["projektinhallinta", "project management", "koordinaatio"],
    "kommunikointi": ["kommunikointi", "viestintä", "communication"],
    "viestintä": ["viestintä", "viestinta", "communication"],
    "sisällöntuotanto": ["sisällöntuotanto", "sisallontuotanto", "content"],
    "markkinointi": ["markkinointi", "marketing", "mainonta"],
    "muotoilu": ["muotoilu", "design", "palvelumuotoilu"],
    "kuvallinen": ["kuvallinen", "kuvallisen", "visual"],
}

_EDUCATION_FACETS: dict[str, dict[str, object]] = {
    "visual_design": {
        "label": "visuaalinen suunnittelu",
        "school_terms": [
            "graafinen", "kuvallinen", "visuaalinen", "muotoilu", "design",
            "taiteet", "suunnittelu", "illustrator", "photoshop", "indesign",
        ],
        "profile_terms": [
            "graafinen", "visuaalinen", "designer", "design", "art director",
            "muotoilu", "suunnittelija", "luova ala", "graafinen suunnittelu",
        ],
        "points": 0.72,
    },
    "content_comm": {
        "label": "viestintä ja sisältö",
        "school_terms": [
            "viestintä", "viestinta", "journalismi", "sisältö", "sisalto",
            "content", "media", "mediapalvelu",
        ],
        "profile_terms": [
            "viestintä", "viestinta", "sisällöntuottaja", "sisallontuottaja",
            "content", "content manager", "digitaalinen viestintä", "media",
        ],
        "points": 0.58,
    },
    "marketing": {
        "label": "markkinointi",
        "school_terms": [
            "markkinointi", "digimarkkinointi", "mainonta", "marketing",
            "brändi", "brandi",
        ],
        "profile_terms": [
            "markkinointi", "markkinointisuunnittelija", "mainonta",
            "content manager", "brändi", "brandi",
        ],
        "points": 0.46,
    },
    "ux_service": {
        "label": "UI/UX ja palvelumuotoilu",
        "school_terms": [
            "ui", "ux", "palvelumuotoilu", "human-computer interaction",
            "käyttökokemus", "kayttokokemus",
        ],
        "profile_terms": [
            "ui", "ux", "ui/ux", "palvelumuotoilu", "käyttökokemus",
            "kayttokokemus",
        ],
        "points": 0.43,
    },
    "production_project": {
        "label": "tuotanto ja projektit",
        "school_terms": [
            "tuottaja", "tuotanto", "kulttuurituottaja", "producer",
            "projekti", "projektinhallinta",
        ],
        "profile_terms": [
            "producer", "creative producer", "projektipäällikkö",
            "projektipaallikko", "projekti", "tuottaja",
        ],
        "points": 0.37,
    },
    "video_media": {
        "label": "video ja media",
        "school_terms": [
            "video", "videotuotanto", "liikkuva kuva", "media-ala",
            "media ala", "mediatuotanto",
        ],
        "profile_terms": ["video", "video editor", "editointi", "mediatuotanto"],
        "points": 0.35,
    },
    "tech_digital": {
        "label": "digi ja teknologia",
        "school_terms": [
            "digi", "digitaalinen", "ict", "tekoäly", "tekoaly", "ai",
            "data", "html", "css", "python", "wordpress",
        ],
        "profile_terms": [
            "digi", "digitaalinen", "ict", "ai", "tekoäly", "tekoaly",
            "ui designer", "ux designer", "html", "css", "python",
        ],
        "points": 0.31,
    },
}


def _normalize(text: str | None) -> str:
    """Kevyt normalisointi luotettavampaa keyword-hakua varten."""
    if not text:
        return ""
    return text.lower().replace("\u00a0", " ")


def _contains_keyword(text: str, keyword: str) -> bool:
    """Tarkistaa avainsanan ilman, että lyhyet sanat osuvat vääriin kohtiin.

    Esim. "ai" ei saa osua sanoihin kuten "mainos" tai "paineensieto".
    Pidemmissä ja moniosaisissa termeissä substring-haku on käytännössä paras,
    koska suomi taipuu ja ilmoituksissa käytetään usein yhdyssanoja.
    """
    text_l = _normalize(text)
    kw = _normalize(keyword).strip()
    aliases = _KEYWORD_ALIASES.get(kw, [kw])

    for alias in aliases:
        alias = alias.strip().lower()
        if not alias:
            continue
        if len(alias) <= 3 and alias.isascii():
            if re.search(rf"(?<![a-zåäö]){re.escape(alias)}(?![a-zåäö])", text_l):
                return True
        elif alias in text_l:
            return True
    return False


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


_HIGHER_EDUCATION_RE = re.compile(
    r"("
    r"korkeakoulututkin\w*|korkeakoulutaust\w*|korkeakoulukoulut\w*|"
    r"amk\s*[- ]?\s*tutkin\w*|amk\s*[- ]?\s*koulut\w*|amk\s*[- ]?\s*taust\w*|"
    r"ammattikorkeakoulututkin\w*|ammattikorkeakoulukoulut\w*|ammattikorkeakoulutaust\w*|"
    r"yliopistotutkin\w*|yliopistokoulut\w*|yliopistotaust\w*|"
    r"alempi korkeakoulututkin\w*|ylempi korkeakoulututkin\w*|"
    r"tradenom\w*|medianom\w*|\bktm\b|maister\w*|kandidaat\w*|"
    r"bachelor\w*|master\w*"
    r")"
)

_FORMAL_EDUCATION_RE = re.compile(
    r"("
    r"koulutuks\w*|koulutusta\w*|tutkin\w*|perustutkin\w*|ammattitutkin\w*|"
    r"erikoisammattitutkin\w*|opinto\w*|pätevy\w*|patevy\w*|kelpoisu\w*"
    r")"
)

_GENERAL_EDUCATION_RE = re.compile(
    r"(soveltuva koulutus|soveltuva tutkinto|alan koulutus|"
    r"koulutus katsotaan eduksi|kokemus ratkaisee|portfolio ratkaisee|"
    r"näytöt ratkaisevat|naytot ratkaisevat|käytännön osaaminen|kaytannon osaaminen|"
    r"tärkeintä on käytännön osaaminen|tarkeinta on kaytannon osaaminen)"
)

_UNCLEAR_EDUCATION_RE = re.compile(
    r"(koulutusvaatimus|tutkintovaatimus|kelpoisuus|pätevyys|patevyys)"
)

_LEGAL_BLOCKING_RE = re.compile(
    r"(laillistet\w*|laillistus|pätevöity\w*|patevoit\w*|"
    r"opettajan pedagoginen pätevyys|opettajan pedagoginen patevyys|"
    r"sosiaali- ja terveysalan laillistus|pätevyysvaatimus|patevyysvaatimus)"
)

_NO_FORMAL_EDUCATION_REQUIREMENT_RE = re.compile(
    r"(ei\s+(?:edellytetä|edellyteta|vaadita|tarvita|tarvitse)\s+"
    r"(?:\w+\s+){0,5}(?:korkeakoulututkin\w*|koulutuks\w*|koulutusta\w*|tutkin\w*|pätevy\w*|patevy\w*|kelpoisu\w*)|"
    r"(?:korkeakoulututkin\w*|koulutuks\w*|koulutusta\w*|tutkin\w*)\s+ei\s+"
    r"(?:ole\s+)?(?:edellytys|vaatimus|pakollinen|välttämätön|valttamaton)|"
    r"koulutamme\s+(?:sinut|tehtävään|tehtavaan))"
)

_EDUCATION_MATCH_SCORES = {
    "low": 100,
    "medium": 70,
    "high": 35,
    "blocking": 0,
    "unknown": 50,
}


def _normalize_education_text(text: str | None) -> str:
    clean = _normalize(text)
    clean = re.sub(r"[\u2010-\u2015]", "-", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def _has_higher_education_term(text: str) -> bool:
    return bool(_HIGHER_EDUCATION_RE.search(text))


def _has_formal_education_term(text: str) -> bool:
    return bool(_FORMAL_EDUCATION_RE.search(text))


def _near_education(text: str, marker_re: str, distance: int = 90) -> bool:
    return bool(
        re.search(rf"{marker_re}.{{0,{distance}}}{_HIGHER_EDUCATION_RE.pattern}", text)
        or re.search(rf"{_HIGHER_EDUCATION_RE.pattern}.{{0,{distance}}}{marker_re}", text)
    )


def _near_formal_education(text: str, marker_re: str, distance: int = 90) -> bool:
    return bool(
        re.search(rf"{marker_re}.{{0,{distance}}}{_FORMAL_EDUCATION_RE.pattern}", text)
        or re.search(rf"{_FORMAL_EDUCATION_RE.pattern}.{{0,{distance}}}{marker_re}", text)
    )


def _explicitly_says_no_formal_education_required(text: str) -> bool:
    return bool(_NO_FORMAL_EDUCATION_REQUIREMENT_RE.search(text))


def classify_education_risk(job_text: str) -> str:
    """Luokittelee ilmoituksen muodollisen koulutusriskin käyttäjän profiilia vasten."""
    text = _normalize_education_text(job_text)
    if not text:
        return "unknown"

    blocking_marker = (
        r"(vaaditaan|kelpoisuusvaatimuksena(?: on)?|virkaan vaaditaan|"
        r"tehtävään valittavalta edellytetään|tehtavaan valittavalta edellytetaan|"
        r"ehdoton vaatimus)"
    )
    high_marker = (
        r"(edellytämme|edellytamme|edellytetään|edellytetaan|"
        r"edellytettävä|edellytettava|"
        r"tehtävä edellyttää|tehtava edellyttaa|tehtävässä edellytetään|"
        r"tehtavassa edellytetaan|sinulla on|hakijalla on|hakijalta edellytetään|"
        r"hakijalta edellytetaan|vaatimuksena(?: on)?|vaatimus|vaatimukset:?|"
        r"pakollinen|välttämätön|valttamaton)"
    )
    medium_marker = (
        r"(toivomme|katsotaan eduksi|on eduksi|eduksi katsotaan|"
        r"eduksi katsomme|katsomme eduksi|pidämme etuna|pidamme etuna|"
        r"etuna|plussaa|plussa|hyödyksi|hyodyksi|arvostamme)"
    )

    if _LEGAL_BLOCKING_RE.search(text) or _near_education(text, blocking_marker, 120):
        return "blocking"

    if _near_education(text, high_marker, 120) or _near_formal_education(text, blocking_marker, 120):
        return "high"

    if _near_formal_education(text, high_marker, 120):
        return "high"

    if _near_education(text, medium_marker, 120):
        return "medium"

    if _near_formal_education(text, medium_marker, 120):
        if _GENERAL_EDUCATION_RE.search(text) and not _has_higher_education_term(text):
            return "low"
        return "medium"

    if _has_higher_education_term(text):
        if _explicitly_says_no_formal_education_required(text):
            return "low"
        return "high"

    if _UNCLEAR_EDUCATION_RE.search(text) and not _GENERAL_EDUCATION_RE.search(text):
        return "unknown"

    return "low"


def education_risk_reason(job_text: str, risk: str, user_education: dict | None = None) -> str:
    """Palauttaa lyhyen perustelun, joka erottaa osaamisen ja muodollisen koulutuksen."""
    education = user_education or USER_EDUCATION
    degree = str(education.get("degree") or "").strip()
    level = str(education.get("level") or "").strip()
    if degree:
        user_background = (
            f"Käyttäjän tutkinto on {degree}"
            f"{f' ({level})' if level else ''}."
        )
    else:
        user_background = "Demoversiossa käyttäjän koulutustaustaa ei ole asetettu."

    if risk == "blocking":
        return (
            "Ilmoituksessa vaikuttaa olevan ehdoton tutkinto-, kelpoisuus- tai "
            f"pätevyysvaatimus. {user_background}"
        )
    if risk == "high":
        text = _normalize_education_text(job_text)
        if _has_higher_education_term(text):
            return (
                "Ilmoitus näyttää vaativan soveltuvaa korkeakoulututkintoa. "
                f"{user_background}"
            )
        return (
            "Ilmoitus näyttää vaativan muodollista koulutusta tai tutkintoa, "
            "mutta vaatimuksen tarkka taso tai ala pitää tarkistaa ilmoituksesta. "
            f"{user_background}"
        )
    if risk == "medium":
        text = _normalize_education_text(job_text)
        if _has_higher_education_term(text):
            return (
                "Korkeakoulututkinto mainitaan toiveena, etuna tai plussana, "
                f"mutta ei selvästi ehdottomana vaatimuksena. {user_background}"
            )
        return (
            "Muodollinen koulutus tai tutkinto mainitaan toiveena, etuna tai plussana, "
            f"mutta ei selvästi ehdottomana vaatimuksena. {user_background}"
        )
    if risk == "unknown":
        return (
            "Ilmoituksen koulutusvaatimusta ei voi tulkita luotettavasti tekstistä. "
            f"{user_background}"
        )
    return (
        "Ilmoituksesta ei löydy tehtävään vaadittua muodollista koulutusta "
        "tai korkeakoulututkintoa; koulutus mainitaan enintään yleisesti."
    )


def recommendation_for_education_risk(risk: str) -> str:
    if risk == "blocking":
        return "do_not_recommend"
    if risk == "high":
        return "high_risk"
    if risk == "medium":
        return "possible_but_note_risk"
    if risk == "unknown":
        return "manual_review_needed"
    return "recommend_if_skill_match_is_good"


def calculate_match_analysis(
    job_text: str,
    skill_match_score: int | float,
    user_education: dict | None = None,
) -> dict[str, object]:
    """Yhdistää osaamisosuman ja erillisen koulutusriskin kokonaisarvioksi."""
    try:
        skill_score = int(round(float(skill_match_score)))
    except (TypeError, ValueError):
        skill_score = 0
    skill_score = max(0, min(skill_score, 100))

    risk = classify_education_risk(job_text)
    education_score = _EDUCATION_MATCH_SCORES.get(risk, _EDUCATION_MATCH_SCORES["unknown"])
    base_overall = int(round((skill_score * 0.8) + (education_score * 0.2)))
    recommendation = recommendation_for_education_risk(risk)

    if risk == "blocking":
        overall = min(base_overall, 45)
    elif risk == "high":
        overall = min(base_overall, 65)
    elif risk == "medium":
        overall = min(base_overall, 80)
    elif risk == "unknown":
        overall = min(base_overall, 70)
    else:
        overall = skill_score

    return {
        "education_risk": risk,
        "education_risk_reason": education_risk_reason(job_text, risk, user_education),
        "skill_match_score": skill_score,
        "education_match_score": education_score,
        "overall_match_score": overall,
        "recommendation_level": recommendation,
    }


def _profile_text() -> str:
    """Kokoaa asetuksista käyttäjän suuntaa kuvaavan tekstin pisteytystä varten."""
    return " ".join(settings_manager.get_target_roles() + settings_manager.get_search_keywords())


def _profile_facet_weight(profile_text: str, terms: list[str]) -> float:
    """Painottaa koulutusosumia sen mukaan, näkyykö sama suunta omissa tavoitteissa."""
    hits = sum(1 for term in terms if _contains_keyword(profile_text, term))
    if hits == 0:
        return 0.35
    return min(1.0 + hits * 0.16, 1.8)


def _education_text(name: str, status: str = "", url: str = "") -> str:
    url_words = re.sub(r"[/_.:%?=&\-]+", " ", url or "")
    return _normalize(f"{name} {status} {url_words}")


def calculate_education_score_details(
    name: str, status: str = "", url: str = ""
) -> tuple[float, list[str]]:
    """Laskee koulutussuosituksen sopivuuden käyttäjän omiin tavoitteisiin.

    Työpaikkojen pisteytys toimii huonosti kouluille, koska koulutuksissa ei ole
    varsinaista ilmoitustekstiä. Tämä laskuri tulkitsee koulun nimen, statuksen
    ja URL-polun koulutusalaksi ja vertaa sitä asetusten tavoiterooleihin sekä
    hakusanoihin. Palauttaa pisteen lisäksi lyhyet perustelut käyttöliittymään.
    """
    text = _education_text(name, status, url)
    profile = _normalize(_profile_text())
    score = 1.15
    reasons: list[str] = []
    matched_core_facets: set[str] = set()

    for facet_key, facet in _EDUCATION_FACETS.items():
        school_terms = facet["school_terms"]
        profile_terms = facet["profile_terms"]
        if not isinstance(school_terms, list) or not isinstance(profile_terms, list):
            continue

        hits = [term for term in school_terms if _contains_keyword(text, term)]
        if not hits:
            continue

        base_points = float(facet["points"])
        profile_weight = _profile_facet_weight(profile, profile_terms)
        # Ensimmäinen osuma kertoo suunnan, lisäosumat vahvistavat mutta eivät räjäytä pisteitä.
        score += base_points * profile_weight
        score += min((len(hits) - 1) * 0.08, 0.24)
        label = str(facet["label"])
        reasons.append(label)
        matched_core_facets.add(facet_key)

    status_l = _normalize(status)
    name_l = _normalize(name)
    url_l = _normalize(url)

    if any(term in text for term in ("taiteet", "taiteiden")) and _contains_keyword(text, "suunnittelu"):
        score += 0.82
        reasons.append("laaja luova koulutus")
    if _contains_keyword(text, "graafinen") and _contains_keyword(text, "kuvallinen"):
        score += 0.68
        reasons.append("vahva portfolio-osuma")
    if _contains_keyword(text, "viestintä") and _contains_keyword(text, "muotoilu"):
        score += 0.48
        reasons.append("monialainen luova suunta")
    if _contains_keyword(text, "media") and _contains_keyword(text, "kuvallinen"):
        score += 0.42
        reasons.append("media ja kuvallinen ilmaisu")
    if _contains_keyword(name_l, "digimarkkinointi"):
        score += 0.38
        reasons.append("suora markkinointiosuma")
    if _contains_keyword(name_l, "kulttuurituottaja"):
        score += 0.42
        reasons.append("producer-suunta")

    if any(term in status_l or term in name_l for term in ("huippu", "aalto-yliopisto")):
        score += 0.42
        reasons.append("vahva brändi")
    if "portfolio" in status_l:
        score += 0.32
        reasons.append("portfolioon sopiva")
    if "jatkuva haku" in status_l:
        score += 0.30
        reasons.append("jatkuva haku")
    if any(term in status_l for term in ("erikoistuminen", "aikuis")):
        score += 0.24
        reasons.append("joustava lisäkoulutus")
    if any(term in status_l for term in ("amk", "haku")):
        score += 0.20
        reasons.append("tutkintopolku")
    if any(term in url_l for term in ("verkko", "eta", "etä", "osatutkinto", "tutkinnon-osa")):
        score += 0.22
        reasons.append("joustava toteutus")
    if any(city in f"{status_l} {url_l}" for city in ("helsinki", "hki", "espoo", "vantaa")):
        score += 0.16
        reasons.append("pääkaupunkiseutu")

    creative_facets = {
        "visual_design", "content_comm", "marketing", "ux_service",
        "video_media", "production_project",
    }
    if not matched_core_facets & creative_facets:
        score -= 0.35
        reasons.append("vähemmän luova-alapainotusta")
    elif matched_core_facets == {"tech_digital"}:
        score = min(score, 3.2)

    if any(term in text for term in ("osatutkinto", "tutkinnon osa", "erikoistuminen", "aikuis")):
        score = min(score, 4.6)

    score = round(max(1.0, min(score, 5.0)), 1)
    return score, _dedupe_preserve_order(reasons)[:4]


def calculate_education_score(name: str, status: str = "", url: str = "") -> float:
    """Palauttaa koulutussuosituksen pisteen asteikolla 1.0–5.0."""
    score, _reasons = calculate_education_score_details(name, status, url)
    return score


def local_text_analysis(text: str) -> tuple[dict[str, int], int, list[str]]:
    """Paikallinen deterministic keyword-analyysi tekstille.

    Palauttaa:
    - kategoriakohtaiset löydöt
    - kokonaispisteet max 10
    - puuttuvat sanat deterministisesti, ei satunnaisesti
    """
    found_stats: dict[str, int] = {}
    missing_words: list[str] = []
    total_score = 0

    for category, words in _KEYWORD_CATEGORIES.items():
        count = 0
        for word in words:
            if _contains_keyword(text, word):
                count += 1
                total_score += 1
            else:
                missing_words.append(word)
        found_stats[category] = count

    return found_stats, min(total_score, 10), _dedupe_preserve_order(missing_words)[:10]


def calculate_score(title: str, location: str, description: str = "") -> float:
    """Laskee ilmoituksen alustavan kiinnostavuus-/match-scoren asteikolla 1.0–5.0.

    Huom: tämä ei ole lopullinen CV-vastaavuus, vaan työpaikkailmoituksen
    karkea sopivuus käyttäjän tavoiterooleihin, sijaintiin ja osaamistermeihin.
    CV-kohtainen sopivuus kannattaa ankkuroida quick_keyword_match()-tulokseen
    ja score_to_percent()-apufunktioon.
    """
    score = 1.0
    title_l = _normalize(title)
    location_l = _normalize(location)
    desc_l = _normalize(description)

    target_roles = settings_manager.get_target_roles()
    role_hits_title = sum(1 for role in target_roles if _contains_keyword(title_l, role))
    role_hits_desc = sum(1 for role in target_roles if _contains_keyword(desc_l, role))

    score += min(role_hits_title * 0.6, 2.0)
    score += min(role_hits_desc * 0.25, 1.0)

    if any(x in title_l for x in ("strateg", "lead", "head", "päällikkö", "manager")):
        score += 0.6

    all_keywords = ["ai", "genai", "technolog", "chatgpt", "midjourney"] + UNI_KEYWORDS + AMK_KEYWORDS
    if any(_contains_keyword(title_l, kw) for kw in all_keywords):
        score += 0.8
    elif any(_contains_keyword(desc_l, kw) for kw in all_keywords):
        score += 0.5

    if any(city in location_l for city in ("helsinki", "espoo", "vantaa")):
        score += 0.8
    elif any(remote in location_l for remote in ("remote", "etä", "hybridi", "hybrid")):
        score += 0.7

    return round(min(score, 5.0), 1)


def quick_keyword_match(job_text: str, cv_text: str) -> tuple[int, int, int, list[str]]:
    """Vertaa ilmoituksen vaatimia avainsanoja CV:n tekstiin.

    Palauttaa:
    - prosentti 0–100
    - osumien määrä
    - ilmoituksesta löydettyjen relevanttien avainsanojen määrä
    - CV:stä puuttuvat avainsanat max 5
    """
    quick_kw: dict[str, list[str]] = {
        "Luova": [
            "photoshop", "illustrator", "indesign", "figma", "video", "editointi",
            "visuaalinen", "creative", "brändi", "graafinen", "adobe", "canva",
        ],
        "Tekninen/AI": [
            "ai", "tekoäly", "chatgpt", "python", "html", "css", "genai",
            "wordpress", "prompt",
        ],
        "Soft Skills": [
            "tiimityö", "projektinhallinta", "kommunikointi", "analyyttinen",
            "oma-aloitteisuus", "koordinoi",
        ],
    }

    all_keywords = [w for words in quick_kw.values() for w in words]
    job_keywords = _dedupe_preserve_order([w for w in all_keywords if _contains_keyword(job_text, w)])

    matched = [w for w in job_keywords if _contains_keyword(cv_text, w)]
    missing = [w for w in job_keywords if w not in matched]

    pct = int(round(len(matched) / len(job_keywords) * 100)) if job_keywords else 0
    return pct, len(matched), len(job_keywords), missing[:5]


def score_to_percent(match_score: float) -> int:
    """Muuntaa 1.0–5.0 Match Scoren prosentiksi ilman AI:n tulkintaa.

    Esim. 3.0/5.0 => 60 %. Tätä lukua kannattaa näyttää käyttöliittymässä
    ja antaa AI:lle vain selitettäväksi, ei uudelleen arvioitavaksi.
    """
    try:
        score = float(match_score)
    except (TypeError, ValueError):
        score = 1.0
    score = max(1.0, min(score, 5.0))
    return int(round((score / 5.0) * 100))


def ai_score_guardrail_prompt(match_score: float, keyword_pct: int, missing_keywords: list[str]) -> str:
    """Prompt-pala, joka estää AI:ta hallusinoimasta omaa sopivuusprosenttia."""
    calculated_percent = score_to_percent(match_score)
    missing = ", ".join(missing_keywords) if missing_keywords else "ei keskeisiä puuttuvia avainsanoja"
    return f"""
TÄRKEÄ ARVIOINTISÄÄNTÖ:
- Älä keksi omaa yhteensopivuusprosenttia.
- Käytä vain laskettua Match Scorea: {match_score}/5.0 = {calculated_percent} %.
- Avainsanaosumat ovat {keyword_pct} %.
- Puuttuvat avainsanat: {missing}.
- Jos kirjoitat yhteensopivuudesta, käytä lukua {calculated_percent} % tai sanallista arviota, joka vastaa tätä tasoa.
- Älä nosta arviota yli {min(calculated_percent + 10, 100)} %, ellei käyttäjän oma laskettu analytiikka sitä tue.
- AI:n tehtävä on selittää laskettu tulos, ei korvata sitä omalla optimistisella arviolla.
""".strip()
