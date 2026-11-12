# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional
from xml.dom import minidom

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import APIError
from ..core.error_codes import ErrorCode
from ..models.catalog import CatalogItem
from ..models.collection import ArchivalLevel, Collection, CollectionItem
from ..schemas.collection import (
    CollectionCreate,
    CollectionTreeNode,
    CollectionUpdate,
)


EAD3_NS = "http://ead3.archivists.org/schema/"


class ArchivalCollectionError(APIError):

    def __init__(self, message: str, code: ErrorCode = ErrorCode.VALIDATION_FAILED, status_code: int = 400):
        super().__init__(code=code, message=message, status_code=status_code)


async def _validate_parent(
    db: AsyncSession, parent_id: Optional[int], self_id: Optional[int] = None
) -> None:
    if parent_id is None:
        return
    if self_id is not None and parent_id == self_id:
        raise ArchivalCollectionError("A collection cannot be its own parent.")
    parent = await db.get(Collection, parent_id)
    if parent is None:
        raise ArchivalCollectionError(
            f"Parent collection {parent_id} not found.", status_code=404
        )
    if self_id is not None and await _is_descendant_of(db, parent_id, self_id):
        raise ArchivalCollectionError(
            "Cannot move a collection beneath one of its own descendants."
        )


async def _is_descendant_of(
    db: AsyncSession, candidate_id: int, ancestor_id: int
) -> bool:
    current = await db.get(Collection, candidate_id)
    while current is not None and current.parent_id is not None:
        if current.parent_id == ancestor_id:
            return True
        current = await db.get(Collection, current.parent_id)
    return False


async def create_collection(
    db: AsyncSession, data: CollectionCreate
) -> Collection:
    await _validate_parent(db, data.parent_id)
    if data.reference_code:
        existing = await db.execute(
            select(Collection.id).where(Collection.reference_code == data.reference_code)
        )
        if existing.scalar_one_or_none() is not None:
            raise ArchivalCollectionError(
                f"Reference code {data.reference_code!r} is already in use.",
                status_code=409,
            )
    payload = data.model_dump(exclude_unset=False)
    collection = Collection(**payload)
    db.add(collection)
    await db.flush()
    await db.refresh(collection)
    return collection


