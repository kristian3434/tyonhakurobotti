"""
gdpr_scanner.py — Tekninen GDPR/ePrivacy-evästeskanneri.

Skanneri käyttää Playwrightia, jos se on asennettu. Auditointi on tekninen
riskitarkistus, ei lopullinen juridinen lausunto.
"""
from __future__ import annotations

import asyncio
import html as html_lib
import json
import os
import re
import sys
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse


BASE_DIR = Path(__file__).resolve().parent
VENDOR_DIR = BASE_DIR / ".vendor"
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BASE_DIR / ".playwright-browsers"))


SCAN_VERSION = "2026-07-03"

LEGAL_REFERENCES = [
    {
        "name": "EDPB Guidelines 05/2020 on consent under Regulation 2016/679",
        "url": "https://www.edpb.europa.eu/documents/guideline/guidelines-052020-on-consent-under-regulation-2016679_en",
        "used_for": "Suostumuksen on oltava vapaaehtoinen, yksilöity, tietoinen ja yksiselitteinen; ennakkovalinnat ja passiivisuus eivät riitä; perumisen on oltava yhtä helppoa kuin antamisen.",
    },
    {
        "name": "EDPB Report of the Cookie Banner Taskforce, 18 Jan 2023",
        "url": "https://www.edpb.europa.eu/documents/task-force-report/report-of-the-work-undertaken-by-the-cookie-banner-taskforce_en",
        "used_for": "Reject all -käytännöt, oikeutetun edun käyttö evästeiden lukemiseen/asettamiseen, olennaisten evästeiden luokittelu ja suostumuksen peruminen.",
    },
    {
        "name": "European Commission Cookies policy",
        "url": "https://commission.europa.eu/cookies-policy_en",
        "used_for": "Käytännön vertailukohta evästeluettelon sisällölle: nimi, palvelu, tarkoitus, tyyppi ja kesto.",
    },
]


ACCEPT_RE = re.compile(
    r"\b(accept all|accept|allow all|agree|agree all|ok|got it|hyv[aä]ksy kaikki|hyv[aä]ksy|salli kaikki|"
    r"godk[aä]nn alla|godk[aä]nn|acceptera alla|jag accepterar)\b",
    re.I,
)
REJECT_RE = re.compile(
    r"\b(reject all|reject|decline|deny|refuse|no thanks|only necessary|necessary only|essential only|"
    r"hylk[aä][aä] kaikki|hylk[aä][aä]|kiell[aä]|vain v[aä]ltt[aä]m[aä]tt[oö]m[aä]t|ei kiitos|"
    r"avvisa alla|avvisa|endast n[oö]dv[aä]ndiga|bara n[oö]dv[aä]ndiga)\b",
    re.I,
)
SETTINGS_RE = re.compile(
    r"\b(settings|preferences|manage|manage choices|customi[sz]e|options|details|cookie settings|privacy settings|"
    r"asetukset|ev[aä]steasetukset|hallinnoi|muokkaa|valinnat|tietosuoja-asetukset|"
    r"inst[aä]llningar|hantera|anpassa|val)\b",
    re.I,
)
WITHDRAW_RE = re.compile(
    r"\b(cookie settings|privacy settings|manage consent|change consent|withdraw consent|consent preferences|"
    r"ev[aä]steasetukset|muuta suostumus|peru suostumus|hallinnoi suostumusta|tietosuoja-asetukset|"
    r"hantera samtycke|cookieinst[aä]llningar)\b",
    re.I,
)
BANNER_RE = re.compile(
    r"\b(cookie|cookies|ev[aä]ste|ev[aä]steet|kakor|gdpr|consent|suostumus|samtycke|privacy|tietosuoja|"
    r"track|tracking|seuranta|profiling|profilointi)\b",
    re.I,
)
COOKIE_POLICY_RE = re.compile(
    r"\b(cookie policy|cookies policy|cookie notice|ev[aä]stek[aä]yt[aä]nt[oö]|ev[aä]steseloste|"
    r"privacy policy|privacy notice|tietosuojaseloste|tietosuojak[aä]yt[aä]nt[oö]|dataskydd)\b",
    re.I,
)
CATEGORY_RE = re.compile(
    r"\b(necessary|essential|functional|preferences|statistics|analytics|marketing|advertising|personalisation|"
    r"v[aä]ltt[aä]m[aä]tt[oö]m[aä]t|toiminnalliset|mieltymykset|tilastot|analytiikka|markkinointi|mainonta|"
    r"n[oö]dv[aä]ndiga|funktionella|statistik|analys|marknadsf[oö]ring)\b",
    re.I,
)
NON_ESSENTIAL_CATEGORY_RE = re.compile(
    r"\b(statistics|analytics|marketing|advertising|ads|personalisation|personalization|profiling|social|partners|"
    r"tilastot|analytiikka|markkinointi|mainonta|profilointi|kumppanit|"
    r"statistik|analys|marknadsf[oö]ring|annonsering|partners)\b",
    re.I,
)
LEGITIMATE_INTEREST_RE = re.compile(
    r"\b(legitimate interest|legitimate interests|oikeutettu etu|ber[aä]ttigat intresse)\b",
    re.I,
)
COOKIE_WALL_RE = re.compile(
    r"\b(accept.*continue|continue.*accept|accept.*access|hyv[aä]ksy.*jatka|jatka.*hyv[aä]ksym[aä]ll[aä]|"
    r"must accept|pakko hyv[aä]ksy[aä])\b",
    re.I,
)


TRACKER_COOKIE_PATTERNS = [
    (re.compile(r"^_ga(_|$)", re.I), "Google Analytics"),
    (re.compile(r"^_gid$", re.I), "Google Analytics"),
    (re.compile(r"^_gat", re.I), "Google Analytics"),
    (re.compile(r"^_gcl_", re.I), "Google Ads"),
    (re.compile(r"^_fbp$", re.I), "Meta Pixel"),
    (re.compile(r"^fr$", re.I), "Meta Ads"),
    (re.compile(r"^IDE$", re.I), "Google DoubleClick"),
    (re.compile(r"^NID$", re.I), "Google services"),
    (re.compile(r"^MUID$", re.I), "Microsoft Ads/Bing"),
    (re.compile(r"^ANONCHK$", re.I), "Microsoft Ads/Bing"),
    (re.compile(r"^_hj", re.I), "Hotjar"),
    (re.compile(r"^_clck$", re.I), "Microsoft Clarity"),
    (re.compile(r"^_clsk$", re.I), "Microsoft Clarity"),
    (re.compile(r"^hubspotutk$", re.I), "HubSpot"),
    (re.compile(r"^__hst", re.I), "HubSpot"),
    (re.compile(r"^_pin_unauth$", re.I), "Pinterest"),
    (re.compile(r"^(bcookie|bscookie|li_gc|lidc)$", re.I), "LinkedIn"),
    (re.compile(r"^(YSC|VISITOR_INFO1_LIVE|PREF)$", re.I), "YouTube/Google"),
    (re.compile(r"^personalization_id$", re.I), "X/Twitter"),
    (re.compile(r"^amplitude_", re.I), "Amplitude"),
    (re.compile(r"^ajs_", re.I), "Segment"),
]

