import logging
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from gtservice.db.common import Actuality
from gtservice.db.models import WordModel, ExampleModel, DefinitionModel
from gtservice.translation_loader.schemas import TranslatedWordSchema

logger = logging.getLogger(__name__)


async def insert_or_update_translation(
        db_session: AsyncSession,
        updated_word_info: TranslatedWordSchema
) -> WordModel:
    """
    Persists an updated word schema with all dependencies to the database.
    Merges if needed.
    :param db_session: async session
    :param updated_word_info: new or updated word information
    :return: created/updated word model
    """
    word_model = await WordModel.get_full_word(
        db_session, updated_word_info.word.word, updated_word_info.word.language
    )

    if word_model is None:
        logger.debug(
            f"Creating a new word: {updated_word_info.word} "
        )

        word_model = WordModel(**asdict(updated_word_info.word))
        new_word_created = True
    else:
        logger.debug(
            f"Updating an old word: {updated_word_info.word}"
        )
        new_word_created = False

    word_model.actuality = Actuality.ACTUAL
    word_model.deleted = False

    all_persisted_words = await WordModel.get_words_by_list(
        db_session, updated_word_info.get_all_words()
    )

    all_persisted_words_dict = {
        (w.word, w.language): w for w in all_persisted_words
    }

    t_trans = set()
    word_model.translations.clear()
    for new_translation in updated_word_info.translations:
        present_word = all_persisted_words_dict.get(
            (new_translation.word, new_translation.language)
        )
        if present_word is None:
            present_word = WordModel(**asdict(new_translation))

        if present_word is not None and new_translation.word not in t_trans:
            t_trans.add(present_word.word)
            word_model.translations.append(present_word)

    t_syn = set()
    word_model.synonyms.clear()
    for new_synonym in updated_word_info.synonyms:
        present_word = all_persisted_words_dict.get(
            (new_synonym.word, new_synonym.language)
        )
        if present_word is None:
            present_word = WordModel(**asdict(new_synonym))

        if present_word is not None and new_synonym.word not in t_syn:
            word_model.synonyms.append(present_word)
            t_syn.add(present_word.word)

    other_present_examples = {
        item.text for item in word_model.examples
    }
    word_model.examples.extend([
        ExampleModel(**asdict(nex))
        for nex in updated_word_info.examples
        if nex.text not in other_present_examples
    ])

    other_present_definitions = {
        item.text for item in word_model.definitions
    }
    word_model.definitions.extend([
        DefinitionModel(**asdict(ndef))
        for ndef in updated_word_info.definitions
        if ndef.text not in other_present_definitions
    ])

    if new_word_created:
        db_session.add(word_model)

    await db_session.commit()

    world_model_full = await WordModel.get_full_word(
        db_session,
        updated_word_info.word.word,
        updated_word_info.word.language
    )

    if world_model_full is None:
        raise ValueError(f"World model not found: {updated_word_info}")

    return world_model_full
