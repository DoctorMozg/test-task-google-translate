import pytest

from gtservice.translation_loader.loader import fetch_translation


@pytest.mark.asyncio
async def test_api_call():
    resulting_word_info = await fetch_translation(
        "car", "en", "ru"
    )

    assert 'car' == resulting_word_info.word.word
    assert 'en' == resulting_word_info.word.language
    assert 'ru' == resulting_word_info.translation_language
    assert len(resulting_word_info.synonyms) > 0
    assert len(resulting_word_info.translations) > 0
    assert len(resulting_word_info.examples) > 0
    assert len(resulting_word_info.definitions) > 0
