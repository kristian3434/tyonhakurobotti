import unittest
from unittest.mock import patch

import pandas as pd

import sheets
import settings_manager
from config import PORTFOLIO_URL, SIMULATED_API_KEY, VISITOR_DATA_ENABLED
from router import call_demo


class PublicDemoTests(unittest.TestCase):
    def test_simulated_key_is_obviously_non_secret(self):
        self.assertEqual(SIMULATED_API_KEY, "demo-api-key-not-a-real-secret")

    def test_demo_answer_does_not_make_network_calls(self):
        with (
            patch("router.requests.get") as get,
            patch("router.requests.post") as post,
        ):
            text, error = call_demo("Analysoi tämä ilmoitus")

        self.assertIsNone(error)
        self.assertIn("simuloitiin paikallisesti", text)
        get.assert_not_called()
        post.assert_not_called()

    def test_visitor_data_integration_is_disabled(self):
        self.assertFalse(VISITOR_DATA_ENABLED)
        with patch.object(sheets.requests, "get") as get:
            data = sheets.load_visitor_data()

        self.assertIsInstance(data, pd.DataFrame)
        self.assertTrue(data.empty)
        get.assert_not_called()

    def test_portfolio_url_falls_back_to_public_site(self):
        self.assertEqual(
            PORTFOLIO_URL,
            "https://tulevaisuudentekija.janmyllymaki.workers.dev/",
        )
        with patch.object(
            settings_manager,
            "get_settings",
            return_value={"portfolio_url": ""},
        ):
            self.assertEqual(settings_manager.get_portfolio_url(), PORTFOLIO_URL)


if __name__ == "__main__":
    unittest.main()
