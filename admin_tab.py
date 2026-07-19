"""
admin_tab.py — Hallintapaneeli.
Kaikkien dynaamisten sisältöjen (mainostoimistot, koulut, kurssit,
avainsanat ja linkit) hallinta suoraan käyttöliittymästä ilman koodausta.
Muutokset tallentuvat settings.json-tiedostoon.
"""
from __future__ import annotations
import pandas as pd
import streamlit as st
import settings_manager


# ── Pääfunktio ────────────────────────────────────────────────────────────────

def render_tab_admin() -> None:
    st.header("⚙️ Hallintapaneeli")
    st.markdown(
        "Hallitse sovelluksen kaikkia dynaamisia sisältöjä suoraan täältä — "
        "ei koodausta tarvita. **Muutokset tallentuvat `settings.json`-tiedostoon** "
        "ja pysyvät tallessa sovelluksen uudelleenkäynnistyksen jälkeen."
    )

    # Globaali nollaus
    with st.expander("🔄 Palauta KAIKKI oletuksiin", expanded=False):
        st.warning("⚠️ Tämä ylikirjoittaa kaikki muutoksesi oletusarvoilla.")
        if st.checkbox("Ymmärrän — haluan palauttaa kaiken", key="confirm_global_reset"):
            if st.button("🔴 Palauta kaikki oletuksiin", type="primary", key="global_reset_btn"):
                settings_manager.save_settings(settings_manager._build_defaults())
                st.success("✅ Kaikki palautettu oletuksiin!")
                st.rerun()

    st.markdown("---")

    tabs = st.tabs([
        "🏢 Mainostoimistot",
        "🔗 Linkit & Portfolio",
        "🎓 Koulutus & Ehdotukset",
        "🤖 AI-koulutukset",
        "🕵️ Agentin asetukset",
    ])

    s = settings_manager.get_settings()

    with tabs[0]:
        _section_agencies(s)
    with tabs[1]:
        _section_links(s)
    with tabs[2]:
        _section_schools(s)
    with tabs[3]:
        _section_ai_courses(s)
    with tabs[4]:
        _section_agent(s)


# ── OSIO 1: Mainostoimistot ───────────────────────────────────────────────────

def _section_agencies(s: dict) -> None:
    st.subheader("🏢 Mainostoimistot")
    st.markdown(
        "Muokkaa mainostoimistoja suoraan taulukossa. Lisää rivejä `+`-napilla, "
        "poista klikkaamalla rivinumeroa ja `Delete`. "
        "**Logo URL** on valinnainen — tyhjänä käytetään tunnettujen toimistojen "
        "virallista logoa tai haetaan logo automaattisesti toimiston sivulta. "
        "Lista järjestetään tallennettaessa aakkosjärjestykseen."
    )

    df = pd.DataFrame(
        s.get("agencies", []),
        columns=["name", "url", "logo_url"],
    ).fillna("")

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_agencies",
        column_config={
            "name":     st.column_config.TextColumn("Nimi",              width="medium"),
            "url":      st.column_config.TextColumn("Verkko-osoite",     width="large"),
            "logo_url": st.column_config.TextColumn("Logo URL (valinnainen)", width="large"),
        },
    )

    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("💾 Tallenna", key="save_agencies", type="primary"):
            s["agencies"] = settings_manager.normalize_agencies(
                edited.fillna("").to_dict("records")
            )
            settings_manager.save_settings(s)
            st.success("✅ Mainostoimistot tallennettu!")
            st.rerun()
    with c2:
        _reset_expander(s, "agencies", "Mainostoimistot", "agencies")

    st.markdown("---")
    st.caption("**Esikatselu** — näin mainostoimistot näkyvät sovelluksessa:")
    cols = st.columns(4)
    preview_agencies = settings_manager.normalize_agencies(
        edited.fillna("").to_dict("records")
    )
    for i, agency in enumerate(preview_agencies):
        logo = settings_manager.agency_logo(agency)
        fallback = settings_manager.agency_logo_fallback(agency)
        logo_class = settings_manager.agency_logo_class(agency)
        with cols[i % 4]:
            st.markdown(
                f'<a href="{agency.get("url","#")}" target="_blank" class="link-btn">'
                f'<span class="link-logo"><img class="{logo_class}" src="{logo}" alt="" '
                f'onerror="this.onerror=null;this.src=\'{fallback}\';"></span>'
                f'{agency.get("name","")}</a>',
                unsafe_allow_html=True,
            )


# ── OSIO 2: Linkit & Portfolio ────────────────────────────────────────────────