ESSENTIAL_COOKIE_PATTERNS = [
    (re.compile(r"(session|sessid|phpsessid|jsessionid|asp\.net_sessionid)", re.I), "session"),
    (re.compile(r"(csrf|xsrf|nonce|auth|login|token)", re.I), "security/session"),
    (re.compile(r"(consent|cookie|cck|optanon|cookielawinfo|didomi|onetrust|uc_settings)", re.I), "consent preference"),
    (re.compile(r"(language|locale|lang|font|contrast|theme|preference|prefs)", re.I), "preference"),
    (re.compile(r"(cart|basket|checkout)", re.I), "requested service"),
]

TRACKER_DOMAIN_PATTERNS = [
    ("google-analytics.com", "Google Analytics"),
    ("googletagmanager.com", "Google Tag Manager"),
    ("doubleclick.net", "Google DoubleClick"),
    ("googlesyndication.com", "Google Ads"),
    ("googleadservices.com", "Google Ads"),
    ("facebook.net", "Meta Pixel"),
    ("facebook.com/tr", "Meta Pixel"),
    ("connect.facebook.net", "Meta Pixel"),
    ("analytics.tiktok.com", "TikTok Pixel"),
    ("snap.licdn.com", "LinkedIn Insight"),
    ("linkedin.com/px", "LinkedIn Insight"),
    ("bat.bing.com", "Microsoft Ads"),
    ("clarity.ms", "Microsoft Clarity"),
    ("hotjar.com", "Hotjar"),
    ("hotjar.io", "Hotjar"),
    ("hubspot.com", "HubSpot"),
    ("hs-analytics.net", "HubSpot"),
    ("segment.io", "Segment"),
    ("segment.com", "Segment"),
    ("amplitude.com", "Amplitude"),
    ("mixpanel.com", "Mixpanel"),
    ("pinterest.com", "Pinterest"),
    ("adsrvr.org", "The Trade Desk"),
    ("criteo.com", "Criteo"),
    ("scorecardresearch.com", "Comscore"),
    ("newrelic.com", "New Relic telemetry"),
    ("matomo", "Matomo analytics"),
]


class MissingDependencyError(RuntimeError):
    """Raised when Playwright is not available."""


@dataclass
class ScanConfig:
    url: str
    timeout_seconds: int = 30
    test_reject: bool = True
    test_accept_withdrawal: bool = True
    test_settings: bool = True
    max_policy_pages: int = 2


@dataclass
class ConsentControl:
    text: str
    kind: str
    checked: bool | None = None
    disabled: bool | None = None
    width: float = 0
    height: float = 0
    background: str = ""
    color: str = ""
    tag: str = ""
    role: str = ""

    @property
    def area(self) -> float:
        return max(0, self.width) * max(0, self.height)


@dataclass
class CookieRecord:
    name: str
    domain: str
    path: str
    expires: float
    expires_label: str
    secure: bool
    http_only: bool
    same_site: str
    size: int
    third_party: bool
    classification: str
    reason: str


@dataclass
class StorageRecord:
    storage_type: str
    key: str
    value_preview: str
    size: int
    classification: str
    reason: str


@dataclass
class PolicyEvidence:
    title: str
    url: str
    text_excerpt: str
    has_purpose: bool
    has_duration: bool
    has_third_parties: bool
    has_cookie_table: bool


@dataclass
class PageSnapshot:
    label: str
    url: str
    final_url: str
    title: str
    captured_at: str
    banner_text: str
    controls: list[ConsentControl]
    cookies: list[CookieRecord]
    storage: list[StorageRecord]
    request_domains: list[str]
    tracker_domains: list[str]
    script_urls: list[str]
    policy_links: list[dict[str, str]]
    body_excerpt: str


@dataclass
class Finding:
    severity: str
    title: str
    evidence: str
    recommendation: str
    requirement: str
    confidence: str = "medium"


@dataclass
class ScanSummary:
    score: int
    risk_level: str
    banner_detected: bool
    accept_detected: bool
    reject_detected: bool
    settings_detected: bool
    withdrawal_detected_after_accept: bool | None
    cookies_before_consent: int
    likely_nonessential_before_consent: int
    tracker_domains_before_consent: int
    findings_total: int
    scanned_at: str


@dataclass
class ScanResult:
    scan_version: str
    config: ScanConfig
    initial: PageSnapshot
    after_reject: PageSnapshot | None = None
    settings_snapshot: PageSnapshot | None = None
    after_accept: PageSnapshot | None = None
    after_accept_reload: PageSnapshot | None = None
    policy_evidence: list[PolicyEvidence] = field(default_factory=list)
    reject_clicked: bool = False
    accept_clicked: bool = False
    settings_clicked: bool = False
    summary: ScanSummary | None = None
    findings: list[Finding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def normalize_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    if not url:
        raise ValueError("Anna tarkistettava osoite.")
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError("Osoite ei näytä kelvolliselta.")
    return url


def result_to_json(result: ScanResult) -> str:
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)


def cookies_as_rows(snapshot: PageSnapshot | None) -> list[dict[str, Any]]:
    if snapshot is None:
        return []
    return [
        {
            "nimi": cookie.name,
            "domain": cookie.domain,
            "kesto": cookie.expires_label,
            "luokitus": cookie.classification,
            "kolmas_osapuoli": cookie.third_party,
            "peruste": cookie.reason,
            "secure": cookie.secure,
            "http_only": cookie.http_only,
            "same_site": cookie.same_site,
        }
        for cookie in snapshot.cookies
    ]


def storage_as_rows(snapshot: PageSnapshot | None) -> list[dict[str, Any]]:
    if snapshot is None:
        return []
    return [
        {
            "tyyppi": item.storage_type,
            "avain": item.key,
            "luokitus": item.classification,
            "peruste": item.reason,
            "arvon_alku": item.value_preview,
            "koko": item.size,
        }
        for item in snapshot.storage
    ]


def findings_as_rows(result: ScanResult) -> list[dict[str, str]]:
    return [asdict(finding) for finding in result.findings]


def scan_website(config: ScanConfig) -> ScanResult:
    config.url = normalize_url(config.url)
    return _run_async_scan(config)


