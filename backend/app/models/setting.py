"""A tiny key/value store for settings the owner can change at runtime.

Most configuration comes from the environment (one value per shop, fixed at
deploy time). A few things — like the brand colours — are nicer to tweak live
from the UI, so they live here in the database instead.
"""

from sqlmodel import Field, SQLModel


class Setting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str

    def __str__(self) -> str:
        return f"{self.key} = {self.value}"
