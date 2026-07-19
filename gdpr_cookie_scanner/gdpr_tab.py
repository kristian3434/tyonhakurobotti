"""
gdpr_tab.py — Streamlit-näkymä GDPR/ePrivacy-evästeskannerille.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from gdpr_scanner import (
    LEGAL_REFERENCES,
    MissingDependencyError,
    ScanConfig,
    ScanResult,
    cookies_as_rows,
    findings_as_rows,
    result_to_json,
    scan_website,
    storage_as_rows,
)


SEVERITY_LABELS = {
    "high": ("Korkea", "error"),
    "medium": ("Kohtalainen", "warning"),
    "low": ("Matala", "info"),
    "info": ("Info", "success"),
}


def render_tab_gdpr_scanner() -> None:
    st.header("🛡️ GDPR-evästeskanneri")

    with st.form("gdpr_scan_form"):
        url = st.text_input("Tarkistettava verkkosivu", placeholder="https://example.com")
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        with c1:
            test_reject = st.checkbox("Testaa hylkäys", value=True)
        with c2:
            test_accept = st.checkbox("Testaa peruminen", value=True)
        with c3:
            test_settings = st.checkbox("Tarkista asetukset", value=True)
        with c4:
            timeout = st.number_input("Aikaraja / s", min_value=10, max_value=90, value=30, step=5)

        submitted = st.form_submit_button("Skannaa sivu", type="primary")

    if submitted:
        if not url.strip():
            st.warning("Anna verkkosivun osoite.")
            return

        config = ScanConfig(
            url=url,
            timeout_seconds=int(timeout),
            test_reject=test_reject,
            test_accept_withdrawal=test_accept,
            test_settings=test_settings,
        )
        with st.spinner("Skannataan sivua oikealla selaimella..."):
            try:
                st.session_state.gdpr_scan_result = scan_website(config)
            except MissingDependencyError as exc:
                st.error("Selaintarkistus tarvitsee Playwrightin.")
                st.code(
                    "python3 -m pip install playwright\n"
                    "python3 -m playwright install chromium",
                    language="bash",
                )
                st.caption(str(exc))
                return
            except Exception as exc:
                st.error(f"Skannaus epäonnistui: {exc}")
                return

    result = st.session_state.get("gdpr_scan_result")
    if not result:
        _render_reference_panel()
        return

    _render_summary(result)
    _render_findings(result)
    _render_evidence(result)
    _render_reference_panel()


def _render_summary(result: ScanResult) -> None:
    summary = result.summary
    if not summary:
        return

    st.subheader("Yhteenveto")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pisteet", f"{summary.score}/100")
    c2.metric("Riskitaso", summary.risk_level)
    c3.metric("Evästeitä ennen valintaa", summary.cookies_before_consent)
    c4.metric("Riskitunnisteita ennen valintaa", summary.likely_nonessential_before_consent)

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Banneri", "Kyllä" if summary.banner_detected else "Ei")
    c6.metric("Hyväksy", "Kyllä" if summary.accept_detected else "Ei")
    c7.metric("Hylkää", "Kyllä" if summary.reject_detected else "Ei")
    c8.metric("Peruminen", _yes_no_unknown(summary.withdrawal_detected_after_accept))

    if result.errors:
        with st.expander("Skannauksen huomautukset"):
            for error in result.errors:
                st.write(f"- {error}")

    st.download_button(
        "Lataa JSON-raportti",
        result_to_json(result),
        file_name="gdpr_cookie_scan_report.json",
        mime="application/json",
    )


def _render_findings(result: ScanResult) -> None:
    st.subheader("Havainnot")
    for finding in result.findings:
        label, streamlit_method = SEVERITY_LABELS.get(finding.severity, ("Info", "info"))
        message = (
            f"**{label}: {finding.title}**\n\n"
            f"{finding.evidence}\n\n"
            f"Korjaus: {finding.recommendation}\n\n"
            f"Vaatimus: {finding.requirement}"
        )
        getattr(st, streamlit_method)(message)

    findings_rows = findings_as_rows(result)
    if findings_rows:
        with st.expander("Havainnot taulukkona"):
            st.dataframe(pd.DataFrame(findings_rows), use_container_width=True, hide_index=True)


def _render_evidence(result: ScanResult) -> None:
    st.subheader("Tekninen näyttö")

    tab_before, tab_reject, tab_accept, tab_storage, tab_domains, tab_docs = st.tabs(
        [
            "Ennen valintaa",
            "Hylkäyksen jälkeen",
            "Hyväksynnän jälkeen",
            "Tallennustila",
            "Domainit",
            "Dokumentaatio",
        ]
    )

    with tab_before:
        _render_cookie_table(result.initial, "Evästeet ennen suostumusvalintaa")
        _render_controls(result.initial)

    with tab_reject:
        if result.after_reject:
            _render_cookie_table(result.after_reject, "Evästeet hylkäyksen jälkeen")
        else:
            st.info("Hylkäystestiä ei ajettu tai hylkäyspainiketta ei löytynyt.")

    with tab_accept:
        if result.after_accept:
            _render_cookie_table(result.after_accept, "Evästeet hyväksynnän jälkeen")
        else:
            st.info("Hyväksymistestiä ei ajettu tai hyväksymispainiketta ei löytynyt.")
        if result.after_accept_reload:
            st.markdown("**Perumisen etsintä uudelleenlatauksen jälkeen**")
            _render_controls(result.after_accept_reload)

    with tab_storage:
        rows = storage_as_rows(result.initial)
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("localStorage/sessionStorage-tallenteita ei havaittu ennen valintaa.")

    with tab_domains:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Kaikki pyynnöissä nähdyt domainit**")
            if result.initial.request_domains:
                st.dataframe(pd.DataFrame({"domain": result.initial.request_domains}), use_container_width=True, hide_index=True)
            else:
                st.info("Pyyntödomianeja ei kerätty.")
        with c2:
            st.markdown("**Tunnetut seuranta-/mainontadomainit**")
            if result.initial.tracker_domains:
                st.dataframe(pd.DataFrame({"domain": result.initial.tracker_domains}), use_container_width=True, hide_index=True)
            else:
                st.success("Tunnettuja seuranta-/mainontadomaineja ei havaittu ennen valintaa.")

    with tab_docs:
        if result.policy_evidence:
            rows = [
                {
                    "otsikko": item.title,
                    "url": item.url,
                    "tarkoitukset": item.has_purpose,
                    "kestot": item.has_duration,
                    "kolmannet_osapuolet": item.has_third_parties,
                    "evästetaulukko": item.has_cookie_table,
                }
                for item in result.policy_evidence
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Eväste-/tietosuojaselostetta ei saatu avattua automaattisesti.")

        if result.initial.policy_links:
            st.markdown("**Löydetyt linkit**")
            st.dataframe(pd.DataFrame(result.initial.policy_links), use_container_width=True, hide_index=True)


def _render_cookie_table(snapshot, title: str) -> None:
    st.markdown(f"**{title}**")
    rows = cookies_as_rows(snapshot)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.success("Evästeitä ei havaittu tässä vaiheessa.")


def _render_controls(snapshot) -> None:
    controls = [
        {
            "teksti": control.text,
            "tyyppi": control.kind,
            "valittu": control.checked,
            "koko": round(control.area),
            "tausta": control.background,
        }
        for control in snapshot.controls
        if control.text
    ][:80]
    if controls:
        with st.expander("Havaitut painikkeet ja valinnat"):
            st.dataframe(pd.DataFrame(controls), use_container_width=True, hide_index=True)


def _render_reference_panel() -> None:
    with st.expander("Tarkistusperusteet ja lähteet"):
        st.write(
            "Skanneri tarkistaa teknisiä riskejä: suostumus ennen ei-välttämätöntä seurantaa, "
            "hylkäysmahdollisuus, tarkoituskohtaisuus, ennakkovalinnat, oikeutettu etu, "
            "perumisen helppous sekä evästedokumentaation näkyvät puutteet."
        )
        for ref in LEGAL_REFERENCES:
            st.markdown(f"- [{ref['name']}]({ref['url']}) — {ref['used_for']}")
        st.caption("Tulos on tekninen auditointiapu. Lopullinen lainmukaisuus pitää arvioida myös sopimusten, consent logien, CMP-asetusten ja kansallisen sääntelyn perusteella.")


def _yes_no_unknown(value: bool | None) -> str:
    if value is True:
        return "Kyllä"
    if value is False:
        return "Ei"
    return "Ei testattu"
