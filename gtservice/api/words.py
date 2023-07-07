import logging
import uuid
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic.dataclasses import dataclass
from sqlalchemy.orm import Session, joinedload

from gtservice import settings
from gtservice.db import get_session
from gtservice.db.common import Actuality
from gtservice.db.models import WordModel
from gtservice.schemas import Language
from gtservice.translation_loader.gt_loader import fetch_translation
from gtservice.translation_loader.schemas import Definition, Synonym, Translation, Example, \
    TranslatedWordInfo

router = APIRouter(prefix='/translations', tags=['translate'])


logger = logging.getLogger(__name__)


@dataclass
class TranslatedWordResponse:
    word: str
    language: Language

    definitions: list[Definition]
    synonyms: list[Synonym]
    translations: list[Translation]
    examples: list[Example]


@dataclass
class TranslatedWordsListResponse:
    count: int
    page: int
    page_size: int
    total_pages: int
    result: list[TranslatedWordResponse]


class WordSearchFilter:
    word_part: str | None
    language: str | None


@router.get('/', response_model=TranslatedWordsListResponse)
async def get_translated_words(
        words_filter: WordSearchFilter,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 50,
        db_session: Session = Depends(get_session),
) -> TranslatedWordsListResponse:
    async with db_session as session:
        query = session.query(WordModel)

        if words_filter.word_part is not None:
            query = query.filter(
                WordModel.word.match(f"%{words_filter.word_part}%")
            )

        if words_filter.language is not None:
            query = query.filter(
                WordModel.language_code == words_filter.language
            )

        total = await query.count()
        items = query.offset((page - 1) * page_size).limit(page_size)
        total_pages = ceil(total / page_size)

        all_items = await items.all()

        return TranslatedWordsListResponse(
            page=page,
            page_size=page_size,
            count=total,
            total_pages=total_pages,
            result=all_items,
        )


@router.get('/{word}', response_model=TranslatedWordResponse)
async def get_text(
        word: Annotated[str, Path(min_length=1, max_length=128)],
        source_language: str,
        translation_language: str,
        db_session: Session = Depends(get_session),
) -> TranslatedWordResponse:
    async with db_session as session:

        logger.info(f'Handling text "{word}"')
        text_value = word.lower()
        db_word: WordModel = await (
            db_session.query(WordModel)
            .options(joinedload(WordModel.translations))
            .options(joinedload(WordModel.synonyms))
            .options(joinedload(WordModel.examples))
            .options(joinedload(WordModel.definitions))
            .filter(
                WordModel.word == word,
                WordModel.language_code == source_language,
                not WordModel.deleted
            )
            .one_or_none()
        )
        if db_word is None or db_word.status == Actuality.OUTDATED:
            logger.info(f'Need to update data')
            if db_word is None:
                logger.info(f'Detecting new text')
                db_word = WordModel(
                    text_value=text_value,
                    language=source_language,
                )
            try:
                logger.info('Requesting to Google API for text details')
                data = await fetch_translation(
                    word=text_value,
                    source_language=source_language,
                    translation_language=translation_language,
                )
            except Exception as e:
                logger.exception(f'Failed to fetch data from Google Translate API. Reason: {e}')
                raise HTTPException(status_code=500, detail='Internal server error')

            db_word.status = Actuality.ACTUAL
            db_session.add(db_word)
            db_session.commit()

            try:
                logger.info(f'Updating data for "{db_word.word}"')
                _update_data(db_session=db_session, word=db_word, new_data=data)
            except Exception as e:
                logger.exception(f'Failed to update data for {word}. Reason: {e}')
                raise HTTPException(status_code=500, detail='Internal server error')
        else:
            logger.info('Taking data from db')

        if translation_language is not None:
            logger.info(f'Extracting only translations for lang {translation_language}')
            db_word = await (
                db_session.query(WordModel)
                .options(joinedload(WordModel.translations))
                .options(joinedload(WordModel.synonyms))
                .options(joinedload(WordModel.examples))
                .options(joinedload(WordModel.definitions))
                .filter(
                    WordModel.word == word,
                    WordModel.language_code == source_language,
                    not WordModel.deleted
                )
                .one_or_none()
            )
            db_session.expunge(db_word)
            db_word.translations = [
                translated_text
                for translated_text in db_word.translations
                if translated_text.language == translation_language
            ]

        return TranslatedWordResponse(
            text_value=db_word.text_value,
            language=db_word.language,
            definitions=db_word.definitions,
            examples=db_word.examples,
            translations=list(map(Translation.from_orm, db_word.translations)),
            synonyms=list(map(Synonym.from_orm, db_word.synonyms)),
        )


@router.delete('/{text}', response_model=str)
def delete_text(text: str, db_session: Session = Depends(get_db_session)) -> str:
    db_texts: list[WordModel] = (
        db_session.query(WordModel)
        .options(joinedload(WordModel.translations))
        .options(joinedload(WordModel.synonyms))
        .options(joinedload(WordModel.examples))
        .options(joinedload(WordModel.definitions))
        .filter(WordModel.word == text)
        .all()
    )
    if db_texts:
        logger.info('Detecting data to delete')
        for db_text in db_texts:
            db_text.deleted = True
            db_session.add(db_text)

        db_session.commit()
    return 'deleted'


def _update_data(
        db_session: Session,
        word: WordModel,
        new_data: TranslatedWordInfo,
) -> None:
    translation_values_translations: dict[str, Translation] = {
        translation.word: translation for translation in new_data.translations
    }
    synonym_values_synonyms: dict[str, Synonym] = {
        synonym.word: synonym for synonym in new_data.synonyms
    }

    texts = list(translation_values_translations) + list(synonym_values_synonyms)
    db_existing_text_values_texts: dict[str, WordModel] = {
        db_text_item.text_value: db_text_item for db_text_item in _get_text_data(db_session, texts)
    }

    new_translations = [
        WordModel(**item.dict())
        for text_value, item in translation_values_translations.items()
        if text_value not in db_existing_text_values_texts
    ]
    if new_translations:
        logger.info('Adding new translations')
        word.translations.extend(new_translations)

    existing_translations = [
        db_existing_text_values_texts[text_value]
        for text_value, item in translation_values_translations.items()
        if text_value in db_existing_text_values_texts
    ]
    if existing_translations:
        logger.info('Linking existing translations')
        word.translations.extend(existing_translations)

    new_synonyms = [
        WordModel(**item.dict())
        for text_value, item in synonym_values_synonyms.items()
        if text_value not in db_existing_text_values_texts
    ]
    if new_synonyms:
        logger.info('Adding new synonyms')
        word.synonyms.extend(new_synonyms)

    existing_synonyms = [
        db_existing_text_values_texts[text_value]
        for text_value, item in synonym_values_synonyms.items()
        if text_value in db_existing_text_values_texts
    ]
    if existing_synonyms:
        logger.info('Linking existing synonyms')
        word.synonyms.extend(existing_synonyms)

    if new_data.examples:
        logger.info('Adding new examples')
        word.examples.extend(Example(**item.dict()) for item in new_data.examples)

    if new_data.definitions:
        logger.info('Adding new definitions')
        word.definitions.extend(Definition(**item.dict()) for item in new_data.definitions)

    logger.info('Commiting to db')
    db_session.commit()


def _get_text_data(db_session: Session, texts: list[str]) -> list[WordModel]:
    return db_session.query(Text).filter(Text.text_value.in_(texts)).all()  # type: ignore
