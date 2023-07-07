from sqlalchemy import Boolean, Column, ForeignKey, String, Table, UniqueConstraint, Integer
from sqlalchemy.orm import relationship

from gtservice.db.common import DbActuality, Actuality, Base


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


class WordModel(Base):
    __tablename__ = 'words'
    __table_args__ = (UniqueConstraint('word', 'language_code'),)

    id: int = Column(Integer, primary_key=True)
    word: str = Column(String(255), nullable=False, index=True)
    language_code: str = Column(String(2), nullable=False, index=True)
    actual: DbActuality = Column(DbActuality, nullable=False, default=Actuality.OUTDATED)
    deleted: bool = Column(Boolean, default=False, server_default='FALSE')

    definitions = relationship('Definition', back_populates='word')
    examples = relationship('Example', back_populates='word')

    translations: list['Word'] = relationship(
        'Word',
        secondary=_word_translations,
        primaryjoin='Word.id == word_translations.c.from_word_id',
        secondaryjoin='Word.id == word_translations.c.to_word_id',
        back_populates='translations',
    )

    synonyms: list['Word'] = relationship(
        'Word',
        secondary=_word_synonyms,
        primaryjoin='Word.id == word_synonyms.c.from_word_id',
        secondaryjoin='Word.id == word_synonyms.c.to_word_id',
        back_populates='synonyms',
    )


class DefinitionModel(Base):
    __tablename__ = 'definitions'

    text: str = Column(String, nullable=False, index=True)
    word_id: int = Column(Integer, ForeignKey('words.id'))

    word = relationship('Word', back_populates='definitions')


class ExampleModel(Base):
    __tablename__ = 'examples'

    text: str = Column(String, nullable=False, index=True)
    word_id: int = Column(Integer, ForeignKey('words.id'))

    word = relationship('Word', back_populates='examples')
