from pydantic.dataclasses import dataclass
from pydantic import field_validator


@dataclass
class Language:
    code: str

    # @field_validator("code")
    # def language_code_must_be_valid(cls, field: str):
    #     if len(field) != 2:
    #         raise ValueError(f"Language code is of wrong length")
    #
    #     # TODO: Add language validation
