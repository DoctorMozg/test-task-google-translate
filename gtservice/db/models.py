from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    String,
    Table,
    UniqueConstraint,
    Integer,
    select,
    or_
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, Mapped, selectinload
from sqlalchemy_utils import generic_repr

from gtservice.db.common import DbActuality, Actuality, Base
from gtservice.translation_loader.schemas import WordSchema

_word_translations = Table(
    'word_translations',
    Base.metadata,
    Column(
        'from_word_id',
        Integer,
        ForeignKey('words.id'),
        primary_key=True,
    ),
    Column(
        'to_word_id',
        Integer,
        ForeignKey('words.id'),
        primary_key=True,
    ),
)

_word_synonyms = Table(
    'word_synonyms',
    Base.metadata,
    Column(
        'from_word_id',
        Integer,
        ForeignKey('words.id'),
        primary_key=True
    ),
    Column(
        'to_word_id',
        Integer,
        ForeignKey('words.id'),
        primary_key=True,
    ),
)


@generic_repr
class WordModel(Base):
    __tablename__ = 'words'
    __table_args__ = (UniqueConstraint('word', 'language'),)

    id: Mapped[int] = Column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    word: Mapped[str] = Column(String(255), nullable=False, index=True)
    language: Mapped[str] = Column(String(2), nullable=False, index=True)
    actuality: Mapped[DbActuality] = Column(
        DbActuality, nullable=False, default=Actuality.OUTDATED
    )
    deleted: Mapped[bool] = Column(
        Boolean, default=False, server_default='FALSE'
    )

    definitions: Mapped[list['DefinitionModel']] = relationship(
        'DefinitionModel',
        back_populates='word',
        cascade="all, delete"
    )
    examples: Mapped[list['ExampleModel']] = relationship(
        'ExampleModel',
        back_populates='word',
        cascade="all, delete"
    )

    translations: Mapped[list['WordModel']] = relationship(
        'WordModel',
        secondary=_word_translations,
        primaryjoin='WordModel.id == word_translations.c.from_word_id',
        secondaryjoin='WordModel.id == word_translations.c.to_word_id',
        back_populates='translations'
    )

    synonyms: Mapped[list['WordModel']] = relationship(
        'WordModel',
        secondary=_word_synonyms,
        primaryjoin='WordModel.id == word_synonyms.c.from_word_id',
        secondaryjoin='WordModel.id == word_synonyms.c.to_word_id',
        back_populates='synonyms'
    )

    @staticmethod
    async def get_full_word(
            db_session: AsyncSession, word: str, language: str
    ) -> 'WordModel | None':
        query = (
            select(WordModel)
            .options(selectinload(WordModel.translations))
            .options(selectinload(WordModel.synonyms))
            .options(selectinload(WordModel.examples))
            .options(selectinload(WordModel.definitions))
            .filter(
                WordModel.word == word,
                WordModel.language == language
            )
        )
        return (await db_session.execute(query)).scalar_one_or_none()

    @staticmethod
    async def get_words_by_list(
            db_session: AsyncSession,
            words: list[WordSchema],
    ) -> list['WordModel']:

        filters = [
            WordModel.word == word.word and WordModel.language == word.language
            for word in words
        ]
        query = select(WordModel).filter(or_(*filters))
        result = await db_session.execute(query)
        return list(result.scalars().all())

    def as_tuple(self) -> tuple[str, str]:
        return self.word, self.language


@generic_repr
class DefinitionModel(Base):
    __tablename__ = 'definitions'

    id: Mapped[int] = Column(Integer, primary_key=True, index=True, autoincrement=True)

    text: Mapped[str] = Column(String, nullable=False, index=True)
    word_id: Mapped[int] = Column(Integer, ForeignKey('words.id'))

    word: Mapped[WordModel] = relationship(WordModel, back_populates='definitions')


class ExampleModel(Base):
    __tablename__ = 'examples'

    id: Mapped[int] = Column(Integer, primary_key=True, index=True, autoincrement=True)

    text: Mapped[str] = Column(String, nullable=False, index=True)
    word_id: Mapped[int] = Column(Integer, ForeignKey('words.id'))

    word: Mapped[WordModel] = relationship(WordModel, back_populates='examples')