def _run_async_scan(config: ScanConfig) -> ScanResult:
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_scan_website_async(config))

    if not running_loop.is_running():
        return running_loop.run_until_complete(_scan_website_async(config))

    holder: dict[str, Any] = {}

    def _runner() -> None:
        try:
            holder["result"] = asyncio.run(_scan_website_async(config))
        except Exception as exc:  # pragma: no cover - thread transport only
            holder["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in holder:
        raise holder["error"]
    return holder["result"]


async def _scan_website_async(config: ScanConfig) -> ScanResult:
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ModuleNotFoundError as exc:
        return _scan_static(
            config,
            "Playwright puuttuu, joten käytössä on rajatumpi staattinen HTML-tarkistus. "
            "Asenna täysi selaintarkistus komennolla: python3 -m pip install playwright && python3 -m playwright install chromium",
            exc,
        )

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception as exc:
            return _scan_static(
                config,
                "Chromium-selaimen käynnistys epäonnistui, joten käytössä on rajatumpi staattinen HTML-tarkistus.",
                exc,
            )
        errors: list[str] = []

        try:
            initial, reject_clicked, policy_evidence = await _run_initial_context(
                browser, config, PlaywrightTimeoutError
            )
        except Exception:
            await browser.close()
            raise

        result = ScanResult(
            scan_version=SCAN_VERSION,
            config=config,
            initial=initial,
            reject_clicked=reject_clicked,
            policy_evidence=policy_evidence,
            errors=errors,
        )

        if config.test_reject and reject_clicked:
            result.after_reject = getattr(initial, "_after_reject", None)
        elif config.test_reject:
            errors.append("Hylkäyspainiketta ei löytynyt automaattista hylkäystestiä varten.")

        if config.test_settings and _has_settings(initial.controls):
            try:
                settings_snapshot, settings_clicked = await _run_action_context(
                    browser,
                    config,
                    action="settings",
                    label="settings",
                    timeout_error=PlaywrightTimeoutError,
                )
                result.settings_snapshot = settings_snapshot
                result.settings_clicked = settings_clicked
            except Exception as exc:
                errors.append(f"Asetusnäkymän testaus epäonnistui: {exc}")

        if config.test_accept_withdrawal:
            try:
                after_accept, after_reload, accept_clicked = await _run_accept_context(
                    browser, config, PlaywrightTimeoutError
                )
                result.after_accept = after_accept
                result.after_accept_reload = after_reload
                result.accept_clicked = accept_clicked
                if not accept_clicked:
                    errors.append("Hyväksymispainiketta ei löytynyt perumistestiä varten.")
            except Exception as exc:
                errors.append(f"Hyväksymis- ja perumistesti epäonnistui: {exc}")

        await browser.close()

    result.findings = audit_scan_result(result)
    result.summary = summarize_scan_result(result)
    return result


async def _new_context(browser: Any, config: ScanConfig) -> Any:
    return await browser.new_context(
        locale="fi-FI",
        timezone_id="Europe/Helsinki",
        viewport={"width": 1366, "height": 900},
        ignore_https_errors=True,
        extra_http_headers={"Accept-Language": "fi-FI,fi;q=0.9,en-US;q=0.8,en;q=0.7"},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36 GDPRScanner/1.0"
        ),
    )


async def _run_initial_context(browser: Any, config: ScanConfig, timeout_error: type[Exception]) -> tuple[PageSnapshot, bool, list[PolicyEvidence]]:
    context = await _new_context(browser, config)
    page, requests = await _open_page(context, config, timeout_error)
    initial = await _collect_snapshot(context, page, requests, "before_consent", config.url)
    policy_evidence = await _collect_policy_evidence(context, initial.policy_links, config, timeout_error)
    reject_clicked = False

    if config.test_reject:
        reject_clicked = await _click_consent_action(page, "reject")
        if reject_clicked:
            await page.wait_for_timeout(2500)
            after_reject = await _collect_snapshot(context, page, requests, "after_reject", config.url)
            setattr(initial, "_after_reject", after_reject)

    await context.close()
    return initial, reject_clicked, policy_evidence


async def _run_accept_context(
    browser: Any, config: ScanConfig, timeout_error: type[Exception]
) -> tuple[PageSnapshot | None, PageSnapshot | None, bool]:
    context = await _new_context(browser, config)
    page, requests = await _open_page(context, config, timeout_error)
    clicked = await _click_consent_action(page, "accept")
    if not clicked:
        await context.close()
        return None, None, False

    await page.wait_for_timeout(2500)
    after_accept = await _collect_snapshot(context, page, requests, "after_accept", config.url)
    try:
        await page.reload(wait_until="domcontentloaded", timeout=config.timeout_seconds * 1000)
        await _soft_network_idle(page)
    except Exception:
        pass
    await page.wait_for_timeout(1500)
    after_reload = await _collect_snapshot(context, page, requests, "after_accept_reload", config.url)
    await context.close()
    return after_accept, after_reload, True


async def _run_action_context(
    browser: Any, config: ScanConfig, action: str, label: str, timeout_error: type[Exception]
) -> tuple[PageSnapshot | None, bool]:
    context = await _new_context(browser, config)
    page, requests = await _open_page(context, config, timeout_error)
    clicked = await _click_consent_action(page, action)
    if not clicked:
        await context.close()
        return None, False
    await page.wait_for_timeout(1500)
    snapshot = await _collect_snapshot(context, page, requests, label, config.url)
    await context.close()
    return snapshot, True


async def _open_page(context: Any, config: ScanConfig, timeout_error: type[Exception]) -> tuple[Any, list[dict[str, str]]]:
    page = await context.new_page()
    requests: list[dict[str, str]] = []

    def _on_request(req: Any) -> None:
        try:
            requests.append({"url": req.url, "resource_type": req.resource_type})
        except Exception:
            pass

    page.on("request", _on_request)
    await page.goto(config.url, wait_until="domcontentloaded", timeout=config.timeout_seconds * 1000)
    await _soft_network_idle(page, timeout_error)
    await page.wait_for_timeout(2500)
    return page, requests


async def _soft_network_idle(page: Any, timeout_error: type[Exception] | None = None) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception as exc:
        if timeout_error and isinstance(exc, timeout_error):
            return
        return


async def _collect_snapshot(
    context: Any, page: Any, requests: list[dict[str, str]], label: str, requested_url: str
) -> PageSnapshot:
    site_host = urlparse(page.url or requested_url).hostname or ""
    raw_cookies = await context.cookies()
    cookies = [_cookie_record(cookie, site_host) for cookie in raw_cookies]

    storage_raw = await _safe_evaluate(
        page,
        """() => {
            const read = (store, type) => {
                const rows = [];
                try {
                    for (let i = 0; i < store.length; i++) {
                        const key = store.key(i);
                        const value = store.getItem(key) || "";
                        rows.push({type, key, value});
                    }
                } catch (e) {}
                return rows;
            };
            return [...read(window.localStorage, "localStorage"), ...read(window.sessionStorage, "sessionStorage")];
        }""",
        [],
    )
    storage = [_storage_record(item) for item in storage_raw or []]

    controls_raw = await _safe_evaluate(page, _CONTROL_JS, [])
    controls = [_control_record(item) for item in controls_raw or []]

    body_text = await _safe_evaluate(
        page,
        """() => (document.body && document.body.innerText || "").replace(/\\s+/g, " ").slice(0, 25000)""",
        "",
    )
    banner_text = _extract_banner_text(body_text or "", controls)
    title = await _safe_title(page)
    policy_links = await _safe_evaluate(page, _POLICY_LINK_JS, [])

    request_domains = sorted({_domain_from_url(item.get("url", "")) for item in requests if _domain_from_url(item.get("url", ""))})
    tracker_domains = sorted({_tracker_domain(item.get("url", "")) for item in requests if _tracker_domain(item.get("url", ""))})
    script_urls = sorted(
        {
            item.get("url", "")
            for item in requests
            if item.get("resource_type") == "script" and item.get("url")
        }
    )[:250]

    return PageSnapshot(
        label=label,
        url=requested_url,
        final_url=page.url,
        title=title,
        captured_at=datetime.now(timezone.utc).isoformat(),
        banner_text=banner_text,
        controls=controls,
        cookies=sorted(cookies, key=lambda c: (c.classification, c.domain, c.name)),
        storage=sorted(storage, key=lambda s: (s.classification, s.storage_type, s.key)),
        request_domains=request_domains,
        tracker_domains=tracker_domains,
        script_urls=script_urls,
        policy_links=policy_links[:20],
        body_excerpt=(body_text or "")[:5000],
    )


