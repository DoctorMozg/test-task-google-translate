from itertools import chain
from typing import Annotated

from pydantic import AfterValidator
from pydantic.dataclasses import dataclass


def language_validator(lang: str) -> str:
    assert len(lang) == 2, f"Language code must consist of 2 symbols, has {len(lang)}"
    assert lang.isalpha(), f"Language code must consist only from chars, has '{lang}'"

    return lang


Language = Annotated[str, AfterValidator(language_validator)]


@dataclass(config=dict(frozen=True))
class WordSchema:
    word: str
    language: Language


@dataclass(config=dict(frozen=True))
class TextSchema:
    text: str


@dataclass(config=dict(frozen=True))
class TranslatedWordSchema:
    word: WordSchema
    translation_language: Language
    synonyms: list[WordSchema]
    translations: list[WordSchema]
    definitions: list[TextSchema]
    examples: list[TextSchema]

    def get_all_words(self) -> list[WordSchema]:
        return list(chain([self.word], self.translations, self.synonyms))
