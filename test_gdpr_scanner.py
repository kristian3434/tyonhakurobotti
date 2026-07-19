import unittest

from gdpr_scanner import (
    ConsentControl,
    CookieRecord,
    PageSnapshot,
    ScanConfig,
    ScanResult,
    audit_scan_result,
    classify_cookie,
    normalize_url,
    summarize_scan_result,
)


def _snapshot(label="before_consent", controls=None, cookies=None, body="", banner=""):
    return PageSnapshot(
        label=label,
        url="https://example.com",
        final_url="https://example.com",
        title="Example",
        captured_at="2026-07-03T00:00:00+00:00",
        banner_text=banner,
        controls=controls or [],
        cookies=cookies or [],
        storage=[],
        request_domains=[],
        tracker_domains=[],
        script_urls=[],
        policy_links=[],
        body_excerpt=body,
    )


def _cookie(name, domain="example.com", classification="unknown_first_party", reason="test"):
    return CookieRecord(
        name=name,
        domain=domain,
        path="/",
        expires=-1,
        expires_label="Istunto",
        secure=True,
        http_only=False,
        same_site="Lax",
        size=12,
        third_party=domain != "example.com",
        classification=classification,
        reason=reason,
    )


class GdprScannerTests(unittest.TestCase):
    def test_normalize_url_adds_https(self):
        self.assertEqual(normalize_url("example.com"), "https://example.com")

    def test_classifies_known_tracking_cookie(self):
        classification, reason = classify_cookie("_ga", "example.com", "example.com")

        self.assertEqual(classification, "likely_nonessential")
        self.assertIn("Google Analytics", reason)

    def test_classifies_consent_cookie_as_preference(self):
        classification, reason = classify_cookie("CookieConsent", "example.com", "example.com")

        self.assertEqual(classification, "likely_essential_or_preference")
        self.assertIn("consent", reason)

    def test_audit_flags_tracking_before_consent_and_missing_reject(self):
        initial = _snapshot(
            banner="We use cookies to personalize ads.",
            controls=[ConsentControl(text="Accept all", kind="button")],
            cookies=[_cookie("_ga", classification="likely_nonessential", reason="Google Analytics")],
        )
        result = ScanResult(scan_version="test", config=ScanConfig(url="https://example.com"), initial=initial)

        titles = [finding.title for finding in audit_scan_result(result)]

        self.assertIn("Ei-välttämättömiä evästeitä asetetaan ennen valintaa", titles)
        self.assertIn("Ensimmäiseltä tasolta puuttuu hylkäämisvalinta", titles)

    def test_audit_flags_reject_that_leaves_tracking_cookie(self):
        initial = _snapshot(
            banner="We use cookies.",
            controls=[
                ConsentControl(text="Accept all", kind="button"),
                ConsentControl(text="Reject all", kind="button"),
            ],
        )
        after_reject = _snapshot(
            label="after_reject",
            cookies=[_cookie("_fbp", classification="likely_nonessential", reason="Meta Pixel")],
        )
        result = ScanResult(
            scan_version="test",
            config=ScanConfig(url="https://example.com"),
            initial=initial,
            after_reject=after_reject,
            reject_clicked=True,
        )

        titles = [finding.title for finding in audit_scan_result(result)]

        self.assertIn("Hylkäyksen jälkeen jää mahdollisia ei-välttämättömiä tunnisteita", titles)

    def test_audit_flags_prechecked_marketing_toggle(self):
        initial = _snapshot(
            banner="We use cookies.",
            controls=[
                ConsentControl(text="Accept all", kind="button"),
                ConsentControl(text="Reject all", kind="button"),
                ConsentControl(text="Cookie settings", kind="button"),
            ],
        )
        settings = _snapshot(
            label="settings",
            controls=[ConsentControl(text="Marketing partners", kind="checkbox", checked=True)],
        )
        result = ScanResult(
            scan_version="test",
            config=ScanConfig(url="https://example.com"),
            initial=initial,
            settings_snapshot=settings,
            settings_clicked=True,
        )

        titles = [finding.title for finding in audit_scan_result(result)]

        self.assertIn("Ei-välttämättömiä tarkoituksia on valittu valmiiksi", titles)

    def test_summary_penalizes_high_findings(self):
        initial = _snapshot(
            banner="We use cookies to personalize ads.",
            controls=[ConsentControl(text="Accept all", kind="button")],
            cookies=[_cookie("_ga", classification="likely_nonessential", reason="Google Analytics")],
        )
        result = ScanResult(scan_version="test", config=ScanConfig(url="https://example.com"), initial=initial)
        result.findings = audit_scan_result(result)
        summary = summarize_scan_result(result)

        self.assertLess(summary.score, 100)
        self.assertGreaterEqual(summary.findings_total, 1)


if __name__ == "__main__":
    unittest.main()
