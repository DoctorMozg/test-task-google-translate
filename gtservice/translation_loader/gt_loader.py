import logging

import aiohttp

from gtservice.schemas import Language
from gtservice.translation_loader.schemas import (
    Translation, Definition, TranslatedWordInfo, Synonym, Example
)

GOOGLE_TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'

COMMON_GOOGLE_TRANSLATE_PARAMS = {
    'client': 'gtx',
    'dj': 1,
    'hl': "en",
    'dt': ['t', 'bd', 'md', 'ss', 'ex'],
}

logger = logging.getLogger(__name__)


def validate_has_blocks(source: dict, *field_names):
    for name in field_names:
        if name not in source:
            raise ValueError(f'No "{name}" block found - response is wrong')


def _deserialize_translations(
        sentences: list[dict], translation_language: Language
) -> list[Translation]:
    return [
        Translation(
            word=item['trans'],
            language=translation_language,
        )
        for item in sentences
        if 'trans' in item
    ]


def _deserialize_definitions(definitions: list[dict]) -> list[Definition]:
    return [
        Definition(
            word=definition['gloss']
        )
        for item in definitions
        for definition in item.get('entry', [])
        if 'example' in definition
    ]


def _deserialize_synonyms(
        synonyms: list[dict],
        translation_language: Language,
) -> list[Synonym]:
    return [
        Synonym(
            word=synonym,
            language=translation_language,
        )
        for item in synonyms
        for entry_list in item.get('entry', [])
        for synonym in entry_list.get('synonym', [])
    ]


def _deserialize_examples(examples: dict) -> list[Example]:
    return [
        Example(
            word=example['text'],
        )
        for example in examples.get("example", [])
        if 'text' in example
    ]


async def fetch_translation(
        word: str, source_language: Language, translation_language: Language
) -> TranslatedWordInfo:
    params = {
        'q': word,
        'sl': source_language.code,
        'tl': translation_language.code,
        **COMMON_GOOGLE_TRANSLATE_PARAMS
    }

    logger.debug(
        f"Fetching translation data for word: {word} "
        f"({source_language} -> {translation_language})"
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(GOOGLE_TRANSLATE_URL, params=params) as response:
            response.raise_for_status()
            body = await response.json()

    validate_has_blocks(body, 'sentences')

    definitions = _deserialize_definitions(body.get('definitions', []))
    synonyms = _deserialize_synonyms(body.get('synsets', []), source_language)
    translations = _deserialize_translations(body['sentences'], translation_language)
    examples = _deserialize_examples(body.get('examples', []))

    return TranslatedWordInfo(
        word=word,
        source_language=source_language,
        translation_language=translation_language,
        definitions=definitions,
        synonyms=synonyms,
        translations=translations,
        examples=examples,
    )