_CONTROL_JS = """() => {
    const candidates = Array.from(document.querySelectorAll(
        'button, [role="button"], a, input[type="button"], input[type="submit"], input[type="checkbox"], input[type="radio"], [role="switch"], [aria-checked]'
    ));
    const visible = el => {
        const s = window.getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return s && s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
    };
    const labelFor = el => {
        let txt = '';
        if (el.innerText) txt += ' ' + el.innerText;
        if (el.value) txt += ' ' + el.value;
        if (el.getAttribute('aria-label')) txt += ' ' + el.getAttribute('aria-label');
        if (el.getAttribute('title')) txt += ' ' + el.getAttribute('title');
        if (el.id) {
            try {
                const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                if (lbl && lbl.innerText) txt += ' ' + lbl.innerText;
            } catch (e) {}
        }
        const closest = el.closest('label, li, fieldset, div, section');
        if (closest && closest.innerText && closest.innerText.length < 900) txt += ' ' + closest.innerText;
        return txt.replace(/\\s+/g, ' ').trim().slice(0, 500);
    };
    return candidates.filter(visible).slice(0, 250).map(el => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        const tag = el.tagName.toLowerCase();
        const role = el.getAttribute('role') || '';
        let kind = tag;
        if (tag === 'input') kind = el.type || 'input';
        if (role === 'switch') kind = 'switch';
        let checked = null;
        if ('checked' in el) checked = !!el.checked;
        if (el.getAttribute('aria-checked') !== null) checked = el.getAttribute('aria-checked') === 'true';
        return {
            text: labelFor(el),
            kind,
            checked,
            disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
            width: rect.width,
            height: rect.height,
            background: style.backgroundColor || '',
            color: style.color || '',
            tag,
            role
        };
    });
}"""


_POLICY_LINK_JS = """() => {
    const links = Array.from(document.querySelectorAll('a[href]'));
    return links.map(a => ({
        text: (a.innerText || a.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim().slice(0, 180),
        href: a.href
    })).filter(item => {
        const hay = `${item.text} ${item.href}`.toLowerCase();
        return hay.includes('cookie') || hay.includes('eväste') || hay.includes('evaste') ||
               hay.includes('privacy') || hay.includes('tietosuoja') || hay.includes('dataskydd');
    }).slice(0, 20);
}"""


async def _collect_policy_evidence(
    context: Any, policy_links: list[dict[str, str]], config: ScanConfig, timeout_error: type[Exception]
) -> list[PolicyEvidence]:
    evidence: list[PolicyEvidence] = []
    seen: set[str] = set()
    candidates = []
    for link in policy_links:
        href = link.get("href", "")
        if href and href not in seen:
            candidates.append(link)
            seen.add(href)
        if len(candidates) >= config.max_policy_pages:
            break

    for link in candidates:
        page = await context.new_page()
        try:
            await page.goto(link["href"], wait_until="domcontentloaded", timeout=min(config.timeout_seconds, 15) * 1000)
            await _soft_network_idle(page, timeout_error)
            text = await _safe_evaluate(
                page,
                """() => (document.body && document.body.innerText || "").replace(/\\s+/g, " ").slice(0, 30000)""",
                "",
            )
            title = await _safe_title(page)
            evidence.append(_policy_record(title or link.get("text", ""), page.url, text or ""))
        except Exception:
            continue
        finally:
            await page.close()
    return evidence


async def _click_consent_action(page: Any, action: str) -> bool:
    pattern = {"accept": ACCEPT_RE, "reject": REJECT_RE, "settings": SETTINGS_RE}[action]
    avoid = REJECT_RE if action == "accept" else ACCEPT_RE if action == "reject" else None

    roles = ["button", "link", "checkbox", "switch"]
    for role in roles:
        try:
            locator = page.get_by_role(role, name=pattern).first
            if await locator.count() and await locator.is_visible(timeout=1200):
                text = await _locator_text(locator)
                if avoid and avoid.search(text or ""):
                    continue
                await locator.click(timeout=3000)
                return True
        except Exception:
            pass

    controls = await _safe_evaluate(page, _CLICKABLE_INDEX_JS, [])
    for idx, item in enumerate(controls or []):
        text = item.get("text", "")
        if not pattern.search(text):
            continue
        if avoid and avoid.search(text):
            continue
        try:
            clicked = await page.evaluate(
                """(idx) => {
                    const candidates = Array.from(document.querySelectorAll(
                        'button, [role="button"], a, input[type="button"], input[type="submit"]'
                    )).filter(el => {
                        const s = window.getComputedStyle(el);
                        const r = el.getBoundingClientRect();
                        return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
                    });
                    const el = candidates[idx];
                    if (!el) return false;
                    el.click();
                    return true;
                }""",
                idx,
            )
            if clicked:
                return True
        except Exception:
            continue
    return False


_CLICKABLE_INDEX_JS = """() => {
    const candidates = Array.from(document.querySelectorAll(
        'button, [role="button"], a, input[type="button"], input[type="submit"]'
    ));
    const visible = el => {
        const s = window.getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
    };
    const text = el => `${el.innerText || ''} ${el.value || ''} ${el.getAttribute('aria-label') || ''} ${el.title || ''}`.replace(/\\s+/g, ' ').trim();
    return candidates.filter(visible).map(el => ({text: text(el).slice(0, 250)}));
}"""


async def _locator_text(locator: Any) -> str:
    try:
        return (await locator.inner_text(timeout=1000)) or ""
    except Exception:
        try:
            return (await locator.get_attribute("aria-label", timeout=1000)) or ""
        except Exception:
            return ""


async def _safe_evaluate(page: Any, script: str, fallback: Any) -> Any:
    try:
        return await page.evaluate(script)
    except Exception:
        return fallback


async def _safe_title(page: Any) -> str:
    try:
        return await page.title()
    except Exception:
        return ""


def _cookie_record(cookie: dict[str, Any], site_host: str) -> CookieRecord:
    name = str(cookie.get("name", ""))
    domain = str(cookie.get("domain", ""))
    value = str(cookie.get("value", ""))
    classification, reason = classify_cookie(name, domain, site_host)
    expires = float(cookie.get("expires", -1) or -1)
    return CookieRecord(
        name=name,
        domain=domain,
        path=str(cookie.get("path", "")),
        expires=expires,
        expires_label=_format_expires(expires),
        secure=bool(cookie.get("secure", False)),
        http_only=bool(cookie.get("httpOnly", False)),
        same_site=str(cookie.get("sameSite", "")),
        size=len(name) + len(value),
        third_party=_is_third_party(domain, site_host),
        classification=classification,
        reason=reason,
    )


def _storage_record(item: dict[str, Any]) -> StorageRecord:
    key = str(item.get("key", ""))
    value = str(item.get("value", ""))
    classification, reason = classify_storage(key, value)
    return StorageRecord(
        storage_type=str(item.get("type", "")),
        key=key,
        value_preview=value[:140],
        size=len(key) + len(value),
        classification=classification,
        reason=reason,
    )


