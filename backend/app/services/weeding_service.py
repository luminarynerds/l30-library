# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import case, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.catalog import CatalogItem, ItemStatus
from ..models.circulation import Checkout, CheckoutStatus
from ..models.inventory import ItemCondition, ItemCopy
from ..models.weeding import (
    CREWCategory,
    DisposalMethod,
    DispositionRecommendation,
    WeedingCandidate,
    WeedingReason,
    WeedingRule,
    WeedingStatus,
)

logger = get_logger(__name__)

# CREW method recommended maximum ages by Dewey category (in years)
CREW_AGE_THRESHOLDS: dict[str, int] = {
    "000": 10,   # General works
    "100": 10,   # Philosophy & psychology
    "200": 10,   # Religion
    "300": 5,    # Social sciences
    "400": 10,   # Language
    "500": 5,    # Science
    "600": 3,    # Technology (medical, computing)
    "700": 10,   # Arts & recreation
    "800": 100,  # Literature (keep classics)
    "900": 10,   # History & geography
    "fiction": 5,     # Fiction with no recent circ
    "travel": 3,      # Travel guides
    "law": 5,         # Legal references
    "medical": 3,     # Medical references
    "computing": 3,   # Computer/tech books
}

# Keywords for detecting outdated content areas
OUTDATED_CONTENT_KEYWORDS: dict[str, list[str]] = {
    "medical_outdated": [
        "medical", "medicine", "health", "disease", "diagnosis",
        "treatment", "surgery", "pharmaceutical", "drug guide",
        "nursing", "anatomy", "pathology",
    ],
    "tech_outdated": [
        "computer", "programming", "software", "internet", "web design",
        "networking", "database", "coding", "javascript", "python",
        "windows", "linux", "android", "ios", "cybersecurity",
    ],
    "travel_outdated": [
        "travel", "guide", "lonely planet", "fodor", "frommer",
        "tourism", "vacation", "road trip", "atlas",
    ],
    "legal_outdated": [
        "law", "legal", "statute", "regulation", "tax guide",
        "court", "litigation", "compliance",
    ],
}

# Condition enum to numeric score mapping
CONDITION_SCORES: dict[str, float] = {
    "new": 1.0,
    "good": 0.8,
    "fair": 0.5,
    "poor": 0.25,
    "damaged": 0.1,
    "withdrawn": 0.0,
}


def _classify_crew_category(item: CatalogItem) -> CREWCategory | None:
    subjects = (item.subjects or "").lower()
    title = (item.title or "").lower()

    # Check specific content areas first
    for keyword in OUTDATED_CONTENT_KEYWORDS.get("medical_outdated", []):
        if keyword in subjects or keyword in title:
            return CREWCategory.MEDICAL
    for keyword in OUTDATED_CONTENT_KEYWORDS.get("tech_outdated", []):
        if keyword in subjects or keyword in title:
            return CREWCategory.COMPUTING
    for keyword in OUTDATED_CONTENT_KEYWORDS.get("travel_outdated", []):
        if keyword in subjects or keyword in title:
            return CREWCategory.TRAVEL
    for keyword in OUTDATED_CONTENT_KEYWORDS.get("legal_outdated", []):
        if keyword in subjects or keyword in title:
            return CREWCategory.LAW

    # Try Dewey classification
    dewey = item.dewey_decimal or ""
    if dewey:
        dewey_class = dewey[:3] if len(dewey) >= 3 else dewey
        for prefix in ["000", "100", "200", "300", "400", "500", "600", "700", "800", "900"]:
            if dewey_class.startswith(prefix[0]):
                try:
                    return CREWCategory(prefix)
                except ValueError:
                    pass

    # Fiction detection
    if item.item_type and str(item.item_type) == "book":
        if "fiction" in subjects or (item.call_number and item.call_number.upper().startswith("F ")):
            return CREWCategory.FICTION

    return None


