import unittest
from unittest.mock import patch

import tabs
from models import TrackedItem


class AIFallbackTests(unittest.TestCase):
    def setUp(self):
        self.item = TrackedItem(
            company="S-pankki",
            role="Suunnittelija",
            status="Odottaa",
            date="01.07.2026",
            contact_name="Laura",
        )

    def test_followup_email_falls_back_to_ready_template_on_ai_error(self):
        with patch.object(tabs, "call_ai", return_value=(None, "AI ei vastaa")):
            draft = tabs._draft_followup_email(self.item, 14, "LOCAL_GEMMA_ACTIVE")

        self.assertIn("Hei Laura", draft)
        self.assertIn("S-pankki", draft)
        self.assertIn("Ystävällisin terveisin", draft)
        self.assertNotIn("AI ei vastaa", draft)

    def test_followup_email_keeps_successful_ai_answer(self):
        ai_answer = (
            "Aihe: Hakemukseni tilanne\n\nHei Laura,\n\n"
            "Haluaisin tiedustella rekrytointiprosessin tilannetta. "
            "Olen edelleen kiinnostunut tehtävästä."
        )
        with patch.object(tabs, "call_ai", return_value=(ai_answer, None)):
            draft = tabs._draft_followup_email(self.item, 14, "LOCAL_GEMMA_ACTIVE")

        self.assertEqual(draft, ai_answer)

    def test_followup_email_repairs_mojibake_from_ai(self):
        broken = (
            "Aihe: Hakemukseni tilanne\n\nHei Laura,\n\n"
            "Haluaisin kysyÃ¤, onko rekrytointiprosessista pÃ¤ivitystÃ¤. "
            "Olen erittÃ¤in kiinnostunut tehtÃ¤vÃ¤stÃ¤."
        )
        with patch.object(tabs, "call_ai", return_value=(broken, None)):
            draft = tabs._draft_followup_email(self.item, 14, "LOCAL_GEMMA_ACTIVE")

        self.assertIn("kysyä", draft)
        self.assertIn("päivitystä", draft)
        self.assertNotIn("Ã", draft)


if __name__ == "__main__":
    unittest.main()
