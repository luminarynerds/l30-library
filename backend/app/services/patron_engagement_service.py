# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from typing import Optional
from app.core.logging import get_logger

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.email import COLORS
from ..core.frontend_routes import routes
from ..models.user import User
from ..models.circulation import Checkout, CheckoutStatus
from ..models.event_registration import EventRegistration, EventRegistrationStatus
from ..models.notification import NotificationType, NotificationQueue
from .notifications import notification_service

settings = get_settings()
logger = get_logger(__name__)


class PatronEngagementService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_celebrate_100th_checkout(self, user_id: int) -> Optional[NotificationQueue]:
        # Count completed checkouts for this user
        count_result = await self.db.execute(
            select(func.count(Checkout.id)).where(
                and_(
                    Checkout.user_id == user_id,
                    Checkout.status.in_([
                        CheckoutStatus.returned,
                        CheckoutStatus.overdue,
                        CheckoutStatus.lost,
                        CheckoutStatus.lost_by_patron,
                        CheckoutStatus.lost_in_transit,
                        CheckoutStatus.claims_returned,
                        CheckoutStatus.damaged,
                        CheckoutStatus.returned_damaged,
                    ])
                )
            )
        )
        checkout_count = count_result.scalar() or 0

        # Only send if exactly 100 (to avoid duplicate celebrations)
        if checkout_count != 100:
            return None

        # Get user for personalization
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return None

        # Render celebration email
        subject, html_body = self._render_100th_checkout_email(user)

        # Queue notification
        notification = await notification_service.queue_notification(
            user_id=user_id,
            notification_type=NotificationType.CHECKOUT_RECEIPT,  # Reuse circulation type
            recipient_email=user.email,
            subject=subject,
            html_body=html_body,
            context_data={
                "celebration_type": "100th_checkout",
                "milestone": 100,
            },
            db=self.db,
        )

        logger.info(f"Queued 100th checkout celebration for user {user_id}")
        await self.db.commit()
        return notification

    async def check_and_celebrate_card_anniversary(self, user_id: int) -> Optional[NotificationQueue]:
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user or not user.created_at:
            return None

        today = datetime.now(timezone.utc).date()
        card_anniversary_date = user.created_at.date()

        # Check if today is their anniversary (month and day match, but not year)
        if (today.month == card_anniversary_date.month and
            today.day == card_anniversary_date.day):

            years_member = today.year - card_anniversary_date.year

            # Render anniversary email
            subject, html_body = self._render_anniversary_email(user, years_member)

            # Queue notification
            notification = await notification_service.queue_notification(
                user_id=user_id,
                notification_type=NotificationType.TRAINING_MILESTONE_REACHED,
                recipient_email=user.email,
                subject=subject,
                html_body=html_body,
                context_data={
                    "celebration_type": "card_anniversary",
                    "years_member": years_member,
                    "anniversary_date": card_anniversary_date.isoformat(),
                },
                db=self.db,
            )

            logger.info(f"Queued card anniversary celebration for user {user_id}, {years_member} years")
            await self.db.commit()
            return notification

        return None

    async def send_event_thank_you(
        self,
        user_id: int,
        event_id: int,
        event_title: str,
        attendee_name: Optional[str] = None,
        attendee_email: Optional[str] = None,
    ) -> Optional[NotificationQueue]:
        # Get user if not provided
        if not attendee_email:
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return None
            attendee_email = user.email
            attendee_name = user.first_name or attendee_name or "Patron"
        else:
            attendee_name = attendee_name or "Patron"

        # Render thank you email
        subject, html_body = self._render_event_thank_you_email(
            attendee_name, event_title
        )

        # Queue notification
        notification = await notification_service.queue_notification(
            user_id=user_id,
            notification_type=NotificationType.EVENT_REMINDER,
            recipient_email=attendee_email,
            subject=subject,
            html_body=html_body,
            context_data={
                "celebration_type": "event_thank_you",
                "event_id": event_id,
                "event_title": event_title,
                "attendee_name": attendee_name,
            },
            db=self.db,
        )

        logger.info(f"Queued event thank you for user {user_id}, event {event_id}")
        await self.db.commit()
        return notification

    @staticmethod
    def _render_100th_checkout_email(user: User) -> tuple[str, str]:
        subject = "🎉 Congratulations! You've Reached 100 Checkouts!"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {COLORS['heading']}; text-align: center;">🎉 Milestone Achievement 🎉</h2>

            <p>Hi {user.first_name},</p>

            <p>We wanted to take a moment to celebrate <strong>you</strong>! You've just reached an incredible milestone:</p>

            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 30px; border-radius: 10px; margin: 30px 0;
                        text-align: center; color: white;">
                <h1 style="margin: 0; font-size: 48px;">100</h1>
                <p style="margin: 10px 0 0 0; font-size: 20px;">Items Checked Out</p>
            </div>

            <p style="color: {COLORS['body']}; line-height: 1.6;">
                Whether you're a voracious reader, a lifelong learner, or someone who explores our entire collection,
                this milestone shows your commitment to personal growth and discovery. You're helping make our library
                community vibrant and engaged!
            </p>

            <p style="color: {COLORS['body']}; line-height: 1.6;">
                Thank you for being such a valued member of our library family. Keep exploring, learning, and growing!
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{routes.url(settings.frontend_url, routes.account_checkouts)}"
                   style="background-color: {COLORS['button']}; color: white; padding: 14px 32px;
                          text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                    View Your Checkouts
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
            <p style="color: {COLORS['text_light']}; font-size: 12px; text-align: center;">
                {settings.app_name}<br>
                This is an automated celebration notification. Keep up the great work!
            </p>
        </div>
        """

        return subject, html

    @staticmethod
    def _render_anniversary_email(user: User, years_member: int) -> tuple[str, str]:
        subject = f"Happy {years_member}-Year Library Anniversary, {user.first_name}!"

        anniversary_emoji = ["🎂", "🎉", "⭐", "💫"][min(years_member - 1, 3)]

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {COLORS['heading']}; text-align: center;">{anniversary_emoji} Library Anniversary {anniversary_emoji}</h2>

            <p>Hi {user.first_name},</p>

            <p>Today marks a special day! It's been <strong>{years_member} year{"s" if years_member != 1 else ""}</strong> since you became a valued member
            of our library family.</p>

            <div style="background-color: #F0EDE8; padding: 25px; border-radius: 10px; margin: 25px 0;
                        border-left: 5px solid {COLORS['button']};">
                <p style="margin: 0; font-size: 16px; color: {COLORS['heading']}; font-weight: bold;">
                    Thank You for {years_member} Year{"s" if years_member != 1 else ""} of Support!
                </p>
                <p style="margin: 10px 0 0 0; color: {COLORS['body']};">
                    Your continued membership and engagement mean the world to us. Whether you're discovering new books,
                    attending programs, or simply exploring, you're an essential part of our library community.
                </p>
            </div>

            <p style="color: {COLORS['body']}; line-height: 1.6;">
                Here's to {years_member} year{"s" if years_member != 1 else ""} of reading, learning, and growing together.
                We look forward to many more years of service and friendship!
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{routes.url(settings.frontend_url, routes.my_account)}"
                   style="background-color: {COLORS['button']}; color: white; padding: 14px 32px;
                          text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                    Visit Your Account
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
            <p style="color: {COLORS['text_light']}; font-size: 12px; text-align: center;">
                {settings.app_name}<br>
                Happy Anniversary! We're grateful for you.
            </p>
        </div>
        """

        return subject, html

    @staticmethod
    def _render_event_thank_you_email(attendee_name: str, event_title: str) -> tuple[str, str]:
        subject = f"Thank You for Attending: {event_title}"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {COLORS['heading']};">Thank You for Coming!</h2>

            <p>Hi {attendee_name},</p>

            <p>We wanted to say a heartfelt <strong>thank you</strong> for joining us at:</p>

            <div style="background-color: #F0EDE8; padding: 25px; border-radius: 10px; margin: 25px 0;
                        border-left: 5px solid {COLORS['button']};">
                <p style="margin: 0; font-size: 18px; color: {COLORS['heading']}; font-weight: bold;">
                    {event_title}
                </p>
            </div>

            <p style="color: {COLORS['body']}; line-height: 1.6;">
                Your attendance and participation made the event better! Whether you discovered something new,
                connected with fellow community members, or simply took time to learn and grow, you contributed
                to making our library community vibrant and engaged.
            </p>

            <p style="color: {COLORS['body']}; line-height: 1.6;">
                We'd love to hear about your experience. If you have feedback or suggestions for future events,
                please don't hesitate to reach out. We're always looking to improve!
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{routes.url(settings.frontend_url, routes.events)}"
                   style="background-color: {COLORS['button']}; color: white; padding: 14px 32px;
                          text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                    Explore More Events
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
            <p style="color: {COLORS['text_light']}; font-size: 12px; text-align: center;">
                {settings.app_name}<br>
                Thanks for being part of our community!
            </p>
        </div>
        """

        return subject, html


# Note: Service is instantiated per-request with AsyncSession dependency injection