def _detect_outdated_flags(item: CatalogItem) -> list[str]:
    flags = []
    subjects = (item.subjects or "").lower()
    title = (item.title or "").lower()
    pub_year = item.publication_year
    current_year = date.today().year

    if not pub_year:
        return flags

    for flag_name, keywords in OUTDATED_CONTENT_KEYWORDS.items():
        threshold = CREW_AGE_THRESHOLDS.get(flag_name.replace("_outdated", ""), 5)
        age = current_year - pub_year
        if age > threshold:
            for keyword in keywords:
                if keyword in subjects or keyword in title:
                    flags.append(flag_name)
                    break
    return flags


def _compute_condition_score(condition: ItemCondition | str) -> float:
    cond_str = condition.value if hasattr(condition, "value") else str(condition)
    return CONDITION_SCORES.get(cond_str.lower(), 0.5)


def _compute_crew_score(
    age_years: int,
    total_checkouts: int,
    days_since_circ: int | None,
    condition_score: float,
    is_duplicate: bool,
    is_outdated: bool,
    is_superseded: bool,
    never_circulated: bool,
    section_fill_rate: float | None,
    crew_category: CREWCategory | None,
) -> float:
    score = 0.0

    # Age factor (up to 25 points)
    if crew_category:
        threshold = CREW_AGE_THRESHOLDS.get(crew_category.value, 10)
        if age_years > threshold:
            age_ratio = min(age_years / threshold, 3.0)
            score += min(25.0, age_ratio * 10)
        elif age_years > threshold * 0.7:
            score += 5.0

    # Circulation factor (up to 25 points)
    if never_circulated:
        score += 20.0
    elif days_since_circ is not None:
        years_no_circ = days_since_circ / 365.0
        if years_no_circ > 5:
            score += 25.0
        elif years_no_circ > 3:
            score += 15.0
        elif years_no_circ > 1:
            score += 8.0

    if total_checkouts == 0:
        score += 5.0
    elif total_checkouts < 3:
        score += 2.0

    # Condition factor (up to 20 points)
    score += (1.0 - condition_score) * 20.0

    # Duplicate factor (up to 10 points)
    if is_duplicate:
        score += 10.0

    # Outdated content factor (up to 10 points)
    if is_outdated:
        score += 10.0

    # Superseded edition factor (up to 5 points)
    if is_superseded:
        score += 5.0

    # Space pressure factor (up to 5 points)
    if section_fill_rate is not None and section_fill_rate > 0.85:
        score += min(5.0, (section_fill_rate - 0.85) * 33.3)

    return min(100.0, max(0.0, score))


def _recommend_disposition(
    condition_score: float,
    total_checkouts: int,
    is_duplicate: bool,
) -> tuple[DispositionRecommendation, str]:
    if condition_score >= 0.5:
        if total_checkouts > 5:
            return (
                DispositionRecommendation.SELL_POPULAR_TITLE,
                "Item is in acceptable condition and has good circulation history - consider book sale.",
            )
        if is_duplicate:
            return (
                DispositionRecommendation.TRANSFER_TO_BRANCH,
                "Duplicate copy in good condition - consider transferring to another branch.",
            )
        return (
            DispositionRecommendation.DONATE_GOOD_CONDITION,
            "Item in acceptable condition - suitable for donation to community organizations.",
        )
    elif condition_score >= 0.25:
        return (
            DispositionRecommendation.RECYCLE_POOR_CONDITION,
            "Item in poor condition - recycle to reduce waste.",
        )
    else:
        return (
            DispositionRecommendation.DISCARD,
            "Item is damaged or in very poor condition - discard.",
        )


