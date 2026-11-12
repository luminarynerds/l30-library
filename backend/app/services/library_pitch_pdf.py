# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import qrcode
from ..core.branding import branding


ACCENT_COLOR = "#D4783C"
PRIMARY_TEXT = "#333333"
SECONDARY_TEXT = "#666666"
TABLE_BORDER = "#CCCCCC"
TABLE_HEADER_BG = "#F5F5F5"


async def generate_library_pitch_pdf() -> bytes:
    pdf_buffer = io.BytesIO()

    # US Letter: 8.5" x 11"
    width, height = letter
    c = canvas.Canvas(pdf_buffer, pagesize=letter)

    # Set up fonts
    c.setFont("Helvetica-Bold", 32)

    # ===== HEADER =====
    y = height - 0.75 * inch

    # "L30" title
    c.setFont("Times-Bold", 36)
    c.setFillColor(colors.HexColor(ACCENT_COLOR))
    c.drawString(0.5 * inch, y, branding.library_short_name)

    # Subtitle
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.HexColor(PRIMARY_TEXT))
    c.drawString(1.5 * inch, y + 0.1 * inch, "Indie Author Vault")

    # Tagline
    y -= 0.4 * inch
    c.setFont("Helvetica-Oblique", 12)
    c.setFillColor(colors.HexColor(SECONDARY_TEXT))
    tagline = "Indie books. Fair royalties. Your library's catalog, expanded."
    c.drawString(0.5 * inch, y, tagline)

    # ===== SECTION 1: COMPARISON TABLE (LEFT SIDE) =====
    y -= 0.6 * inch

    # Section title
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor(PRIMARY_TEXT))
    c.drawString(0.5 * inch, y, f"Why {branding.library_short_name} Indie Vault?")

    y -= 0.25 * inch

    # Table headers and rows
    table_x_left = 0.5 * inch
    col_1_width = 1.8 * inch
    col_2_width = 1.6 * inch
    col_3_width = 1.6 * inch

    row_height = 0.22 * inch

    # Header row background
    c.setFillColor(colors.HexColor(TABLE_HEADER_BG))
    c.rect(table_x_left, y - row_height, col_1_width + col_2_width + col_3_width, row_height, fill=1)

    # Header text
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor(PRIMARY_TEXT))
    c.drawString(table_x_left + 0.05 * inch, y - 0.17 * inch, "")
    c.drawString(table_x_left + col_1_width + 0.05 * inch, y - 0.17 * inch, "OverDrive")
    c.drawString(table_x_left + col_1_width + col_2_width + 0.05 * inch, y - 0.17 * inch, f"{branding.library_short_name} Vault")

    y -= row_height

    # Table borders and data rows
    rows = [
        ("Cost per eBook", "$15-65", "$10"),
        ("License term", "1-2 years", "Forever"),
        ("Author royalty", "~10-25%", "80%"),
        ("Library kitty", "N/A", "$1/sale"),
        ("Platform + processing", "Yes", "$1/sale"),
        ("Local authors", "Rarely", "Primary"),
    ]

    c.setFont("Helvetica", 8.5)
    c.setStrokeColor(colors.HexColor(TABLE_BORDER))
    c.setLineWidth(0.5)

    for label, od_val, l30_val in rows:
        # Row border
        c.rect(table_x_left, y - row_height, col_1_width + col_2_width + col_3_width, row_height)

        # Text
        c.setFillColor(colors.HexColor(PRIMARY_TEXT))
        c.drawString(table_x_left + 0.05 * inch, y - 0.17 * inch, label)
        c.drawString(table_x_left + col_1_width + 0.05 * inch, y - 0.17 * inch, od_val)
        c.drawString(table_x_left + col_1_width + col_2_width + 0.05 * inch, y - 0.17 * inch, l30_val)

        y -= row_height

    # ===== SECTION 2: BUDGET IMPACT (RIGHT SIDE) =====
    # Position to the right of table
    budget_x = 4.2 * inch
    budget_y = height - 1.9 * inch

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor(PRIMARY_TEXT))
    c.drawString(budget_x, budget_y, "Budget Impact")

    budget_y -= 0.25 * inch

    # Budget items
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor(SECONDARY_TEXT))

    budget_items = [
        ("Start:", "$200 → 20 titles"),
        ("Card revenue:", "~$360/month"),
        ("Year 1 total:", "$4,320"),
        ("Status:", "Self-sustaining"),
    ]

    for label, value in budget_items:
        c.setFont("Helvetica-Bold", 9.5)
        c.setFillColor(colors.HexColor(ACCENT_COLOR))
        c.drawString(budget_x, budget_y, label)

        c.setFont("Helvetica", 9.5)
        c.setFillColor(colors.HexColor(PRIMARY_TEXT))
        c.drawString(budget_x + 1.2 * inch, budget_y, value)

        budget_y -= 0.22 * inch

    # Footnote
    budget_y -= 0.1 * inch
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(colors.HexColor(SECONDARY_TEXT))
    c.drawString(budget_x, budget_y, "Assumes 2 card sales/title/month")

    # ===== SECTION 3: HOW TO START (BOTTOM, FULL WIDTH) =====
    y = 3.2 * inch

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor(PRIMARY_TEXT))
    c.drawString(0.5 * inch, y, "How to Start")

    y -= 0.25 * inch

    c.setFont("Helvetica", 9.5)
    c.setFillColor(colors.HexColor(PRIMARY_TEXT))

    steps = [
        "1. We send you an OPDS feed URL. Add it to your ILS.",
        "2. Patrons see indie titles alongside your regular collection. Done.",
    ]

    for step in steps:
        c.drawString(0.7 * inch, y, step)
        y -= 0.22 * inch

    # ===== QR CODE + FOOTER =====
    footer_y = 0.6 * inch

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2,
    )
    qr.add_data(f"{branding.domain}/indie/vault/subscribe")
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Render QR code to in-memory buffer instead of temp file
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    # Draw QR code (0.9" square, left side)
    qr_size = 0.9 * inch
    c.drawImage(ImageReader(qr_buffer), 0.5 * inch, footer_y, width=qr_size, height=qr_size, preserveAspectRatio=True)

    # Footer text (right of QR)
    footer_text_x = 1.6 * inch
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor(ACCENT_COLOR))
    c.drawString(footer_text_x, footer_y + 0.35 * inch, "Questions?")

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor(PRIMARY_TEXT))
    c.drawString(footer_text_x, footer_y + 0.15 * inch, branding.contact_email)
    c.drawString(footer_text_x, footer_y, f"{branding.domain}/indie")

    # Finalize PDF
    c.save()
    pdf_buffer.seek(0)

    return pdf_buffer.getvalue()
