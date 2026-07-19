import unittest
from unittest.mock import Mock, patch

import router


class RouterTests(unittest.TestCase):
    def test_normalizes_common_engine_names(self):
        cases = {
            "Demo (simuloitu API)": "demo",
            "Gemini": "demo",
            "Claude": "demo",
            "Anthropic Claude": "demo",
            "ChatGPT": "demo",
            "OpenAI": "demo",
            "GPT-4o": "demo",
            "Gemma 4 12B paikallinen": "local",
            "LM Studio": "local",
            None: "demo",
            "tuntematon": "demo",
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(router._normalize_engine(raw), expected)

    def test_local_engine_uses_call_local(self):
        with (
            patch.object(
                router.st,
                "session_state",
                {"ai_engine": "Gemma 4 12B paikallinen"},
            ),
            patch.object(router, "call_local", return_value=("local", None)) as call_local,
        ):
            self.assertEqual(router.call_ai("prompt"), ("local", None))
            call_local.assert_called_once_with("prompt")

    def test_demo_engine_returns_simulated_answer_without_network(self):
        with (
            patch.object(
                router.st,
                "session_state",
                {"ai_engine": "Demo (simuloitu API)"},
            ),
            patch.object(router.requests, "get") as get,
            patch.object(router.requests, "post") as post,
        ):
            text, error = router.call_ai("Kirjoita työhakemus")

        self.assertIsNone(error)
        self.assertIn("simuloitiin paikallisesti", text)
        get.assert_not_called()
        post.assert_not_called()

    def test_stream_uses_demo_provider(self):
        with (
            patch.object(
                router.st,
                "session_state",
                {"ai_engine": "Demo (simuloitu API)"},
            ),
        ):
            chunks = list(router.stream_ai("prompt"))

        self.assertEqual(len(chunks), 1)
        self.assertIn("oikeat pilvipalvelut", chunks[0])

    def test_local_status_selects_loaded_language_model(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "models": [
                {
                    "type": "embedding",
                    "loaded_instances": [{"id": "embed-model"}],
                },
                {
                    "type": "llm",
                    "loaded_instances": [],
                },
                {
                    "type": "llm",
                    "loaded_instances": [{"id": "google/gemma-local"}],
                },
            ]
        }

        with patch.object(router.requests, "get", return_value=response):
            available, model, message = router.local_server_status()

        self.assertTrue(available)
        self.assertEqual(model, "google/gemma-local")
        self.assertEqual(message, "Yhteys kunnossa.")

    def test_local_status_rejects_server_without_loaded_llm(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "models": [{"type": "llm", "loaded_instances": []}]
        }

        with patch.object(router.requests, "get", return_value=response):
            available, model, message = router.local_server_status()

        self.assertFalse(available)
        self.assertIsNone(model)
        self.assertIn("kielimallia ei ole ladattu", message)

    def test_local_stream_uses_sse_and_loaded_model_identifier(self):
        response = Mock()
        response.iter_lines.return_value = [
            'data: {"choices":[{"delta":{"content":"Hei"}}]}'.encode("utf-8"),
            'data: {"choices":[{"delta":{"content":" maailma, hyvää päivää"}}]}'.encode("utf-8"),
            b"data: [DONE]",
        ]

        with (
            patch.object(
                router,
                "local_server_status",
                return_value=(True, "google/gemma-local", "Yhteys kunnossa."),
            ),
            patch.object(router.requests, "post", return_value=response) as post,
        ):
            chunks = list(router._iter_local_chunks("Tervehdi"))

        self.assertEqual(chunks, ["Hei", " maailma, hyvää päivää"])
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "google/gemma-local")
        self.assertTrue(payload["stream"])
        response.iter_lines.assert_called_once_with(decode_unicode=False)
        response.close.assert_called_once()

    def test_repairs_utf8_mojibake(self):
        broken = "Olen hakenut sisÃ¤llÃ¶ntuottajan paikkaa ja haluaisin kysyÃ¤ pÃ¤ivitystÃ¤."
        repaired = router.repair_text_encoding(broken)

        self.assertEqual(
            repaired,
            "Olen hakenut sisällöntuottajan paikkaa ja haluaisin kysyä päivitystä.",
        )

    def test_call_local_returns_friendly_error_when_server_is_offline(self):
        with patch.object(
            router,
            "local_server_status",
            return_value=(False, None, "LM Studio ei vastaa portissa 1234."),
        ):
            text, error = router.call_local("prompt")

        self.assertIsNone(text)
        self.assertIn("LM Studio ei vastaa portissa 1234", error)
        self.assertNotIn("HTTPConnectionPool", error)


if __name__ == "__main__":
    unittest.main()