async def run_weeding_analysis(
    db: AsyncSession,
    staff_user_id: int,
    location_filter: str | None = None,
    crew_category_filter: CREWCategory | None = None,
    min_crew_score: float = 50.0,
    include_reasons: list[WeedingReason] | None = None,
    max_results: int = 100,
) -> list[WeedingCandidate]:
    current_date = date.today()
    current_year = current_date.year
    candidates_created = []

    # Subquery: item_copy_ids with active checkouts
    active_checkout_subq = (
        select(Checkout.item_copy_id)
        .where(
            Checkout.item_copy_id.isnot(None),
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    ).subquery()

    # Build base query for item copies with their catalog info
    query = (
        select(ItemCopy)
        .join(CatalogItem, ItemCopy.catalog_item_id == CatalogItem.id)
        .options(selectinload(ItemCopy.catalog_item))
        .where(
            ItemCopy.condition != ItemCondition.WITHDRAWN,
            CatalogItem.status != ItemStatus.withdrawn,
            ItemCopy.id.notin_(select(active_checkout_subq.c.item_copy_id)),
        )
    )

    if location_filter:
        safe_loc = location_filter.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(ItemCopy.location.ilike(f"%{safe_loc}%"))

    result = await db.execute(query)
    item_copies = result.scalars().all()

    # Get existing candidate item_copy_ids to avoid duplicates
    existing_q = select(WeedingCandidate.item_copy_id).where(
        WeedingCandidate.status.in_([WeedingStatus.CANDIDATE, WeedingStatus.UNDER_REVIEW])
    )
    existing_result = await db.execute(existing_q)
    existing_ids = {row[0] for row in existing_result.all()}

    # Get last checkout dates for all items
    checkout_subq = (
        select(
            Checkout.item_copy_id,
            func.max(Checkout.checked_out_at).label("last_checkout"),
            func.count(Checkout.id).label("checkout_count"),
        )
        .where(Checkout.item_copy_id.isnot(None))
        .group_by(Checkout.item_copy_id)
    ).subquery()

    checkout_result = await db.execute(select(checkout_subq))
    checkout_map: dict[int, tuple] = {}
    for row in checkout_result.all():
        checkout_map[row[0]] = (row[1], row[2])

    # Compute section fill rates (items per location)
    section_counts_q = (
        select(
            ItemCopy.location,
            func.count(ItemCopy.id).label("item_count"),
        )
        .where(ItemCopy.condition != ItemCondition.WITHDRAWN)
        .group_by(ItemCopy.location)
    )
    section_result = await db.execute(section_counts_q)
    section_counts: dict[str, int] = {}
    for row in section_result.all():
        if row[0]:
            section_counts[row[0]] = row[1]

    # Estimate capacity per section (heuristic: 150 items per section)
    SECTION_CAPACITY = 150

    # Detect duplicates: catalog items with multiple copies
    dup_q = (
        select(
            ItemCopy.catalog_item_id,
            func.count(ItemCopy.id).label("copy_count"),
        )
        .where(ItemCopy.condition != ItemCondition.WITHDRAWN)
        .group_by(ItemCopy.catalog_item_id)
        .having(func.count(ItemCopy.id) > 1)
    )
    dup_result = await db.execute(dup_q)
    duplicate_map: dict[int, int] = {}
    for row in dup_result.all():
        duplicate_map[row[0]] = row[1]

    # Detect superseded editions: same title/author, different publication years
    superseded_q = (
        select(
            CatalogItem.id,
            CatalogItem.title,
            CatalogItem.author,
            CatalogItem.publication_year,
        )
        .where(
            CatalogItem.publication_year.isnot(None),
            CatalogItem.status != ItemStatus.withdrawn,
        )
        .order_by(CatalogItem.title, CatalogItem.author, CatalogItem.publication_year.desc())
    )
    superseded_result = await db.execute(superseded_q)
    all_items_for_superseded = superseded_result.all()

    # Build superseded map: older item_id -> newer item_id
    superseded_map: dict[int, int] = {}
    seen_titles: dict[str, tuple[int, int]] = {}  # (title+author) -> (newest_id, newest_year)
    for item_id, title, author, pub_year in all_items_for_superseded:
        key = f"{(title or '').lower().strip()}|{(author or '').lower().strip()}"
        if key in seen_titles:
            newest_id, newest_year = seen_titles[key]
            if pub_year and newest_year and pub_year < newest_year:
                superseded_map[item_id] = newest_id
        else:
            if pub_year:
                seen_titles[key] = (item_id, pub_year)

    # Analyze each item copy
    for copy in item_copies:
        if copy.id in existing_ids:
            continue

        catalog_item = copy.catalog_item
        if not catalog_item:
            continue

        # Compute age
        pub_year = catalog_item.publication_year
        acq_date = copy.acquisition_date
        age_years = 0
        if pub_year:
            age_years = current_year - pub_year
        elif acq_date:
            age_years = (current_date - acq_date).days // 365

        years_since_acquisition = 0
        if acq_date:
            years_since_acquisition = (current_date - acq_date).days // 365

        # Circulation data
        circ_data = checkout_map.get(copy.id)
        last_checkout_dt = circ_data[0] if circ_data else None
        total_checkouts = circ_data[1] if circ_data else 0

        last_checkout_date_val = None
        days_since_circ = None
        if last_checkout_dt:
            if isinstance(last_checkout_dt, datetime):
                last_checkout_date_val = last_checkout_dt.date()
            else:
                last_checkout_date_val = last_checkout_dt
            days_since_circ = (current_date - last_checkout_date_val).days

        never_circulated = total_checkouts == 0

        # Condition
        condition_score = _compute_condition_score(copy.condition)

        # CREW category
        crew_cat = _classify_crew_category(catalog_item)
        if crew_category_filter and crew_cat != crew_category_filter:
            continue

        # Outdated content
        outdated_flags = _detect_outdated_flags(catalog_item)
        is_outdated = len(outdated_flags) > 0

        # Duplicates
        dup_count = duplicate_map.get(catalog_item.id, 1)
        is_duplicate = dup_count > 2  # More than 2 copies = flag

        # Superseded
        is_superseded = catalog_item.id in superseded_map
        superseded_by_id = superseded_map.get(catalog_item.id)

        # Section fill rate
        location = copy.location or ""
        section_item_count = section_counts.get(location, 0)
        section_fill_rate = section_item_count / SECTION_CAPACITY if SECTION_CAPACITY > 0 else 0.0

        # Compute CREW score
        crew_score = _compute_crew_score(
            age_years=age_years,
            total_checkouts=total_checkouts,
            days_since_circ=days_since_circ,
            condition_score=condition_score,
            is_duplicate=is_duplicate,
            is_outdated=is_outdated,
            is_superseded=is_superseded,
            never_circulated=never_circulated,
            section_fill_rate=section_fill_rate,
            crew_category=crew_cat,
        )

        if crew_score < min_crew_score:
            continue

        # Determine primary reason
        reason = _determine_primary_reason(
            never_circulated=never_circulated,
            is_outdated=is_outdated,
            condition_score=condition_score,
            is_duplicate=is_duplicate,
            is_superseded=is_superseded,
            days_since_circ=days_since_circ,
            section_fill_rate=section_fill_rate,
        )

        if include_reasons and reason not in include_reasons:
            continue

        # Disposition recommendation
        disp_rec, disp_rationale = _recommend_disposition(
            condition_score=condition_score,
            total_checkouts=total_checkouts,
            is_duplicate=is_duplicate,
        )

        # Create candidate
        candidate = WeedingCandidate(
            item_copy_id=copy.id,
            status=WeedingStatus.CANDIDATE,
            reason=reason,
            reason_notes=_build_reason_notes(
                crew_score=crew_score,
                crew_cat=crew_cat,
                age_years=age_years,
                total_checkouts=total_checkouts,
                condition_score=condition_score,
                is_duplicate=is_duplicate,
                is_outdated=is_outdated,
                outdated_flags=outdated_flags,
                is_superseded=is_superseded,
                never_circulated=never_circulated,
            ),
            last_checkout_date=last_checkout_date_val,
            total_checkouts=total_checkouts,
            years_since_acquisition=years_since_acquisition,
            condition_score=condition_score,
            crew_category=crew_cat,
            crew_score=crew_score,
            is_outdated_content=is_outdated,
            outdated_flags=json.dumps(outdated_flags) if outdated_flags else None,
            is_duplicate=is_duplicate,
            duplicate_of_item_id=None,
            duplicate_count=dup_count,
            is_superseded=is_superseded,
            superseded_by_item_id=superseded_by_id,
            never_circulated=never_circulated,
            days_since_last_circulation=days_since_circ,
            section_fill_rate=section_fill_rate,
            disposition_recommendation=disp_rec,
            disposition_rationale=disp_rationale,
            auto_generated=True,
            created_by_id=staff_user_id,
        )
        db.add(candidate)
        candidates_created.append(candidate)

        if len(candidates_created) >= max_results:
            break

    await db.commit()

    # Refresh all to get IDs
    for c in candidates_created:
        await db.refresh(c)

    logger.info(
        "Weeding analysis complete: %d candidates generated (location=%s, min_score=%.1f)",
        len(candidates_created),
        location_filter,
        min_crew_score,
    )
    return candidates_created


def _determine_primary_reason(
    never_circulated: bool,
    is_outdated: bool,
    condition_score: float,
    is_duplicate: bool,
    is_superseded: bool,
    days_since_circ: int | None,
    section_fill_rate: float | None,
) -> WeedingReason:
    if condition_score <= 0.1:
        return WeedingReason.DAMAGED_BEYOND_REPAIR
    if condition_score <= 0.25:
        return WeedingReason.POOR_CONDITION
    if never_circulated:
        return WeedingReason.NEVER_CIRCULATED
    if is_outdated:
        return WeedingReason.OUTDATED
    if is_superseded:
        return WeedingReason.SUPERSEDED
    if is_duplicate:
        return WeedingReason.DUPLICATE
    if days_since_circ is not None and days_since_circ > 365 * 3:
        return WeedingReason.LOW_CIRCULATION
    if section_fill_rate is not None and section_fill_rate > 0.9:
        return WeedingReason.SPACE_PRESSURE
    return WeedingReason.LOW_CIRCULATION


def _build_reason_notes(
    crew_score: float,
    crew_cat: CREWCategory | None,
    age_years: int,
    total_checkouts: int,
    condition_score: float,
    is_duplicate: bool,
    is_outdated: bool,
    outdated_flags: list[str],
    is_superseded: bool,
    never_circulated: bool,
) -> str:
    parts = [f"CREW Score: {crew_score:.0f}/100"]
    if crew_cat:
        parts.append(f"Category: {crew_cat.value}")
    parts.append(f"Age: {age_years} years")
    parts.append(f"Total checkouts: {total_checkouts}")
    parts.append(f"Condition: {condition_score:.0%}")
    if never_circulated:
        parts.append("Never circulated since acquisition")
    if is_outdated:
        flag_labels = [f.replace("_", " ").title() for f in outdated_flags]
        parts.append(f"Outdated content: {', '.join(flag_labels)}")
    if is_superseded:
        parts.append("Newer edition available")
    if is_duplicate:
        parts.append("Excess duplicate copies in collection")
    return " | ".join(parts)


async def get_section_pressure(
    db: AsyncSession,
    location_filter: str | None = None,
) -> list[dict]:
    SECTION_CAPACITY = 150

    query = (
        select(
            ItemCopy.location,
            func.count(ItemCopy.id).label("total_items"),
            func.avg(
                case(
                    (CatalogItem.publication_year.isnot(None),
                     date.today().year - CatalogItem.publication_year),
                    else_=0,
                )
            ).label("avg_age"),
        )
        .join(CatalogItem, ItemCopy.catalog_item_id == CatalogItem.id)
        .where(
            ItemCopy.condition != ItemCondition.WITHDRAWN,
            ItemCopy.location.isnot(None),
        )
        .group_by(ItemCopy.location)
        .order_by(func.count(ItemCopy.id).desc())
    )

    if location_filter:
        safe_loc = location_filter.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(ItemCopy.location.ilike(f"%{safe_loc}%"))

    result = await db.execute(query)
    rows = result.all()

    sections = []
    for row in rows:
        location = row[0]
        total_items = row[1]
        avg_age = float(row[2] or 0)
        fill_rate = total_items / SECTION_CAPACITY

        # Count low-circulation items in this section
        low_circ_q = (
            select(func.count(ItemCopy.id))
            .where(
                ItemCopy.location == location,
                ItemCopy.condition != ItemCondition.WITHDRAWN,
            )
            .join(CatalogItem, ItemCopy.catalog_item_id == CatalogItem.id)
            .where(CatalogItem.total_checkouts <= 1)
        )
        low_circ_result = await db.execute(low_circ_q)
        low_circ_count = low_circ_result.scalar() or 0

        # Count existing weeding candidates
        weed_q = (
            select(func.count(WeedingCandidate.id))
            .join(ItemCopy, WeedingCandidate.item_copy_id == ItemCopy.id)
            .where(
                ItemCopy.location == location,
                WeedingCandidate.status.in_([WeedingStatus.CANDIDATE, WeedingStatus.UNDER_REVIEW]),
            )
        )
        weed_result = await db.execute(weed_q)
        weed_count = weed_result.scalar() or 0

        # Avg checkouts for the section
        avg_co_q = (
            select(func.avg(CatalogItem.total_checkouts))
            .join(ItemCopy, ItemCopy.catalog_item_id == CatalogItem.id)
            .where(
                ItemCopy.location == location,
                ItemCopy.condition != ItemCondition.WITHDRAWN,
            )
        )
        avg_co_result = await db.execute(avg_co_q)
        avg_checkouts = float(avg_co_result.scalar() or 0)

        sections.append({
            "location": location,
            "total_items": total_items,
            "capacity_estimate": SECTION_CAPACITY,
            "fill_rate": round(fill_rate, 2),
            "weeding_candidates_count": weed_count,
            "avg_item_age_years": round(avg_age, 1),
            "avg_checkouts": round(avg_checkouts, 1),
            "low_circ_items": low_circ_count,
        })

    return sections


async def detect_duplicates(db: AsyncSession) -> list[dict]:
    query = (
        select(
            CatalogItem.id,
            CatalogItem.title,
            CatalogItem.author,
            CatalogItem.isbn,
            func.count(ItemCopy.id).label("copy_count"),
        )
        .join(ItemCopy, ItemCopy.catalog_item_id == CatalogItem.id)
        .where(ItemCopy.condition != ItemCondition.WITHDRAWN)
        .group_by(CatalogItem.id, CatalogItem.title, CatalogItem.author, CatalogItem.isbn)
        .having(func.count(ItemCopy.id) > 2)
        .order_by(func.count(ItemCopy.id).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    groups = []
    total_excess = 0

    for row in rows:
        catalog_id, title, author, isbn, copy_count = row
        recommended = 2  # Default recommended copies
        excess = max(0, copy_count - recommended)
        total_excess += excess

        # Get individual copies
        copies_q = (
            select(ItemCopy)
            .where(
                ItemCopy.catalog_item_id == catalog_id,
                ItemCopy.condition != ItemCondition.WITHDRAWN,
            )
            .order_by(ItemCopy.condition, ItemCopy.acquisition_date)
        )
        copies_result = await db.execute(copies_q)
        copies = copies_result.scalars().all()

        copy_info = []
        for c in copies:
            copy_info.append({
                "id": c.id,
                "barcode": c.barcode,
                "condition": c.condition.value if hasattr(c.condition, "value") else str(c.condition),
                "location": c.location,
                "acquisition_date": str(c.acquisition_date) if c.acquisition_date else None,
            })

        groups.append({
            "catalog_item_id": catalog_id,
            "title": title,
            "author": author,
            "isbn": isbn,
            "total_copies": copy_count,
            "recommended_copies": recommended,
            "excess_copies": excess,
            "copies": copy_info,
        })

    return groups


async def detect_superseded_editions(db: AsyncSession) -> list[dict]:
    # Get all items with edition or publication year info
    query = (
        select(CatalogItem)
        .where(
            CatalogItem.publication_year.isnot(None),
            CatalogItem.status != ItemStatus.withdrawn,
        )
        .order_by(CatalogItem.title, CatalogItem.author, CatalogItem.publication_year.desc())
    )

    result = await db.execute(query)
    items = result.scalars().all()

    # Group by normalized title + author
    title_groups: dict[str, list] = {}
    for item in items:
        key = f"{(item.title or '').lower().strip()}|{(item.author or '').lower().strip()}"
        if key not in title_groups:
            title_groups[key] = []
        title_groups[key].append(item)

    superseded = []
    for key, group in title_groups.items():
        if len(group) < 2:
            continue
        # Sort by publication year descending
        group.sort(key=lambda x: x.publication_year or 0, reverse=True)
        newest = group[0]
        for older in group[1:]:
            if older.publication_year and newest.publication_year and older.publication_year < newest.publication_year:
                superseded.append({
                    "older_item_id": older.id,
                    "older_title": older.title,
                    "older_edition": older.edition,
                    "older_publication_year": older.publication_year,
                    "newer_item_id": newest.id,
                    "newer_title": newest.title,
                    "newer_edition": newest.edition,
                    "newer_publication_year": newest.publication_year,
                })

    return superseded


async def get_weeding_summary(db: AsyncSession) -> dict:
    # Total candidates by status
    status_q = (
        select(
            WeedingCandidate.status,
            func.count(WeedingCandidate.id),
        )
        .group_by(WeedingCandidate.status)
    )
    status_result = await db.execute(status_q)
    by_status = {(row[0].value if hasattr(row[0], "value") else row[0]): row[1] for row in status_result.all()}

    # By reason
    reason_q = (
        select(
            WeedingCandidate.reason,
            func.count(WeedingCandidate.id),
        )
        .where(WeedingCandidate.status.in_([WeedingStatus.CANDIDATE, WeedingStatus.UNDER_REVIEW]))
        .group_by(WeedingCandidate.reason)
    )
    reason_result = await db.execute(reason_q)
    by_reason = {(row[0].value if hasattr(row[0], "value") else row[0]): row[1] for row in reason_result.all()}

    total_candidates = sum(
        v for k, v in by_status.items()
        if k in [WeedingStatus.CANDIDATE.value, WeedingStatus.UNDER_REVIEW.value]
    )

    # Avg CREW score
    avg_score_q = (
        select(func.avg(WeedingCandidate.crew_score))
        .where(WeedingCandidate.status.in_([WeedingStatus.CANDIDATE, WeedingStatus.UNDER_REVIEW]))
    )
    avg_result = await db.execute(avg_score_q)
    avg_crew = avg_result.scalar()

    # Never circulated count
    never_circ_q = (
        select(func.count(WeedingCandidate.id))
        .where(
            WeedingCandidate.never_circulated == True,
            WeedingCandidate.status.in_([WeedingStatus.CANDIDATE, WeedingStatus.UNDER_REVIEW]),
        )
    )
    never_circ_result = await db.execute(never_circ_q)
    never_circ_count = never_circ_result.scalar() or 0

    # Outdated count
    outdated_q = (
        select(func.count(WeedingCandidate.id))
        .where(
            WeedingCandidate.is_outdated_content == True,
            WeedingCandidate.status.in_([WeedingStatus.CANDIDATE, WeedingStatus.UNDER_REVIEW]),
        )
    )
    outdated_result = await db.execute(outdated_q)
    outdated_count = outdated_result.scalar() or 0

    # Duplicates excess
    dup_q = (
        select(func.sum(WeedingCandidate.duplicate_count))
        .where(
            WeedingCandidate.is_duplicate == True,
            WeedingCandidate.status.in_([WeedingStatus.CANDIDATE, WeedingStatus.UNDER_REVIEW]),
        )
    )
    dup_result = await db.execute(dup_q)
    dup_total = dup_result.scalar() or 0

    # Sections over capacity
    section_data = await get_section_pressure(db)
    over_capacity = sum(1 for s in section_data if s["fill_rate"] > 1.0)

    return {
        "total_candidates": total_candidates,
        "by_status": by_status,
        "by_reason": by_reason,
        "sections_over_capacity": over_capacity,
        "total_duplicates_excess": int(dup_total),
        "outdated_items": outdated_count,
        "never_circulated_items": never_circ_count,
        "avg_crew_score": round(float(avg_crew), 1) if avg_crew else None,
    }
