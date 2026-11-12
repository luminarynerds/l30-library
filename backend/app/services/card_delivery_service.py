# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import os
from enum import StrEnum
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from io import BytesIO

_LIBRARY_NAME = os.environ.get("LIBRARY_NAME", "My Library")

logger = get_logger(__name__)


class CardDeliveryMethod(StrEnum):
    PRINT = "print"  # Print physical card at checkout
    TEXT = "text"    # Send digital card via SMS


async def generate_library_card_pdf(
    library_card_number: str,
    first_name: str,
    last_name: str,
    email: str,
) -> bytes:
    buffer = BytesIO()

    # Create PDF (business card size: 3.5" x 2")
    c = canvas.Canvas(buffer, pagesize=(3.5*inch, 2*inch))

    # Card background
    c.setFillColor(0.98, 0.62, 0.31)  # L30 Orange
    c.rect(0, 0, 3.5*inch, 2*inch, fill=1, stroke=0)

    # Border
    c.setStrokeColor(0.2, 0.2, 0.2)
    c.setLineWidth(2)
    c.rect(0.1*inch, 0.1*inch, 3.3*inch, 1.8*inch, fill=0, stroke=1)

    # Library name (top)
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(1, 1, 1)  # White
    c.drawString(0.15*inch, 1.7*inch, _LIBRARY_NAME)
    c.setFont("Helvetica", 10)
    c.drawString(0.15*inch, 1.5*inch, "Library System")

    # Card number (center-left)
    c.setFont("Courier-Bold", 14)
    c.setFillColor(0.2, 0.2, 0.2)  # Dark
    c.drawString(0.15*inch, 1.1*inch, library_card_number)

    # Patron name (below card number)
    c.setFont("Helvetica", 10)
    c.drawString(0.15*inch, 0.8*inch, f"{first_name} {last_name}")

    # Bottom info (email and valid message)
    c.setFont("Helvetica", 7)
    c.drawString(0.15*inch, 0.4*inch, email)
    c.drawString(0.15*inch, 0.2*inch, "Valid immediately")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


async def send_card_via_sms(
    phone_number: Optional[str],
    library_card_number: str,
    patron_name: str,
) -> bool:
    if not phone_number:
        logger.warning("No phone number provided for SMS delivery")
        return False

    # SMS delivery is not yet configured - report honestly
    logger.warning(
        "SMS delivery not configured: no SMS provider integrated. "
        f"Card {library_card_number} for {patron_name} was NOT sent to {phone_number}. "
        "Configure an SMS provider to enable this feature."
    )
    return False


async def process_card_delivery(
    delivery_method: CardDeliveryMethod,
    library_card_number: str,
    first_name: str,
    last_name: str,
    email: str,
    phone_number: Optional[str] = None,
) -> dict:
    result = {
        "success": False,
        "method": delivery_method.value,
        "card_number": library_card_number,
    }

    try:
        if delivery_method == CardDeliveryMethod.PRINT:
            # Generate printable PDF
            await generate_library_card_pdf(
                library_card_number,
                first_name,
                last_name,
                email,
            )
            result["success"] = True
            result["message"] = "Card PDF generated. Ready to print at checkout."
            result["pdf_available"] = True

            logger.info("Generated card PDF for patron")

        elif delivery_method == CardDeliveryMethod.TEXT:
            # Send SMS
            sms_success = await send_card_via_sms(
                phone_number,
                library_card_number,
                f"{first_name} {last_name}",
            )
            result["success"] = sms_success
            if sms_success:
                result["message"] = f"Card sent via SMS to {phone_number}"
            else:
                result["message"] = (
                    "SMS delivery is not currently configured. "
                    "Your card number is available in your account."
                )

    except Exception as e:  # noqa: BLE001 -- channel dispatch boundary: email/SMS failures must return user-safe error not crash route
        logger.error(f"Card delivery failed: {e}")
        result["success"] = False
        result["message"] = "Card delivery failed. Please try again or visit the library."

    return result
