# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Catalog import must land subjects in both the legacy text column AND the
normalized Subject / CatalogItemSubject tables."""
import pytest
from sqlalchemy import select

from app.models.catalog import CatalogItem
from app.models.subject import CatalogItemSubject, Subject
from app.services.catalog_import import run_import, save_upload


@pytest.mark.asyncio
async def test_import_normalizes_comma_delimited_subjects(db_session):
    csv_text = (
        "title,author,isbn,subjects\n"
        'The Great Gatsby,F. Scott Fitzgerald,9780743273565,"Fiction, Jazz Age"\n'
    )
    upload_id = save_upload(csv_text.encode("utf-8"), "test_comma.csv")

    await run_import(
        upload_id=upload_id, fmt="csv", field_mapping=None,
        skip_invalid=True, db=db_session,
    )

    item = (await db_session.execute(
        select(CatalogItem).where(CatalogItem.isbn == "9780743273565")
    )).scalar_one()

    # Legacy column still populated (back-compat).
    assert item.subjects == "Fiction, Jazz Age"

    # Normalized tables populated.
    subj_names = (await db_session.execute(
        select(Subject.label)
        .join(CatalogItemSubject, CatalogItemSubject.subject_id == Subject.id)
        .where(CatalogItemSubject.catalog_item_id == item.id)
    )).scalars().all()
    assert sorted(subj_names) == ["Fiction", "Jazz Age"]


@pytest.mark.asyncio
async def test_import_handles_semicolon_delimited_subjects(db_session):
    csv_text = (
        "title,isbn,subjects\n"
        'Beloved,9781400033416,"Fiction; American Literature; Pulitzer"\n'
    )
    upload_id = save_upload(csv_text.encode("utf-8"), "test_semi.csv")
    await run_import(
        upload_id=upload_id, fmt="csv", field_mapping=None,
        skip_invalid=True, db=db_session,
    )
    item = (await db_session.execute(
        select(CatalogItem).where(CatalogItem.isbn == "9781400033416")
    )).scalar_one()
    subj_names = (await db_session.execute(
        select(Subject.label)
        .join(CatalogItemSubject, CatalogItemSubject.subject_id == Subject.id)
        .where(CatalogItemSubject.catalog_item_id == item.id)
    )).scalars().all()
    assert sorted(subj_names) == ["American Literature", "Fiction", "Pulitzer"]


@pytest.mark.asyncio
async def test_subjects_are_deduplicated_across_imports(db_session):
    """Two items sharing 'Fiction' must reuse one Subject row."""
    csv_text = (
        "title,isbn,subjects\n"
        'Item One,1111111111111,"Fiction"\n'
        'Item Two,2222222222222,"Fiction"\n'
    )
    upload_id = save_upload(csv_text.encode("utf-8"), "test_dedup.csv")
    await run_import(
        upload_id=upload_id, fmt="csv", field_mapping=None,
        skip_invalid=True, db=db_session,
    )
    fiction_rows = (await db_session.execute(
        select(Subject).where(Subject.label == "Fiction")
    )).scalars().all()
    assert len(fiction_rows) == 1, "Subject 'Fiction' must be reused across items"
