import logging

import aiohttp
from pydantic import validate_call

from gtservice.translation_loader.schemas import (
    WordSchema, TextSchema, TranslatedWordSchema, Language
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
) -> list[WordSchema]:
    return [
        WordSchema(
            word=item['trans'],
            language=translation_language,
        )
        for item in sentences
        if 'trans' in item
    ]


def _deserialize_synonyms(
        synonyms: list[dict],
        translation_language: Language,
) -> list[WordSchema]:
    return [
        WordSchema(
            word=synonym_text,
            language=translation_language,
        )
        for item in synonyms
        for entry_list in item.get('entry', [])
        for synonym_text in entry_list.get('synonym', [])
    ]


def _deserialize_definitions(definitions: list[dict]) -> list[TextSchema]:
    return [
        TextSchema(definition['gloss'])
        for item in definitions
        for definition in item.get('entry', [])
        if 'example' in definition
    ]


def _deserialize_examples(examples: dict) -> list[TextSchema]:
    return [
        TextSchema(example['text'])
        for example in examples.get("example", [])
        if 'text' in example
    ]


@validate_call
def _parse_from_body(
        body: dict, word: str, source_language: Language, translation_language: Language
) -> TranslatedWordSchema:
    validate_has_blocks(body, 'sentences')

    word_schema = WordSchema(word=word, language=source_language)
    definitions = _deserialize_definitions(body.get('definitions', []))
    synonyms = _deserialize_synonyms(body.get('synsets', []), source_language)
    translations = _deserialize_translations(body['sentences'], translation_language)
    examples = _deserialize_examples(body.get('examples', []))

    return TranslatedWordSchema(
        word=word_schema,
        translation_language=translation_language,
        definitions=definitions,
        synonyms=synonyms,
        translations=translations,
        examples=examples,
    )


@validate_call
async def fetch_translation(
        word: str,
        source_language: Language,
        translation_language: Language
) -> TranslatedWordSchema:
    """
    Loads word information from the remote Google Translate API
    WARNING: API is undocumented and could change anytime
    :param word: word for parsing
    :param source_language: source language code
    :param translation_language: destination language code
    :return: fetched word information
    """
    params = {
        'q': word,
        'sl': source_language,
        'tl': translation_language,
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

    return _parse_from_body(body, word, source_language, translation_language)
