"""
ui/tabs.py — Kaikki välilehdet yhdessä tiedostossa.
Jokainen välilehti on oma funktionsa: render_tab_X().
PÄIVITETTY: Työnhakuvelvoite lukee dynaamisen tavoitteen (2 tai 4) sivupalkin valinnasta.
"""
from __future__ import annotations
import datetime
import html
import json
import urllib.parse

import pandas as pd
import streamlit as st

from config import (
    USER_NAME, SHEET_ID, VISITOR_DATA_ENABLED,
    STATUS_COLORS, ALL_STATUSES,
    MONTHLY_QUOTA, KELA_CYCLE_DAYS,
    AGENT_SILENCE_THRESHOLD, INTERVIEW_WARNING_DAYS,
    USER_EDUCATION,
)
import settings_manager
from models import TrackedItem, KelaData
from storage import save_tracked_items, save_kela_data
from sheets import load_visitor_data
from router import call_ai, repair_text_encoding, stream_ai
from dates import deadline_badge, days_since, days_until, parse_date
from scoring import (
    calculate_education_score_details, calculate_score, local_text_analysis,
    quick_keyword_match, calculate_match_analysis,
)
from links import check_school_application_status


def _safe_text(value, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _rows_to_links(rows: list[dict]) -> dict[str, str]:
    return {
        _safe_text(row.get("name")): _safe_text(row.get("url"))
        for row in rows
        if _safe_text(row.get("name")) and _safe_text(row.get("url"))
    }


def _portfolio_url() -> str:
    return settings_manager.get_portfolio_url() or "#"


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — HAKEMUSGENERAATTORI
# ─────────────────────────────────────────────────────────────────────────────

def render_tab_application(active_key: str) -> None:
    st.header("📝 Hakemusgeneraattori")
    c1, c2 = st.columns(2)
    with c1:
        company  = st.text_input("Yrityksen nimi:")
        role     = st.text_input("Haettava rooli:")
        job_desc = st.text_area("Liitä työpaikkailmoitus tähän:", height=250)
    with c2:
        user_cv  = st.text_area("Oma tausta / CV tiivistelmä:", height=380)

    if not st.button("🚀 LUO HAKEMUS", type="primary"):
        return
    if not job_desc or not user_cv:
        st.warning("Täytä ainakin ilmoitus ja oma tausta.")
        return

    if active_key:
        engine = st.session_state.get("ai_engine", "Demo (simuloitu API)")
        prompt = (
            f"Kirjoita ammattimainen, vakuuttava ja persoonallinen työhakemus.\n"
            f"Yritys: {company}\nRooli: {role}\n"
            f"Ilmoitus: {job_desc}\nOma tausta: {user_cv}\n"
            f"Tyyli: Moderni, ei kapulakieltä. Käytä selkeää rakennetta ja lyhyitä kappaleita."
        )
        st.subheader(f"✨ Valmis hakemus ({engine}):")
        result = st.write_stream(stream_ai(prompt))
        if result:
            st.download_button("💾 Lataa .txt", result, "hakemus.txt")
    else:
        with st.spinner("Luodaan hakemuspohja ilman tekoälyä…"):
            draft = _generate_template_application(company, role, job_desc, user_cv)
        st.subheader("📄 Hakemuspohja (Local Mode):")
        st.info("💡 AI ei ole käytössä — tässä on paikallinen pohja, jonka voit viimeistellä.")
        st.text_area("", value=draft, height=600)


def _generate_template_application(
    company: str, role: str, job_text: str, user_background: str
) -> str:
    date_str   = datetime.datetime.now().strftime("%d.%m.%Y")
    highlights = []
    if "ai" in job_text.lower():         highlights.append("tekoälyosaamiseni")
    if "visuaalinen" in job_text.lower():highlights.append("visuaalisen silmäni")
    if "projekti" in job_text.lower():   highlights.append("kokemukseni projektinhallinnasta")
    highlight_text = " sekä ".join(highlights) if highlights else "monipuolisen osaamiseni"

    return f"""
{USER_NAME}
Helsinki | {date_str}

Vastaanottaja: Rekrytointitiimi / {company or '[YRITYS]'}

HAKEMUS: {(role or '[ROOLI]').upper()}

Hei,

Luin innostuneena ilmoituksenne, jossa haette {role or '[ROOLI]'}-osaajaa.
Seuraan aktiivisesti {company or '[YRITYS]'}:n toimintaa ja uskon, että taustani
toisi tiimiinne juuri oikeanlaista lisäarvoa.

MIKSI MINÄ?
Olen luovan alan ammattilainen, joka yhdistää visuaalisen suunnittelun ja
modernit teknologiat.

Omaan vahvan taustan, johon kuuluu:
- {user_background[:150]}… (Täydennä CV:stäsi)
- Kyky hyödyntää tekoälyä luovassa prosessissa
- Halu oppia uutta ja kehittää prosesseja

MITÄ TUON TALOON?
Uskon, että voisin hyödyntää {highlight_text} heti ensimmäisestä päivästä alkaen.

Odotan innolla mahdollisuutta kertoa lisää osaamisestani haastattelussa.

Ystävällisin terveisin,
{USER_NAME}
Portfolio: {settings_manager.get_portfolio_url()}
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — ANALYSAATTORI
# ─────────────────────────────────────────────────────────────────────────────

def render_tab_analyze(active_key: str) -> None:
    st.header("📊 CV & Ilmoitus -analysaattori")
    st.markdown("Liitä sekä **CV** ja **työpaikkailmoitus** — analysaattori vertaa niitä.")

    c1, c2 = st.columns(2)
    with c1:
        title    = st.text_input("Työnimike")
        location = st.text_input("Sijainti")
        job_desc = st.text_area("📋 Työpaikkailmoitus:", height=280,
                                placeholder="Kopioi koko ilmoitusteksti tähän…")
    with c2:
        cv_text  = st.text_area("👤 Oma CV / tausta:", height=340,
                                placeholder="Kopioi CV:si tai tiivis kuvaus osaamisestasi tähän…")

    if not st.button("🔍 ANALYSOI", type="primary"):
        return
    if not job_desc:
        st.warning("⚠️ Liitä ensin työpaikkailmoitus.")
        return

    score = calculate_score(title, location, job_desc)

    if active_key:
        _ai_analysis(title, location, job_desc, cv_text, score)
    else:
        _local_analysis(job_desc, cv_text, score)
        st.info("💡 Tarkemman AI-analyysin saat kytkemällä API-avaimen sivupalkista.")


def _ai_analysis(title: str, location: str, job_desc: str, cv_text: str, match_score: float) -> None:
    engine = st.session_state.get("ai_engine", "Demo (simuloitu API)")

    # Pikayhteensopivuus heti ennen API-kutsua.
    # Tätä käytetään myös AI-promptin ankkurina, jotta malli ei keksi omaa sopivuusprosenttia.
    keyword_pct = 0
    matched = 0
    total = 0
    missing: list[str] = []

    if cv_text:
        keyword_pct, matched, total, missing = quick_keyword_match(job_desc, cv_text)
        qc1, qc2, qc3 = st.columns(3)
        qc1.metric("🎯 Avainsanat", f"{keyword_pct}%")
        qc2.metric("✅ Osumia", f"{matched}/{total}")
        qc3.metric("⚠️ Puuttuu CV:stä", len(missing))
        if missing:
            st.caption(f"Harkitse näitä: {', '.join(missing)}")
        st.markdown("---")

    skill_pct = _combined_fit_percent(match_score, keyword_pct) if cv_text else _score_to_percent(match_score)
    analysis = calculate_match_analysis(job_desc, skill_pct)
    _render_match_summary(analysis)
    st.markdown("---")

    prompt = (
        _cv_vs_job_prompt(
            cv=cv_text,
            title=title,
            loc=location,
            job=job_desc,
            match_score=match_score,
            keyword_pct=keyword_pct,
            matched=matched,
            total=total,
            missing=missing,
            analysis=analysis,
        ) if cv_text
        else _job_only_prompt(title, location, job_desc, analysis)
    )
    st.markdown(f"### 🤖 AI-analyysi ({engine}):")
    result = st.write_stream(stream_ai(prompt))

    if result and _looks_like_cut_off(str(result)):
        st.warning(
            "AI-analyysi saattaa olla katkennut kesken. "
            "Nosta LM Studion contextia / max_tokens-arvoa tai aja analyysi uudelleen."
        )


def _score_to_percent(match_score: float) -> int:
    """Muuntaa 0–5 Match Score -arvon prosentiksi ilman AI:n omaa tulkintaa."""
    try:
        score = float(match_score)
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(score, 5.0))
    return round((score / 5.0) * 100)


def _combined_fit_percent(match_score: float, keyword_pct: int) -> int:
    """
    Yhdistetty sopivuusprosentti CV-analyysiin.
    Match Score kertoo ilmoituksen yleisen osuvuuden, avainsanaprosentti CV:n ja ilmoituksen päällekkäisyyden.
    Painotus pidetään konservatiivisena, jotta AI ei nosta arviota epärealistisesti.
    """
    base_pct = _score_to_percent(match_score)
    if keyword_pct <= 0:
        return base_pct
    return round((base_pct * 0.4) + (keyword_pct * 0.6))


_EDUCATION_RISK_LABELS = {
    "low": "matala",
    "medium": "kohtalainen",
    "high": "korkea",
    "blocking": "todennäköisesti hylkäävä",
    "unknown": "epäselvä",
}

_RECOMMENDATION_LABELS = {
    "do_not_recommend": "ei ensisijaiseksi",
    "high_risk": "korkean riskin haku",
    "possible_but_note_risk": "mahdollinen, huomioi riski",
    "recommend_if_skill_match_is_good": "suositeltava osaamisosumalla",
    "manual_review_needed": "vaatii käsintarkistuksen",
}


def _risk_label(risk: object) -> str:
    return _EDUCATION_RISK_LABELS.get(str(risk), str(risk))


def _recommendation_label(level: object) -> str:
    return _RECOMMENDATION_LABELS.get(str(level), str(level))


def _render_match_summary(analysis: dict[str, object]) -> None:
    skill = int(analysis.get("skill_match_score", 0))
    education = int(analysis.get("education_match_score", 0))
    overall = int(analysis.get("overall_match_score", 0))
    risk = str(analysis.get("education_risk", "unknown"))
    recommendation = str(analysis.get("recommendation_level", "manual_review_needed"))

    st.markdown("### Kokonaisarvio")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sisällöllinen sopivuus", f"{skill} %")
    c2.metric("Koulutusriski", _risk_label(risk))
    c3.metric("Kokonaisarvio", f"{overall} %")
    c4.metric("Suositus", _recommendation_label(recommendation))
    st.progress(overall / 100)
    st.caption(
        f"Muodollisen koulutuksen osuma: {education} %. "
        f"{analysis.get('education_risk_reason', '')}"
    )
    _render_education_risk_warning(risk)


def _render_education_risk_warning(risk: str) -> None:
    if risk == "high":
        st.warning(
            "⚠️ Koulutusriski: korkea. Tämä työpaikka voi vaatia korkeakoulututkintoa "
            "tai muuta muodollista koulutusta/tutkintoa. Käyttäjällä on datanomin "
            "tutkinto, joka ei ole korkeakoulututkinto. Hakeminen voi silti olla mahdollista, "
            "jos vaatimus täyttyy tai ei ole ehdoton, "
            "mutta paikkaa ei pidä laskea matalan riskin hakukohteeksi."
        )
    elif risk == "blocking":
        st.error(
            "⛔ Todennäköisesti hylkäävä koulutusvaatimus. Ilmoituksessa vaikuttaa "
            "olevan ehdoton tutkinto-, kelpoisuus- tai pätevyysvaatimus, jota "
            "käyttäjän nykyinen koulutustausta ei täytä."
        )
    elif risk == "medium":
        st.info(
            "Koulutusriski on kohtalainen: koulutus tai tutkinto mainitaan etuna "
            "tai toiveena, mutta sitä ei tulkittu ehdottomaksi vaatimukseksi."
        )
    elif risk == "unknown":
        st.warning("Koulutusvaatimus jäi epäselväksi. Tarkista ilmoitus käsin ennen hakupäätöstä.")


def _analysis_prompt_block(analysis: dict[str, object]) -> str:
    user_education = json.dumps(USER_EDUCATION, ensure_ascii=False, indent=2)
    return (
        f"KÄYTTÄJÄN KOULUTUSTAUSTA:\nUSER_EDUCATION = {user_education}\n\n"
        f"Tarkista työpaikkailmoituksen koulutusvaatimus erikseen. Käyttäjän datanomin "
        f"tutkintoa ei saa tulkita korkeakoulututkinnoksi. Jos ilmoitus edellyttää "
        f"ylipäätään muodollista koulutusta tai tutkintoa, huomioi se erillisenä "
        f"koulutusvaatimuksena. Jos ilmoitus edellyttää AMK-, "
        f"yliopisto-, tradenomi-, medianomi-, KTM- tai muuta korkeakoulututkintoa, merkitse "
        f"koulutusriski vähintään high-tasolle. Jos vaatimus on ehdoton, kelpoisuusehto tai "
        f"lakisääteinen pätevyysvaatimus, merkitse education_risk = blocking. Käytännön osaaminen, "
        f"portfolio, tekoälyprojektit, markkinointiosaaminen tai automaatiojärjestelmä voivat "
        f"parantaa skill_match_scorea, mutta ne eivät saa poistaa muodollista koulutusriskiä.\n\n"
        f"LASKETTU ANALYYSIOBJEKTI, jota sinun pitää käyttää:\n"
        f"- education_risk: {analysis['education_risk']}\n"
        f"- education_risk_reason: {analysis['education_risk_reason']}\n"
        f"- skill_match_score: {analysis['skill_match_score']}\n"
        f"- education_match_score: {analysis['education_match_score']}\n"
        f"- overall_match_score: {analysis['overall_match_score']}\n"
        f"- recommendation_level: {analysis['recommendation_level']}\n"
    )


def _looks_like_cut_off(text: str) -> bool:
    """Tunnistaa vain aidosti keskeneräisen mallivastauksen.

    Aiempi versio antoi helposti väärän varoituksen, koska Gemma voi päättää
    vastauksen numeroituun listaan ilman pistettä tai jättää loppumerkin pois.
    Jos viimeinen suunniteltu osio on mukana, hyväksytään analyysi valmiiksi.
    """
    clean = (text or "").strip()
    if not clean:
        return True

    # Ensisijainen onnistumisen merkki, jos malli noudattaa promptia.
    if "ANALYYSI_VALMIS" in clean:
        return False

    # Käytännön onnistumisen merkki: viimeinen suunniteltu osio on mukana.
    # Tämä estää turhan varoituksen kuvassasi näkyvässä tilanteessa.
    completion_markers = (
        "7. Avainsanat hakemukseen",
        "7. **Avainsanat hakemukseen**",
        "6. Avainsanat hakemukseen",
        "6. **Avainsanat hakemukseen**",
        "Avainsanat hakemukseen",
    )
    if any(marker in clean for marker in completion_markers):
        return False

    # Selvästi katkenneet otsikot / puolikkaat otsikot.
    suspicious_endings = (
        "1.", "2.", "3.", "4.", "5.", "6.", "7.",
        "3. Kehity", "3. Kehityskoh", "Kehity", "Kehityskoh",
        "4. Riski", "Riskiarvio",
        "5. Suosit", "Suosit",
        "6. Avainsanat", "7. Avainsanat", "Avainsanat",
    )
    if clean.endswith(suspicious_endings):
        return True

    # Jos vastaus päättyy selvästi kesken lauseen, varoitetaan.
    if clean[-1] not in (".", "!", "?", ")", ":", "”", "\"", "*", "`"):
        return True

    return False


def _cv_vs_job_prompt(
    cv: str,
    title: str,
    loc: str,
    job: str,
    match_score: float,
    keyword_pct: int,
    matched: int,
    total: int,
    missing: list[str],
    analysis: dict[str, object],
) -> str:
    match_pct = _score_to_percent(match_score)
    missing_text = ", ".join(missing) if missing else "Ei selkeitä puuttuvia avainsanoja."
    analysis_rules = _analysis_prompt_block(analysis)
    risk = str(analysis["education_risk"])
    risk_label = _risk_label(risk)
    recommendation = _recommendation_label(analysis["recommendation_level"])
    overall = int(analysis["overall_match_score"])
    skill = int(analysis["skill_match_score"])

    return (
        f"Olet tarkka ja kriittinen rekrytointianalyytikko. Vertaa hakijan CV:tä ja työpaikkailmoitusta.\n\n"
        f"TÄRKEÄ NUMEERINEN ANKKURI — ÄLÄ OHITA TÄTÄ:\n"
        f"- Laskettu Match Score on {match_score}/5.0 eli noin {match_pct} %.\n"
        f"- CV:n ja ilmoituksen avainsanayhteensopivuus on {keyword_pct} % ({matched}/{total}).\n"
        f"- Sisällöllinen sopivuus tähän analyysiin on {skill} %.\n"
        f"- Koulutusriskillä korjattu kokonaisarvio on {overall} %.\n"
        f"- Puuttuvat avainsanat / taidot: {missing_text}\n\n"
        f"{analysis_rules}\n"
        f"SÄÄNNÖT:\n"
        f"1. Älä keksi omaa yhteensopivuusprosenttia. Käytä sisällöllisenä sopivuutena arvoa {skill} %.\n"
        f"2. Älä nosta kokonaisarviota yli {overall} %, koska koulutusriski on {risk}.\n"
        f"3. Jos mainitset prosentin, erota aina sisällöllinen sopivuus {skill} % ja kokonaisarvio {overall} %.\n"
        f"4. Jos avainsanoja puuttuu, käsittele ne kehityskohteina äläkä peitä niitä kehuilla.\n"
        f"5. Arvioi näyttöä CV:stä, älä hakijan potentiaalia irrallaan ilmoituksen vaatimuksista.\n"
        f"6. Jos osaaminen sopii mutta koulutusriski on high tai blocking, sano se suoraan.\n\n"
        f"CV / Tausta:\n{cv}\n\n"
        f"Työpaikkailmoitus ({title}, {loc}):\n{job}\n\n"
        f"Rakenne:\n"
        f"1. **Sisällöllinen sopivuus: {skill} %** – selitä osaamisosuma CV:n perusteella\n"
        f"2. **Koulutusriski: {risk_label}** – käytä arvoa education_risk = {risk}\n"
        f"3. **Kokonaisarvio: {overall} %** – selitä miksi koulutusriski laskee tai ei laske arviota\n"
        f"4. **Suositus: {recommendation}** – käytä arvoa recommendation_level = {analysis['recommendation_level']}\n"
        f"5. **Perustelu** – yhdistä osaaminen ja muodollinen koulutusvaatimus samassa kappaleessa\n"
        f"6. **Kehityskohteet** – 3 konkreettista puuttuvaa tai epäselvää taitoa\n"
        f"7. **Avainsanat hakemukseen** – 5 avainsanaa, jotka perustuvat ilmoitukseen\n"
        f"\nPäätä vastaus täsmälleen rivillä: ANALYYSI_VALMIS"
    )


def _job_only_prompt(title: str, loc: str, job: str, analysis: dict[str, object]) -> str:
    analysis_rules = _analysis_prompt_block(analysis)
    risk = str(analysis["education_risk"])
    risk_label = _risk_label(risk)
    recommendation = _recommendation_label(analysis["recommendation_level"])
    return (
        f"Analysoi tämä työpaikkailmoitus (luova/AI tausta hakijalla).\n"
        f"Työnimike: {title}, Sijainti: {loc}\n\nIlmoitus:\n{job}\n\n"
        f"{analysis_rules}\n"
        f"1. **3 tärkeintä vaadittua taitoa**\n"
        f"2. **Koulutusriski: {risk_label}** – käytä arvoa education_risk = {risk}\n"
        f"3. **Kokonaisarvio: {analysis['overall_match_score']} %**\n"
        f"4. **Suositus: {recommendation}**\n"
        f"5. **Avainsanat** joita hakemuksessa kannattaa käyttää\n"
        f"6. **Vinkki**: Miten erottua muista hakijoista?\n"
        f"\nPäätä vastaus täsmälleen rivillä: ANALYYSI_VALMIS"
    )


def _local_analysis(job_desc: str, cv_text: str, match_score: float) -> None:
    st.markdown("### 📊 Paikallinen analyysi (ilman API-avainta):")
    keyword_pct = 0
    if cv_text:
        keyword_pct, _matched, _total, _missing = quick_keyword_match(job_desc, cv_text)

    skill_pct = _combined_fit_percent(match_score, keyword_pct) if cv_text else _score_to_percent(match_score)
    analysis = calculate_match_analysis(job_desc, skill_pct)
    _render_match_summary(analysis)
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📋 Ilmoituksen avainsanat:**")
        stats_job, _, _ = local_text_analysis(job_desc)
        st.json(stats_job)
    with c2:
        if cv_text:
            st.markdown("**👤 CV:n avainsanat:**")
            stats_cv, _, missing_cv = local_text_analysis(cv_text)
            st.json(stats_cv)
        else:
            st.info("Liitä CV saadaksesi vertailun.")
            return

    st.markdown("---")
    st.markdown("### 🔍 Vertailu: CV vs Ilmoitus")
    _render_keyword_comparison_table(job_desc, cv_text)


def _render_keyword_comparison_table(job_desc: str, cv_text: str) -> None:
    categories: dict[str, list[str]] = {
        "Luova": [
            "photoshop", "illustrator", "indesign", "figma", "video",
            "editointi", "visuaalinen", "brändi", "sommittelu", "creative",
        ],
        "Tekninen/AI": [
            "ai ", "tekoäly", "chatgpt", "midjourney", "python",
            "html", "css", "wordpress", "genai",
        ],
        "Soft Skills": [
            "tiimityö", "oma-aloitteisuus", "paineensieto", "kommunikointi",
            "projektinhallinta", "analyyttinen", "koordinoi",
        ],
    }
    job_l, cv_l = job_desc.lower(), cv_text.lower()
    rows = []
    for category, words in categories.items():
        job_hits     = [w for w in words if w in job_l]
        cv_hits      = [w for w in words if w in cv_l]
        missing_cv   = [w for w in job_hits if w not in cv_l]
        rows.append({
            "Kategoria": category,
            "Ilmoituksessa": len(job_hits),
            "CV:ssä": len(cv_hits),
            "Puuttuu CV:stä": ", ".join(missing_cv) if missing_cv else "–",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    all_job_words = [w for ws in categories.values() for w in ws if w in job_l]
    matched = [w for w in all_job_words if w in cv_l]
    pct = int(len(matched) / len(all_job_words) * 100) if all_job_words else 0
    st.metric("📈 Avainsanayhteensopivuus", f"{pct}%")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — LINKIT
# ─────────────────────────────────────────────────────────────────────────────

def render_tab_links() -> None:
    st.header("🏢 Linkkikirjasto")

    with st.expander("Mainostoimistot", expanded=True):
        cols = st.columns(3)
        for i, agency in enumerate(settings_manager.get_agencies()):
            name = _safe_text(agency.get("name"))
            url = _safe_text(agency.get("url"), "#")
            if not name:
                continue
            logo = settings_manager.agency_logo(agency)
            fallback = settings_manager.agency_logo_fallback(agency)
            logo_class = settings_manager.agency_logo_class(agency)
            with cols[i % 3]:
                st.markdown(
                    f'<a href="{url}" target="_blank" class="link-btn">'
                    f'<span class="link-logo"><img class="{logo_class}" src="{logo}" alt="" '
                    f'onerror="this.onerror=null;this.src=\'{fallback}\';"></span>{name}</a>',
                    unsafe_allow_html=True,
                )

    c1, c2, c3 = st.columns(3)
    _render_link_column(c1, "🌍 Intl", settings_manager.get_sites_intl())
    _render_link_column(c2, "🇫🇮 Suomi", settings_manager.get_sites_fi())
    _render_link_column(c3, "🎬 Media", settings_manager.get_sites_media())


def _render_link_column(col, title: str, links: list[dict]) -> None:
    with col:
        st.subheader(title)
        for name, url in _rows_to_links(links).items():
            st.markdown(f"[{name}]({url})")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — TEHOHAKU
# ─────────────────────────────────────────────────────────────────────────────

def render_tab_search() -> None:
    st.header("⚡️ Tehohaku")
    linkedin_url = _build_linkedin_url()
    st.markdown(
        f'<div class="cta-wrap"><a href="{linkedin_url}" target="_blank" class="cta-btn">'
        f'👉 LINKEDIN (HELSINKI + CREATIVE)</a></div>',
        unsafe_allow_html=True,
    )


def _build_linkedin_url() -> str:
    search_keywords = settings_manager.get_search_keywords() or ["graafinen suunnittelija"]
    query = " OR ".join(f'"{kw}"' for kw in search_keywords)
    params = {
        "keywords": f"({query})",
        "location": "Helsinki Metropolitan Area",
        "f_TPR": "r2592000",
        "sort": "dd",
    }
    return "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(params)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — SEURANTA
# ─────────────────────────────────────────────────────────────────────────────

def render_tab_tracking(items: list[TrackedItem]) -> list[TrackedItem]:
    """
    Renderöi seurantavälilehden.
    Palauttaa (mahdollisesti muokatun) items-listan.
    """
    st.header("📌 Hakemusten Seuranta")

    # Undo-banneri
    if st.session_state.get("deleted_item"):
        deleted = st.session_state.deleted_item
        st.warning(f"Poistit juuri kirjauksen: **{deleted.company}**")
        if st.button("↩️ Kumoa ja palauta kirjaus"):
            items.append(deleted)
            st.session_state.deleted_item = None
            save_tracked_items(items)
            st.rerun()

    # Lisäyslomake
    with st.expander("➕ Lisää manuaalisesti", expanded=False):
        items = _render_add_form(items)

    # Kohteiden lista
    items = _render_items_list(items)
    return items


def _render_add_form(items: list[TrackedItem]) -> list[TrackedItem]:
    c1, c2 = st.columns(2)
    with c1:
        cn = st.text_input("Yritys / Oppilaitos")
    with c2:
        cr = st.text_input("Rooli / Koulutus")
    cs = st.selectbox("Tila", ALL_STATUSES)

    interview_date = interview_time = ""
    if cs in ("Haastattelu", "Soveltuvuuskoe"):
        interview_date = st.date_input("Päivämäärä", key="int_date")
        interview_time = st.time_input("Kellonaika",  key="int_time")

    if st.button("Tallenna", type="primary") and cn:
        new_item = TrackedItem(
            company=cn, role=cr, status=cs,
            date=datetime.datetime.now().strftime("%d.%m."),
            interview_date=str(interview_date) if cs in ("Haastattelu", "Soveltuvuuskoe") else "",
            interview_time=str(interview_time) if cs in ("Haastattelu", "Soveltuvuuskoe") else "",
        )
        items.append(new_item)
        save_tracked_items(items)
        st.success("✅ Tallennettu!")
        st.rerun()
    return items


def _render_items_list(items: list[TrackedItem]) -> list[TrackedItem]:
    for i, item in enumerate(items):
        time_badge    = deadline_badge(item.date)
        status_color  = STATUS_COLORS.get(item.status, {"bg": "#E2E3E5", "text": "#333"})

        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            st.markdown(f"**{item.company}** ({item.role})")
        with c2:
            st.markdown(
                f"<span style='background:{status_color['bg']}; color:{status_color['text']};"
                f"padding:4px 8px; border-radius:6px;'>{item.status}</span> "
                f"<span style='margin-left:8px; font-size:.9em;'>{time_badge}</span>",
                unsafe_allow_html=True,
            )
        with c3:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.deleted_item = items.pop(i)
                save_tracked_items(items)
                st.rerun()

        if item.status in ("Haastattelu", "Soveltuvuuskoe") and item.interview_date:
            badge = deadline_badge(item.interview_date, is_future=True)
            st.markdown(
                f"🗓️ **Tapahtuma:** {item.interview_date} klo {item.interview_time} → "
                f"<span style='color:#d9534f; font-weight:bold;'>{badge}</span>",
                unsafe_allow_html=True,
            )

        _render_edit_expander(item, i, items)

    if not items:
        st.info("Seurantalista on tyhjä.")
    return items


def _render_edit_expander(item: TrackedItem, idx: int, items: list[TrackedItem]) -> None:
    is_editing = st.session_state.get(f"edit_{idx}", False)
    with st.expander("⚙️ Muokkaa yhteystietoja ja tilaa"):
        if st.button(
            "✏️ Avaa muokkaus" if not is_editing else "🔒 Lukitse",
            key=f"edit_btn_{idx}",
        ):
            st.session_state[f"edit_{idx}"] = not is_editing
            st.rerun()

        disabled = not is_editing
        c1, c2, c3 = st.columns(3)
        with c1:
            val = st.text_input("Nimi",        value=item.contact_name,  key=f"cn_{idx}", disabled=disabled)
            if val != item.contact_name: item.contact_name = val; save_tracked_items(items)
        with c2:
            val = st.text_input("Puhelin",     value=item.contact_phone, key=f"cp_{idx}", disabled=disabled)
            if val != item.contact_phone: item.contact_phone = val; save_tracked_items(items)
        with c3:
            val = st.text_input("Sähköposti",  value=item.contact_email, key=f"ce_{idx}", disabled=disabled)
            if val != item.contact_email: item.contact_email = val; save_tracked_items(items)

        if is_editing:
            st.markdown("---")
            options = list(ALL_STATUSES)
            if item.status not in options:
                options.append(item.status)
            new_status = st.selectbox(
                "Päivitä tila:", options,
                index=options.index(item.status),
                key=f"status_{idx}",
            )
            if new_status != item.status:
                item.status = new_status
                save_tracked_items(items)
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — AGENTTI
# ─────────────────────────────────────────────────────────────────────────────

def render_tab_agent(items: list[TrackedItem], kela: KelaData, active_key: str) -> KelaData:
    """Renderöi Agentti-välilehden. Palauttaa mahdollisesti päivitetyn KelaData:n."""
    st.header("🕵️ Ura-agentti & Tutka")
    _render_school_radar()
    st.divider()
    kela = _render_kela_tracker(kela)
    st.divider()
    _render_quota_meter(items)
    st.divider()
    _render_agent_notifications(items, active_key)
    return kela


def _render_school_radar() -> None:
    st.subheader("🎓 Koulutustutka")
    taitotalo_url = settings_manager.get_agent_config().get("taitotalo_url") or "#"
    with st.spinner("Tutka analysoi Taitotalon sivua…"):
        keywords = check_school_application_status(taitotalo_url)
    if keywords:
        st.success(f"🔥 **HAKU TUNNISTETTU!** Indikaattori: '{keywords[0]}'")
        st.markdown(f"[👉 Siirry täyttämään hakemus]({taitotalo_url})")
    else:
        st.info("ℹ️ Ei vahvistusta aktiivisesta hausta. Tarkista sivu manuaalisesti.")
        st.markdown(f"[🔗 Avaa Taitotalon sivu]({taitotalo_url})")


def _render_kela_tracker(kela: KelaData) -> KelaData:
    st.subheader("🏦 Kela-ilmoitus (4 viikon jakso)")
    default = (
        datetime.datetime.strptime(kela.last_date, "%Y-%m-%d").date()
        if kela.last_date else datetime.date.today()
    )
    k1, k2 = st.columns([2, 1])
    with k1:
        input_date = st.date_input("Milloin palautit edellisen ilmoituksen?", value=default)
    with k2:
        st.write(""); st.write("")
        if st.button("💾 Tallenna päivä"):
            kela.last_date = str(input_date)
            save_kela_data(kela)
            st.success("Tallennettu!")
            st.rerun()

    if kela.last_date:
        last   = datetime.datetime.strptime(kela.last_date, "%Y-%m-%d").date()
        nxt    = last + datetime.timedelta(days=KELA_CYCLE_DAYS)
        diff   = (nxt - datetime.date.today()).days
        st.markdown(f"**Seuraava ilmoituspäivä:** {nxt.strftime('%d.%m.%Y')}")
        if diff < 0:
            st.error(f"🔴 Ilmoituksen palautuspäivä oli {abs(diff)} päivää sitten. Palauta heti!")
        elif diff == 0:
            st.error("🔥 TÄNÄÄN ON KELA-ILMOITUKSEN PALAUTUSPÄIVÄ!")
            st.markdown("[👉 Siirry Oma Kelaan](https://www.kela.fi/asiointi)")
        elif diff <= 5:
            st.warning(f"⏳ Kela-ilmoitus on palautettava {diff} päivän kuluttua.")
        else:
            st.success(f"✅ Seuraavaan ilmoitukseen on aikaa {diff} päivää.")
    return kela


def _render_quota_meter(items: list[TrackedItem]) -> None:
    st.subheader("📉 Työnhakuvelvoite (Tämä kuu)")
    current_month = datetime.datetime.now().month
    count = 0
    for item in items:
        if item.status == "Kiinnostunut":
            continue
        try:
            parts = item.date.split(".")
            if len(parts) >= 2 and int(parts[1]) == current_month:
                count += 1
        except (ValueError, IndexError):
            pass

    # Hae käyttäjän valinta, muuten käytä config.py -oletusta
    target_quota = st.session_state.get("target_count", MONTHLY_QUOTA)

    remaining = target_quota - count
    progress  = min(count / target_quota, 1.0) if target_quota > 0 else 1.0

    if remaining > 0:
        st.warning(f"⚠️ Hakemuksia: **{count} / {target_quota}**. Vielä {remaining} puuttuu!")
        st.progress(progress, text=f"Valmiina: {int(progress * 100)}%")
    else:
        st.balloons()
        st.success(f"✅ Kuukauden kiintiö täytetty! ({count} / {target_quota})")
        st.progress(1.0, text="Velvoite täytetty 100%")


def _render_agent_notifications(items: list[TrackedItem], active_key: str) -> None:
    st.subheader("🔔 Ilmoitukset")
    found_any = False

    for i, item in enumerate(items):
        since = days_since(item.date)

        # Hiljainen-varoitus
        if item.status == "Odottaa" and since >= AGENT_SILENCE_THRESHOLD:
            found_any = True
            st.warning(f"⏳ **{item.company}**: {since} päivää hakemuksesta. Hiljaista?")
            show_key = f"show_email_{i}"
            draft_key = f"email_draft_{i}"
            area_key = f"email_ta_{i}"
            if st.button("📧 Kirjoita seurantaviesti", key=f"email_{i}"):
                st.session_state[show_key] = True
                st.session_state[draft_key] = _draft_followup_email(item, since, active_key)
                st.session_state[area_key] = st.session_state[draft_key]
            if st.session_state.get(show_key):
                # Tallenna valmis luonnos session ajaksi. Muuten Streamlit kutsuisi
                # mallia uudelleen jokaisella tekstikentän tai Sulje-painikkeen ajolla.
                draft = st.session_state.get(draft_key) or _fallback_followup_email(item, since)
                # Korjaa myös ennen päivitystä session_stateen jäänyt vanha luonnos.
                draft = repair_text_encoding(draft)
                st.session_state[draft_key] = draft
                if area_key in st.session_state:
                    st.session_state[area_key] = repair_text_encoding(st.session_state[area_key])
                else:
                    st.session_state[area_key] = draft
                st.text_area("Kopioi tästä:", height=200, key=area_key)
                if st.button("Sulje", key=f"close_email_{i}"):
                    st.session_state[show_key] = False
                    st.session_state.pop(draft_key, None)
                    st.session_state.pop(area_key, None)

        # Haastattelu-varoitus
        if item.status in ("Haastattelu", "Soveltuvuuskoe") and item.interview_date:
            diff = days_until(item.interview_date)
            if 0 <= diff <= INTERVIEW_WARNING_DAYS:
                found_any = True
                st.error(f"🔥 **{item.company}**: {item.status} {diff} pv päästä!")
                show_key = f"show_prep_{i}"
                draft_key = f"prep_draft_{i}"
                if st.button("🧠 Luo muistilista", key=f"prep_{i}"):
                    st.session_state[show_key] = True
                    st.session_state[draft_key] = _draft_prep_list(item, active_key)
                if st.session_state.get(show_key):
                    prep = st.session_state.get(draft_key) or _fallback_prep_list()
                    st.markdown(prep)
                    if st.button("Sulje", key=f"close_prep_{i}"):
                        st.session_state[show_key] = False
                        st.session_state.pop(draft_key, None)

    if not found_any:
        st.success("✅ Kaikki ajan tasalla. Ei akuutteja toimenpiteitä.")


def _draft_followup_email(item: TrackedItem, days: int, active_key: str) -> str:
    if active_key:
        greeting = f"Hei {item.contact_name.strip()}," if item.contact_name.strip() else "Hei,"
        prompt = (
            "Kirjoita valmis, luonteva ja ammattimainen suomenkielinen "
            "seurantasähköposti työhakemuksesta. Palauta vain valmis sähköposti, "
            "ei selityksiä eikä lainausmerkkejä.\n\n"
            f"Yritys: {item.company}\n"
            f"Tehtävä: {item.role}\n"
            f"Hakemuspäivä: {item.date}\n"
            f"Hakemuksesta kulunut aika: {days} päivää\n"
            f"Tervehdys: {greeting}\n"
            f"Allekirjoitus: {USER_NAME}\n\n"
            "Kirjoita aiherivi ja 2–3 lyhyttä kappaletta. Kysy kohteliaasti "
            "rekrytointiprosessin tilanteesta, ilmaise jatkuva kiinnostus ja kiitä "
            "vastaanottajaa. Älä keksi uusia tietoja."
        )
        text, _ = call_ai(prompt)
        cleaned = _clean_followup_email(text)
        if cleaned:
            return cleaned
    return _fallback_followup_email(item, days)


def _clean_followup_email(text: str | None) -> str:
    """Siistii mallin vastauksen ja hylkää selvästi rikkoutuneen tekstin."""
    cleaned = repair_text_encoding(text or "").strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
        if cleaned.lower().startswith("text\n"):
            cleaned = cleaned[5:].lstrip()

    broken_markers = ("Ã", "Â", "�", "HTTPConnectionPool", "🔴")
    if len(cleaned) < 60 or any(marker in cleaned for marker in broken_markers):
        return ""
    return cleaned


def _fallback_followup_email(item: TrackedItem, days: int) -> str:
    """Valmis viesti toimii myös silloin, kun valittu AI ei vastaa."""
    greeting = f"Hei {item.contact_name.strip()}," if item.contact_name.strip() else "Hei,"
    return (
        f"Aihe: Hakemukseni tilanne – {item.role}\n\n"
        f"{greeting}\n\n"
        f"Lähetin {item.date} hakemukseni tehtävään ”{item.role}” yrityksessä "
        f"{item.company}. Olen edelleen erittäin kiinnostunut tehtävästä ja "
        f"mahdollisuudesta työskennellä osana tiimiänne.\n\n"
        f"Haluaisin tiedustella, missä vaiheessa rekrytointiprosessi on ja onko "
        f"hakemukseni tilanteesta mahdollista saada lyhyt päivitys. Kiitos ajastanne.\n\n"
        f"Ystävällisin terveisin,\n{USER_NAME}"
    )


def _draft_prep_list(item: TrackedItem, active_key: str) -> str:
    if active_key:
        prompt = (
            f"Olen menossa {item.status}:oon ({item.company}, {item.role}). "
            f"Anna 3 kiperää kysymystä + 3 faktaa yrityksestä."
        )
        text, _ = call_ai(prompt)
        if text:
            return text
    return _fallback_prep_list()


def _fallback_prep_list() -> str:
    return (
        "1. **Tutustu organisaation uutisiin** (Verkkosivut).\n"
        "2. **Kertaa hakemuksesi:** Mitä lupasit osaavasi?\n"
        "3. **Valmistele kysymyksiä:** 'Miltä tyypillinen päivä näyttää?'\n"
        "4. **Pitch:** Harjoittele 2 min hissipuhe."
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — TYÖMARKKINATORI
# ─────────────────────────────────────────────────────────────────────────────

def render_tab_jobs() -> None:
    st.header("🇫🇮 Työmarkkinatori")
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("💼 Työpaikat")
        search_keywords = settings_manager.get_search_keywords() or ["graafinen suunnittelija"]
        options     = ["Kaikki luovat alat"] + search_keywords
        selected    = st.selectbox("Valitse ammattinimike:", options)
        q           = "%20".join(search_keywords) if selected == "Kaikki luovat alat" else selected
        url         = f"https://tyomarkkinatori.fi/henkiloasiakkaat/avoimet-tyopaikat?q={q}&location=Uusimaa"
        st.markdown(
            f'<div class="cta-wrap"><a href="{url}" target="_blank" class="cta-btn">'
            f'👉 HAE: {selected.upper()}</a></div>',
            unsafe_allow_html=True,
        )

    with c2:
        st.subheader("🎓 Koulutus")
        training_topics = settings_manager.get_training_topics() or {"Kaikki aiheet": "media viestintä"}
        topic    = st.selectbox("Valitse ala:", list(training_topics.keys()))
        q_train  = training_topics[topic]
        url_t    = f"https://tyomarkkinatori.fi/henkiloasiakkaat/koulutukset-ja-palvelut?q={q_train}"
        st.markdown(
            f'<div class="cta-wrap"><a href="{url_t}" target="_blank" class="cta-btn dark">'
            f'👉 HAE: {topic.upper()}</a></div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 8 — PORTFOLIO
# ─────────────────────────────────────────────────────────────────────────────

def render_tab_portfolio() -> None:
    st.header("🎨 Portfolio & Data")
    st.markdown(
        f'<div class="cta-wrap"><a href="{_portfolio_url()}" target="_blank" class="cta-btn dark">'
        f'🚀 AVAA PORTFOLIO & CV</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    df = load_visitor_data()
    if not VISITOR_DATA_ENABLED:
        st.info(
            "🧪 Julkisessa demossa vierailudatan rajapinta on poistettu käytöstä "
            "eikä tallennettuja rivejä ole mukana."
        )
        return
    if df is None:
        st.warning(
            "⚠️ Dataa ei voitu hakea. Tarkista Apps Script -endpoint, token ja käyttöoikeudet. "
            "Google Sheetin ei pidä olla julkinen.\n\n"
            f"Sheet ID: `{SHEET_ID}`"
        )
        return
    if df.empty:
        st.info(
            "Vierailijadata-yhteys toimii, mutta Sheetissä ei ole vielä kelvollisia "
            "portfolioanalytiikan rivejä näytettäväksi."
        )
        return

    def first_column(*names: str) -> str | None:
        for name in names:
            if name in df.columns:
                return name
        return None

    col_time = first_column("timestamp", "Saapumisaika", "Aika") or df.columns[0]
    col_date = first_column("date", "Päivämäärä")
    col_clock = first_column("time", "Kellonaika")
    col_event = first_column("event_type", "Klikkaus")
    col_page = first_column("page_path", "Sivu")
    col_device = first_column("device_type", "Saapuva laite", "Laite")
    col_browser = first_column("browser", "Selain")
    col_os = first_column("os", "Käyttöjärjestelmä")
    col_referrer = first_column("referrer_type", "Tulotapa")
    col_connection = first_column("connection_type", "Yhteystyyppi")
    col_operator = first_column("connection_operator", "Operaattori")
    col_duration = first_column("visit_duration_seconds", "Vierailun kesto (s)")
    col_scroll = first_column("scroll_depth_percent", "Scroll (%)")
    col_button = first_column("button_label", "Painike")
    col_target = first_column("button_href", "Kohde")

    show_cols = [
        c
        for c in [
            col_time,
            col_date,
            col_clock,
            col_event,
            col_page,
            col_device,
            col_browser,
            col_os,
            col_referrer,
            col_connection,
            col_operator,
            col_duration,
            col_scroll,
            col_button,
            col_target,
        ]
        if c and c in df.columns
    ]
    df_display = df[show_cols].copy() if show_cols else df.copy()

    event_labels = {
        "visit_start": "Sivun avaus",
        "button_click": "Painikkeen klikkaus",
        "visit_end": "Vierailu päättyi",
    }
    display_names = {
        col_time: "Saapumisaika",
        col_date: "Päivämäärä",
        col_clock: "Kellonaika",
        col_event: "Tapahtuma",
        col_page: "Sivu",
        col_device: "Saapuva laite",
        col_browser: "Selain",
        col_os: "Käyttöjärjestelmä",
        col_referrer: "Tulotapa",
        col_connection: "Yhteystyyppi",
        col_operator: "Operaattori",
        col_duration: "Vierailun kesto (s)",
        col_scroll: "Scroll (%)",
        col_button: "Painike",
        col_target: "Kohde",
    }
    if col_event and col_event in df_display.columns:
        df_display[col_event] = df_display[col_event].replace(event_labels)
    df_display = df_display.rename(
        columns={source: label for source, label in display_names.items() if source}
    )

    last_time = str(df.iloc[-1][col_time])
    if col_date and col_date in df.columns:
        last_date = str(df.iloc[-1][col_date])
    else:
        last_date = last_time.split("T")[0] if "T" in last_time else last_time.split(" ")[0]
    last_device = "Tuntematon"
    if col_device:
        series = df[col_device].replace("", None).dropna()
        last_device = str(series.iloc[-1]) if not series.empty else "Tuntematon"

    m1, m2, m3 = st.columns(3)
    _metric_card(m1, str(len(df)), "Tapahtumat yhteensä")
    _metric_card(m2, last_device, "Viimeisin laite", small=True)
    _metric_card(m3, last_date, "Päivämäärä")

    st.write("")
    st.subheader("📊 Laitteet ja yhteydet")
    chart_left, chart_right = st.columns(2)
    if col_device and col_device in df.columns:
        device_counts = df[col_device].replace("", None).dropna().value_counts().head(7)
        if not device_counts.empty:
            with chart_left:
                st.caption("Laitetyypit")
                st.bar_chart(device_counts, color="#4DA6FF")
    if col_connection and col_connection in df.columns:
        connection_counts = df[col_connection].replace("", None).dropna().value_counts().head(7)
        if not connection_counts.empty:
            with chart_right:
                st.caption("Yhteystyypit")
                st.bar_chart(connection_counts, color="#4DA6FF")

    st.write("")
    st.subheader("📋 Vierailuloki")
    st.dataframe(df_display.iloc[::-1].reset_index(drop=True), use_container_width=True, height=300)


def _metric_card(col, value: str, label: str, small: bool = False) -> None:
    font = "font-size:1.3rem;" if small else ""
    with col:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value" style="{font}">{value}</div>'
            f'<div class="metric-label">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 9 — SUOSITUKSET
# ─────────────────────────────────────────────────────────────────────────────

def render_tab_recommendations(items: list[TrackedItem]) -> list[TrackedItem]:
    st.header("🧠 Suositukset")
    tracked_names   = {item.company for item in items}
    dismissed       = st.session_state.get("dismissed_suggestions", [])

    suggestions = []
    for school in settings_manager.get_schools():
        name = _safe_text(school.get("name"))
        url = _safe_text(school.get("url"))
        if not name or not url:
            continue
        score, reasons = calculate_education_score_details(
            name=name,
            status=_safe_text(school.get("status")),
            url=url,
        )
        suggestions.append({
            "name": name,
            "url": url,
            "cat": "🎓 Koulutus",
            "score": score,
            "reasons": reasons,
        })

    suggestions += [
        {"name": name, "url": url, "cat": "💼 Työ / Hub",
         "score": calculate_score(name, "Helsinki")}
        for name, url in _rows_to_links(settings_manager.get_startups()).items()
    ]
    suggestions = [
        s for s in suggestions
        if s["name"] not in tracked_names and s["name"] not in dismissed
    ]
    suggestions.sort(key=lambda x: x["score"], reverse=True)

    if not suggestions:
        st.success("Kaikki suositukset on jo käsitelty! 🚀")
        return items

    for idx, sug in enumerate(suggestions):
        c1, c2 = st.columns([4, 1])
        with c1:
            name_html = html.escape(sug["name"])
            cat_html = html.escape(sug["cat"])
            reason_text = ", ".join(sug.get("reasons", []))
            reason_html = (
                f'<div class="rec-reasons">Sopii: {html.escape(reason_text)}</div>'
                if reason_text else ""
            )
            st.markdown(
                f'<div class="rec-card">'
                f'<div class="rec-cat">{cat_html}</div>'
                f'<div class="rec-title">{name_html} '
                f'<span class="rec-badge">{sug["score"]:.1f}/5</span></div>'
                f'{reason_html}'
                f'<a href="{html.escape(sug["url"])}" target="_blank" style="color:#4da6ff;">🔗 Avaa sivu</a>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.write("")
            if st.button("➕ Lisää", key=f"add_{idx}", use_container_width=True):
                items.append(TrackedItem(
                    company=sug["name"], role=sug["cat"], status="Kiinnostunut",
                    date=datetime.datetime.now().strftime("%d.%m."),
                ))
                save_tracked_items(items)
                st.rerun()
            if st.button("❌ Piilota", key=f"dis_{idx}", use_container_width=True):
                dismissed.append(sug["name"])
                st.session_state.dismissed_suggestions = dismissed
                st.rerun()
    return items


# ─────────────────────────────────────────────────────────────────────────────
# TAB 10 — AI KOULUTUS
# ─────────────────────────────────────────────────────────────────────────────

def render_tab_ai_courses() -> None:
    st.header("🤖 Tekoälykoulutukset")
    cols = st.columns(3)
    for i, course in enumerate(settings_manager.get_ai_courses()):
        with cols[i % 3]:
            st.markdown(
                f'<div class="ai-card"><div>'
                f'<div class="ai-type">{course.get("type", "")}</div>'
                f'<div class="ai-title">{course.get("name", "")}</div>'
                f'<div class="ai-provider">{course.get("provider", "")}</div>'
                f'<div class="ai-desc">{course.get("desc", "")}</div>'
                f'</div><div style="text-align:right; margin-top:20px;">'
                f'<a href="{course.get("url", "#")}" target="_blank" class="ai-link">Tutustu ➜</a>'
                f'</div></div><div style="margin-bottom:20px;"></div>',
                unsafe_allow_html=True,
            )
