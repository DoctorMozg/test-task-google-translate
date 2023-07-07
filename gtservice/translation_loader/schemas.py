from pydantic.dataclasses import dataclass

from gtservice.schemas import Language


@dataclass
class TextBaseItem:
    word: str


@dataclass
class Word(TextBaseItem):
    language: Language


@dataclass
class Definition(TextBaseItem):
    pass


@dataclass
class Synonym(TextBaseItem):
    pass


@dataclass
class Translation(TextBaseItem):
    language: Language


@dataclass
class Example(TextBaseItem):
    pass


@dataclass
class TranslatedWordInfo:
    word: str
    source_language: Language
    translation_language: Language
    definitions: list[Definition]
    synonyms: list[Synonym]
    translations: list[Translation]
    examples: list[Example]
