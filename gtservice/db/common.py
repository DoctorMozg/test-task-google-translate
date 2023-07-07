import enum
from sqlalchemy import Enum, MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import declarative_base, DeclarativeBase


class Actuality(enum.Enum):
    ACTUAL = 'actual'
    OUTDATED = 'outdated'

    def __str__(self):
        return str(self.value)


def _get_enum_values(enum_cls):
    return [item.value for item in enum_cls]


DbActuality = Enum(Actuality, name='actuality', values_callable=_get_enum_values)


class Base(AsyncAttrs, DeclarativeBase):
    pass

