# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Tuple
from pydantic import BaseModel, Field, field_validator

from .pagination_config import PaginationDefaults


class PaginationParams(BaseModel):

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
    )
    page_size: int = Field(
        default=PaginationDefaults.DEFAULT_PAGE_SIZE,
        ge=1,
        le=PaginationDefaults.MAX_PAGE_SIZE,
        description=f"Results per page (max: {PaginationDefaults.MAX_PAGE_SIZE})",
    )

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page must be at least 1")
        return v

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page_size must be at least 1")
        if v > PaginationDefaults.MAX_PAGE_SIZE:
            raise ValueError(
                f"page_size cannot exceed {PaginationDefaults.MAX_PAGE_SIZE}"
            )
        return v

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def calculate_pagination(
    page: int = 1,
    page_size: int = PaginationDefaults.DEFAULT_PAGE_SIZE,
) -> Tuple[int, int]:
    if page < 1:
        raise ValueError("page must be at least 1")
    if page_size < 1:
        raise ValueError("page_size must be at least 1")
    if page_size > PaginationDefaults.MAX_PAGE_SIZE:
        raise ValueError(
            f"page_size cannot exceed {PaginationDefaults.MAX_PAGE_SIZE}"
        )

    offset = (page - 1) * page_size
    limit = page_size

    return offset, limit


def calculate_total_pages(total_items: int, page_size: int) -> int:
    if page_size <= 0:
        return 0
    return (total_items + page_size - 1) // page_size
