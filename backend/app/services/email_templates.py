# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import html
from pathlib import Path

from jinja2 import Environment, select_autoescape

from ..core.config import get_settings
from ..core.branding import branding
from ..core.frontend_routes import routes
from ..models.acquisition import PurchaseOrder

settings = get_settings()

# Autoescaping environment: vendor/PO fields (vendor name, rejection notes) are
# rendered as HTML email bodies, so every {{ value }} must be escaped by default.
_env = Environment(autoescape=select_autoescape(["html", "xml"]))


def render_po_submitted_email(po: PurchaseOrder) -> str:
    template_path = Path(__file__).parent.parent / "templates/email/po_submitted.html"
    with open(template_path) as f:
        template = _env.from_string(f.read())

    return template.render(
        po_number=po.po_number,
        submitted_by=f"{po.created_by.first_name} {po.created_by.last_name}",
        vendor_name=po.vendor.name if po.vendor else "N/A",
        total_amount=f"{po.total_amount:.2f}",
        fund_name=po.fund.name if po.fund else "N/A",
        item_count=len(po.items),
        view_url=routes.url(settings.frontend_url, routes.staff_acquisition),
        library_name=branding.library_name,
        primary_color=branding.primary_color,
    )


def render_po_approved_email(po: PurchaseOrder, approved_by_name: str) -> str:
    template_path = Path(__file__).parent.parent / "templates/email/po_approved.html"
    with open(template_path) as f:
        template = _env.from_string(f.read())

    return template.render(
        po_number=po.po_number,
        approved_by=approved_by_name,
        vendor_name=po.vendor.name if po.vendor else "N/A",
        total_amount=f"{po.total_amount:.2f}",
        view_url=routes.url(settings.frontend_url, routes.staff_acquisition),
        library_name=branding.library_name,
        primary_color=branding.primary_color,
    )


def render_po_rejected_email(po: PurchaseOrder, rejected_by_name: str) -> str:
    template_path = Path(__file__).parent.parent / "templates/email/po_rejected.html"
    with open(template_path) as f:
        template = _env.from_string(f.read())

    return template.render(
        po_number=po.po_number,
        rejected_by=rejected_by_name,
        vendor_name=po.vendor.name if po.vendor else "N/A",
        total_amount=f"{po.total_amount:.2f}",
        rejection_notes=po.rejection_notes or "No notes provided",
        view_url=routes.url(settings.frontend_url, routes.staff_acquisition),
        library_name=branding.library_name,
        primary_color=branding.primary_color,
    )


def render_vendor_email(po: PurchaseOrder) -> str:
    # Escape vendor- and config-derived fields: this email body is raw HTML.
    lib = html.escape(settings.library_name)
    vendor = html.escape(po.vendor.name if po.vendor else "Vendor")
    po_number = html.escape(str(po.po_number))
    contact_email = html.escape(branding.contact_email or "")
    phone = html.escape(branding.phone or "")
    total = f"{po.total_amount:.2f}"
    return f"""
<html>
<body style="font-family: Arial, sans-serif; color: #2C1810;">
    <h2>Purchase Order from {lib}</h2>

    <p>Dear {vendor},</p>

    <p>Please find attached Purchase Order <strong>{po_number}</strong> for your review and processing.</p>

    <div style="background-color: #F0EDE8; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <table style="width: 100%;">
            <tr>
                <td style="padding: 8px 0; font-weight: bold;">PO Number:</td>
                <td style="padding: 8px 0;">{po_number}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; font-weight: bold;">Total Amount:</td>
                <td style="padding: 8px 0;">${total}</td>
            </tr>
        </table>
    </div>

    <p>If you have any questions regarding this order, please contact:</p>
    <p style="margin-left: 20px;">
        <strong>{lib}</strong><br>
        Email: {contact_email}<br>
        Phone: {phone}
    </p>

    <p>Thank you for your service.</p>

    <p style="margin-top: 30px;">
        Sincerely,<br>
        <strong>{lib}</strong>
    </p>

    <p style="font-size: 12px; color: #8B7B6A; margin-top: 40px;">
        This is an official purchase order. Please retain for your records.
    </p>
</body>
</html>
    """