def _control_record(item: dict[str, Any]) -> ConsentControl:
    return ConsentControl(
        text=str(item.get("text", "")),
        kind=str(item.get("kind", "")),
        checked=item.get("checked"),
        disabled=item.get("disabled"),
        width=float(item.get("width", 0) or 0),
        height=float(item.get("height", 0) or 0),
        background=str(item.get("background", "")),
        color=str(item.get("color", "")),
        tag=str(item.get("tag", "")),
        role=str(item.get("role", "")),
    )


def _scan_static(config: ScanConfig, reason: str, original_error: Exception | None = None) -> ScanResult:
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise MissingDependencyError("Skannaus tarvitsee joko Playwrightin tai requests-kirjaston.") from exc

    session = requests.Session()
    headers = {
        "Accept-Language": "fi-FI,fi;q=0.9,en-US;q=0.8,en;q=0.7",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 GDPRScanner/1.0"
        ),
    }

    response = session.get(
        config.url,
        headers=headers,
        timeout=config.timeout_seconds,
        allow_redirects=True,
    )
    response.raise_for_status()

    html_text = response.text or ""
    final_url = response.url or config.url
    site_host = urlparse(final_url).hostname or urlparse(config.url).hostname or ""
    body_text = _html_to_text(html_text)
    controls = _static_controls(html_text)
    policy_links = _static_policy_links(html_text, final_url)
    script_urls = _static_script_urls(html_text, final_url)
    cookies = [_cookiejar_record(cookie, site_host) for cookie in session.cookies]
    tracker_domains = sorted({_tracker_domain(url) for url in script_urls if _tracker_domain(url)})
    request_domains = sorted({_domain_from_url(url) for url in script_urls if _domain_from_url(url)})

    initial = PageSnapshot(
        label="before_consent_static",
        url=config.url,
        final_url=final_url,
        title=_static_title(html_text),
        captured_at=datetime.now(timezone.utc).isoformat(),
        banner_text=_extract_banner_text(body_text, controls),
        controls=controls,
        cookies=sorted(cookies, key=lambda c: (c.classification, c.domain, c.name)),
        storage=[],
        request_domains=request_domains,
        tracker_domains=tracker_domains,
        script_urls=script_urls[:250],
        policy_links=policy_links[:20],
        body_excerpt=body_text[:5000],
    )

    policy_evidence = _static_policy_evidence(policy_links, headers, config)
    errors = [reason, "Varatila ei voi klikata banneria, avata asetusmodaalia tai nähdä JavaScriptin myöhemmin asettamia tunnisteita."]
    if original_error:
        errors.append(f"Selainvirhe: {type(original_error).__name__}: {str(original_error)[:300]}")

    result = ScanResult(
        scan_version=SCAN_VERSION,
        config=config,
        initial=initial,
        policy_evidence=policy_evidence,
        errors=errors,
    )
    result.findings = audit_scan_result(result)
    result.summary = summarize_scan_result(result)
    return result


def _cookiejar_record(cookie: Any, site_host: str) -> CookieRecord:
    name = str(getattr(cookie, "name", ""))
    value = str(getattr(cookie, "value", ""))
    domain = str(getattr(cookie, "domain", site_host) or site_host)
    classification, reason = classify_cookie(name, domain, site_host)
    expires = float(getattr(cookie, "expires", -1) or -1)
    rest = getattr(cookie, "_rest", {}) or {}
    return CookieRecord(
        name=name,
        domain=domain,
        path=str(getattr(cookie, "path", "/") or "/"),
        expires=expires,
        expires_label=_format_expires(expires),
        secure=bool(getattr(cookie, "secure", False)),
        http_only="httponly" in {str(key).lower() for key in rest.keys()},
        same_site=str(rest.get("SameSite", rest.get("samesite", ""))),
        size=len(name) + len(value),
        third_party=_is_third_party(domain, site_host),
        classification=classification,
        reason=reason,
    )


