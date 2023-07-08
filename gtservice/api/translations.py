import logging
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import Field
from pydantic.dataclasses import dataclass
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from gtservice.db import database_session
from gtservice.db.common import Actuality
from gtservice.db.models import WordModel
from gtservice.logic.translation import insert_or_update_translation
from gtservice.translation_loader.loader import fetch_translation
from gtservice.translation_loader.schemas import WordSchema, TextSchema, Language

MAX_WORD_LENGTH = 64

WORD_INPUT_PARAMS: dict = {
    "min_length": 1,
    "max_length": MAX_WORD_LENGTH
}

router = APIRouter(prefix='/translations', tags=['translate'])

logger = logging.getLogger(__name__)


@dataclass
class TranslatedWordResponse:
    word: str
    language: Language

    translations: list[WordSchema] = Field(default_factory=list)
    synonyms: list[WordSchema] = Field(default_factory=list)
    definitions: list[TextSchema] = Field(default_factory=list)
    examples: list[TextSchema] = Field(default_factory=list)

    @staticmethod
    def from_model(word_model: WordModel) -> 'TranslatedWordResponse':
        return TranslatedWordResponse(
            word=word_model.word,
            language=word_model.language,
            translations=[
                WordSchema(*mdl.as_tuple()) for mdl in word_model.translations
            ],
            synonyms=[
                WordSchema(*mdl.as_tuple()) for mdl in word_model.synonyms
            ],
            definitions=[
                TextSchema(mdl.text) for mdl in word_model.definitions
            ],
            examples=[
                TextSchema(mdl.text) for mdl in word_model.examples
            ],
        )


@dataclass
class TranslatedWordsListResponse:
    page: int
    page_size: int
    total_pages: int
    count: int
    results: list[TranslatedWordResponse]


@dataclass
class SimpleOperationResponse:
    status: bool = Field(default=True)


@router.get('/', response_model=TranslatedWordsListResponse)
async def get_translated_words(
        word_part: Annotated[str | None, Query(**WORD_INPUT_PARAMS)] = None,
        language: Language | None = None,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=50)] = 10,
        db_session: AsyncSession = Depends(database_session),
) -> TranslatedWordsListResponse:
    query = (
        select(WordModel)
        .options(selectinload(WordModel.translations))
        .options(selectinload(WordModel.synonyms))
        .options(selectinload(WordModel.examples))
        .options(selectinload(WordModel.definitions))
    )

    if word_part is not None:
        query = query.filter(
            WordModel.word.like(f"%{word_part}%")
        )

    if language is not None:
        query = query.filter(
            WordModel.language == language
        )

    total = (await db_session.execute(
        select(func.count()).select_from(query)
    )).scalar_one()
    query = query.offset((page - 1) * page_size).limit(page_size)
    total_pages = ceil(total / page_size)

    models = (await db_session.execute(query)).scalars().all()

    return TranslatedWordsListResponse(
        page=page,
        page_size=page_size,
        count=total,
        total_pages=total_pages,
        results=[TranslatedWordResponse.from_model(model) for model in models],
    )


@router.get('/{word}', response_model=TranslatedWordResponse)
async def get_text(
        word: Annotated[str, Path(**WORD_INPUT_PARAMS)],
        source_language: Language,
        translation_language: Language,
        db_session: AsyncSession = Depends(database_session),
) -> TranslatedWordResponse:
    lowercased_word = word.lower()
    word_model = await WordModel.get_full_word(db_session, word, source_language)

    if word_model is None or word_model.actuality == Actuality.OUTDATED:
        try:
            data = await fetch_translation(
                word=lowercased_word,
                source_language=Language(source_language),
                translation_language=Language(translation_language),
            )
        except Exception:
            logger.exception('Failed requesting google API')
            raise HTTPException(status_code=500, detail='Internal server error')

        try:
            word_model = await insert_or_update_translation(db_session=db_session,
                                                            updated_word_info=data)
        except Exception:
            logger.exception(f'Failed to update data for {word}')
            raise HTTPException(status_code=500, detail='Internal server error')

    return TranslatedWordResponse.from_model(word_model)


@router.delete('/{language}/{word}', response_model=SimpleOperationResponse)
async def delete_text(
        language: Language,
        word: str,
        db_session: AsyncSession = Depends(database_session),
) -> SimpleOperationResponse:
    deletion_list = await WordModel.get_words_by_list(
        db_session, [WordSchema(word, language)]
    )
    if deletion_list:
        for word in deletion_list:
            word.deleted = True
            db_session.add(word)

        await db_session.commit()

    return SimpleOperationResponse()
