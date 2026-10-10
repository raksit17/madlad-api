"""Mock Ollama tests: do not download models or require a GPU."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.experimental.qwen.translator import QwenTranslator
from app.services.errors import (
    BatchTooLargeError,
    InputTooLongError,
    TranslationBackendError,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class QwenProviderTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            _env_file=None,
            translation_provider="qwen",
            qwen_model="qwen3.5:4b",
            qwen_base_url="http://localhost:11434",
            qwen_max_input_chars=64,
            max_batch_size=2,
        )
        self.answer = {
            "message": {"content": "ฉันอาจจะพอรู้อยู่บ้างก็ได้"},
            "prompt_eval_count": 52,
            "eval_count": 18,
            "done_reason": "stop",
        }

    def build_provider(self):
        provider = QwenTranslator(self.settings)
        p = patch("app.experimental.qwen.translator.httpx.Client")
        ctor = p.start()
        self.addCleanup(p.stop)
        client = ctor.return_value
        client.post.side_effect = lambda endpoint, **_: FakeResponse(
            {} if endpoint == "/api/show" else self.answer
        )
        provider.load()
        self.addCleanup(provider.unload)
        return provider, client

    def test_translate_preserves_api_shape(self):
        provider, client = self.build_provider()
        result = provider.translate("I might have an idea of it.", "en", num_beams=4)
        self.assertEqual(result["translated"], self.answer["message"]["content"])
        self.assertEqual(result["model"], "qwen3.5:4b")
        self.assertEqual(result["device"], "ollama")
        self.assertEqual(result["input_tokens"], 52)
        self.assertEqual(result["output_tokens"], 18)
        self.assertEqual(
            set(result),
            {"original", "translated", "source", "target",
             "input_tokens", "output_tokens", "model", "device"},
        )
        args, kwargs = client.post.call_args
        self.assertEqual(args[0], "/api/chat")
        self.assertIs(kwargs["json"]["stream"], False)
        self.assertIs(kwargs["json"]["think"], False)
        self.assertEqual(kwargs["json"]["options"]["num_predict"], 512)

    def test_batch_contract_and_sequential_calls(self):
        provider, client = self.build_provider()
        result = provider.translate_batch(["Hello", "Goodbye"], "en")
        self.assertEqual(len(result["translations"]), 2)
        self.assertEqual(result["model"], "qwen3.5:4b")
        self.assertEqual(client.post.call_count, 3)  # /api/show + 2 chats

    def test_input_guards(self):
        provider, client = self.build_provider()
        with self.assertRaises(BatchTooLargeError):
            provider.translate_batch(["a", "b", "c"], "en")
        with self.assertRaises(ValueError):
            provider.translate(" ", "en")
        with self.assertRaises(InputTooLongError):
            provider.translate("X" * 65, "en")
        self.assertEqual(client.post.call_count, 1)

    def test_blank_output_rejected(self):
        provider, client = self.build_provider()
        client.post.side_effect = lambda endpoint, **_: FakeResponse({
            "message": {"content": " "},
        })
        with self.assertRaises(TranslationBackendError):
            provider.translate("Hello", "en")

    def test_api_routes_when_qwen_selected(self):
        import app.main as main

        with patch("app.main.settings", self.settings):
            with patch("app.experimental.qwen.translator.httpx.Client") as ctor:
                ctor.return_value.post.side_effect = (
                    lambda endpoint, **_: FakeResponse(
                        {} if endpoint == "/api/show" else self.answer
                    )
                )
                with TestClient(main.app) as client:
                    ready = client.get("/ready").json()
                    self.assertEqual(ready["provider"], "qwen")
                    self.assertEqual(ready["model"], "qwen3.5:4b")
                    result = client.post("/v1/translate", json={
                        "text": "Hello", "source": "en", "target": "th",
                    })
                    self.assertEqual(result.status_code, 200)
                    self.assertEqual(
                        result.json()["translated"],
                        self.answer["message"]["content"],
                    )
                    batch = client.post("/v1/translate/batch", json={
                        "texts": ["Hello", "Goodbye"], "source": "en",
                    })
                    self.assertEqual(batch.status_code, 200)
                    self.assertEqual(len(batch.json()["translations"]), 2)


if __name__ == "__main__":
    unittest.main()