def _html_to_text(html_text: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", html_text or "")
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _static_title(html_text: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html_text or "")
    return _html_to_text(match.group(1))[:180] if match else ""


def _static_controls(html_text: str) -> list[ConsentControl]:
    controls: list[ConsentControl] = []
    for match in re.finditer(r"(?is)<button\b[^>]*>(.*?)</button>", html_text or ""):
        text = _html_to_text(match.group(1))
        if text:
            controls.append(ConsentControl(text=text[:500], kind="button"))

    for match in re.finditer(r"(?is)<a\b[^>]*href=['\"][^'\"]+['\"][^>]*>(.*?)</a>", html_text or ""):
        text = _html_to_text(match.group(1))
        if text and (BANNER_RE.search(text) or ACCEPT_RE.search(text) or REJECT_RE.search(text) or SETTINGS_RE.search(text)):
            controls.append(ConsentControl(text=text[:500], kind="link"))

    for match in re.finditer(r"(?is)<input\b([^>]+)>", html_text or ""):
        attrs = match.group(1)
        value_match = re.search(r"""(?:value|aria-label|title)=['"]([^'"]+)['"]""", attrs, re.I)
        input_type = _attr(attrs, "type") or "input"
        text = html_lib.unescape(value_match.group(1)).strip() if value_match else ""
        checked = bool(re.search(r"\bchecked\b", attrs, re.I))
        if text or input_type.lower() in {"checkbox", "radio"}:
            controls.append(ConsentControl(text=text[:500], kind=input_type, checked=checked))

    return controls[:250]


def _static_policy_links(html_text: str, base_url: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for match in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html_text or ""):
        attrs, inner = match.groups()
        href = _attr(attrs, "href")
        if not href:
            continue
        text = _html_to_text(inner)
        absolute = urljoin(base_url, html_lib.unescape(href))
        hay = f"{text} {absolute}"
        if COOKIE_POLICY_RE.search(hay) or any(token in hay.lower() for token in ["cookie", "eväste", "privacy", "tietosuoja", "dataskydd"]):
            links.append({"text": text[:180], "href": absolute})
    return links


def _static_script_urls(html_text: str, base_url: str) -> list[str]:
    urls = []
    for match in re.finditer(r"""(?is)<script\b[^>]*\bsrc=['"]([^'"]+)['"]""", html_text or ""):
        urls.append(urljoin(base_url, html_lib.unescape(match.group(1))))
    return sorted(set(urls))


def _static_policy_evidence(policy_links: list[dict[str, str]], headers: dict[str, str], config: ScanConfig) -> list[PolicyEvidence]:
    try:
        import requests
    except ModuleNotFoundError:
        return []

    evidence: list[PolicyEvidence] = []
    for link in policy_links[: config.max_policy_pages]:
        href = link.get("href", "")
        if not href:
            continue
        try:
            response = requests.get(
                href,
                headers=headers,
                timeout=min(config.timeout_seconds, 15),
                allow_redirects=True,
            )
            response.raise_for_status()
            text = _html_to_text(response.text or "")
            evidence.append(_policy_record(_static_title(response.text) or link.get("text", ""), response.url, text))
        except Exception:
            continue
    return evidence


def _attr(attrs: str, name: str) -> str:
    match = re.search(rf"""\b{name}\s*=\s*(['"])(.*?)\1""", attrs or "", re.I | re.S)
    return match.group(2).strip() if match else ""


def _policy_record(title: str, url: str, text: str) -> PolicyEvidence:
    lowered = text.lower()
    has_purpose = bool(re.search(r"\b(purpose|purposes|tarkoitus|käyttötarkoitus|ändamål)\b", lowered))
    has_duration = bool(re.search(r"\b(duration|expires|expiry|retention|kesto|voimassa|säilytys|vanhenee|varaktighet)\b", lowered))
    has_third_parties = bool(re.search(r"\b(third[- ]party|third parties|partners|recipients|kolmas|kolmannet|kumppanit|mottagare|tredje)\b", lowered))
    has_cookie_table = bool(re.search(r"\b(name|service|domain|cookie type|nimi|palvelu|domain|verkkotunnus|tyyppi)\b", lowered)) and len(text) > 500
    return PolicyEvidence(
        title=title[:180],
        url=url,
        text_excerpt=text[:1200],
        has_purpose=has_purpose,
        has_duration=has_duration,
        has_third_parties=has_third_parties,
        has_cookie_table=has_cookie_table,
    )


def classify_cookie(name: str, domain: str, site_host: str) -> tuple[str, str]:
    for pattern, vendor in TRACKER_COOKIE_PATTERNS:
        if pattern.search(name):
            return "likely_nonessential", f"Tunnettu analytiikka-/mainontaeväste: {vendor}"

    third_party = _is_third_party(domain, site_host)
    for pattern, purpose in ESSENTIAL_COOKIE_PATTERNS:
        if pattern.search(name):
            return "likely_essential_or_preference", f"Vaikuttaa {purpose}-evästeeltä"

    tracker_vendor = _tracker_domain(domain)
    if tracker_vendor:
        return "likely_nonessential", f"Tunnettu seuranta-/mainontadomain: {tracker_vendor}"

    if third_party:
        return "unknown_third_party", "Kolmannen osapuolen eväste, tarkoitus varmistettava dokumentaatiosta"

    return "unknown_first_party", "Ensimmäisen osapuolen eväste, tarkoitus varmistettava dokumentaatiosta"


def classify_storage(key: str, value: str) -> tuple[str, str]:
    hay = f"{key} {value[:200]}".lower()
    tracker_tokens = [
        "google_analytics",
        "ga:",
        "_ga",
        "gtm",
        "fbp",
        "facebook",
        "pixel",
        "hotjar",
        "clarity",
        "hubspot",
        "amplitude",
        "mixpanel",
        "segment",
        "intercom",
        "ads",
        "marketing",
    ]
    if any(token in hay for token in tracker_tokens):
        return "likely_nonessential", "Tallenne viittaa analytiikkaan, mainontaan tai seurantaan"
    if any(token in hay for token in ["consent", "cookie", "preference", "language", "locale", "theme", "session"]):
        return "likely_essential_or_preference", "Tallenne vaikuttaa suostumus-, kieli- tai istuntoasetukselta"
    return "unknown_storage", "Selaintallenteen tarkoitus varmistettava dokumentaatiosta"


def audit_scan_result(result: ScanResult) -> list[Finding]:
    findings: list[Finding] = []
    initial = result.initial

    banner_detected = _has_banner(initial)
    accept_controls = _matching_controls(initial.controls, ACCEPT_RE, avoid=REJECT_RE)
    reject_controls = _matching_controls(initial.controls, REJECT_RE, avoid=ACCEPT_RE)
    settings_controls = _matching_controls(initial.controls, SETTINGS_RE)
    nonessential_initial = _nonessential_cookies(initial)
    nonessential_storage = _nonessential_storage(initial)
    tracker_domains = initial.tracker_domains

    if nonessential_initial:
        findings.append(
            Finding(
                "high",
                "Ei-välttämättömiä evästeitä asetetaan ennen valintaa",
                _cookie_evidence(nonessential_initial),
                "Estä analytiikka-, mainonta- ja muut ei-välttämättömät evästeet ennen kuin käyttäjä on antanut aktiivisen suostumuksen.",
                "ePrivacy Art. 5(3) ja GDPR-suostumuksen ehdot",
                "high",
            )
        )

    if nonessential_storage:
        findings.append(
            Finding(
                "high",
                "Selaimen tallennustilaan kirjoitetaan mahdollisia seurantatietoja ennen suostumusta",
                _storage_evidence(nonessential_storage),
                "Siirrä localStorage/sessionStorage-pohjainen analytiikka ja profilointi suostumuksen taakse.",
                "ePrivacy koskee evästeiden lisäksi myös päätelaitteen tietojen tallentamista ja lukemista",
                "medium",
            )
        )

    if tracker_domains:
        findings.append(
            Finding(
                "medium",
                "Tunnettuja seuranta- tai mainontadomaineja latautuu ennen valintaa",
                ", ".join(tracker_domains[:12]),
                "Varmista, ettei näillä skripteillä aseteta tai lueta tunnisteita ennen suostumusta. Lataa markkinointi- ja analytiikkaskriptit vasta valinnan jälkeen.",
                "Tietoinen ja vapaaehtoinen ennakkosuostumus ennen ei-välttämätöntä seurantaa",
                "medium",
            )
        )

    if not banner_detected and (nonessential_initial or nonessential_storage or tracker_domains):
        findings.append(
            Finding(
                "high",
                "Evästebanneria ei havaittu, vaikka seurantaa näyttää tapahtuvan",
                "Sivulta ei löytynyt näkyvää eväste-/suostumuskerrosta ensimmäisellä latauksella.",
                "Näytä selkeä suostumuskerros ennen ei-välttämätöntä tallennusta tai lukemista.",
                "ePrivacy Art. 5(3): selkeä tieto ja suostumus ennen tallennusta/lukemista",
                "medium",
            )
        )

    if banner_detected and accept_controls and not reject_controls:
        findings.append(
            Finding(
                "high",
                "Ensimmäiseltä tasolta puuttuu hylkäämisvalinta",
                f"Hyväksymisvalintoja löytyi {len(accept_controls)}, mutta selkeää 'hylkää kaikki' -valintaa ei löytynyt.",
                "Lisää ensimmäiselle tasolle hyväksymisen kanssa yhtä helposti käytettävä 'Hylkää kaikki' tai 'Vain välttämättömät'.",
                "EDPB Cookie Banner Taskforce: käyttäjälle on annettava aito ja tasapainoinen valinta",
                "medium",
            )
        )

    if banner_detected and accept_controls and reject_controls and _accept_more_prominent(accept_controls, reject_controls):
        findings.append(
            Finding(
                "medium",
                "Hyväksymispainike näyttää hylkäämistä korostetummalta",
                "Painikkeiden koko- tai taustavärivihjeet näyttävät ohjaavan käyttäjää hyväksymään.",
                "Tee hyväksymisestä ja hylkäämisestä visuaalisesti tasapainoiset: sama kerros, sama painoarvo, ei harhaanjohtavaa värikontrastia.",
                "GDPR: suostumuksen on oltava vapaaehtoinen; dark pattern -riski",
                "low",
            )
        )

    if banner_detected and not settings_controls and accept_controls:
        findings.append(
            Finding(
                "medium",
                "Asetus- tai tarkoituskohtainen valinta ei näy ensimmäisellä tasolla",
                "Skanneri ei löytänyt evästeasetusten tai tarkoituskohtaisten valintojen avausta.",
                "Tarjoa käyttäjälle selkeä tapa valita tarkoituskohtaisesti, esimerkiksi välttämättömät, analytiikka ja markkinointi erikseen.",
                "GDPR: suostumuksen on oltava yksilöity ja tietoinen",
                "medium",
            )
        )

    settings_snapshot = result.settings_snapshot
    if settings_snapshot:
        prechecked = _prechecked_nonessential(settings_snapshot.controls)
        if prechecked:
            findings.append(
                Finding(
                    "high",
                    "Ei-välttämättömiä tarkoituksia on valittu valmiiksi",
                    "; ".join(ctrl.text[:120] for ctrl in prechecked[:5]),
                    "Poista ennakkovalinnat analytiikasta, markkinoinnista, profiloinnista ja kumppanivalinnoista. Käyttäjän pitää tehdä aktiivinen myöntävä valinta.",
                    "GDPR Art. 4(11) ja EDPB Guidelines 05/2020: pre-ticked opt-in ei ole pätevä suostumus",
                    "high",
                )
            )

        if not CATEGORY_RE.search(settings_snapshot.body_excerpt + " " + " ".join(c.text for c in settings_snapshot.controls)):
            findings.append(
                Finding(
                    "medium",
                    "Asetusnäkymässä ei näy selkeitä evästekategorioita",
                    "Skanneri ei löytänyt kategoriatermejä, kuten välttämättömät, analytiikka tai markkinointi.",
                    "Nimeä tarkoitukset selkeästi ja vältä yleisiä ilmaisuja kuten 'parempi käyttökokemus' ilman tarkkaa tarkoitusta.",
                    "GDPR: suostumuksen on oltava yksilöity ja tietoinen",
                    "medium",
                )
            )

    text_for_legal_basis = _combined_text(initial, settings_snapshot)
    if LEGITIMATE_INTEREST_RE.search(text_for_legal_basis):
        findings.append(
            Finding(
                "high",
                "Banneri viittaa oikeutettuun etuun eväste-/seurantakontekstissa",
                "Tekstistä löytyi 'legitimate interest' / 'oikeutettu etu'.",
                "Älä käytä oikeutettua etua perusteena evästeiden tai vastaavien tunnisteiden asettamiseen/lukemiseen, kun ePrivacy edellyttää suostumusta.",
                "EDPB Cookie Banner Taskforce: evästeiden sijoittamisen/lukemisen oikeusperuste ei voi olla oikeutettu etu",
                "medium",
            )
        )

    if COOKIE_WALL_RE.search(text_for_legal_basis) and not reject_controls:
        findings.append(
            Finding(
                "high",
                "Mahdollinen evästemuuri",
                "Banneriteksti näyttää kytkevän palvelun jatkamisen hyväksymiseen, eikä hylkäysvalintaa löytynyt.",
                "Varmista, että palvelua voi käyttää ilman ei-välttämätöntä seurantaa, ellei poikkeuksellinen maksullinen vaihtoehto tai muu kansallinen linjaus ole erikseen arvioitu.",
                "GDPR: suostumuksen on oltava vapaaehtoinen; EDPB Guidelines 05/2020 cookie walls",
                "medium",
            )
        )

    if result.after_reject:
        rejected_nonessential = _nonessential_cookies(result.after_reject)
        rejected_storage = _nonessential_storage(result.after_reject)
        if rejected_nonessential or rejected_storage:
            findings.append(
                Finding(
                    "high",
                    "Hylkäyksen jälkeen jää mahdollisia ei-välttämättömiä tunnisteita",
                    _cookie_evidence(rejected_nonessential) or _storage_evidence(rejected_storage),
                    "Hylkäyksen jälkeen saa jäädä vain välttämättömät ja suostumusvalinnan muistamiseen tarvittavat tunnisteet.",
                    "Suostumuksen hylkäämisen pitää estää ei-välttämätön seuranta",
                    "medium",
                )
            )

    withdrawal = _withdrawal_detected(result.after_accept_reload)
    if result.accept_clicked and withdrawal is False:
        findings.append(
            Finding(
                "high",
                "Suostumuksen peruminen ei löydy helposti hyväksymisen jälkeen",
                "Hyväksymisen ja sivun uudelleenlatauksen jälkeen skanneri ei löytänyt näkyvää evästeasetusten/perumisen linkkiä tai painiketta.",
                "Lisää pysyvästi näkyvä tai helposti löydettävä linkki, jolla käyttäjä pääsee muuttamaan tai perumaan suostumuksen samalla helppoudella kuin hän antoi sen.",
                "GDPR Art. 7(3) ja EDPB: perumisen on oltava mahdollista milloin tahansa ja yhtä helppoa kuin antamisen",
                "medium",
            )
        )

    if not _has_cookie_policy(initial, result.policy_evidence):
        findings.append(
            Finding(
                "medium",
                "Evästekäytäntöä tai tietosuojaselostetta ei löytynyt helposti",
                "Ensimmäiseltä sivulta ei löytynyt selkeää eväste-/tietosuojalinkkiä eikä policy-sivua saatu avattua.",
                "Lisää näkyvä evästekäytäntö tai tietosuojaseloste, jossa kerrotaan evästeiden nimet, tarkoitukset, kestot ja kolmannet osapuolet.",
                "Läpinäkyvyys ja tietoinen suostumus",
                "medium",
            )
        )
    else:
        info_finding = _policy_information_finding(result.policy_evidence, initial)
        if info_finding:
            findings.append(info_finding)

    if not findings:
        findings.append(
            Finding(
                "info",
                "Selkeitä teknisiä riskihavaintoja ei löytynyt",
                "Automaattinen tarkistus ei havainnut ennakkoseurantaa tai ilmeisiä banneriongelmia.",
                "Tee silti manuaalinen tarkistus evästedokumentaatiolle, kumppanilistalle, consent log -todisteelle ja kansallisen lainsäädännön erityisvaatimuksille.",
                "Tekninen tarkistus ei korvaa juridista arviota",
                "medium",
            )
        )

    return sorted(findings, key=lambda item: _severity_rank(item.severity))


def summarize_scan_result(result: ScanResult) -> ScanSummary:
    initial = result.initial
    high = sum(1 for finding in result.findings if finding.severity == "high")
    medium = sum(1 for finding in result.findings if finding.severity == "medium")
    low = sum(1 for finding in result.findings if finding.severity == "low")
    score = max(0, 100 - (high * 22) - (medium * 10) - (low * 4))
    if score >= 85:
        risk = "Matala"
    elif score >= 65:
        risk = "Kohtalainen"
    elif score >= 40:
        risk = "Korkea"
    else:
        risk = "Erittäin korkea"

    return ScanSummary(
        score=score,
        risk_level=risk,
        banner_detected=_has_banner(initial),
        accept_detected=bool(_matching_controls(initial.controls, ACCEPT_RE, avoid=REJECT_RE)),
        reject_detected=bool(_matching_controls(initial.controls, REJECT_RE, avoid=ACCEPT_RE)),
        settings_detected=_has_settings(initial.controls),
        withdrawal_detected_after_accept=_withdrawal_detected(result.after_accept_reload),
        cookies_before_consent=len(initial.cookies),
        likely_nonessential_before_consent=len(_nonessential_cookies(initial)) + len(_nonessential_storage(initial)),
        tracker_domains_before_consent=len(initial.tracker_domains),
        findings_total=len(result.findings),
        scanned_at=datetime.now(timezone.utc).isoformat(),
    )


def _has_banner(snapshot: PageSnapshot) -> bool:
    if BANNER_RE.search(snapshot.banner_text or ""):
        return True
    text = " ".join(control.text for control in snapshot.controls[:80])
    return bool(BANNER_RE.search(text) and (_matching_controls(snapshot.controls, ACCEPT_RE) or _matching_controls(snapshot.controls, REJECT_RE)))


def _has_settings(controls: list[ConsentControl]) -> bool:
    return bool(_matching_controls(controls, SETTINGS_RE))


def _matching_controls(
    controls: list[ConsentControl], pattern: re.Pattern[str], avoid: re.Pattern[str] | None = None
) -> list[ConsentControl]:
    matches: list[ConsentControl] = []
    for control in controls:
        text = control.text or ""
        if not text or not pattern.search(text):
            continue
        if avoid and avoid.search(text):
            continue
        matches.append(control)
    return matches


def _nonessential_cookies(snapshot: PageSnapshot) -> list[CookieRecord]:
    return [
        cookie
        for cookie in snapshot.cookies
        if cookie.classification in {"likely_nonessential", "unknown_third_party"}
    ]


def _nonessential_storage(snapshot: PageSnapshot) -> list[StorageRecord]:
    return [item for item in snapshot.storage if item.classification == "likely_nonessential"]


def _prechecked_nonessential(controls: list[ConsentControl]) -> list[ConsentControl]:
    results = []
    for control in controls:
        if control.checked is not True:
            continue
        text = control.text or ""
        if NON_ESSENTIAL_CATEGORY_RE.search(text):
            results.append(control)
    return results


def _accept_more_prominent(accept_controls: list[ConsentControl], reject_controls: list[ConsentControl]) -> bool:
    accept = max(accept_controls, key=lambda c: c.area, default=None)
    reject = max(reject_controls, key=lambda c: c.area, default=None)
    if not accept or not reject:
        return False
    if accept.area > max(1, reject.area) * 1.8:
        return True
    if _looks_filled(accept.background) and not _looks_filled(reject.background):
        return True
    return False


def _looks_filled(background: str) -> bool:
    nums = [int(value) for value in re.findall(r"\d+", background or "")[:3]]
    if len(nums) < 3:
        return False
    return sum(nums) < 690


def _withdrawal_detected(snapshot: PageSnapshot | None) -> bool | None:
    if snapshot is None:
        return None
    hay = f"{snapshot.body_excerpt} {' '.join(control.text for control in snapshot.controls)}"
    return bool(WITHDRAW_RE.search(hay))


def _combined_text(*snapshots: PageSnapshot | None) -> str:
    parts = []
    for snapshot in snapshots:
        if not snapshot:
            continue
        parts.append(snapshot.banner_text)
        parts.append(snapshot.body_excerpt)
        parts.extend(control.text for control in snapshot.controls)
    return " ".join(parts)


def _has_cookie_policy(initial: PageSnapshot, evidence: list[PolicyEvidence]) -> bool:
    if evidence:
        return True
    if initial.policy_links:
        return True
    hay = f"{initial.body_excerpt} {' '.join(control.text for control in initial.controls)}"
    return bool(COOKIE_POLICY_RE.search(hay))


def _policy_information_finding(evidence: list[PolicyEvidence], initial: PageSnapshot) -> Finding | None:
    if not evidence:
        return None

    has_purpose = any(item.has_purpose for item in evidence)
    has_duration = any(item.has_duration for item in evidence)
    has_third = any(item.has_third_parties for item in evidence)
    has_table = any(item.has_cookie_table for item in evidence)
    missing = []
    if not has_purpose:
        missing.append("tarkoitukset")
    if not has_duration:
        missing.append("kestot")
    if not has_third:
        missing.append("kolmannet osapuolet / vastaanottajat")
    if not has_table and initial.cookies:
        missing.append("selkeä evästeluettelo")

    if not missing:
        return None

    return Finding(
        "medium",
        "Evästedokumentaatiossa voi olla puutteita",
        "Puuttuvat tai heikosti havaittavat tiedot: " + ", ".join(missing) + ".",
        "Varmista, että evästekäytännössä on vähintään evästeen nimi, tarjoaja/domain, tarkoitus, kesto, tyyppi ja tieto kolmansien osapuolten pääsystä.",
        "Tietoinen suostumus ja läpinäkyvyys; Planet49-linjaus keston ja kolmansien osapuolten tiedoista",
        "low",
    )


def _extract_banner_text(body_text: str, controls: list[ConsentControl]) -> str:
    if not body_text:
        return ""
    matches = list(BANNER_RE.finditer(body_text))
    if matches:
        start = max(0, matches[0].start() - 500)
        end = min(len(body_text), matches[0].end() + 2500)
        return body_text[start:end].strip()

    control_text = " ".join(control.text for control in controls[:50])
    if BANNER_RE.search(control_text):
        return control_text[:2500]
    return ""


def _cookie_evidence(cookies: list[CookieRecord]) -> str:
    if not cookies:
        return ""
    return "; ".join(f"{cookie.name} ({cookie.domain}, {cookie.reason})" for cookie in cookies[:8])


def _storage_evidence(items: list[StorageRecord]) -> str:
    if not items:
        return ""
    return "; ".join(f"{item.storage_type}:{item.key} ({item.reason})" for item in items[:8])


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2, "info": 3}.get(severity, 4)


def _format_expires(expires: float) -> str:
    if expires in (-1, 0) or expires < 0:
        return "Istunto"
    try:
        return datetime.fromtimestamp(expires, timezone.utc).date().isoformat()
    except Exception:
        return str(expires)


def _domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.hostname or "").lower()


def _tracker_domain(url_or_domain: str) -> str:
    hay = (url_or_domain or "").lower()
    for token, vendor in TRACKER_DOMAIN_PATTERNS:
        if token in hay:
            return vendor
    return ""


def _is_third_party(domain: str, site_host: str) -> bool:
    d1 = _root_domain(domain)
    d2 = _root_domain(site_host)
    if not d1 or not d2:
        return False
    return d1 != d2


def _root_domain(host: str) -> str:
    host = (host or "").lower().strip(".")
    if not host:
        return ""
    if host.startswith("."):
        host = host[1:]
    labels = [part for part in host.split(".") if part]
    if len(labels) <= 2:
        return ".".join(labels)
    second_level = {"co", "com", "org", "net", "gov", "ac", "edu"}
    if labels[-2] in second_level and len(labels[-1]) == 2 and len(labels) >= 3:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def absolute_policy_url(base_url: str, href: str) -> str:
    return urljoin(base_url, href)
