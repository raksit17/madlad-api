from __future__ import annotations

import threading

import torch
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
)

from app.core.config import Settings
from app.services.errors import InputTooLongError, BatchTooLargeError


class MadladTranslator:
    def __init__(self, settings: Settings):
        self.settings = settings

        self.tokenizer = None
        self.model = None

        self.input_device: torch.device | None = None

        self.inference_lock = threading.Semaphore(
            settings.max_concurrent_inference
        )

    def load(self) -> None:
        print("=" * 60)
        print("Loading MADLAD-400")
        print(f"Model: {self.settings.model_name}")
        print("=" * 60)

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.settings.model_name,
        )

        use_cuda = (
            self.settings.device == "auto"
            and torch.cuda.is_available()
        ) or self.settings.device == "cuda"

        if use_cuda and torch.cuda.is_available():

            if torch.cuda.is_bf16_supported():
                dtype = torch.bfloat16
            else:
                dtype = torch.float16

            print(f"CUDA detected: {torch.cuda.get_device_name(0)}")
            print(f"Model dtype: {dtype}")

            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.settings.model_name,
                dtype=dtype,
                device_map="auto",
                max_memory={
                    0: "7GiB",
                    "cpu": "40GiB",
                },
                low_cpu_mem_usage=True,
            )

        else:
            print("Using CPU")

            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.settings.model_name,
                dtype=torch.float32,
                low_cpu_mem_usage=True,
            )
            self.model.to("cpu")

        self.model.eval()

        # สำคัญกรณี model ถูกแบ่งหลาย GPU/device
        self.input_device = (
            self.model.get_input_embeddings()
            .weight
            .device
        )

        print(f"Input device: {self.input_device}")
        print("MADLAD-400 loaded successfully")
        print("=" * 60)

    def unload(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None

        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def is_ready(self) -> bool:
        return (
            self.model is not None
            and self.tokenizer is not None
        )

    @staticmethod
    def _create_prompt(
        text: str,
        target: str,
    ) -> str:
        return f"<2{target}> {text.strip()}"

    def translate(
        self,
        text: str,
        source: str,
        target: str = "th",
        max_new_tokens: int | None = None,
        num_beams: int | None = None,
    ) -> dict:

        if not self.is_ready():
            raise RuntimeError(
                "MADLAD model has not been loaded."
            )

        text = text.strip()

        if not text:
            raise ValueError("Text cannot be empty.")

        prompt = self._create_prompt(
            text=text,
            target=target,
        )

        encoded = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=False,
        )

        input_tokens = encoded["input_ids"].shape[-1]

        if input_tokens > self.settings.max_input_tokens:
            raise InputTooLongError(
                f"Input contains {input_tokens} tokens. "
                f"Maximum allowed is "
                f"{self.settings.max_input_tokens} tokens."
            )

        encoded = {
            key: value.to(self.input_device)
            for key, value in encoded.items()
        }

        generation_max_tokens = (
            max_new_tokens
            or self.settings.max_new_tokens
        )

        generation_beams = (
            num_beams
            or self.settings.num_beams
        )

        with self.inference_lock:
            with torch.inference_mode():

                output = self.model.generate(
                    **encoded,
                    max_new_tokens=generation_max_tokens,
                    num_beams=generation_beams,
                    do_sample=False,
                    early_stopping=True,
                )

        translated = self.tokenizer.decode(
            output[0],
            skip_special_tokens=True,
        ).strip()

        return {
            "source": source,
            "target": target,
            "original": text,
            "translated": translated,
            "input_tokens": input_tokens,
            "output_tokens": output.shape[-1],
            "model": self.settings.model_name,
            "device": str(self.input_device),
        }

    def translate_batch(
        self,
        texts: list[str],
        source: str,
        target: str = "th",
    ) -> dict:

        if not self.is_ready():
            raise RuntimeError(
                "MADLAD model has not been loaded."
            )

        if len(texts) > self.settings.max_batch_size:
            raise BatchTooLargeError(
                f"Batch contains {len(texts)} items. "
                f"Maximum batch size is "
                f"{self.settings.max_batch_size}."
            )

        cleaned_texts = [
            text.strip()
            for text in texts
        ]

        if any(not text for text in cleaned_texts):
            raise ValueError(
                "Batch cannot contain empty text."
            )

        prompts = [
            self._create_prompt(
                text=text,
                target=target,
            )
            for text in cleaned_texts
        ]

        # ตรวจความยาวก่อน padding
        raw_encoded = self.tokenizer(
            prompts,
            padding=False,
            truncation=False,
        )

        for index, token_ids in enumerate(
            raw_encoded["input_ids"]
        ):
            token_count = len(token_ids)

            if token_count > self.settings.max_input_tokens:
                raise InputTooLongError(
                    f"Text at index {index} contains "
                    f"{token_count} tokens. "
                    f"Maximum is "
                    f"{self.settings.max_input_tokens}."
                )

        encoded = self.tokenizer(
            prompts,
            return_tensors="pt",
            padding=True,
            truncation=False,
        )

        encoded = {
            key: value.to(self.input_device)
            for key, value in encoded.items()
        }

        with self.inference_lock:
            with torch.inference_mode():

                outputs = self.model.generate(
                    **encoded,
                    max_new_tokens=(
                        self.settings.max_new_tokens
                    ),
                    num_beams=self.settings.num_beams,
                    do_sample=False,
                    early_stopping=True,
                )

        decoded = self.tokenizer.batch_decode(
            outputs,
            skip_special_tokens=True,
        )

        translations = [
            {
                "original": original,
                "translated": translated.strip(),
            }
            for original, translated
            in zip(cleaned_texts, decoded)
        ]

        return {
            "source": source,
            "target": target,
            "translations": translations,
            "model": self.settings.model_name,
            "device": str(self.input_device),
        }