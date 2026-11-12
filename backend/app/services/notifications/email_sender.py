# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.email import send_email, get_can_spam_footer, COLORS
from ...core.frontend_routes import routes
from .types import NotificationType
from .templates import DomainTemplateProvider

settings = get_settings()
logger = get_logger(__name__)


# =============================================================================
# Email Sender Service
# =============================================================================


class EmailSenderService:

    def __init__(self):
        self.templates = DomainTemplateProvider.get_templates()

    async def send_notification(
        self,
        notification_type: NotificationType,
        recipient_email: Optional[str],
        subject: str,
        html_body: str,
        context_data: Dict,
        user_id: Optional[int] = None,
        scheduled_for: Optional[datetime] = None,
        db: Optional[AsyncSession] = None,
    ):
        if not recipient_email:
            logger.warning(f"No recipient email for {notification_type}")
            return None

        # Check if email notifications are enabled at the organization level
        if db:
            from ..organization_features_service import OrganizationFeaturesService
            enabled = await OrganizationFeaturesService.is_feature_enabled(db, "email_notifications_enabled")
            if not enabled:
                logger.info(f"Email notifications disabled - skipping {notification_type}")
                return None

        if scheduled_for is None:
            scheduled_for = datetime.now(timezone.utc)

        if db and user_id is not None:
            from .batching import BatchNotificationService
            from ...models.notification import NotificationType as DBNotificationType
            return await BatchNotificationService.queue_notification(
                user_id=user_id,
                notification_type=self._map_to_db_type(notification_type),
                recipient_email=recipient_email,
                subject=subject,
                html_body=html_body,
                context_data=context_data,
                scheduled_for=scheduled_for,
                db=db,
            )
        else:
            # No patron account to attribute this to (e.g. anonymous public
            # event registration) - notification_queue.user_id is a NOT NULL
            # FK to users.id, so there's no valid row to queue against.
            # Send immediately instead of persisting to the queue.
            success = await send_email(
                to_email=recipient_email,
                subject=subject,
                html_content=html_body,
            )
            if not success:
                logger.error(f"Failed to send {notification_type}")
            return None

    async def send_templated(
        self,
        notification_type: NotificationType,
        recipient_email: str,
        context_data: Dict,
        db: Optional[AsyncSession] = None,
        user_id: Optional[int] = None,
        categories: Optional[List[str]] = None,
    ) -> bool:
        template = self.templates.get(notification_type)
        if not template:
            logger.warning(f"No template for {notification_type}")
            return False

        subject, body, html, sms = template.render(context_data)

        if db:
            result = await self.send_notification(
                notification_type=notification_type,
                recipient_email=recipient_email,
                subject=subject,
                html_body=html or body,
                context_data=context_data,
                user_id=user_id,
                db=db,
            )
            return result is not None
        else:
            success = await send_email(
                to_email=recipient_email,
                subject=subject,
                html_content=html or body,
                categories=categories,
            )
            if success:
                logger.info(f"Sent {notification_type.value}")
            else:
                logger.error(f"Failed to send {notification_type.value}")
            return success

    # =========================================================================
    # Patron circulation email rendering
    # =========================================================================

    @staticmethod
    def render_checkout_receipt_email(user, item, checkout) -> tuple:
        subject = f"Checkout Receipt: {item.title}"
        due_date_str = checkout.due_date.strftime("%B %d, %Y")
        author_line = (
            f'<p style="color: {COLORS["text_light"]}; margin: 5px 0;">by {item.author}</p>'
            if item.author
            else ""
        )

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {COLORS['heading']};">Item Checked Out</h2>
            <p>Hi {user.first_name},</p>
            <p>You have successfully checked out the following item:</p>

            <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: {COLORS['heading']}; margin-top: 0;">{item.title}</h3>
                {author_line}

                <table style="width: 100%; margin-top: 15px;">
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Checked Out:</td>
                        <td style="padding: 10px 0; color: {COLORS['body']};">{checkout.checked_out_at.strftime("%B %d, %Y")}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Due Date:</td>
                        <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{due_date_str}</td>
                    </tr>
                </table>
            </div>

            <p style="color: {COLORS['body']};">
                Please return this item by the due date so others can enjoy it too!
                You can return items at any library branch or book drop.
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{routes.url(settings.frontend_url, routes.account_checkouts)}"
                   style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View My Checkouts
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
            <p style="color: {COLORS['text_light']}; font-size: 12px;">
                {settings.app_name}<br>
                This is an automated notification. Please do not reply to this email.
            </p>
        </div>
        """

        return subject, html

    @staticmethod
    def render_due_date_reminder_email(user, item, checkout, days_until_due: int) -> tuple:
        subject = f"Due Date Reminder: {item.title}"
        due_date_str = checkout.due_date.strftime("%B %d, %Y")
        author_line = (
            f'<p style="color: {COLORS["text_light"]}; margin: 5px 0;">by {item.author}</p>'
            if item.author
            else ""
        )

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {COLORS['heading']};">Due Date Reminder</h2>
            <p>Hi {user.first_name},</p>
            <p>This is a friendly reminder that the following item is due in {days_until_due} day(s):</p>

            <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: {COLORS['heading']}; margin-top: 0;">{item.title}</h3>
                {author_line}

                <table style="width: 100%; margin-top: 15px;">
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Due Date:</td>
                        <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{due_date_str}</td>
                    </tr>
                </table>
            </div>

            <p style="color: {COLORS['body']};">
                Please return or renew this item before the due date.
                Need more time? You can easily renew online or at the library!
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{routes.url(settings.frontend_url, routes.account_checkouts)}"
                   style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Renew or View Checkouts
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
            <p style="color: {COLORS['text_light']}; font-size: 12px;">
                {settings.app_name}<br>
                This is an automated notification. Please do not reply to this email.
            </p>
        </div>
        """

        return subject, html

    @staticmethod
    def render_overdue_notice_email(
        user, item, checkout, days_overdue: int, fine_amount: Optional[float] = None
    ) -> tuple:
        subject = f"Overdue Notice: {item.title}"
        due_date_str = checkout.due_date.strftime("%B %d, %Y")
        author_line = (
            f'<p style="color: {COLORS["text_light"]}; margin: 5px 0;">by {item.author}</p>'
            if item.author
            else ""
        )
        fine_section = ""

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #C0392B;">Overdue Notice</h2>
            <p>Hi {user.first_name},</p>
            <p>The following item is now <strong>{days_overdue} day(s) overdue</strong>. Please return it as soon as possible.</p>

            <div style="background-color: #FFE6E6; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #C0392B;">
                <h3 style="color: {COLORS['heading']}; margin-top: 0;">{item.title}</h3>
                {author_line}

                <table style="width: 100%; margin-top: 15px;">
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Was Due:</td>
                        <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{due_date_str}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Days Overdue:</td>
                        <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{days_overdue}</td>
                    </tr>
                    {fine_section}
                </table>
            </div>

            <p style="color: {COLORS['body']};">
                We know life gets busy! Please return this item when you can so others can enjoy it.
                You can return items at any library branch or book drop. Need help? Just ask!
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{routes.url(settings.frontend_url, routes.account_checkouts)}"
                   style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View My Checkouts
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
            <p style="color: {COLORS['text_light']}; font-size: 12px;">
                {settings.app_name}<br>
                This is an automated notification. Please do not reply to this email.
            </p>
        </div>
        """

        return subject, html

    @staticmethod
    def render_hold_ready_email(user, item, hold) -> tuple:
        subject = f"Your Hold is Ready: {item.title}"
        expires_at_str = hold.expires_at.strftime("%B %d, %Y") if hold.expires_at else "Soon"
        author_line = (
            f'<p style="color: {COLORS["text_light"]}; margin: 5px 0;">by {item.author}</p>'
            if item.author
            else ""
        )

        location_section = ""
        if item.location:
            location_section = f"""
            <tr>
                <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Pickup Location:</td>
                <td style="padding: 10px 0; color: {COLORS['body']};">{item.location}</td>
            </tr>
            """

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {COLORS['heading']};">Your Hold is Ready!</h2>
            <p>Hi {user.first_name},</p>
            <p>Great news! The item you placed on hold is now available for pickup.</p>

            <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: {COLORS['heading']}; margin-top: 0;">{item.title}</h3>
                {author_line}

                <table style="width: 100%; margin-top: 15px;">
                    {location_section}
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Pickup By:</td>
                        <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{expires_at_str}</td>
                    </tr>
                </table>
            </div>

            <p style="color: {COLORS['body']};">
                Please pick up your item by the date shown above. After this date,
                the hold will expire and the item will be made available to the next patron in line.
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{routes.url(settings.frontend_url, routes.account_holds)}"
                   style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View My Holds
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
            <p style="color: {COLORS['text_light']}; font-size: 12px;">
                {settings.app_name}<br>
                This is an automated notification. Please do not reply to this email.
            </p>
        </div>
        """

        return subject, html

    @staticmethod
    def render_hold_expiring_email(user, item, hold, days_until_expiry: int) -> tuple:
        subject = f"Hold Expiring Soon: {item.title}"
        expires_at_str = hold.expires_at.strftime("%B %d, %Y") if hold.expires_at else "Soon"
        author_line = (
            f'<p style="color: {COLORS["text_light"]}; margin: 5px 0;">by {item.author}</p>'
            if item.author
            else ""
        )

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #E89B44;">Hold Expiring Soon</h2>
            <p>Hi {user.first_name},</p>
            <p>Your hold will expire in {days_until_expiry} day(s). Please pick up your item soon!</p>

            <div style="background-color: #FFF9F0; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #E89B44;">
                <h3 style="color: {COLORS['heading']}; margin-top: 0;">{item.title}</h3>
                {author_line}

                <table style="width: 100%; margin-top: 15px;">
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Expires:</td>
                        <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{expires_at_str}</td>
                    </tr>
                </table>
            </div>

            <p style="color: {COLORS['body']};">
                If you don't pick up this item before it expires, it will be made available to the next patron in line.
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{routes.url(settings.frontend_url, routes.account_holds)}"
                   style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View My Holds
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
            <p style="color: {COLORS['text_light']}; font-size: 12px;">
                {settings.app_name}<br>
                This is an automated notification. Please do not reply to this email.
            </p>
        </div>
        """

        return subject, html

    @staticmethod
    def _map_to_db_type(notification_type: NotificationType):
        from ...models.notification import NotificationType as DBNotificationType

        mapping = {
            NotificationType.CHECKOUT_RECEIPT: DBNotificationType.CHECKOUT_RECEIPT,
            NotificationType.DUE_DATE_REMINDER: DBNotificationType.DUE_DATE_REMINDER,
            NotificationType.OVERDUE_NOTICE: DBNotificationType.OVERDUE_NOTICE,
            NotificationType.HOLD_READY: DBNotificationType.HOLD_READY,
            NotificationType.HOLD_EXPIRING: DBNotificationType.HOLD_EXPIRING,
            NotificationType.EVENT_REGISTRATION_CANCELLED: DBNotificationType.EVENT_REGISTRATION_CANCELLED,
        }
        return mapping.get(notification_type, DBNotificationType.CHECKOUT_RECEIPT)
