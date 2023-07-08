import pytest
from httpx import AsyncClient

from gtservice.api.translations import TranslatedWordResponse


@pytest.mark.usefixtures("testing_words", "mock_google_translation_api")
@pytest.mark.asyncio
async def test_get_present_word(client: AsyncClient):
    rv = await client.get('/translations/interesting?source_language=en&translation_language=ru')
    rv.raise_for_status()

    result: dict = rv.json()
    translated_word: TranslatedWordResponse = TranslatedWordResponse(**result)

    assert translated_word.language == 'en'
    assert translated_word.word == 'interesting'
    assert len(translated_word.translations) > 0
    assert len(translated_word.definitions) > 0
    assert len(translated_word.synonyms) > 0
    assert len(translated_word.examples) > 0


@pytest.mark.usefixtures("testing_words", "mock_google_translation_api")
@pytest.mark.asyncio
async def test_unknown_word_merge(client: AsyncClient):
    rv = await client.get('/translations/render?source_language=en&translation_language=ru')
    rv.raise_for_status()

    result: dict = rv.json()
    translated_word: TranslatedWordResponse = TranslatedWordResponse(**result)

    assert translated_word.language == 'en'
    assert translated_word.word == 'render'


@pytest.mark.usefixtures("db_session", "mock_google_translation_api")
@pytest.mark.asyncio
async def test_unknown_word(client: AsyncClient):
    rv = await client.get('/translations/render?source_language=en&translation_language=ru')
    rv.raise_for_status()

    result: dict = rv.json()
    translated_word: TranslatedWordResponse = TranslatedWordResponse(**result)

    assert translated_word.language == 'en'
    assert translated_word.word == 'render'


@pytest.mark.usefixtures("testing_words")
@pytest.mark.asyncio
async def test_delete_word(client: AsyncClient):
    rv = await client.delete('/translations/en/interesting')
    rv.raise_for_status()

    result: dict = rv.json()
    assert result['status'], 'Should be true if deleted'


@pytest.mark.parametrize(
    'params, expected_result',
    [
        pytest.param(
            'word_part=fascinating&language=en',
            {
                'count': 1,
                'page': 1,
                'page_size': 10,
                'total_pages': 1,
                'results': 1
            },
            id='one_word',
        ),
        pytest.param(
            'word_part=ing',
            {
                'count': 37,
                'page': 1,
                'page_size': 10,
                'total_pages': 4,
                'results': 10
            },
            id='part_word',
        ),
        pytest.param(
            'word_part=ing&page=4',
            {
                'count': 37,
                'page': 4,
                'page_size': 10,
                'total_pages': 4,
                'results': 7
            },
            id='part_word_paging',
        ),
        pytest.param(
            'language=en&page_size=30',
            {
                'count': 58,
                'page': 1,
                'page_size': 30,
                'total_pages': 2,
                'results': 30
            },
            id='only_language',
        ),
    ]
)
@pytest.mark.usefixtures("testing_words")
@pytest.mark.asyncio
async def test_get_word_list(client: AsyncClient, params: str, expected_result: dict):
    rv = await client.get(f'/translations/?{params}')
    rv.raise_for_status()
    data = rv.json()

    assert {
        'count': data['count'],
        'page': data['page'],
        'page_size': data['page_size'],
        'total_pages': data['total_pages'],
        'results': len(data['results'])
    } == expected_result