def _section_links(s: dict) -> None:
    st.subheader("🔗 Linkit & Portfolio")

    # Portfolio URL
    st.markdown("**Portfolio / CV -linkki**")
    portfolio = st.text_input(
        "Portfolio URL",
        value=s.get("portfolio_url", ""),
        key="input_portfolio",
        label_visibility="collapsed",
    )
    if st.button("💾 Tallenna portfolio-linkki", key="save_portfolio"):
        s["portfolio_url"] = portfolio.strip()
        settings_manager.save_settings(s)
        st.success("✅ Portfolio-linkki tallennettu!")
        st.rerun()

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        _link_table(s, "sites_intl",  "🌍 Kansainväliset työsivustot",  "sites_intl")
        st.markdown("---")
        _link_table(s, "sites_fi",    "🇫🇮 Suomalaiset työsivustot",    "sites_fi")

    with col_b:
        _link_table(s, "sites_media", "🎬 Media-alan sivustot",          "sites_media")
        st.markdown("---")
        _link_table(s, "startups",    "🚀 Start-upit & hubit",           "startups")

    st.markdown("---")
    _training_topics_table(s)


def _link_table(s: dict, key: str, title: str, btn_suffix: str) -> None:
    """Yleinen 2-sarakkeinen (nimi + URL) taulukkoeditori."""
    st.markdown(f"**{title}**")
    items = s.get(key, [])
    df = pd.DataFrame(
        items if items else [{"name": "", "url": ""}],
        columns=["name", "url"],
    ).fillna("")

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"editor_{btn_suffix}",
        column_config={
            "name": st.column_config.TextColumn("Nimi", width="medium"),
            "url":  st.column_config.TextColumn("URL",  width="large"),
        },
        height=200,
    )
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("💾 Tallenna", key=f"save_{btn_suffix}"):
            cleaned = edited.fillna("").to_dict("records")
            cleaned = [r for r in cleaned if r.get("name", "").strip()]
            s[key] = cleaned
            settings_manager.save_settings(s)
            st.success(f"✅ {title} tallennettu!")
            st.rerun()
    with c2:
        _reset_expander(s, key, title, btn_suffix)


def _training_topics_table(s: dict) -> None:
    """Työmarkkinatorin hakuaiheiden hallinta."""
    st.markdown("**🇫🇮 Työmarkkinatorin hakuaiheet**")
    st.caption("'Label' = näkyvä nimi sovelluksessa. 'Query' = hakusana Työmarkkinatorille.")
    items = s.get("training_topics", [])
    df = pd.DataFrame(
        items if items else [{"label": "", "query": ""}],
        columns=["label", "query"],
    ).fillna("")

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_training",
        column_config={
            "label": st.column_config.TextColumn("Näkyvä nimi", width="medium"),
            "query": st.column_config.TextColumn("Hakusana",    width="large"),
        },
    )
    if st.button("💾 Tallenna hakuaiheet", key="save_training"):
        cleaned = edited.fillna("").to_dict("records")
        cleaned = [r for r in cleaned if r.get("label", "").strip()]
        s["training_topics"] = cleaned
        settings_manager.save_settings(s)
        st.success("✅ Hakuaiheet tallennettu!")
        st.rerun()


# ── OSIO 3: Koulutus & Ehdotukset ────────────────────────────────────────────

def _section_schools(s: dict) -> None:
    st.subheader("🎓 Koulutus & Ehdotukset")
    st.markdown(
        "Nämä koulut ja oppilaitokset näkyvät **Suositukset**-välilehdellä. "
        "Status-sarake on vapaa teksti (esim. 'AMK / Haku', '⭐ HUIPPU')."
    )

    df = pd.DataFrame(
        s.get("schools", []),
        columns=["name", "url", "status"],
    ).fillna("")

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_schools",
        column_config={
            "name":   st.column_config.TextColumn("Nimi",    width="large"),
            "url":    st.column_config.TextColumn("URL",     width="large"),
            "status": st.column_config.TextColumn("Status",  width="small"),
        },
    )

    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("💾 Tallenna", key="save_schools", type="primary"):
            cleaned = edited.fillna("").to_dict("records")
            cleaned = [r for r in cleaned if r.get("name", "").strip()]
            s["schools"] = cleaned
            settings_manager.save_settings(s)
            st.success("✅ Koulut tallennettu!")
            st.rerun()
    with c2:
        _reset_expander(s, "schools", "Koulutus & Ehdotukset", "schools")


# ── OSIO 4: AI-koulutukset ────────────────────────────────────────────────────

