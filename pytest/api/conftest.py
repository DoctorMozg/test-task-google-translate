import asyncio
from typing import Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from pytest_mock import MockerFixture

from gtservice.app import create_application
from gtservice.translation_loader.schemas import TranslatedWordSchema, WordSchema, TextSchema


@pytest.yield_fixture(scope='session')
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client(event_loop) -> Generator[AsyncClient, None, None]:
    async with AsyncClient(app=create_application(), base_url="http://testserver") as cl:
        yield cl


@pytest.fixture
def mock_google_translation_api(mocker: MockerFixture):
    mocker.patch(
        'gtservice.translation_loader.loader.fetch_translation',
        return_value=TranslatedWordSchema(
            word=WordSchema("render", "en"),
            translation_language="ru",
            translations=[
                WordSchema('оказывать', 'ru')
            ],
            synonyms=[
                WordSchema('renderds', 'en'),
                WordSchema('renderwww', 'en'),
            ],
            examples=[
                TextSchema('money serves as a reward for services rendered')
            ],
            definitions=[
                TextSchema('provide or give (a service, help, etc.).')
            ],
        ),
    )
    yield
