import json
from typing import Generator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from gtservice.db import database, database_session_context
from gtservice.logic.translation import insert_or_update_translation


@pytest_asyncio.fixture
async def db_session() -> Generator[Session, None, None]:
    await database.drop_all()
    await database.create_all()

    async with database_session_context() as session:
        yield session
        await database.drop_all()


@pytest_asyncio.fixture
async def testing_words(db_session: AsyncSession) -> Generator[None, None, None]:
    from gtservice.translation_loader.loader import _parse_from_body

    for word, sl, tl, path in [
        ('interesting', 'en', 'ru', './pytest/files/testing_data_gt.json'),
        ('appealing', 'en', 'ru', './pytest/files/testing_data_gt_2.json'),
    ]:
        with open(path, "r") as file:  # blocks, but that's ok here
            body = json.load(file)
            parsed_word = _parse_from_body(
                body, word, sl, tl
            )
            await insert_or_update_translation(db_session, parsed_word)

    await db_session.commit()

    yield