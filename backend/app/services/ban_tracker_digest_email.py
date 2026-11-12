# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import html as _html
from typing import Iterable

from ..models.ban_tracker import BanReport, BanTrackerSubscription
from ..models.user import User


# Email-client-safe palette: only inline styles, no external CSS, no web
# fonts. Matches the visual tone of app.core.email's COLORS.
_HEADING_COLOR = "#2C1810"
_BODY_COLOR = "#5C4F3D"
_MUTED_COLOR = "#8B7B6A"
_BORDER_COLOR = "#E5E0D8"
_ACCENT_COLOR = "#B85C2E"


_BAN_TYPE_LABELS = {
    "challenged": "Challenged",
    "restricted": "Restricted",
    "banned": "Banned",
    "pending": "Pending",
    "CHALLENGED": "Challenged",
    "RESTRICTED": "Restricted",
    "BANNED": "Banned",
    "PENDING": "Pending",
}


def _esc(s: object) -> str:
    if s is None:
        return ""
    return _html.escape(str(s))


def _scope_blurb(sub: BanTrackerSubscription) -> str:
    if sub.scope == "state" and sub.state_filter:
        base = f"ban reports in {_esc(sub.state_filter)}"
    elif sub.scope == "catalog":
        base = "ban reports that match items in our catalog"
    else:
        base = "all new ban reports"
    if sub.ban_type_filter:
        label = _BAN_TYPE_LABELS.get(sub.ban_type_filter, sub.ban_type_filter)
        base += f", filtered to {_esc(label)}"
    return base


def _report_link(report: BanReport, site_url: str) -> str:
    if report.source_url:
        return report.source_url
    if report.state:
        return f"{site_url}/ban-tracker?state={_esc(report.state)}"
    return f"{site_url}/ban-tracker"


def _ban_type_value(report: BanReport) -> str:
    bt = report.ban_type
    if hasattr(bt, "value"):
        return bt.value
    return str(bt) if bt is not None else ""


def _render_report_row(report: BanReport, site_url: str) -> str:
    bt_raw = _ban_type_value(report)
    badge = _BAN_TYPE_LABELS.get(bt_raw, bt_raw.title() if bt_raw else "")
    link = _report_link(report, site_url)
    state_str = f" &middot; {_esc(report.state)}" if report.state else ""
    reason_str = (
        f"<div style=\"margin-top:4px;color:{_MUTED_COLOR};font-size:13px;\">"
        f"Reason: {_esc(report.reason_category)}</div>"
        if report.reason_category
        else ""
    )
    badge_html = (
        f"<span style=\"display:inline-block;padding:2px 8px;"
        f"background:#F5EFE8;color:{_ACCENT_COLOR};"
        f"border-radius:10px;font-size:12px;font-weight:600;\">"
        f"{_esc(badge)}</span>"
        if badge
        else ""
    )
    return (
        f"<li style=\"padding:12px 0;border-bottom:1px solid {_BORDER_COLOR};list-style:none;\">"
        f"<div style=\"font-size:15px;color:{_HEADING_COLOR};\">"
        f"<a href=\"{_esc(link)}\" style=\"color:{_HEADING_COLOR};text-decoration:none;font-weight:600;\">"
        f"{_esc(report.title)}</a>"
        f" by {_esc(report.author)}"
        f"</div>"
        f"<div style=\"margin-top:4px;color:{_MUTED_COLOR};font-size:13px;\">"
        f"{badge_html}{state_str}"
        f"</div>"
        f"{reason_str}"
        f"</li>"
    )


def render_digest_email(
    *,
    user: User,
    subscription: BanTrackerSubscription,
    reports: Iterable[BanReport],
    capped: bool,
    unsubscribe_url: str,
    site_url: str,
) -> str:
    reports_list = list(reports)
    n = len(reports_list)
    greeting_name = user.first_name or "there"

    rows_html = "".join(_render_report_row(r, site_url) for r in reports_list)

    capped_note = ""
    if capped:
        capped_note = (
            f"<p style=\"color:{_MUTED_COLOR};font-size:13px;font-style:italic;\">"
            f"Showing the {n} oldest new reports. There may be more on the site."
            f"</p>"
        )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Ban Tracker Digest</title></head>
<body style="margin:0;padding:0;background:#FAF7F2;font-family:Georgia,serif;color:{_BODY_COLOR};">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#FAF7F2;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid {_BORDER_COLOR};border-radius:6px;padding:32px;max-width:600px;">
<tr><td>
<h1 style="margin:0 0 16px 0;color:{_HEADING_COLOR};font-size:22px;">
Ban Tracker Digest
</h1>
<p style="margin:0 0 16px 0;font-size:15px;line-height:1.5;">
Hi {_esc(greeting_name)},
</p>
<p style="margin:0 0 16px 0;font-size:15px;line-height:1.5;">
You're subscribed to {_scope_blurb(subscription)}. Here's what's new:
</p>
<ul style="margin:0 0 24px 0;padding:0;">
{rows_html}
</ul>
{capped_note}
<p style="margin:24px 0 0 0;font-size:14px;line-height:1.5;">
<a href="{_esc(site_url)}/ban-tracker" style="color:{_ACCENT_COLOR};text-decoration:underline;">
View the full ban tracker
</a>
</p>
<div style="margin-top:32px;padding-top:20px;border-top:1px solid {_BORDER_COLOR};font-size:12px;color:{_MUTED_COLOR};text-align:center;line-height:1.6;">
You're receiving this because you subscribed at l30.org.<br>
<a href="{_esc(unsubscribe_url)}" style="color:{_MUTED_COLOR};text-decoration:underline;">
Unsubscribe
</a>
</div>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""
