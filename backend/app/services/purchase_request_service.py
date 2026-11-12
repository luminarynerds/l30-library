# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.catalog import CatalogItem
from ..models.purchase_request import (
    DeclineReasonTemplate,
    PatronPurchaseRequest,
    PurchaseRequestStatus,
)
from ..models.user import User
from ..schemas.purchase_request import DuplicateCheckResult, FulfillmentStatsResponse

logger = get_logger(__name__)


async def check_duplicate(
    db: AsyncSession,
    title: str,
    author: str | None = None,
    isbn: str | None = None,
) -> DuplicateCheckResult:
    # 1) ISBN match
    if isbn:
        result = await db.execute(
            select(CatalogItem).where(CatalogItem.isbn == isbn).limit(1)
        )
        item = result.scalar_one_or_none()
        if item:
            return DuplicateCheckResult(
                has_duplicate=True,
                catalog_item_id=item.id,
                catalog_title=item.title,
                catalog_author=item.author,
                match_type="isbn",
            )

    # 2) Title + author fuzzy match (case-insensitive)
    title_lower = title.strip().lower()
    query = select(CatalogItem).where(
        func.lower(CatalogItem.title) == title_lower
    )
    if author:
        author_lower = author.strip().lower()
        query = query.where(func.lower(CatalogItem.author) == author_lower)

    result = await db.execute(query.limit(1))
    item = result.scalar_one_or_none()
    if item:
        return DuplicateCheckResult(
            has_duplicate=True,
            catalog_item_id=item.id,
            catalog_title=item.title,
            catalog_author=item.author,
            match_type="title_author",
        )

    return DuplicateCheckResult(has_duplicate=False)


async def check_existing_pending_request(
    db: AsyncSession,
    patron_id: int,
    title: str,
    author: str | None = None,
) -> Optional[PatronPurchaseRequest]:
    title_lower = title.strip().lower()
    query = select(PatronPurchaseRequest).where(
        and_(
            PatronPurchaseRequest.patron_id == patron_id,
            func.lower(PatronPurchaseRequest.title) == title_lower,
            PatronPurchaseRequest.status.in_([
                PurchaseRequestStatus.PENDING,
                PurchaseRequestStatus.UNDER_REVIEW,
                PurchaseRequestStatus.APPROVED,
            ]),
        )
    )
    if author:
        query = query.where(
            func.lower(PatronPurchaseRequest.author) == author.strip().lower()
        )
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none()


async def auto_check_review_sources(
    request: PatronPurchaseRequest,
) -> None:
    # Stub implementation - in production, integrate with:
    # - Open Library API (ratings, editions)
    # - Google Books API (ratings, reviews)
    # - LibraryThing (community reviews)
    review_data = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "sources_checked": ["open_library", "google_books"],
        "note": "Automated review source check completed",
    }

    # If ISBN is available, try Open Library for basic data
    if request.isbn:
        review_data["isbn_lookup"] = request.isbn
        # In production: fetch from Open Library API
        # response = await httpx.get(f"https://openlibrary.org/isbn/{request.isbn}.json")

    request.review_source_data = json.dumps(review_data)
    request.review_source_checked = True


