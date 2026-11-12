# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.config import get_settings
from app.core.email import COLORS, send_email

settings = get_settings()


async def send_staff_invite_email(to_email: str, invite_token: str, first_name: str) -> bool:
    # Fragment carries the token so it never lands in server access logs.
    accept_url = f"{settings.frontend_url}/staff/accept-invite#" + invite_token
    html = (
        "<div style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;'>"
        f"<h2 style='color: {COLORS['heading']};'>You're invited to {settings.app_name}</h2>"
        f"<p>Hi {first_name},</p>"
        f"<p>An administrator has invited you to join {settings.app_name} as a staff member.</p>"
        "<p>Click below to set your password and activate your account:</p>"
        "<p style='text-align: center; margin: 30px 0;'>"
        f"<a href='{accept_url}'"
        f" style='background-color: {COLORS['button']}; color: white; padding: 12px 30px;"
        " text-decoration: none; border-radius: 5px; display: inline-block;'>"
        "Set up my account"
        "</a></p>"
        f"<p style='color: {COLORS['text_light']}; font-size: 14px;'>"
        "This link expires in 72 hours. If you weren't expecting this, you can ignore this email."
        "</p>"
        f"<hr style='border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;'>"
        f"<p style='color: {COLORS['text_light']}; font-size: 12px;'>{settings.app_name}</p>"
        "</div>"
    )
    return await send_email(to_email, f"You're invited to {settings.app_name}", html)
