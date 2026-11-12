# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import html
from html import escape as escape_html
from typing import Dict

from ...core.config import get_settings
from ...core.email import COLORS
from ...core.frontend_routes import routes
from ...core.i18n import t, get_translator
from .types import NotificationType, NotificationTemplate

settings = get_settings()


# =============================================================================
# HTML Template Renderers
# =============================================================================


def render_checkout_receipt_html(lang: str = "en") -> str:
    tr = get_translator(lang)
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {{{{COLORS['heading']}}}};">{tr("email.checkout_receipt.heading")}</h2>
        <p>{tr("email.checkout_receipt.greeting")}</p>
        <p>{tr("email.checkout_receipt.body")}</p>
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {{{{COLORS['heading']}}}};">{{{{item_title}}}}</h3>
            <table style="width: 100%; margin-top: 15px;">
                <tr>
                    <td style="padding: 10px 0; font-weight: bold;">{tr("email.checkout_receipt.due_date_label")}</td>
                    <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{{{{due_date}}}}</td>
                </tr>
            </table>
        </div>
        <p>{tr("email.checkout_receipt.return_reminder")}</p>
        <hr style="border: none; border-top: 1px solid {{{{COLORS['divider']}}}}; margin: 30px 0;">
        <p style="color: {{{{COLORS['text_light']}}}}; font-size: 12px;">
            {{{{app_name}}}}<br>
            {tr("email.automated_notice")}
        </p>
    </div>
    """


def render_due_date_reminder_html(lang: str = "en") -> str:
    tr = get_translator(lang)
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {{{{COLORS['heading']}}}};">{tr("email.due_date_reminder.heading")}</h2>
        <p>{tr("email.due_date_reminder.greeting")}</p>
        <p>{tr("email.due_date_reminder.body")}</p>
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3>{{{{item_title}}}}</h3>
            <p><strong>{tr("email.due_date_reminder.due_date_label")}</strong> {{{{due_date}}}}</p>
        </div>
        <p>{tr("email.due_date_reminder.return_or_renew")}</p>
    </div>
    """


def render_overdue_notice_html(lang: str = "en") -> str:
    tr = get_translator(lang)
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #C0392B;">{tr("email.overdue_notice.heading")}</h2>
        <p>{tr("email.overdue_notice.greeting")}</p>
        <p>{tr("email.overdue_notice.body")}</p>
        <div style="background-color: #FFE6E6; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #C0392B;">
            <h3>{{{{item_title}}}}</h3>
            <p><strong>{tr("email.overdue_notice.was_due_label")}</strong> {{{{due_date}}}}</p>
        </div>
        <p>{tr("email.overdue_notice.return_message")}</p>
    </div>
    """


def render_hold_ready_html(lang: str = "en") -> str:
    tr = get_translator(lang)
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {{{{COLORS['heading']}}}};">{tr("email.hold_ready.heading")}</h2>
        <p>{tr("email.hold_ready.greeting")}</p>
        <p>{tr("email.hold_ready.body")}</p>
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3>{{{{item_title}}}}</h3>
            <p><strong>{tr("email.hold_ready.pickup_by_label")}</strong> {{{{expires_at}}}}</p>
        </div>
        <p>{tr("email.hold_ready.pickup_reminder")}</p>
    </div>
    """


