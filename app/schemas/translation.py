from typing import Literal

from pydantic import BaseModel, Field


SourceLanguage = Literal["en", "ja"]
TargetLanguage = Literal["th"]


class TranslateRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        description="Text to translate",
    )

    source: SourceLanguage

    target: TargetLanguage = "th"

    max_new_tokens: int | None = Field(
        default=None,
        ge=1,
        le=2048,
    )

    num_beams: int | None = Field(
        default=None,
        ge=1,
        le=8,
    )


class TranslateResponse(BaseModel):
    source: str
    target: str

    original: str
    translated: str

    input_tokens: int
    output_tokens: int

    model: str
    device: str


class BatchTranslateRequest(BaseModel):
    texts: list[str] = Field(
        ...,
        min_length=1,
    )

    source: SourceLanguage
    target: TargetLanguage = "th"


class BatchTranslationItem(BaseModel):
    original: str
    translated: str


class BatchTranslateResponse(BaseModel):
    source: str
    target: str

    translations: list[BatchTranslationItem]

    model: str
    device: str