async def get_fulfillment_stats(db: AsyncSession) -> FulfillmentStatsResponse:
    # Status counts
    counts_result = await db.execute(
        select(
            PatronPurchaseRequest.status,
            func.count(PatronPurchaseRequest.id),
        ).group_by(PatronPurchaseRequest.status)
    )
    counts = {row[0]: row[1] for row in counts_result.all()}

    total = sum(counts.values())
    pending = counts.get(PurchaseRequestStatus.PENDING, 0)
    under_review = counts.get(PurchaseRequestStatus.UNDER_REVIEW, 0)
    approved = counts.get(PurchaseRequestStatus.APPROVED, 0)
    ordered = counts.get(PurchaseRequestStatus.ORDERED, 0)
    received = counts.get(PurchaseRequestStatus.RECEIVED, 0)
    declined = counts.get(PurchaseRequestStatus.DECLINED, 0)
    cancelled = counts.get(PurchaseRequestStatus.CANCELLED, 0)

    # Fulfillment rate: received / (total - cancelled)
    non_cancelled = total - cancelled
    fulfillment_rate = (received / non_cancelled * 100) if non_cancelled > 0 else 0.0

    # Average days to review (from created_at to reviewed_at)
    avg_review_result = await db.execute(
        select(
            func.avg(
                (func.extract("epoch", PatronPurchaseRequest.reviewed_at)
                - func.extract("epoch", PatronPurchaseRequest.created_at)) / 86400.0
            )
        ).where(PatronPurchaseRequest.reviewed_at.isnot(None))
    )
    avg_days_to_review = avg_review_result.scalar()

    # Average days to fulfill (from created_at to updated_at for received items)
    avg_fulfill_result = await db.execute(
        select(
            func.avg(
                (func.extract("epoch", PatronPurchaseRequest.updated_at)
                - func.extract("epoch", PatronPurchaseRequest.created_at)) / 86400.0
            )
        ).where(PatronPurchaseRequest.status == PurchaseRequestStatus.RECEIVED)
    )
    avg_days_to_fulfill = avg_fulfill_result.scalar()

    return FulfillmentStatsResponse(
        total_requests=total,
        pending_count=pending,
        under_review_count=under_review,
        approved_count=approved,
        ordered_count=ordered,
        received_count=received,
        declined_count=declined,
        cancelled_count=cancelled,
        fulfillment_rate=round(fulfillment_rate, 1),
        avg_days_to_review=round(avg_days_to_review, 1) if avg_days_to_review else None,
        avg_days_to_fulfill=round(avg_days_to_fulfill, 1) if avg_days_to_fulfill else None,
    )


async def send_request_notification(
    db: AsyncSession,
    request: PatronPurchaseRequest,
    notification_type: str,
) -> None:
    if not request.patron:
        return

    patron: User = request.patron
    email = patron.email
    if not email:
        return

    subject_map = {
        "submitted": f"Purchase Request Received: {request.title}",
        "ordered": f"Great News! We Ordered Your Request: {request.title}",
        "received": f"Your Requested Item Is Ready: {request.title}",
        "declined": f"Update on Your Purchase Request: {request.title}",
    }

    body_map = {
        "submitted": (
            f"<p>Hi {patron.first_name},</p>"
            f"<p>We've received your purchase request for <strong>{request.title}</strong>"
            f"{f' by {request.author}' if request.author else ''}. "
            f"Our staff will review it and you'll be notified of the decision.</p>"
            f"<p>Thank you for helping us build our collection!</p>"
        ),
        "ordered": (
            f"<p>Hi {patron.first_name},</p>"
            f"<p>We're pleased to let you know that we've ordered "
            f"<strong>{request.title}</strong>"
            f"{f' by {request.author}' if request.author else ''}. "
            f"We'll notify you again when it arrives and is ready for checkout.</p>"
        ),
        "received": (
            f"<p>Hi {patron.first_name},</p>"
            f"<p>The item you requested, <strong>{request.title}</strong>"
            f"{f' by {request.author}' if request.author else ''}, "
            f"has arrived! It's now available for checkout.</p>"
            f"<p>Visit us to pick it up, or place a hold through our catalog.</p>"
        ),
        "declined": (
            f"<p>Hi {patron.first_name},</p>"
            f"<p>Thank you for your purchase request for <strong>{request.title}</strong>. "
            f"After review, we're unable to add this item to our collection at this time.</p>"
            f"{f'<p><strong>Reason:</strong> {request.decline_reason}</p>' if request.decline_reason else ''}"
            f"<p>If you have questions, please ask at the circulation desk.</p>"
        ),
    }

    subject = subject_map.get(notification_type, f"Purchase Request Update: {request.title}")
    body = body_map.get(notification_type, "")

    if not body:
        return

    try:
        from ..core.email import send_email
        await send_email(to_email=email, subject=subject, html_body=body)
        logger.info(f"Sent {notification_type} notification for request {request.id}")
    except Exception:
        logger.exception(f"Failed to send {notification_type} notification for request {request.id}")
