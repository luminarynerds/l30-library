# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.catalog import CatalogItem, ItemStatus, ItemType
from app.core.logging import get_logger
from ..models.bibframe import (
    BibframeWork, BibframeInstance, BibframeItem,
    BibframeContributor, BibframeSubject,
    WorkType, InstanceType, CarrierType, MediaType,
    ContributorRole, AuthoritySource,
    work_contributors, work_subjects,
)
from .catalog_subjects import parse_subjects_field


def _split_isbn(raw: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not raw:
        return (None, None)
    value = raw.replace("-", "").replace(" ", "").strip()
    if not value:
        return (None, None)
    if len(value) == 10:
        body, check = value[:9], value[9].upper()
        if body.isdigit() and (check.isdigit() or check == "X"):
            return (body + check, None)
        return (None, None)
    if len(value) == 13 and value.isdigit():
        return (None, value)
    return (None, None)


class CatalogBibframeSync:

    @staticmethod
    async def _get_work_type(item_type: ItemType) -> WorkType:
        type_map = {
            ItemType.book: WorkType.text,
            ItemType.audiobook: WorkType.text,
            ItemType.ebook: WorkType.text,
            ItemType.magazine: WorkType.text,
            ItemType.dvd: WorkType.three_dimensional_moving_image,
            ItemType.bluray: WorkType.three_dimensional_moving_image,
            ItemType.cd: WorkType.performed_music,
            ItemType.vinyl: WorkType.performed_music,
            ItemType.game: WorkType.computer_program,
            ItemType.equipment: WorkType.three_dimensional_form,
            ItemType.kit: WorkType.three_dimensional_form,
            ItemType.tool: WorkType.three_dimensional_form,
            ItemType.other: WorkType.other,
        }
        return type_map.get(item_type, WorkType.other)

    @staticmethod
    async def _get_instance_type(item_type: ItemType) -> InstanceType:
        type_map = {
            ItemType.book: InstanceType.print,
            ItemType.audiobook: InstanceType.audio,
            ItemType.ebook: InstanceType.electronic,
            ItemType.magazine: InstanceType.print,
            ItemType.dvd: InstanceType.audiovisual,
            ItemType.bluray: InstanceType.audiovisual,
            ItemType.cd: InstanceType.audio,
            ItemType.vinyl: InstanceType.audio,
            ItemType.game: InstanceType.electronic,
            ItemType.equipment: InstanceType.print,
            ItemType.kit: InstanceType.print,
            ItemType.tool: InstanceType.print,
            ItemType.other: InstanceType.print,
        }
        return type_map.get(item_type, InstanceType.print)

    @staticmethod
    async def _get_carrier_type(item_type: ItemType) -> CarrierType:
        type_map = {
            ItemType.book: CarrierType.volume,
            ItemType.audiobook: CarrierType.audiocassette,
            ItemType.ebook: CarrierType.online_resource,
            ItemType.magazine: CarrierType.volume,
            ItemType.dvd: CarrierType.videodisc,
            ItemType.bluray: CarrierType.videodisc,
            ItemType.cd: CarrierType.audio_disc,
            ItemType.vinyl: CarrierType.audio_disc,
            ItemType.game: CarrierType.computer_disc,
            ItemType.equipment: CarrierType.object,
            ItemType.kit: CarrierType.object,
            ItemType.tool: CarrierType.object,
            ItemType.other: CarrierType.other,
        }
        return type_map.get(item_type, CarrierType.other)

    @staticmethod
    async def _get_media_type(item_type: ItemType) -> MediaType:
        type_map = {
            ItemType.book: MediaType.unmediated,
            ItemType.audiobook: MediaType.audio,
            ItemType.ebook: MediaType.computer,
            ItemType.magazine: MediaType.unmediated,
            ItemType.dvd: MediaType.video,
            ItemType.bluray: MediaType.video,
            ItemType.cd: MediaType.audio,
            ItemType.vinyl: MediaType.audio,
            ItemType.game: MediaType.computer,
            ItemType.equipment: MediaType.unmediated,
            ItemType.kit: MediaType.unmediated,
            ItemType.tool: MediaType.unmediated,
            ItemType.other: MediaType.unmediated,
        }
        return type_map.get(item_type, MediaType.unmediated)

    @staticmethod
    async def _get_bibframe_item_status(catalog_status: ItemStatus) -> str:
        status_map = {
            ItemStatus.available: "available",
            ItemStatus.checked_out: "checked_out",
            ItemStatus.on_hold: "on_hold",
            ItemStatus.in_processing: "in_processing",
            ItemStatus.in_transit: "in_transit",
            ItemStatus.lost_by_patron: "lost",
            ItemStatus.lost_in_transit: "lost",
            ItemStatus.claims_returned: "claims_returned",
            ItemStatus.damaged_repairable: "damaged",
            ItemStatus.damaged_withdrawn: "withdrawn",
            ItemStatus.in_mending: "in_mending",
        }
        return status_map.get(catalog_status, "unknown")

    @staticmethod
    async def create_from_catalog(
        db: AsyncSession,
        catalog_item: CatalogItem,
    ) -> Optional[BibframeItem]:
        try:
            # Step 1: Get or create Work.
            #
            # Dedup by (title, work_type) plus the AUTHOR-role contributor
            # when one is present on the catalog item. Title-only dedup
            # collided unrelated books with identical titles ("Beloved",
            # "Open", "Home") into one Work, and a later update on any
            # child silently rewrote the shared title. Including
            # ``work_type`` separates books from films and the contributor
            # join scopes the lookup to the right author.
            work_type = await CatalogBibframeSync._get_work_type(
                ItemType(catalog_item.item_type)
            )
            work_query = (
                select(BibframeWork)
                .where(
                    BibframeWork.title == catalog_item.title,
                    BibframeWork.work_type == work_type,
                )
                .limit(1)
            )
            if catalog_item.author:
                work_query = (
                    work_query
                    .join(work_contributors, work_contributors.c.work_id == BibframeWork.id)
                    .join(
                        BibframeContributor,
                        BibframeContributor.id == work_contributors.c.contributor_id,
                    )
                    .where(BibframeContributor.name == catalog_item.author)
                )
            work_result = await db.execute(work_query)
            work = work_result.scalar_one_or_none()

            if not work:
                work = BibframeWork(
                    title=catalog_item.title,
                    work_type=work_type,
                    language="eng",
                    summary=catalog_item.description,
                )
                db.add(work)
                await db.flush()

            # Step 2: Get or create Instance (dedup by ISBN + item_type combo)
            isbn_10, isbn_13 = _split_isbn(catalog_item.isbn)
            instance_query = select(BibframeInstance).where(
                BibframeInstance.work_id == work.id
            )
            if isbn_10 or isbn_13:
                # Match either column; only one will be non-None for a given catalog row.
                instance_query = instance_query.where(
                    or_(
                        BibframeInstance.isbn_10 == isbn_10,
                        BibframeInstance.isbn_13 == isbn_13,
                    )
                )
            # If the catalog ISBN is missing or malformed, skip the ISBN filter
            # entirely and fall through to the work-title dedup above.

            instance_result = await db.execute(instance_query)
            instance = instance_result.scalar_one_or_none()

            if not instance:
                instance_type = await CatalogBibframeSync._get_instance_type(
                    ItemType(catalog_item.item_type)
                )
                carrier_type = await CatalogBibframeSync._get_carrier_type(
                    ItemType(catalog_item.item_type)
                )
                media_type = await CatalogBibframeSync._get_media_type(
                    ItemType(catalog_item.item_type)
                )

                instance = BibframeInstance(
                    work_id=work.id,
                    title=catalog_item.title,
                    isbn_10=isbn_10,
                    isbn_13=isbn_13,
                    publisher=catalog_item.publisher,
                    publication_year=catalog_item.publication_year,
                    instance_type=instance_type,
                    carrier_type=carrier_type,
                    media_type=media_type,
                    catalog_item_id=catalog_item.id,
                )
                db.add(instance)
                await db.flush()
            elif instance.catalog_item_id is None:
                instance.catalog_item_id = catalog_item.id
                await db.flush()

            # Step 3: Create Item
            bibframe_item_status = await CatalogBibframeSync._get_bibframe_item_status(
                ItemStatus(catalog_item.status)
            )

            item = BibframeItem(
                instance_id=instance.id,
                barcode=catalog_item.barcode,
                call_number=catalog_item.call_number,
                circulation_status=bibframe_item_status,
                library_branch="Main",
                shelving_location=catalog_item.location or "Main",
            )
            db.add(item)
            await db.flush()

            # Step 4: Add contributors (author/director/artist)
            await CatalogBibframeSync._sync_contributors(db, work, catalog_item)

            # Step 5: Add subjects
            await CatalogBibframeSync._sync_subjects(db, work, catalog_item)

            return item

        except Exception as e:
            # Log but don't fail the catalog operation if BIBFRAME sync fails
            import logging
            logger = get_logger(__name__)
            logger.error(f"Failed to sync catalog item {catalog_item.id} to BIBFRAME: {e}", exc_info=True)
            return None

    @staticmethod
    async def update_from_catalog(
        db: AsyncSession,
        catalog_item: CatalogItem,
    ) -> Optional[BibframeItem]:
        try:
            # Find existing BIBFRAME item by matching barcode or title/item_type
            item_result = await db.execute(
                select(BibframeItem).where(
                    BibframeItem.barcode == catalog_item.barcode
                ) if catalog_item.barcode else
                select(BibframeItem).join(BibframeInstance).join(BibframeWork).where(
                    BibframeWork.title == catalog_item.title
                )
            )
            bibframe_item = item_result.scalar_one_or_none()

            if not bibframe_item:
                # Create if doesn't exist
                return await CatalogBibframeSync.create_from_catalog(db, catalog_item)

            # Update existing item
            bibframe_item_status = await CatalogBibframeSync._get_bibframe_item_status(
                ItemStatus(catalog_item.status)
            )

            bibframe_item.call_number = catalog_item.call_number
            bibframe_item.circulation_status = bibframe_item_status
            bibframe_item.shelving_location = catalog_item.location or "Main"

            # Update instance metadata if changed. ``publication_year`` was
            # previously omitted, so catalog edits to that field silently
            # drifted from the linked-data layer.
            if bibframe_item.instance:
                isbn_10, isbn_13 = _split_isbn(catalog_item.isbn)
                bibframe_item.instance.title = catalog_item.title
                bibframe_item.instance.isbn_10 = isbn_10
                bibframe_item.instance.isbn_13 = isbn_13
                bibframe_item.instance.publisher = catalog_item.publisher
                if hasattr(bibframe_item.instance, "publication_year"):
                    bibframe_item.instance.publication_year = catalog_item.publication_year

                # Update work metadata if needed
                if bibframe_item.instance.work:
                    bibframe_item.instance.work.title = catalog_item.title
                    bibframe_item.instance.work.summary = catalog_item.description

            await db.flush()
            return bibframe_item

        except Exception as e:
            import logging
            logger = get_logger(__name__)
            logger.error(f"Failed to update catalog item {catalog_item.id} in BIBFRAME: {e}", exc_info=True)
            return None

    @staticmethod
    async def delete_from_catalog(
        db: AsyncSession,
        catalog_item: CatalogItem,
    ) -> None:
        try:
            # Without a barcode there is no safe way to identify which
            # BibframeItem belongs to this catalog row -- the previous
            # title-only fallback silently deleted an unrelated item that
            # happened to share a title (or raised ``MultipleResultsFound``
            # when the title was non-unique). Skip the delete in that case
            # and log loudly so manual cleanup can happen.
            if not catalog_item.barcode:
                import logging
                get_logger(__name__).warning(
                    "Skipping BIBFRAME delete for catalog_item %s: no barcode "
                    "to disambiguate; manual cleanup required if a stale "
                    "BibframeItem remains.",
                    catalog_item.id,
                )
                return

            # Find and delete the BIBFRAME item (but keep Work/Instance for reference)
            item_result = await db.execute(
                select(BibframeItem).where(
                    BibframeItem.barcode == catalog_item.barcode
                )
            )
            bibframe_item = item_result.scalar_one_or_none()

            if bibframe_item:
                await db.delete(bibframe_item)
                await db.flush()

        except Exception as e:
            import logging
            logger = get_logger(__name__)
            logger.error(f"Failed to delete catalog item {catalog_item.id} from BIBFRAME: {e}", exc_info=True)

    @staticmethod
    async def _sync_contributors(
        db: AsyncSession,
        work: BibframeWork,
        catalog_item: CatalogItem,
    ) -> None:
        contributors_to_add = []

        if catalog_item.author:
            contributors_to_add.append((catalog_item.author, ContributorRole.author))
        if catalog_item.director:
            contributors_to_add.append((catalog_item.director, ContributorRole.director))
        if catalog_item.artist:
            contributors_to_add.append((catalog_item.artist, ContributorRole.performer))

        for name, role in contributors_to_add:
            # Get or create contributor
            contrib_result = await db.execute(
                select(BibframeContributor).where(
                    BibframeContributor.name == name
                )
            )
            contrib = contrib_result.scalar_one_or_none()

            if not contrib:
                contrib = BibframeContributor(name=name)
                db.add(contrib)
                await db.flush()

            # Link to work if not already linked
            existing = await db.execute(
                select(work_contributors).where(
                    work_contributors.c.work_id == work.id,
                    work_contributors.c.contributor_id == contrib.id,
                )
            )
            if not existing.first():
                await db.execute(
                    work_contributors.insert().values(
                        work_id=work.id,
                        contributor_id=contrib.id,
                        role=role,
                    )
                )

    @staticmethod
    async def _sync_subjects(
        db: AsyncSession,
        work: BibframeWork,
        catalog_item: CatalogItem,
    ) -> None:
        if not catalog_item.subjects:
            return

        subject_names = parse_subjects_field(catalog_item.subjects)

        for subject_name in subject_names:
            if not subject_name:
                continue

            # Get or create subject
            subject_result = await db.execute(
                select(BibframeSubject).where(
                    BibframeSubject.label == subject_name
                )
            )
            subject = subject_result.scalar_one_or_none()

            if not subject:
                subject = BibframeSubject(label=subject_name, source=AuthoritySource.LCSH)
                db.add(subject)
                await db.flush()

            # Link to work if not already linked
            existing = await db.execute(
                select(work_subjects).where(
                    work_subjects.c.work_id == work.id,
                    work_subjects.c.subject_id == subject.id,
                )
            )
            if not existing.first():
                await db.execute(
                    work_subjects.insert().values(
                        work_id=work.id,
                        subject_id=subject.id,
                    )
                )
