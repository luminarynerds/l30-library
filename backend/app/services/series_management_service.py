# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.series_management import (
    SeriesReadingOrder, PatronReadingHistory, SeriesCompletion,
    SeriesWaitlist, SeriesRecommendation, SeriesNotificationRule,
    SeriesPopularity, NotificationTrigger, WaitlistStatus,
    RecommendationReason
)
from ..models.bibframe import BibframeWork
from ..models.circulation import Checkout, CheckoutStatus
from ..models.user import User
from app.core.datetime_utils import utc_now


class SeriesManagementService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Series Reading Order ====================

    async def get_series_reading_order(
        self, series_title: str, limit: Optional[int] = None
    ) -> List[SeriesReadingOrder]:
        stmt = select(SeriesReadingOrder).where(
            SeriesReadingOrder.series_title == series_title
        ).order_by(SeriesReadingOrder.sequence_number)

        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_next_book_in_series(
        self, series_title: str, current_sequence: float
    ) -> Optional[SeriesReadingOrder]:
        result = await self.db.execute(
            select(SeriesReadingOrder).where(
                SeriesReadingOrder.series_title == series_title,
                SeriesReadingOrder.sequence_number > current_sequence
            ).order_by(
                SeriesReadingOrder.sequence_number
            )
        )
        return result.scalars().first()

    async def get_series_starting_points(self, series_title: str) -> List[SeriesReadingOrder]:
        result = await self.db.execute(
            select(SeriesReadingOrder).where(
                SeriesReadingOrder.series_title == series_title,
                SeriesReadingOrder.is_recommended_starting_point == True
            ).order_by(SeriesReadingOrder.sequence_number)
        )
        return result.scalars().all()

    async def add_book_to_series(
        self,
        series_title: str,
        bibframe_work_id: int,
        sequence_number: float,
        book_title: str,
        series_type: str = "main_series",
        created_by_id: Optional[int] = None,
        is_recommended_start: bool = False
    ) -> SeriesReadingOrder:
        entry = SeriesReadingOrder(
            series_title=series_title,
            bibframe_work_id=bibframe_work_id,
            sequence_number=sequence_number,
            book_title=book_title,
            series_type=series_type,
            created_by_id=created_by_id,
            is_recommended_starting_point=is_recommended_start
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    # ==================== Patron Reading History ====================

    async def log_book_read(
        self,
        user_id: int,
        bibframe_work_id: int,
        is_completed: bool = True,
        rating: Optional[float] = None,
        review: Optional[str] = None,
        format_read: Optional[str] = None
    ) -> PatronReadingHistory:
        result = await self.db.execute(
            select(PatronReadingHistory).where(
                PatronReadingHistory.user_id == user_id,
                PatronReadingHistory.bibframe_work_id == bibframe_work_id
            )
        )
        history = result.scalars().first()

        if not history:
            history = PatronReadingHistory(
                user_id=user_id,
                bibframe_work_id=bibframe_work_id,
            )
            self.db.add(history)

        history.is_completed = is_completed
        if is_completed:
            history.completed_date = utc_now()
        if rating is not None:
            history.rating = max(0.0, min(5.0, rating))
        if review:
            history.review = review
        if format_read:
            history.format_read = format_read

        await self.db.flush()
        return history

    async def get_patron_reading_history(self, user_id: int) -> List[PatronReadingHistory]:
        result = await self.db.execute(
            select(PatronReadingHistory).where(
                PatronReadingHistory.user_id == user_id
            ).order_by(desc(PatronReadingHistory.completed_date))
        )
        return result.scalars().all()

    async def get_patron_books_in_series(
        self, user_id: int, series_title: str
    ) -> List[PatronReadingHistory]:
        result = await self.db.execute(
            select(PatronReadingHistory).join(
                SeriesReadingOrder,
                PatronReadingHistory.bibframe_work_id == SeriesReadingOrder.bibframe_work_id,
            ).where(
                and_(
                    PatronReadingHistory.user_id == user_id,
                    SeriesReadingOrder.series_title == series_title,
                )
            )
        )
        return result.scalars().all()

    async def mark_book_as_favorite(self, user_id: int, bibframe_work_id: int) -> PatronReadingHistory:
        history = await self.log_book_read(user_id, bibframe_work_id)
        history.favorite = True
        await self.db.flush()
        return history

    # ==================== Series Completion Tracking ====================

    async def track_series_progress(
        self, user_id: int, series_title: str
    ) -> SeriesCompletion:
        result = await self.db.execute(
            select(SeriesCompletion).where(
                SeriesCompletion.user_id == user_id,
                SeriesCompletion.series_title == series_title
            )
        )
        completion = result.scalars().first()

        if not completion:
            completion = SeriesCompletion(
                user_id=user_id,
                series_title=series_title
            )
            self.db.add(completion)

        # Get all books in series
        series_books = await self.get_series_reading_order(series_title)
        completion.total_books_in_series = len(series_books)

        # Get books patron has read
        read_books = await self.get_patron_books_in_series(user_id, series_title)
        read_sequence_numbers = [
            h.work.series_number for h in read_books if h.work.series_number
        ]

        completion.books_read = len([b for b in series_books if b.sequence_number in read_sequence_numbers])

        # Get next unread book
        for book in series_books:
            if book.sequence_number not in read_sequence_numbers:
                completion.next_book_number = book.sequence_number
                completion.next_book_title = book.book_title
                break

        # Get last read book
        if read_books:
            last_read = read_books[0]
            work = await self.db.get(BibframeWork, last_read.bibframe_work_id)
            if work:
                completion.last_book_read_number = work.series_number
                completion.last_book_read_title = work.title
                completion.last_read_date = last_read.completed_date or utc_now()

        # Check if series completed
        completion.is_completed = (
            completion.next_book_number is None and
            completion.books_read > 0
        )
        if completion.is_completed and not completion.completed_date:
            completion.completed_date = utc_now()

        await self.db.flush()
        return completion

    async def get_patron_series_progress(self, user_id: int) -> List[SeriesCompletion]:
        result = await self.db.execute(
            select(SeriesCompletion).where(
                SeriesCompletion.user_id == user_id,
                SeriesCompletion.is_following == True
            ).order_by(desc(SeriesCompletion.preferred))
        )
        return result.scalars().all()

    async def get_series_completion_percentage(
        self, user_id: int, series_title: str
    ) -> float:
        completion = await self.track_series_progress(user_id, series_title)
        if not completion.total_books_in_series or completion.total_books_in_series == 0:
            return 0.0
        return (completion.books_read / completion.total_books_in_series) * 100

    # ==================== Series Waitlist ====================

    async def add_to_series_waitlist(
        self,
        user_id: int,
        series_title: str,
        next_book_sequence: Optional[float] = None,
        next_book_title: Optional[str] = None,
        notification_method: str = "email"
    ) -> SeriesWaitlist:
        # Check if already on waitlist
        result = await self.db.execute(
            select(SeriesWaitlist).where(
                SeriesWaitlist.user_id == user_id,
                SeriesWaitlist.series_title == series_title,
                SeriesWaitlist.status == WaitlistStatus.active
            )
        )
        existing = result.scalars().first()

        if existing:
            return existing

        waitlist_entry = SeriesWaitlist(
            user_id=user_id,
            series_title=series_title,
            next_book_sequence=next_book_sequence,
            next_book_title=next_book_title,
            notification_method=notification_method,
            status=WaitlistStatus.active
        )
        self.db.add(waitlist_entry)
        await self.db.flush()
        return waitlist_entry

    async def get_active_waitlist_entries(self, user_id: int) -> List[SeriesWaitlist]:
        result = await self.db.execute(
            select(SeriesWaitlist).where(
                SeriesWaitlist.user_id == user_id,
                SeriesWaitlist.status == WaitlistStatus.active
            )
        )
        return result.scalars().all()

    async def fulfill_waitlist_entry(
        self,
        waitlist_id: int,
        bibframe_work_id: int
    ) -> SeriesWaitlist:
        entry = await self.db.get(SeriesWaitlist, waitlist_id)
        if entry:
            entry.status = WaitlistStatus.fulfilled
            entry.fulfilled_date = utc_now()
            entry.fulfilled_by_bibframe_work_id = bibframe_work_id
            entry.notified_at = utc_now()
            await self.db.flush()
        return entry

    async def get_series_waitlist_patrons(self, series_title: str) -> List[SeriesWaitlist]:
        result = await self.db.execute(
            select(SeriesWaitlist).where(
                SeriesWaitlist.series_title == series_title,
                SeriesWaitlist.status == WaitlistStatus.active
            )
        )
        return result.scalars().all()

    # ==================== Series Recommendations ====================

    async def create_recommendation(
        self,
        user_id: int,
        series_title: str,
        reason: RecommendationReason,
        confidence_score: float = 0.5,
        first_book_work_id: Optional[int] = None
    ) -> SeriesRecommendation:
        rec = SeriesRecommendation(
            user_id=user_id,
            series_title=series_title,
            reason=reason,
            confidence_score=max(0.0, min(1.0, confidence_score)),
            first_book_bibframe_work_id=first_book_work_id
        )
        self.db.add(rec)
        await self.db.flush()
        return rec

    async def get_patron_recommendations(self, user_id: int, limit: int = 10) -> List[SeriesRecommendation]:
        result = await self.db.execute(
            select(SeriesRecommendation).where(
                SeriesRecommendation.user_id == user_id
            ).order_by(
                desc(SeriesRecommendation.confidence_score)
            ).limit(limit)
        )
        return result.scalars().all()

    async def generate_recommendations_for_patron(self, user_id: int) -> List[SeriesRecommendation]:
        recommendations = []

        # Get patron's reading history
        history = await self.get_patron_reading_history(user_id)
        if not history:
            return recommendations

        # Get genres and authors from read books (with eager loading to avoid N+1)
        work_ids = [h.bibframe_work_id for h in history if h.bibframe_work_id]
        if work_ids:
            result = await self.db.execute(
                select(BibframeWork).where(BibframeWork.id.in_(work_ids))
            )
            read_works = result.scalars().all()
        else:
            read_works = []

        # Get completed series
        result = await self.db.execute(
            select(SeriesCompletion).where(
                SeriesCompletion.user_id == user_id,
                SeriesCompletion.is_completed == True
            )
        )
        completed_series = result.scalars().all()

        completed_series_titles = {s.series_title for s in completed_series}

        # Recommend related series not yet started
        for work in read_works[:10]:  # Check last 10 read books
            if work.series_title and work.series_title not in completed_series_titles:
                # Check if already recommended
                result = await self.db.execute(
                    select(SeriesRecommendation).where(
                        SeriesRecommendation.user_id == user_id,
                        SeriesRecommendation.series_title == work.series_title
                    )
                )
                existing = result.scalars().first()

                if not existing:
                    rec = await self.create_recommendation(
                        user_id=user_id,
                        series_title=work.series_title,
                        reason=RecommendationReason.reading_history,
                        confidence_score=0.7,
                        first_book_work_id=work.id
                    )
                    recommendations.append(rec)

        return recommendations

    async def track_recommendation_engagement(
        self,
        recommendation_id: int,
        viewed: bool = False,
        clicked: bool = False,
        added_to_wishlist: bool = False,
        started_series: bool = False
    ) -> SeriesRecommendation:
        rec = await self.db.get(SeriesRecommendation, recommendation_id)
        if rec:
            if viewed:
                rec.viewed = True
                rec.viewed_at = utc_now()
            if clicked:
                rec.clicked = True
                rec.clicked_at = utc_now()
            if added_to_wishlist:
                rec.added_to_wishlist = True
            if started_series:
                rec.started_series = True
            await self.db.flush()
        return rec

    # ==================== Series Notifications ====================

    async def create_notification_rule(
        self,
        user_id: int,
        series_title: str,
        trigger_type: NotificationTrigger,
        notification_method: str = "email",
        frequency: str = "immediate"
    ) -> SeriesNotificationRule:
        # Check if rule already exists
        result = await self.db.execute(
            select(SeriesNotificationRule).where(
                SeriesNotificationRule.user_id == user_id,
                SeriesNotificationRule.series_title == series_title,
                SeriesNotificationRule.trigger_type == trigger_type
            )
        )
        existing = result.scalars().first()

        if existing:
            existing.is_active = True
            await self.db.flush()
            return existing

        rule = SeriesNotificationRule(
            user_id=user_id,
            series_title=series_title,
            trigger_type=trigger_type,
            notification_method=notification_method,
            frequency=frequency,
            is_active=True
        )
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def get_active_notification_rules(self, user_id: int) -> List[SeriesNotificationRule]:
        result = await self.db.execute(
            select(SeriesNotificationRule).where(
                SeriesNotificationRule.user_id == user_id,
                SeriesNotificationRule.is_active == True
            )
        )
        return result.scalars().all()

    async def get_notification_rules_for_trigger(
        self, trigger_type: NotificationTrigger
    ) -> List[SeriesNotificationRule]:
        result = await self.db.execute(
            select(SeriesNotificationRule).where(
                SeriesNotificationRule.trigger_type == trigger_type,
                SeriesNotificationRule.is_active == True
            )
        )
        return result.scalars().all()

    async def disable_notification_rule(self, rule_id: int) -> SeriesNotificationRule:
        rule = await self.db.get(SeriesNotificationRule, rule_id)
        if rule:
            rule.is_active = False
            await self.db.flush()
        return rule

    # ==================== Series Popularity ====================

    async def update_series_popularity(self, series_title: str) -> SeriesPopularity:
        result = await self.db.execute(
            select(SeriesPopularity).where(
                SeriesPopularity.series_title == series_title
            )
        )
        popularity = result.scalars().first()

        if not popularity:
            popularity = SeriesPopularity(series_title=series_title)
            self.db.add(popularity)

        # Count followers
        popularity.patron_followers = (await self.db.execute(
            select(func.count()).select_from(SeriesCompletion).where(
                SeriesCompletion.series_title == series_title,
                SeriesCompletion.is_following == True
            )
        )).scalar()

        # Count completions
        popularity.patron_completion_count = (await self.db.execute(
            select(func.count()).select_from(SeriesCompletion).where(
                SeriesCompletion.series_title == series_title,
                SeriesCompletion.is_completed == True
            )
        )).scalar()

        # Get unique patrons who have read series
        popularity.unique_patrons_read = (await self.db.execute(
            select(
                func.count(func.distinct(PatronReadingHistory.user_id))
            ).select_from(PatronReadingHistory).join(
                SeriesReadingOrder,
                SeriesReadingOrder.bibframe_work_id == PatronReadingHistory.bibframe_work_id
            ).where(
                SeriesReadingOrder.series_title == series_title
            )
        )).scalar()

        # Calculate average rating
        avg_rating = (await self.db.execute(
            select(func.avg(PatronReadingHistory.rating)).select_from(
                PatronReadingHistory
            ).join(
                SeriesReadingOrder,
                SeriesReadingOrder.bibframe_work_id == PatronReadingHistory.bibframe_work_id
            ).where(
                SeriesReadingOrder.series_title == series_title,
                PatronReadingHistory.rating.isnot(None)
            )
        )).scalar()
        popularity.average_rating = avg_rating

        # Count total checkouts
        popularity.total_checkouts = (await self.db.execute(
            select(func.count(Checkout.id)).select_from(BibframeWork).join(
                SeriesReadingOrder,
                SeriesReadingOrder.bibframe_work_id == BibframeWork.id
            ).join(
                Checkout,
                Checkout.item_id == BibframeWork.id
            ).where(
                SeriesReadingOrder.series_title == series_title
            )
        )).scalar() or 0

        # Determine if trending
        recent_activity = (await self.db.execute(
            select(func.count(SeriesCompletion.id)).where(
                SeriesCompletion.series_title == series_title,
                SeriesCompletion.started_date >= utc_now() - timedelta(days=30)
            )
        )).scalar()

        popularity.is_trending = recent_activity > 10
        popularity.trend_score = float(recent_activity)

        popularity.last_updated = utc_now()
        await self.db.flush()
        return popularity

    async def get_trending_series(self, limit: int = 10) -> List[SeriesPopularity]:
        result = await self.db.execute(
            select(SeriesPopularity).where(
                SeriesPopularity.is_trending == True
            ).order_by(desc(SeriesPopularity.trend_score)).limit(limit)
        )
        return result.scalars().all()

    async def get_popular_series(self, limit: int = 10) -> List[SeriesPopularity]:
        result = await self.db.execute(
            select(SeriesPopularity).order_by(
                desc(SeriesPopularity.patron_followers)
            ).limit(limit)
        )
        return result.scalars().all()

    # ==================== Utility Methods ====================

    async def get_series_suggestions(
        self, user_id: int, limit: int = 5
    ) -> List[Dict]:
        suggestions = []

        # Get patron's series completion progress
        result = await self.db.execute(
            select(SeriesCompletion).where(
                SeriesCompletion.user_id == user_id
            )
        )
        completions = result.scalars().all()

        for completion in completions:
            if completion.next_book_number and completion.books_available > completion.books_read:
                suggestions.append({
                    "type": "next_in_series",
                    "series_title": completion.series_title,
                    "message": f"You've read {completion.books_read} books in {completion.series_title}. Book {int(completion.next_book_number)} is available!",
                    "book_number": completion.next_book_number,
                    "book_title": completion.next_book_title,
                    "books_read": completion.books_read,
                    "total_books": completion.total_books_in_series
                })

        return suggestions[:limit]

    async def get_available_next_books(self, user_id: int) -> List[Dict]:
        available = []

        result = await self.db.execute(
            select(SeriesCompletion).where(
                SeriesCompletion.user_id == user_id,
                SeriesCompletion.is_following == True
            )
        )
        completions = result.scalars().all()

        for completion in completions:
            if completion.next_book_number:
                result = await self.db.execute(
                    select(SeriesReadingOrder).where(
                        SeriesReadingOrder.series_title == completion.series_title,
                        SeriesReadingOrder.sequence_number == completion.next_book_number
                    )
                )
                next_book = result.scalars().first()

                if next_book and next_book.work:
                    available.append({
                        "series_title": completion.series_title,
                        "book_number": completion.next_book_number,
                        "book_title": next_book.book_title,
                        "work_id": next_book.bibframe_work_id,
                        "progress": f"{completion.books_read} of {completion.total_books_in_series}"
                    })

        return available