async def update_collection(
    db: AsyncSession, collection_id: int, data: CollectionUpdate
) -> Collection:
    collection = await db.get(Collection, collection_id)
    if collection is None:
        raise ArchivalCollectionError(
            f"Collection {collection_id} not found.", status_code=404
        )
    updates = data.model_dump(exclude_unset=True)
    if "parent_id" in updates:
        await _validate_parent(db, updates["parent_id"], self_id=collection_id)
    if "reference_code" in updates and updates["reference_code"]:
        existing = await db.execute(
            select(Collection.id).where(
                Collection.reference_code == updates["reference_code"],
                Collection.id != collection_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ArchivalCollectionError(
                f"Reference code {updates['reference_code']!r} is already in use.",
                status_code=409,
            )
    for key, value in updates.items():
        setattr(collection, key, value)
    await db.flush()
    await db.refresh(collection)
    return collection


async def delete_collection(db: AsyncSession, collection_id: int) -> None:
    collection = await db.get(Collection, collection_id)
    if collection is None:
        raise ArchivalCollectionError(
            f"Collection {collection_id} not found.", status_code=404
        )
    child_count = await db.scalar(
        select(func.count(Collection.id)).where(Collection.parent_id == collection_id)
    )
    if child_count:
        raise ArchivalCollectionError(
            "Cannot delete a collection that has child components. "
            "Move or delete children first.",
            status_code=409,
        )
    await db.delete(collection)
    await db.flush()


async def move_collection(
    db: AsyncSession,
    collection_id: int,
    new_parent_id: Optional[int],
    position: int,
) -> Collection:
    collection = await db.get(Collection, collection_id)
    if collection is None:
        raise ArchivalCollectionError(
            f"Collection {collection_id} not found.", status_code=404
        )
    await _validate_parent(db, new_parent_id, self_id=collection_id)
    collection.parent_id = new_parent_id
    collection.position = position
    await db.flush()
    await db.refresh(collection)
    return collection


async def get_collection(db: AsyncSession, collection_id: int) -> Collection:
    collection = await db.get(Collection, collection_id)
    if collection is None:
        raise ArchivalCollectionError(
            f"Collection {collection_id} not found.", status_code=404
        )
    return collection


async def list_root_collections(db: AsyncSession) -> list[Collection]:
    result = await db.execute(
        select(Collection)
        .where(Collection.parent_id.is_(None))
        .order_by(Collection.position, Collection.id)
    )
    return list(result.scalars().all())


async def get_subtree(db: AsyncSession, root_id: int) -> CollectionTreeNode:
    root = await db.get(Collection, root_id)
    if root is None:
        raise ArchivalCollectionError(
            f"Collection {root_id} not found.", status_code=404
        )

    descendants = await _fetch_descendants(db, root_id)
    counts = await _fetch_item_counts(db, [root_id, *(c.id for c in descendants)])

    by_parent: dict[int, list[Collection]] = {}
    for c in descendants:
        by_parent.setdefault(c.parent_id, []).append(c)
    for siblings in by_parent.values():
        siblings.sort(key=lambda x: (x.position, x.id))

    def build(node: Collection) -> CollectionTreeNode:
        children = by_parent.get(node.id, [])
        tree_node = CollectionTreeNode.model_validate(node)
        tree_node.item_count = counts.get(node.id, 0)
        tree_node.children = [build(child) for child in children]
        return tree_node

    return build(root)


async def _fetch_descendants(
    db: AsyncSession, root_id: int
) -> list[Collection]:
    queue = [root_id]
    descendants: list[Collection] = []
    seen = {root_id}
    while queue:
        result = await db.execute(
            select(Collection).where(Collection.parent_id.in_(queue))
        )
        layer = list(result.scalars().all())
        next_queue: list[int] = []
        for c in layer:
            if c.id in seen:
                continue
            seen.add(c.id)
            descendants.append(c)
            next_queue.append(c.id)
        queue = next_queue
    return descendants


async def _fetch_item_counts(
    db: AsyncSession, collection_ids: list[int]
) -> dict[int, int]:
    if not collection_ids:
        return {}
    result = await db.execute(
        select(
            CollectionItem.collection_id,
            func.count(CollectionItem.id),
        )
        .where(CollectionItem.collection_id.in_(collection_ids))
        .group_by(CollectionItem.collection_id)
    )
    return {row[0]: row[1] for row in result.all()}


async def add_item(
    db: AsyncSession,
    collection_id: int,
    catalog_item_id: int,
    position: int = 0,
    component_label: Optional[str] = None,
    note: Optional[str] = None,
) -> CollectionItem:
    collection = await db.get(Collection, collection_id)
    if collection is None:
        raise ArchivalCollectionError(
            f"Collection {collection_id} not found.", status_code=404
        )
    item = await db.get(CatalogItem, catalog_item_id)
    if item is None:
        raise ArchivalCollectionError(
            f"Catalog item {catalog_item_id} not found.", status_code=404
        )
    existing = await db.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == collection_id,
            CollectionItem.catalog_item_id == catalog_item_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ArchivalCollectionError(
            "Catalog item is already assigned to this collection.",
            status_code=409,
        )
    link = CollectionItem(
        collection_id=collection_id,
        catalog_item_id=catalog_item_id,
        position=position,
        component_label=component_label,
        note=note,
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return link


async def remove_item(db: AsyncSession, collection_id: int, link_id: int) -> None:
    link = await db.get(CollectionItem, link_id)
    if link is None or link.collection_id != collection_id:
        raise ArchivalCollectionError(
            "Collection item link not found.", status_code=404
        )
    await db.delete(link)
    await db.flush()


async def list_items(
    db: AsyncSession, collection_id: int
) -> list[tuple[CollectionItem, CatalogItem]]:
    result = await db.execute(
        select(CollectionItem, CatalogItem)
        .join(CatalogItem, CatalogItem.id == CollectionItem.catalog_item_id)
        .where(CollectionItem.collection_id == collection_id)
        .order_by(CollectionItem.position, CollectionItem.id)
    )
    return [(link, item) for link, item in result.all()]


# ---------------------------------------------------------------------------
# EAD3 XML export
# ---------------------------------------------------------------------------


def _ead_level(level: Optional[ArchivalLevel]) -> str:
    if level is None:
        return "otherlevel"
    return {
        ArchivalLevel.collection: "collection",
        ArchivalLevel.fonds: "fonds",
        ArchivalLevel.recordgrp: "recordgrp",
        ArchivalLevel.subgrp: "subgrp",
        ArchivalLevel.series: "series",
        ArchivalLevel.subseries: "subseries",
        ArchivalLevel.file: "file",
        ArchivalLevel.item: "item",
    }.get(level, "otherlevel")


def _add_text(parent: ET.Element, tag: str, text: Optional[str]) -> Optional[ET.Element]:
    if text is None or text == "":
        return None
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


def _add_paragraph_block(parent: ET.Element, tag: str, text: Optional[str]) -> None:
    if text is None or text == "":
        return
    block = ET.SubElement(parent, tag)
    para = ET.SubElement(block, "p")
    para.text = text


async def render_ead3(
    db: AsyncSession, collection_id: int
) -> str:
    collection = await db.get(Collection, collection_id)
    if collection is None:
        raise ArchivalCollectionError(
            f"Collection {collection_id} not found.", status_code=404
        )
    descendants = await _fetch_descendants(db, collection_id)
    by_id = {c.id: c for c in [collection, *descendants]}
    by_parent: dict[Optional[int], list[Collection]] = {}
    for c in [collection, *descendants]:
        by_parent.setdefault(c.parent_id, []).append(c)
    for siblings in by_parent.values():
        siblings.sort(key=lambda x: (x.position, x.id))

    items_by_collection: dict[int, list[tuple[CollectionItem, CatalogItem]]] = {}
    for cid in by_id:
        items_by_collection[cid] = await list_items(db, cid)

    ET.register_namespace("", EAD3_NS)
    root = ET.Element(f"{{{EAD3_NS}}}ead")

    control = ET.SubElement(root, "control")
    recordid = ET.SubElement(control, "recordid")
    recordid.text = collection.reference_code or f"l30-collection-{collection.id}"
    filedesc = ET.SubElement(control, "filedesc")
    titlestmt = ET.SubElement(filedesc, "titlestmt")
    titleproper = ET.SubElement(titlestmt, "titleproper")
    titleproper.text = collection.title or collection.name

    archdesc = ET.SubElement(root, "archdesc", level=_ead_level(collection.level))
    _build_did(archdesc, collection)
    _build_descriptive(archdesc, collection)

    children = by_parent.get(collection.id, [])
    root_items = items_by_collection.get(collection.id, [])
    if children or root_items:
        dsc = ET.SubElement(archdesc, "dsc")
        for child in children:
            _build_component(dsc, child, by_parent, items_by_collection)
        for link, item in root_items:
            item_c = ET.SubElement(dsc, "c", attrib={"level": "item"})
            item_did = ET.SubElement(item_c, "did")
            unittitle = ET.SubElement(item_did, "unittitle")
            unittitle.text = link.component_label or item.title
            if item.author:
                origination = ET.SubElement(item_did, "origination")
                persname = ET.SubElement(origination, "persname")
                persname.text = item.author

    rough = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def _build_did(parent: ET.Element, collection: Collection) -> None:
    did = ET.SubElement(parent, "did")
    if collection.reference_code:
        unitid = ET.SubElement(did, "unitid")
        unitid.text = collection.reference_code
    unittitle = ET.SubElement(did, "unittitle")
    unittitle.text = collection.title or collection.name
    if collection.date_creation:
        unitdate = ET.SubElement(did, "unitdate", attrib={"datechar": "creation"})
        unitdate.text = collection.date_creation
    if collection.date_accumulation:
        unitdate = ET.SubElement(did, "unitdate", attrib={"datechar": "accumulation"})
        unitdate.text = collection.date_accumulation
    if collection.extent:
        physdesc = ET.SubElement(did, "physdesc")
        extent = ET.SubElement(physdesc, "extent")
        extent.text = collection.extent
    if collection.creator:
        origination = ET.SubElement(did, "origination")
        persname = ET.SubElement(origination, "persname")
        persname.text = collection.creator
    if collection.languages:
        langmaterial = ET.SubElement(did, "langmaterial")
        langmaterial.text = collection.languages
    if collection.description:
        abstract = ET.SubElement(did, "abstract")
        abstract.text = collection.description


def _build_descriptive(
    parent: ET.Element,
    collection: Collection,
) -> None:
    _add_paragraph_block(parent, "bioghist", collection.biographical_history)
    _add_paragraph_block(parent, "custodhist", collection.archival_history)
    _add_paragraph_block(parent, "acqinfo", collection.acquisition_source)
    _add_paragraph_block(parent, "scopecontent", collection.scope_content)
    _add_paragraph_block(parent, "appraisal", collection.appraisal)
    _add_paragraph_block(parent, "accruals", collection.accruals)
    _add_paragraph_block(parent, "arrangement", collection.arrangement)
    _add_paragraph_block(parent, "accessrestrict", collection.access_conditions)
    _add_paragraph_block(parent, "userestrict", collection.reproduction_conditions)
    _add_paragraph_block(parent, "phystech", collection.technical_access)
    _add_paragraph_block(parent, "otherfindaid", collection.finding_aids)
    _add_paragraph_block(parent, "originalsloc", collection.originals_location)
    _add_paragraph_block(parent, "altformavail", collection.copies_location)
    _add_paragraph_block(parent, "relatedmaterial", collection.related_materials)
    _add_paragraph_block(parent, "bibliography", collection.publication_note)
    _add_paragraph_block(parent, "odd", collection.notes)


def _build_component(
    parent: ET.Element,
    node: Collection,
    by_parent: dict[Optional[int], list[Collection]],
    items_by_collection: dict[int, list[tuple[CollectionItem, CatalogItem]]],
) -> None:
    c = ET.SubElement(parent, "c", attrib={"level": _ead_level(node.level)})
    _build_did(c, node)
    _build_descriptive(c, node)
    for link, item in items_by_collection.get(node.id, []):
        item_c = ET.SubElement(c, "c", attrib={"level": "item"})
        item_did = ET.SubElement(item_c, "did")
        unittitle = ET.SubElement(item_did, "unittitle")
        unittitle.text = link.component_label or item.title
        if item.author:
            origination = ET.SubElement(item_did, "origination")
            persname = ET.SubElement(origination, "persname")
            persname.text = item.author
    for child in by_parent.get(node.id, []):
        _build_component(c, child, by_parent, items_by_collection)