def render_hold_expiring_html(lang: str = "en") -> str:
    tr = get_translator(lang)
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #E89B44;">{tr("email.hold_expiring.heading")}</h2>
        <p>{tr("email.hold_expiring.greeting")}</p>
        <p>{tr("email.hold_expiring.body")}</p>
        <div style="background-color: #FFF9F0; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3>{{{{item_title}}}}</h3>
            <p><strong>{tr("email.hold_expiring.expires_label")}</strong> {{{{expires_at}}}}</p>
        </div>
    </div>
    """


def render_panic_alert_html() -> str:
    return """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #FFF5F5;">
        <div style="background-color: #C0392B; color: white; padding: 20px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">🚨 URGENT PANIC ALERT 🚨</h1>
        </div>

        <div style="padding: 30px; background-color: white; margin: 20px; border: 3px solid #C0392B; border-radius: 8px;">
            <h2 style="color: #C0392B; margin-top: 0;">Immediate Response Required</h2>

            <div style="background-color: #FFE6E6; padding: 20px; border-radius: 8px; border-left: 4px solid #C0392B; margin: 20px 0;">
                <table style="width: 100%;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: #C0392B;">Alert Number:</td>
                        <td style="padding: 8px 0; font-weight: bold;">{{{{alert_number}}}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: #C0392B;">Location:</td>
                        <td style="padding: 8px 0;">{{{{location}}}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: #C0392B;">Time:</td>
                        <td style="padding: 8px 0;">{{{{triggered_at}}}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: #C0392B;">Triggered By:</td>
                        <td style="padding: 8px 0;">{{{{staff_name}}}}</td>
                    </tr>
                </table>
            </div>

            <p style="font-size: 16px; font-weight: bold; color: #C0392B;">
                A staff member has activated a panic alert and requires immediate assistance.
            </p>

            <p style="margin: 20px 0;">
                <strong>Action Required:</strong><br>
                1. Respond immediately to the location<br>
                2. Acknowledge alert in the system<br>
                3. Contact building security if needed
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{{{{alert_url}}}}"
                   style="background-color: #C0392B; color: white; padding: 15px 40px;
                          text-decoration: none; border-radius: 5px; display: inline-block;
                          font-weight: bold; font-size: 16px;">
                    ACKNOWLEDGE ALERT
                </a>
            </p>

            {{{{situation_notes}}}}
        </div>

        <div style="padding: 20px; text-align: center; color: #666; font-size: 12px;">
            <p style="margin: 0;">This is an automated emergency notification.</p>
            <p style="margin: 5px 0 0 0; font-weight: bold; color: #C0392B;">
                DO NOT reply to this email. Take immediate action.
            </p>
        </div>
    </div>
    """


def render_claims_returned_html() -> str:
    return """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #E89B44; color: white; padding: 15px; text-align: center; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0;">Claims Returned Dispute Filed</h2>
        </div>

        <div style="padding: 30px; background-color: white; border: 2px solid #E89B44; border-top: none; border-radius: 0 0 8px 8px;">
            <p>A patron has filed a claims returned dispute requiring staff review and investigation.</p>

            <div style="background-color: #FFF9F0; padding: 20px; border-radius: 8px; border-left: 4px solid #E89B44; margin: 20px 0;">
                <table style="width: 100%;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: #E89B44;">Dispute ID:</td>
                        <td style="padding: 8px 0;">{{{{dispute_id}}}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: #E89B44;">Patron:</td>
                        <td style="padding: 8px 0;">{{{{patron_name}}}} (ID: {{{{patron_id}}}})</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: #E89B44;">Item:</td>
                        <td style="padding: 8px 0;">{{{{item_title}}}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: #E89B44;">Checkout ID:</td>
                        <td style="padding: 8px 0;">{{{{checkout_id}}}}</td>
                    </tr>
                </table>
            </div>

            <div style="background-color: #F0F0F0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0 0 10px 0; font-weight: bold;">Patron Statement:</p>
                <p style="margin: 0; color: #333;">{{{{patron_statement}}}}</p>
            </div>

            <p style="font-weight: bold; color: #E89B44; margin-top: 20px;">
                Action Required: Review the dispute and begin investigation
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{{{{dispute_url}}}}"
                   style="background-color: #E89B44; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;
                          font-weight: bold;">
                    Review Dispute
                </a>
            </p>

            <p style="color: #666; font-size: 14px;">
                Please investigate this claim by reviewing checkout history, checking return bins,
                and searching shelves. Document your findings in the dispute record.
            </p>
        </div>

        <div style="padding: 20px; text-align: center; color: #666; font-size: 12px;">
            <p style="margin: 0;">This is an automated staff notification.</p>
        </div>
    </div>
    """


# =============================================================================
# Circulation Email Renderers (object-based, used by CirculationNotificationService)
# =============================================================================


def render_checkout_receipt_email(user, item, checkout, lang: str = "en") -> tuple:
    tr = get_translator(lang)
    subject = tr("email.checkout_receipt.subject", item_title=item.title)
    due_date_str = checkout.due_date.strftime("%B %d, %Y")
    by_label = tr("common.by", author=escape_html(item.author)) if item.author else ""
    author_line = (
        f'<p style="color: {COLORS["text_light"]}; margin: 5px 0;">{by_label}</p>'
        if item.author
        else ""
    )

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">{tr("email.checkout_receipt.heading")}</h2>
        <p>{tr("email.checkout_receipt.greeting", user_name=escape_html(user.first_name or ""))}</p>
        <p>{tr("email.checkout_receipt.body")}</p>

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{escape_html(item.title or "")}</h3>
            {author_line}

            <table style="width: 100%; margin-top: 15px;">
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">{tr("email.checkout_receipt.checked_out_label")}</td>
                    <td style="padding: 10px 0; color: {COLORS['body']};">{checkout.checked_out_at.strftime("%B %d, %Y")}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">{tr("email.checkout_receipt.due_date_label")}</td>
                    <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{due_date_str}</td>
                </tr>
            </table>
        </div>

        <p style="color: {COLORS['body']};">
            {tr("email.checkout_receipt.return_reminder_extended")}
        </p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.account_checkouts)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                {tr("email.checkout_receipt.view_checkouts")}
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            {tr("email.automated_notice")}
        </p>
    </div>
    """

    return subject, html


def render_due_date_reminder_email(user, item, checkout, days_until_due: int, lang: str = "en") -> tuple:
    tr = get_translator(lang)
    subject = tr("email.due_date_reminder.subject", item_title=item.title)
    due_date_str = checkout.due_date.strftime("%B %d, %Y")
    by_label = tr("common.by", author=escape_html(item.author)) if item.author else ""
    author_line = (
        f'<p style="color: {COLORS["text_light"]}; margin: 5px 0;">{by_label}</p>'
        if item.author
        else ""
    )

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">{tr("email.due_date_reminder.heading")}</h2>
        <p>{tr("email.due_date_reminder.greeting", user_name=escape_html(user.first_name or ""))}</p>
        <p>{tr("email.due_date_reminder.body", days_until_due=days_until_due)}</p>

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{escape_html(item.title or "")}</h3>
            {author_line}

            <table style="width: 100%; margin-top: 15px;">
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">{tr("email.due_date_reminder.due_date_label")}</td>
                    <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{due_date_str}</td>
                </tr>
            </table>
        </div>

        <p style="color: {COLORS['body']};">
            {tr("email.due_date_reminder.return_or_renew_extended")}
        </p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.account_checkouts)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                {tr("email.due_date_reminder.view_checkouts")}
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            {tr("email.automated_notice")}
        </p>
    </div>
    """

    return subject, html


def render_overdue_notice_email(
    user, item, checkout, days_overdue: int, fine_amount=None, lang: str = "en"
) -> tuple:
    tr = get_translator(lang)
    subject = tr("email.overdue_notice.subject", item_title=item.title)
    due_date_str = checkout.due_date.strftime("%B %d, %Y")
    by_label = tr("common.by", author=escape_html(item.author)) if item.author else ""
    author_line = (
        f'<p style="color: {COLORS["text_light"]}; margin: 5px 0;">{by_label}</p>'
        if item.author
        else ""
    )
    fine_section = ""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #C0392B;">{tr("email.overdue_notice.heading")}</h2>
        <p>{tr("email.overdue_notice.greeting", user_name=escape_html(user.first_name or ""))}</p>
        <p>{tr("email.overdue_notice.body_extended", days_overdue=days_overdue)}</p>

        <div style="background-color: #FFE6E6; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #C0392B;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{escape_html(item.title or "")}</h3>
            {author_line}

            <table style="width: 100%; margin-top: 15px;">
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">{tr("email.overdue_notice.was_due_label")}</td>
                    <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{due_date_str}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">{tr("email.overdue_notice.days_overdue_label")}</td>
                    <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{days_overdue}</td>
                </tr>
                {fine_section}
            </table>
        </div>

        <p style="color: {COLORS['body']};">
            {tr("email.overdue_notice.return_message_extended")}
        </p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.account_checkouts)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                {tr("email.overdue_notice.view_checkouts")}
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            {tr("email.automated_notice")}
        </p>
    </div>
    """

    return subject, html


def render_hold_ready_email(user, item, hold=None, lang: str = "en") -> tuple:
    tr = get_translator(lang)
    subject = tr("email.hold_ready.subject", item_title=item.title)
    expires_at_str = hold.expires_at.strftime("%B %d, %Y") if hold and hold.expires_at else tr("common.soon")
    by_label = tr("common.by", author=escape_html(item.author)) if item.author else ""
    author_line = (
        f'<p style="color: {COLORS["text_light"]}; margin: 5px 0;">{by_label}</p>'
        if item.author
        else ""
    )

    location_section = ""
    item_location = getattr(item, "location", None)
    if item_location:
        location_section = f"""
        <tr>
            <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">{tr("email.hold_ready.pickup_location_label")}</td>
            <td style="padding: 10px 0; color: {COLORS['body']};">{escape_html(item_location)}</td>
        </tr>
        """

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">{tr("email.hold_ready.heading")}</h2>
        <p>{tr("email.hold_ready.greeting", user_name=escape_html(user.first_name or ""))}</p>
        <p>{tr("email.hold_ready.body")}</p>

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{escape_html(item.title or "")}</h3>
            {author_line}

            <table style="width: 100%; margin-top: 15px;">
                {location_section}
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">{tr("email.hold_ready.pickup_by_label")}</td>
                    <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{expires_at_str}</td>
                </tr>
            </table>
        </div>

        <p style="color: {COLORS['body']};">
            {tr("email.hold_ready.pickup_reminder_extended")}
        </p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.account_holds)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                {tr("email.hold_ready.view_holds")}
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            {tr("email.automated_notice")}
        </p>
    </div>
    """

    return subject, html


def render_hold_expiring_email(user, item, hold, days_until_expiry: int, lang: str = "en") -> tuple:
    tr = get_translator(lang)
    subject = tr("email.hold_expiring.subject", item_title=item.title)
    expires_at_str = hold.expires_at.strftime("%B %d, %Y") if hold.expires_at else tr("common.soon")
    by_label = tr("common.by", author=escape_html(item.author)) if item.author else ""
    author_line = (
        f'<p style="color: {COLORS["text_light"]}; margin: 5px 0;">{by_label}</p>'
        if item.author
        else ""
    )

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #E89B44;">{tr("email.hold_expiring.heading")}</h2>
        <p>{tr("email.hold_expiring.greeting", user_name=escape_html(user.first_name or ""))}</p>
        <p>{tr("email.hold_expiring.body", days_until_expiry=days_until_expiry)}</p>

        <div style="background-color: #FFF9F0; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #E89B44;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{escape_html(item.title or "")}</h3>
            {author_line}

            <table style="width: 100%; margin-top: 15px;">
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">{tr("email.hold_expiring.expires_label")}</td>
                    <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{expires_at_str}</td>
                </tr>
            </table>
        </div>

        <p style="color: {COLORS['body']};">
            {tr("email.hold_expiring.expiry_warning")}
        </p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.account_holds)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                {tr("email.hold_expiring.view_holds")}
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            {tr("email.automated_notice")}
        </p>
    </div>
    """

    return subject, html


# =============================================================================
# Payout Email Renderers
# =============================================================================


def render_payout_notification_email(
    author_name: str, amount: float, transfer_id: str,
    ebook_count: int, checkout_count: int
) -> tuple:
    from ...core.email import get_can_spam_footer

    subject = f"Royalty Payout Received - ${amount:.2f}"

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: {COLORS['heading']};">Congratulations, {author_name}!</h2>

                <p>Your royalty payout has been processed and transferred to your Stripe account.</p>

                <div style="background: {COLORS['border']}; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #27ae60; margin-top: 0;">Payout Summary</h3>
                    <p><strong>Amount:</strong> ${amount:.2f}</p>
                    <p><strong>Checkouts Included:</strong> {checkout_count}</p>
                    <p><strong>Books Earning:</strong> {ebook_count}</p>
                    <p><strong>Transfer ID:</strong> <code>{transfer_id}</code></p>
                    <p><strong>Status:</strong> Completed</p>
                </div>

                <p>
                    The funds should be available in your Stripe dashboard immediately.
                    You can withdraw to your bank account anytime through your Stripe account.
                </p>

                <p>
                    <a href="https://dashboard.stripe.com" style="color: #27ae60; text-decoration: none;">
                        View Your Stripe Dashboard &rarr;
                    </a>
                </p>

                {get_can_spam_footer(is_transactional=True)}
            </div>
        </body>
    </html>
    """

    return subject, html_body


def render_earnings_summary_email(
    author_name: str, period: str, total_checkouts: int,
    total_earnings: float, top_ebooks: list
) -> tuple:
    from ...core.email import get_can_spam_footer

    period_name = period.capitalize()
    subject = f"Your {period_name} Royalty Earnings Summary"

    ebook_list_html = ""
    for ebook in top_ebooks:
        ebook_list_html += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 10px;">{ebook['title']}</td>
            <td style="padding: 10px; text-align: right;">{ebook['checkouts']}</td>
            <td style="padding: 10px; text-align: right;">${ebook['earnings']:.2f}</td>
        </tr>
        """

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: {COLORS['heading']};">{period_name} Earnings Summary</h2>

                <p>Hello {author_name},</p>

                <p>Here's your {period} royalty earnings report:</p>

                <div style="background: {COLORS['border']}; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #27ae60; margin-top: 0;">Overview</h3>
                    <p><strong>Total Checkouts:</strong> {total_checkouts}</p>
                    <p><strong>Total Earnings:</strong> ${total_earnings:.2f}</p>
                </div>

                <h3>Top Earning Books</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f5f5f5;">
                            <th style="padding: 10px; text-align: left;">Book Title</th>
                            <th style="padding: 10px; text-align: right;">Checkouts</th>
                            <th style="padding: 10px; text-align: right;">Earnings</th>
                        </tr>
                    </thead>
                    <tbody>
                        {ebook_list_html}
                    </tbody>
                </table>

                <p style="margin-top: 20px;">
                    Your earnings are accumulating in your account. Once you reach the minimum payout
                    amount, your royalties will be automatically transferred to your Stripe account based
                    on your payout settings.
                </p>

                {get_can_spam_footer(is_transactional=True)}
            </div>
        </body>
    </html>
    """

    return subject, html_body


def render_payout_failed_email(
    author_name: str, amount: float, error_reason: str
) -> tuple:
    from ...core.email import get_can_spam_footer

    subject = "Royalty Payout Issue - Action May Be Required"

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c;">Payout Transfer Failed</h2>

                <p>Hello {author_name},</p>

                <p>We attempted to transfer your royalty earnings, but the transfer failed:</p>

                <div style="background: #ffe6e6; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #e74c3c;">
                    <p><strong>Amount:</strong> ${amount:.2f}</p>
                    <p><strong>Error:</strong> {error_reason}</p>
                </div>

                <h3>What to do:</h3>
                <ol>
                    <li>Check that your Stripe account is still active and verified</li>
                    <li>Ensure your account accepts incoming transfers</li>
                    <li>Contact support if you need help with your Stripe account</li>
                </ol>

                <p>
                    Your earnings are safely held in your author account and we'll retry the
                    payout during the next processing cycle.
                </p>

                {get_can_spam_footer(is_transactional=True)}
            </div>
        </body>
    </html>
    """

    return subject, html_body


# =============================================================================
# Template Provider (aggregates all domain templates)
# =============================================================================


class DomainTemplateProvider:

    @staticmethod
    def get_templates() -> Dict[NotificationType, NotificationTemplate]:
        return {
            # ==================================================================
            # LIBRARY PATRON CIRCULATION
            # ==================================================================
            NotificationType.CHECKOUT_RECEIPT: NotificationTemplate(
                subject="Checkout Receipt: {item_title}",
                body="Item {item_title} checked out. Due: {due_date}",
                html_body=render_checkout_receipt_html()
            ),

            NotificationType.DUE_DATE_REMINDER: NotificationTemplate(
                subject="Due Date Reminder: {item_title}",
                body="Item {item_title} is due in {days_until_due} day(s)",
                html_body=render_due_date_reminder_html()
            ),

            NotificationType.OVERDUE_NOTICE: NotificationTemplate(
                subject="Overdue Notice: {item_title}",
                body="Item {item_title} is {days_overdue} day(s) overdue",
                html_body=render_overdue_notice_html()
            ),

            NotificationType.HOLD_READY: NotificationTemplate(
                subject="Your Hold is Ready: {item_title}",
                body="Item {item_title} is ready for pickup until {expires_at}",
                html_body=render_hold_ready_html()
            ),

            NotificationType.HOLD_EXPIRING: NotificationTemplate(
                subject="Hold Expiring Soon: {item_title}",
                body="Your hold expires in {days_until_expiry} day(s)",
                html_body=render_hold_expiring_html()
            ),

            NotificationType.CLAIMS_RETURNED: NotificationTemplate(
                subject="Claims Returned Dispute - {patron_name}",
                body="Patron {patron_name} filed a claims returned dispute for {item_title}",
                html_body=render_claims_returned_html()
            ),

            # ==================================================================
            # MAKERSPACE
            # ==================================================================
            NotificationType.RESERVATION_CREATED: NotificationTemplate(
                subject="Makerspace Reservation Confirmed - {resource_name}",
                body="Your reservation for {resource_name} is confirmed for {start_time}"
            ),

            NotificationType.RESERVATION_REMINDER: NotificationTemplate(
                subject="Reminder: Makerspace Reservation Tomorrow - {resource_name}",
                body="Your reservation for {resource_name} is tomorrow at {start_time}"
            ),

            NotificationType.JOB_SUBMITTED: NotificationTemplate(
                subject="Job Submitted: {job_number}",
                body="Your job {job_number} has been submitted and is awaiting review"
            ),

            NotificationType.JOB_APPROVED: NotificationTemplate(
                subject="Job Approved: {job_number}",
                body="Great news! Your job {job_number} has been approved"
            ),

            NotificationType.JOB_REJECTED: NotificationTemplate(
                subject="Job Review Update: {job_number}",
                body="Your job {job_number} could not be approved. Reason: {rejection_reason}"
            ),

            NotificationType.JOB_READY_PICKUP: NotificationTemplate(
                subject="Ready for Pickup: {job_number}",
                body="Your print job {job_number} is ready for pickup"
            ),

            NotificationType.CERTIFICATION_EXPIRING: NotificationTemplate(
                subject="Certification Expiring Soon: {cert_type}",
                body="Your {cert_type} certification expires in {days_until_expiry} days"
            ),

            NotificationType.CERTIFICATION_COMPLETED: NotificationTemplate(
                subject="Congratulations! Certification Complete: {cert_type}",
                body="You've successfully completed your {cert_type} certification"
            ),

            # ==================================================================
            # HOME DELIVERY
            # ==================================================================
            NotificationType.DELIVERY_REMINDER: NotificationTemplate(
                subject="Reminder: Library Delivery Tomorrow",
                body="Your library delivery is scheduled for tomorrow at {time_window}",
                sms_body="Library delivery reminder: Tomorrow {time_window}. {item_count} items."
            ),

            NotificationType.DELIVERY_SCHEDULED: NotificationTemplate(
                subject="Your Library Delivery Has Been Scheduled",
                body="Delivery scheduled for {delivery_date} at {time_window}",
                sms_body="Library delivery scheduled for {delivery_date} between {time_window}."
            ),

            NotificationType.DELIVERY_RESCHEDULED: NotificationTemplate(
                subject="Your Library Delivery Has Been Rescheduled",
                body="New date: {delivery_date} at {time_window} (was {original_date})"
            ),

            NotificationType.DELIVERY_OUT_FOR_DELIVERY: NotificationTemplate(
                subject="Your Library Delivery is On Its Way!",
                body="Estimated arrival: {time_window}. {item_count} items."
            ),

            NotificationType.DELIVERY_COMPLETED: NotificationTemplate(
                subject="Your Library Delivery Has Arrived",
                body="{items_delivered} items delivered. Items due: {due_date}"
            ),

            NotificationType.ENROLLMENT_APPROVED: NotificationTemplate(
                subject="Welcome to Library HomeDelivery Services!",
                body="Your application approved. First delivery: {first_delivery_date}"
            ),

            # ==================================================================
            # ALERTS
            # ==================================================================
            NotificationType.PRIVACY_ALERT: NotificationTemplate(
                subject="Privacy Alert: {alert_type}",
                body="Alert severity: {severity}. Changes made: {change_count}"
            ),

            NotificationType.MODERATION_ALERT: NotificationTemplate(
                subject="Moderation Alert: {alert_type}",
                body="Pending items: {pending_count}. Overdue: {overdue_count}"
            ),

            # ==================================================================
            # EMERGENCY / PANIC ALERTS
            # ==================================================================
            NotificationType.PANIC_ALERT: NotificationTemplate(
                subject="🚨 URGENT: Staff Panic Alert - {alert_number}",
                body="PANIC ALERT triggered at {location}. Staff member {staff_name} needs immediate assistance. Alert #{alert_number} at {triggered_at}",
                html_body=render_panic_alert_html(),
                sms_body="🚨 URGENT: Panic alert at {location}. Staff: {staff_name}. Check app NOW. Alert #{alert_number}"
            ),

            # ==================================================================
            # REVIEW RESPONSES
            # ==================================================================
            NotificationType.REVIEW_RESPONSE: NotificationTemplate(
                subject="New Response to Your Review",
                body="{responder_name} responded to your review"
            ),

            # ==================================================================
            # PAYOUTS
            # ==================================================================
            NotificationType.PAYOUT_SENT: NotificationTemplate(
                subject="Royalty Payout Received - ${amount:.2f}",
                body="Your payout of ${amount:.2f} has been processed (ID: {transfer_id})"
            ),

            NotificationType.EARNINGS_SUMMARY: NotificationTemplate(
                subject="Your {period} Royalty Earnings Summary",
                body="Total earnings: ${total_earnings:.2f} from {total_checkouts} checkouts"
            ),

            # ==================================================================
            # ACCOUNT LIFECYCLE
            # ==================================================================
            NotificationType.WELCOME_EMAIL: NotificationTemplate(
                subject="Welcome to {library_name}!",
                body="Welcome {patron_name}! Your library account has been created. Your library card number is {card_number}. Visit us to explore our collections, programs, and services.",
                html_body=(
                    '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">'
                    '<h2 style="color: #2563eb;">Welcome to {library_name}!</h2>'
                    '<p>Hello {patron_name},</p>'
                    '<p>Your library account has been created successfully.</p>'
                    '<p><strong>Library Card Number:</strong> {card_number}</p>'
                    '<p>Here are some things you can do:</p>'
                    '<ul>'
                    '<li>Browse and check out books, DVDs, and more</li>'
                    '<li>Place holds on popular items</li>'
                    '<li>Access digital resources and e-books</li>'
                    '<li>Register for events and programs</li>'
                    '</ul>'
                    '<p>Visit us anytime — we are excited to have you!</p>'
                    '</div>'
                ),
            ),

            NotificationType.FINE_ASSESSMENT_NOTICE: NotificationTemplate(
                subject="Fine Notice: {fine_type} - ${fine_amount:.2f}",
                body="A fine of ${fine_amount:.2f} has been added to your account for: {fine_reason}. Item: {item_title}.",
                html_body=(
                    '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">'
                    '<h2 style="color: #dc2626;">Fine Notice</h2>'
                    '<p>Hello {patron_name},</p>'
                    '<p>A fine has been assessed on your library account:</p>'
                    '<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">'
                    '<tr><td style="padding: 8px; border: 1px solid #e5e7eb;"><strong>Type</strong></td>'
                    '<td style="padding: 8px; border: 1px solid #e5e7eb;">{fine_type}</td></tr>'
                    '<tr><td style="padding: 8px; border: 1px solid #e5e7eb;"><strong>Amount</strong></td>'
                    '<td style="padding: 8px; border: 1px solid #e5e7eb;">${fine_amount:.2f}</td></tr>'
                    '<tr><td style="padding: 8px; border: 1px solid #e5e7eb;"><strong>Item</strong></td>'
                    '<td style="padding: 8px; border: 1px solid #e5e7eb;">{item_title}</td></tr>'
                    '<tr><td style="padding: 8px; border: 1px solid #e5e7eb;"><strong>Reason</strong></td>'
                    '<td style="padding: 8px; border: 1px solid #e5e7eb;">{fine_reason}</td></tr>'
                    '</table>'
                    '<p>You can pay this fine online or at any library branch.</p>'
                    '</div>'
                ),
            ),

            NotificationType.FINE_PAYMENT_CONFIRMATION: NotificationTemplate(
                subject="Payment Confirmation - ${amount_paid:.2f}",
                body="Payment of ${amount_paid:.2f} received. Receipt #{receipt_number}. Remaining balance: ${remaining_balance:.2f}.",
            ),

            NotificationType.EVENT_REGISTRATION_CONFIRMATION: NotificationTemplate(
                subject="Registration Confirmed: {event_title}",
                body="You're registered for {event_title} on {event_date} at {event_time}. Location: {event_location}.",
                html_body=(
                    '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">'
                    '<h2 style="color: #16a34a;">Registration Confirmed!</h2>'
                    '<p>Hello {patron_name},</p>'
                    '<p>You are registered for the following event:</p>'
                    '<div style="background: #f0fdf4; padding: 16px; border-radius: 8px; margin: 16px 0;">'
                    '<h3 style="margin: 0 0 8px;">{event_title}</h3>'
                    '<p style="margin: 4px 0;">Date: {event_date}</p>'
                    '<p style="margin: 4px 0;">Time: {event_time}</p>'
                    '<p style="margin: 4px 0;">Location: {event_location}</p>'
                    '</div>'
                    '<p>We look forward to seeing you there!</p>'
                    '</div>'
                ),
            ),

            NotificationType.EVENT_REGISTRATION_CANCELLED: NotificationTemplate(
                subject="Registration Cancelled: {event_title}",
                body=(
                    "Your registration for {event_title} on {event_date} at {event_time} "
                    "has been cancelled. If this was a mistake, you can re-register from "
                    "the event page."
                ),
            ),

            NotificationType.EVENT_REMINDER: NotificationTemplate(
                subject="Reminder: {event_title} is Tomorrow!",
                body="Reminder: {event_title} is tomorrow, {event_date} at {event_time}. Location: {event_location}.",
            ),

            NotificationType.EVENT_CANCELLED: NotificationTemplate(
                subject="Event Cancelled: {event_title}",
                body="We're sorry, {event_title} scheduled for {event_date} has been cancelled. {cancellation_reason}",
                html_body=(
                    '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">'
                    '<h2 style="color: #dc2626;">Event Cancelled</h2>'
                    '<p>Hello {patron_name},</p>'
                    '<p>We\'re sorry to let you know that the following event has been cancelled:</p>'
                    '<div style="background: #fef2f2; padding: 16px; border-radius: 8px; margin: 16px 0;">'
                    '<h3 style="margin: 0 0 8px;">{event_title}</h3>'
                    '<p style="margin: 4px 0;">Date: {event_date}</p>'
                    '<p style="margin: 4px 0;">Time: {event_time}</p>'
                    '<p style="margin: 4px 0;">Location: {event_location}</p>'
                    '</div>'
                    '<p>{cancellation_reason}</p>'
                    '<p>We apologize for any inconvenience.</p>'
                    '</div>'
                ),
            ),

            NotificationType.EVENT_WAITLIST_PROMOTED: NotificationTemplate(
                subject="You're In: {event_title}",
                body="Good news! A spot opened up and you've been moved off the waitlist for {event_title} on {event_date} at {event_time}. Location: {event_location}.",
                html_body=(
                    '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">'
                    '<h2 style="color: #16a34a;">You\'re In!</h2>'
                    '<p>Hello {patron_name},</p>'
                    '<p>Good news! A spot has opened up and you have been promoted from the waitlist. You are now confirmed for:</p>'
                    '<div style="background: #f0fdf4; padding: 16px; border-radius: 8px; margin: 16px 0;">'
                    '<h3 style="margin: 0 0 8px;">{event_title}</h3>'
                    '<p style="margin: 4px 0;">Date: {event_date}</p>'
                    '<p style="margin: 4px 0;">Time: {event_time}</p>'
                    '<p style="margin: 4px 0;">Location: {event_location}</p>'
                    '</div>'
                    '<p>We look forward to seeing you there!</p>'
                    '</div>'
                ),
            ),

            NotificationType.EVENT_WAITLIST_JOINED: NotificationTemplate(
                subject="You're on the waitlist: {event_title}",
                body="Thanks for joining the waitlist for {event_title} on {event_date} at {event_time}. You are #{position} in line. We'll email you if a spot opens.",
                html_body=(
                    '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">'
                    '<h2 style="color: #4a7c59;">You\'re on the waitlist</h2>'
                    '<p>Hello {patron_name},</p>'
                    '<p>Thanks for joining the waitlist. You are <strong>#{position}</strong> in line for:</p>'
                    '<div style="background: #f0fdf4; padding: 16px; border-radius: 8px; margin: 16px 0;">'
                    '<h3 style="margin: 0 0 8px;">{event_title}</h3>'
                    '<p style="margin: 4px 0;">Date: {event_date}</p>'
                    '<p style="margin: 4px 0;">Time: {event_time}</p>'
                    '<p style="margin: 4px 0;">Location: {event_location}</p>'
                    '</div>'
                    '<p>We\'ll email you as soon as a spot opens up.</p>'
                    '</div>'
                ),
            ),

            NotificationType.EVENT_WAITLIST_SPOT_AVAILABLE: NotificationTemplate(
                subject="A spot opened: {event_title}",
                body="A spot just opened up for {event_title} on {event_date} at {event_time}. Claim it within {claim_minutes} minutes: {claim_url}",
                html_body=(
                    '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">'
                    '<h2 style="color: #16a34a;">A spot just opened up</h2>'
                    '<p>Hello {patron_name},</p>'
                    '<p>A registered patron cancelled and you are first on the waitlist for:</p>'
                    '<div style="background: #f0fdf4; padding: 16px; border-radius: 8px; margin: 16px 0;">'
                    '<h3 style="margin: 0 0 8px;">{event_title}</h3>'
                    '<p style="margin: 4px 0;">Date: {event_date}</p>'
                    '<p style="margin: 4px 0;">Time: {event_time}</p>'
                    '<p style="margin: 4px 0;">Location: {event_location}</p>'
                    '</div>'
                    '<p><strong>Claim your spot in the next {claim_minutes} minutes:</strong></p>'
                    '<p><a href="{claim_url}" style="display:inline-block;background:#16a34a;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;">Claim my spot</a></p>'
                    '<p style="color:#888;font-size:12px">If you don\'t respond in time, the spot goes to the next person on the list.</p>'
                    '</div>'
                ),
            ),
        }

# =============================================================================
# Reference Chat Email Renderers
# =============================================================================


def render_staff_reply_email(
    *,
    patron_name: str,
    staff_name: str,
    patron_question: str,
    staff_response: str,
    chat_url: str,
    library_name: str,
) -> tuple:
    pn = html.escape(patron_name)
    sn = html.escape(staff_name)
    pq = html.escape(patron_question)
    sr = html.escape(staff_response)
    cu = html.escape(chat_url, quote=True)
    ln = html.escape(library_name)

    subject = f"A librarian answered your question at {ln}"

    html_body = (
        f"<p>Hi {pn},</p>"
        f"<p><strong>{sn}</strong> replied to your question:</p>"
        f'<blockquote style="border-left:3px solid #ccc;padding-left:12px;color:#555">'
        f"<p><em>Your question</em></p><p>{pq}</p></blockquote>"
        f'<blockquote style="border-left:3px solid #4a7c59;padding-left:12px">'
        f"<p><em>Librarian\'s reply</em></p><p>{sr}</p></blockquote>"
        f'<p><a href="{cu}">Continue the conversation</a></p>'
        f'<p style="color:#888;font-size:12px">-- {ln}</p>'
    )

    return subject, html_body


# =============================================================================
# Saved Search Email Renderers
# =============================================================================


def render_saved_search_alert_email(
    *,
    patron_name: str,
    search_name: str,
    items: list,
    new_count: int,
    catalog_url: str,
    library_name: str,
) -> tuple:
    pn = html.escape(patron_name)
    sn = html.escape(search_name)
    cu = html.escape(catalog_url, quote=True)
    ln = html.escape(library_name)

    subject = f"{new_count} new items match your saved search \"{search_name}\""

    rows = []
    for item in items:
        title = html.escape(getattr(item, "title", "") or "(untitled)")
        author = getattr(item, "author", None)
        if author:
            rows.append(
                f"<li><strong>{title}</strong> "
                f"<span style=\"color:#666\">by {html.escape(author)}</span></li>"
            )
        else:
            rows.append(f"<li><strong>{title}</strong></li>")

    overflow = ""
    if new_count > len(items):
        overflow = (
            f"<p style=\"color:#666\">"
            f"...and {new_count - len(items)} more.</p>"
        )

    html_body = (
        f"<p>Hi {pn},</p>"
        f"<p>We added {new_count} new items that match your saved search "
        f"<strong>{sn}</strong>:</p>"
        f"<ul>{''.join(rows)}</ul>"
        f"{overflow}"
        f"<p><a href=\"{cu}\">View them in your catalog</a></p>"
        f"<p style=\"color:#888;font-size:12px\">-- {ln}</p>"
    )

    return subject, html_body