def _section_ai_courses(s: dict) -> None:
    st.subheader("🤖 AI-koulutukset")
    st.markdown(
        "Nämä kurssit näkyvät **AI Koulutus** -välilehdellä. "
        "Type-sarake (esim. 'MOOC / ETÄ', 'SERTIFIKAATTI') näkyy kortin yläosassa."
    )

    df = pd.DataFrame(
        s.get("ai_courses", []),
        columns=["name", "provider", "url", "type", "desc"],
    ).fillna("")

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_ai_courses",
        column_config={
            "name":     st.column_config.TextColumn("Nimi",        width="medium"),
            "provider": st.column_config.TextColumn("Tarjoaja",    width="medium"),
            "url":      st.column_config.TextColumn("URL",         width="medium"),
            "type":     st.column_config.TextColumn("Tyyppi",      width="small"),
            "desc":     st.column_config.TextColumn("Kuvaus",      width="large"),
        },
    )

    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("💾 Tallenna", key="save_ai_courses", type="primary"):
            cleaned = edited.fillna("").to_dict("records")
            cleaned = [r for r in cleaned if r.get("name", "").strip()]
            s["ai_courses"] = cleaned
            settings_manager.save_settings(s)
            st.success("✅ AI-koulutukset tallennettu!")
            st.rerun()
    with c2:
        _reset_expander(s, "ai_courses", "AI-koulutukset", "ai_courses")


# ── OSIO 5: Agentin asetukset ─────────────────────────────────────────────────

def _section_agent(s: dict) -> None:
    st.subheader("🕵️ Agentin asetukset")

    # Taitotalo URL
    st.markdown("**Koulutustutkan kohde-URL**")
    st.caption("Tämä on sivu, jota agentti tarkkailee aktiivisen haun merkkejä varten.")
    taitotalo_url = st.text_input(
        "Tutkan URL",
        value=s.get("agent_taitotalo_url", ""),
        key="input_taitotalo",
        label_visibility="collapsed",
    )
    if st.button("💾 Tallenna tutkan URL", key="save_taitotalo"):
        s["agent_taitotalo_url"] = taitotalo_url.strip()
        settings_manager.save_settings(s)
        st.success("✅ Tutkan URL tallennettu!")
        st.rerun()

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        _keyword_list(s, "agent_haku_keywords",  "🔍 Hakuindikaattorit (mitä sivulta etsitään)",  "haku_kw")
        st.caption("Nämä avainsanat etsitään tutkan kohdesivulta. Jos löytyy → 'haku aktiivinen'.")

    with col_b:
        _keyword_list(s, "agent_media_keywords", "🎨 Media-ala -suodattimet",                      "media_kw")
        st.caption("Vahvistaa hakuindikaattorin — hakusivun pitää myös sisältää jokin näistä.")

    st.markdown("---")

    col_c, col_d = st.columns(2)

    with col_c:
        _keyword_list(s, "target_roles",    "🎯 Tavoiteroolit (pisteytystä varten)", "target_roles")
        st.caption("Näitä rooleja vastaavat ilmoitukset saavat lisäpisteitä Match Score -laskurissa.")

    with col_d:
        _keyword_list(s, "search_keywords", "🔎 LinkedIn-hakusanat",                "search_kw")
        st.caption("Nämä muodostavat LinkedIn-tehohakujen URL:n.")


def _keyword_list(s: dict, key: str, title: str, btn_suffix: str) -> None:
    """Yksisarakkeinen avainsanalista-editori."""
    st.markdown(f"**{title}**")
    items = s.get(key, [])
    df = pd.DataFrame({"avainsana": items if items else [""]})

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"editor_{btn_suffix}",
        column_config={
            "avainsana": st.column_config.TextColumn("Avainsana", width="large"),
        },
        height=220,
    )
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("💾 Tallenna", key=f"save_{btn_suffix}"):
            new_list = edited["avainsana"].fillna("").tolist()
            new_list = [x.strip() for x in new_list if str(x).strip()]
            s[key] = new_list
            settings_manager.save_settings(s)
            st.success(f"✅ Tallennettu! ({len(new_list)} kpl)")
            st.rerun()
    with c2:
        _reset_expander(s, key, title, btn_suffix)


# ── Apufunktiot ───────────────────────────────────────────────────────────────

def _reset_expander(s: dict, key: str, label: str, suffix: str) -> None:
    """Piilossa oleva 'Palauta oletukset' -toiminto per osio."""
    with st.expander(f"↩️ Palauta '{label}' oletuksiin"):
        st.warning("Tämä ylikirjoittaa tämän osion kaikki muutokset.")
        if st.button(f"Palauta oletukset", key=f"reset_{suffix}"):
            settings_manager.reset_section(key)
            st.success(f"✅ '{label}' palautettu oletuksiin!")
            st.rerun()
