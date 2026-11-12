# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""ICU locale-aware sort for catalog title/author across scripts.

Postgres byte-order sort puts Arabic/CJK and accented Latin at the bottom
of A-Z lists. ICU "und-x-icu" collation orders them by locale rules so
non-Latin and accented titles interleave correctly.
"""

import pytest
from sqlalchemy import select

from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)


@pytest.fixture
async def mixed_script_catalog(test_db):
    """Three titles: English, accented Spanish, Arabic.

    Byte-order would sort: Apple, Banana, Ávila, الكتاب
        (Latin A-Z < UTF-8 multibyte; Á=0xC3 sorts AFTER B=0x42; Arabic=0xD8 last)
    ICU und-x-icu collation sorts: Apple, Ávila, Banana, الكتاب
        (accent-insensitive primary: Á≈A, so Ávila falls between Apple and Banana;
         Arabic sorts after Latin in the root locale, which is expected.)

    The discriminating assertion is the Ávila placement — ICU puts it BEFORE
    Banana; byte order puts it AFTER.
    """
    items = [
        CatalogItem(
            title="Banana Republic",
            author="Smith",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
        CatalogItem(
            title="Ávila",
            author="García",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
        CatalogItem(
            title="Apple Orchards",
            author="Jones",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
        CatalogItem(
            title="الكتاب",  # Arabic: "The Book"
            author="ابن سينا",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
    ]
    for item in items:
        test_db.add(item)
    await test_db.commit()
    return items


@pytest.mark.asyncio
async def test_title_sort_is_icu_locale_aware(test_db, mixed_script_catalog):
    """ICU collation places accented Latin between unaccented siblings."""
    if test_db.bind.dialect.name != "postgresql":
        pytest.skip("ICU collation requires Postgres (SQLite has no und-x-icu)")

    query = (
        select(CatalogItem.title)
        .where(CatalogItem.title.in_(["Apple Orchards", "Ávila", "Banana Republic", "الكتاب"]))
        .order_by(CatalogItem.title.collate("und-x-icu"))
    )
    result = await test_db.execute(query)
    titles = [row[0] for row in result.all()]

    # The byte-order sort would give: ["Apple Orchards", "Banana Republic", "Ávila", "الكتاب"]
    # ICU root locale: "Ávila" sorts between "Apple Orchards" and "Banana Republic".
    apple_idx = titles.index("Apple Orchards")
    avila_idx = titles.index("Ávila")
    banana_idx = titles.index("Banana Republic")

    assert apple_idx < avila_idx < banana_idx, (
        f"Expected ICU order Apple < Ávila < Banana, got: {titles}"
    )
