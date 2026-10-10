"""Experimental Qwen translator; consumes Ollama's HTTP API synchronously.

Matches the existing MADLAD translate/translate_batch response contracts.
"""

from __future__ import annotations

import threading

import httpx

from app.core.config import Settings
from app.experimental.qwen.prompts import SYSTEM_PROMPT
from app.services.errors import (
    BatchTooLargeError,
    InputTooLongError,
    TranslationBackendError,
)


class QwenTranslator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client: httpx.Client | None = None
        self.input_device = "ollama"
        self.inference_lock = threading.Semaphore(
            settings.max_concurrent_inference
        )

    def load(self) -> None:
        client = httpx.Client(
            base_url=self.settings.qwen_base_url.rstrip("/"),
            timeout=httpx.Timeout(
                self.settings.qwen_timeout_seconds,
                connect=15.0,
            ),
        )
        try:
            response = client.post(
                "/api/show",
                json={"model": self.settings.qwen_model},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            client.close()
            raise TranslationBackendError(
                "Cannot access the Qwen model in Ollama. "
                f"Check QWEN_BASE_URL and run: ollama pull {self.settings.qwen_model}. "
                f"Reason: {exc}"
            ) from exc

        self.client = client

    def unload(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None

    def is_ready(self) -> bool:
        return self.client is not None

    def translate(
        self,
        text: str,
        source: str,
        target: str = "th",
        max_new_tokens: int | None = None,
        num_beams: int | None = None,
    ) -> dict:
        if not self.is_ready():
            raise RuntimeError("Qwen provider is not ready.")

        text = text.strip()
        if not text:
            raise ValueError("Text cannot be empty.")

        if len(text) > self.settings.qwen_max_input_chars:
            raise InputTooLongError(
                f"Input has {len(text)} characters; "
                f"Qwen limit is {self.settings.qwen_max_input_chars}."
            )

        if source not in ("en", "ja") or target != "th":
            raise ValueError("Qwen mode supports en/ja -> th only.")

        # num_beams is intentionally ignored: Ollama does not provide
        # MADLAD-style beam search. Keep the parameter for API compatibility.
        _ = num_beams
        source_name = "English" if source == "en" else "Japanese"
        request_body = {
            "model": self.settings.qwen_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Translate this {source_name} subtitle into Thai:\n"
                        "<subtitle>\n"
                        f"{text}\n"
                        "</subtitle>"
                    ),
                },
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": self.settings.qwen_temperature,
                "num_ctx": self.settings.qwen_context_tokens,
                "num_predict": (
                    max_new_tokens
                    if max_new_tokens is not None
                    else self.settings.max_new_tokens
                ),
                "seed": 42,
            },
        }

        assert self.client is not None
        try:
            with self.inference_lock:
                response = self.client.post("/api/chat", json=request_body)
                response.raise_for_status()
            result = response.json()
            translated = result["message"]["content"].strip()
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise TranslationBackendError(
                f"Qwen translation failed via Ollama: {exc}"
            ) from exc

        if not translated:
            raise TranslationBackendError(
                "Qwen returned an empty translation. "
                "Check that thinking is disabled and the model supports it."
            )

        if result.get("done_reason") == "length":
            raise TranslationBackendError(
                "Qwen output hit the token limit; increase max_new_tokens."
            )

        return {
            "source": source,
            "target": target,
            "original": text,
            "translated": translated,
            # Ollama may omit counters; 0 means unavailable, not estimated.
            "input_tokens": int(result.get("prompt_eval_count") or 0),
            "output_tokens": int(result.get("eval_count") or 0),
            "model": self.settings.qwen_model,
            "device": self.input_device,
        }

    def translate_batch(
        self,
        texts: list[str],
        source: str,
        target: str = "th",
    ) -> dict:
        if not self.is_ready():
            raise RuntimeError("Qwen provider is not ready.")

        if len(texts) > self.settings.max_batch_size:
            raise BatchTooLargeError(
                f"Batch contains {len(texts)} items. "
                f"Maximum is {self.settings.max_batch_size}."
            )

        cleaned = [text.strip() for text in texts]
        if any(not text for text in cleaned):
            raise ValueError("Batch cannot contain empty text.")

        # Sequential requests prevent spikes in GPU memory on 8GB cards.
        translations = []
        for text in cleaned:
            result = self.translate(text, source, target)
            translations.append({
                "original": result["original"],
                "translated": result["translated"],
            })

        return {
            "source": source,
            "target": target,
            "translations": translations,
            "model": self.settings.qwen_model,
            "device": self.input_device,
        }
