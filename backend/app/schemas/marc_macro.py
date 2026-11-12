# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema

from app.models.marc_macro import MarcMacroVisibility


# Catalog fields a macro can target. Keys are MARC tag/subfield strings;
# values are the CatalogItem column they map to. Kept here (not in the model)
# because it is a service-layer concern, but exposed for the schema validator
# so callers see a 400 -- not a 500 -- on unknown tags.
SUPPORTED_TARGETS: dict[str, str] = {
    "245$a": "title",
    "245$n": "volume_number",
    "245$p": "volume_label",
    "100$a": "author",
    "020$a": "isbn",
    "010$a": "lccn",
    "035$a": "oclc_number",
    "260$b": "publisher",
    "260$c": "publication_year",
    "250$a": "edition",
    "490$a": "series_name",
    "490$v": "series_number",
    "520$a": "description",
    "650$a": "subjects",
    "082$a": "dewey_decimal",
    "050$a": "lc_classification",
    "300$a": "page_count",
}

OpType = Literal["set", "clear", "find_replace", "append"]


class MarcMacroStep(BaseModel):
    op: OpType
    tag: str = Field(..., min_length=3, max_length=3)
    subfield: str = Field(..., min_length=1, max_length=1)
    value: str | None = None
    find: str | None = None
    replace: str | None = None

    @field_validator("tag")
    @classmethod
    def _tag_is_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("tag must be three digits")
        return v

    @field_validator("subfield")
    @classmethod
    def _subfield_is_alnum(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("subfield must be a single alphanumeric character")
        return v.lower()

    def target(self) -> str:
        return f"{self.tag}${self.subfield}"


class MarcMacroBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    visibility: MarcMacroVisibility
    steps: list[MarcMacroStep] = Field(default_factory=list)


class MarcMacroCreate(StrictInputSchema, MarcMacroBase):
    pass


class MarcMacroUpdate(StrictInputSchema):
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = None
    visibility: MarcMacroVisibility | None = None
    steps: list[MarcMacroStep] | None = None


class MarcMacroResponse(MarcMacroBase):
    id: int
    owner_id: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MarcMacroListResponse(BaseModel):
    items: list[MarcMacroResponse]
    total: int


class MarcMacroRunRequest(StrictInputSchema):
    catalog_item_ids: list[int] = Field(..., min_length=1, max_length=500)


class MarcMacroRunItemResult(BaseModel):
    catalog_item_id: int
    changed_fields: list[str]
    skipped_steps: list[str] = Field(default_factory=list)
    error: str | None = None


class MarcMacroRunResponse(BaseModel):
    macro_id: int
    total: int
    succeeded: int
    failed: int
    results: list[MarcMacroRunItemResult]
