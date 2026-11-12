# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.models.acquisition import PurchaseOrder, PurchaseOrderItem
from app.models.edi import VendorEDIProfile, EDIStandard

logger = get_logger(__name__)


class EDIGenerator:

    # EDIFACT delimiters (default UNA segment)
    COMPONENT_SEPARATOR = ":"
    DATA_SEPARATOR = "+"
    DECIMAL_NOTATION = "."
    ESCAPE_CHARACTER = "?"
    SEGMENT_TERMINATOR = "'"

    def __init__(self, profile: VendorEDIProfile):
        self.profile = profile
        self.vendor_settings = self._parse_vendor_settings()

        # Apply vendor-specific settings if provided
        if self.vendor_settings.get("decimal_notation"):
            self.DECIMAL_NOTATION = self.vendor_settings["decimal_notation"]

    def _parse_vendor_settings(self) -> dict:
        if self.profile.vendor_settings:
            try:
                return json.loads(self.profile.vendor_settings)
            except json.JSONDecodeError:
                logger.warning(f"Invalid vendor settings JSON for profile {self.profile.id}")
        return {}

    def _escape_value(self, value: str | None) -> str:
        if value is None:
            return ""

        value = str(value)
        # Escape special characters: ?, +, :, '
        for char in [self.ESCAPE_CHARACTER, self.DATA_SEPARATOR,
                     self.COMPONENT_SEPARATOR, self.SEGMENT_TERMINATOR]:
            value = value.replace(char, f"{self.ESCAPE_CHARACTER}{char}")
        return value

    def _format_decimal(self, value: Decimal | float | None) -> str:
        if value is None:
            return "0"
        # EDIFACT uses the decimal notation from UNA
        return str(value).replace(".", self.DECIMAL_NOTATION)

    def _format_date(self, dt: datetime | None, format_code: str = "102") -> str:
        if dt is None:
            dt = datetime.now()

        if format_code == "102":
            return dt.strftime("%Y%m%d")
        elif format_code == "203":
            return dt.strftime("%Y%m%d%H%M")
        return dt.strftime("%Y%m%d")

    def _generate_control_number(self) -> str:
        # Use timestamp-based control number
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def generate_orders_message(
        self,
        purchase_order: PurchaseOrder,
        interchange_control_number: str | None = None
    ) -> tuple[str, str]:
        if interchange_control_number is None:
            interchange_control_number = self._generate_control_number()

        segments = []

        # UNA - Service String Advice
        segments.append(self._build_una_segment())

        # UNB - Interchange Header
        segments.append(self._build_unb_segment(interchange_control_number))

        # UNH - Message Header
        message_reference = "1"
        segments.append(self._build_unh_segment(message_reference))

        # BGM - Beginning of Message
        segments.append(self._build_bgm_segment(purchase_order))

        # DTM - Date/Time/Period
        segments.append(self._build_dtm_segment(purchase_order.order_date, "137"))  # Document date
        if purchase_order.expected_delivery:
            segments.append(self._build_dtm_segment(purchase_order.expected_delivery, "2"))  # Delivery date

        # NAD - Name and Address (Buyer)
        segments.append(self._build_nad_buyer_segment())

        # NAD - Name and Address (Supplier)
        segments.append(self._build_nad_supplier_segment(purchase_order))

        # CUX - Currency
        currency = self.vendor_settings.get("currency", "USD")
        segments.append(self._build_cux_segment(currency))

        # Line Items
        segment_count = len(segments)
        for idx, item in enumerate(purchase_order.items, start=1):
            item_segments = self._build_line_item_segments(item, idx)
            segments.extend(item_segments)

        # UNS - Section Control (summary section)
        segments.append(f"UNS+S{self.SEGMENT_TERMINATOR}")

        # CNT - Control Total (total number of line items)
        segments.append(f"CNT+2:{len(purchase_order.items)}{self.SEGMENT_TERMINATOR}")

        # UNT - Message Trailer
        segment_count = len(segments) - 1  # Excluding UNA and UNB, including UNT
        segments.append(f"UNT+{segment_count}+{message_reference}{self.SEGMENT_TERMINATOR}")

        # UNZ - Interchange Trailer
        segments.append(f"UNZ+1+{interchange_control_number}{self.SEGMENT_TERMINATOR}")

        message = "\n".join(segments)
        return message, interchange_control_number

    def _build_una_segment(self) -> str:
        return f"UNA{self.COMPONENT_SEPARATOR}{self.DATA_SEPARATOR}{self.DECIMAL_NOTATION}{self.ESCAPE_CHARACTER} {self.SEGMENT_TERMINATOR}"

    def _build_unb_segment(self, control_number: str) -> str:
        syntax_id = "UNOC"  # Character set
        syntax_version = "3"

        sender = f"{self.profile.sender_id or 'LIBRARY'}{self.COMPONENT_SEPARATOR}{self.profile.sender_qualifier}"
        receiver = f"{self.profile.receiver_id or 'VENDOR'}{self.COMPONENT_SEPARATOR}{self.profile.receiver_qualifier}"

        now = datetime.now()
        date_str = now.strftime("%y%m%d")
        time_str = now.strftime("%H%M")

        test_indicator = "1" if self.profile.is_test_mode else ""

        parts = [
            "UNB",
            f"{syntax_id}{self.COMPONENT_SEPARATOR}{syntax_version}",
            sender,
            receiver,
            f"{date_str}{self.COMPONENT_SEPARATOR}{time_str}",
            control_number,
        ]

        if test_indicator:
            parts.extend(["", "", "", "", "", test_indicator])  # Pad to test indicator position

        return self.DATA_SEPARATOR.join(parts) + self.SEGMENT_TERMINATOR

    def _build_unh_segment(self, message_reference: str) -> str:
        message_type = "ORDERS"
        version = "D"
        release = "96A"
        controlling_agency = "UN"

        return f"UNH+{message_reference}+{message_type}{self.COMPONENT_SEPARATOR}{version}{self.COMPONENT_SEPARATOR}{release}{self.COMPONENT_SEPARATOR}{controlling_agency}{self.SEGMENT_TERMINATOR}"

    def _build_bgm_segment(self, po: PurchaseOrder) -> str:
        document_type = "220"  # Order
        document_number = self._escape_value(po.po_number)
        message_function = "9"  # Original

        return f"BGM+{document_type}+{document_number}+{message_function}{self.SEGMENT_TERMINATOR}"

    def _build_dtm_segment(self, date_value: Any, qualifier: str) -> str:
        if date_value:
            if hasattr(date_value, 'strftime'):
                date_str = date_value.strftime("%Y%m%d")
            else:
                date_str = str(date_value).replace("-", "")
        else:
            date_str = datetime.now().strftime("%Y%m%d")

        return f"DTM+{qualifier}{self.COMPONENT_SEPARATOR}{date_str}{self.COMPONENT_SEPARATOR}102{self.SEGMENT_TERMINATOR}"

    def _build_nad_buyer_segment(self) -> str:
        buyer_id = self.profile.sender_id or "LIBRARY"
        return f"NAD+BY+{buyer_id}{self.COMPONENT_SEPARATOR}{self.COMPONENT_SEPARATOR}91{self.SEGMENT_TERMINATOR}"

    def _build_nad_supplier_segment(self, po: PurchaseOrder) -> str:
        supplier_id = self.profile.receiver_id or ""
        vendor_name = self._escape_value(po.vendor.name if po.vendor else "")

        return f"NAD+SU+{supplier_id}{self.COMPONENT_SEPARATOR}{self.COMPONENT_SEPARATOR}91++{vendor_name}{self.SEGMENT_TERMINATOR}"

    def _build_cux_segment(self, currency: str) -> str:
        return f"CUX+2{self.COMPONENT_SEPARATOR}{currency}{self.COMPONENT_SEPARATOR}4{self.SEGMENT_TERMINATOR}"

    def _build_line_item_segments(self, item: PurchaseOrderItem, line_number: int) -> list[str]:
        segments = []

        # LIN - Line Item
        isbn = self._escape_value(item.isbn) if item.isbn else ""
        if isbn:
            # Use ISBN as product ID with EN (EAN) qualifier
            segments.append(f"LIN+{line_number}++{isbn}{self.COMPONENT_SEPARATOR}EN{self.SEGMENT_TERMINATOR}")
        else:
            segments.append(f"LIN+{line_number}{self.SEGMENT_TERMINATOR}")

        # PIA - Additional Product ID (if ISBN available, also use IB qualifier)
        if item.isbn:
            clean_isbn = item.isbn.replace("-", "").replace(" ", "")
            segments.append(f"PIA+5+{clean_isbn}{self.COMPONENT_SEPARATOR}IB{self.SEGMENT_TERMINATOR}")

        # IMD - Item Description
        title = self._escape_value(item.title)[:70]  # EDIFACT limit
        segments.append(f"IMD+F++:::{title}{self.SEGMENT_TERMINATOR}")

        # Author in separate IMD if present
        if item.author:
            author = self._escape_value(item.author)[:70]
            segments.append(f"IMD+F++AUT::{author}{self.SEGMENT_TERMINATOR}")

        # QTY - Quantity
        segments.append(f"QTY+21:{item.quantity}{self.SEGMENT_TERMINATOR}")

        # PRI - Price
        if item.unit_price:
            price = self._format_decimal(item.unit_price)
            segments.append(f"PRI+AAA:{price}{self.SEGMENT_TERMINATOR}")

        return segments

    def generate_filename(self, po: PurchaseOrder, message_type: str = "ORDERS") -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        po_number = po.po_number.replace("/", "-").replace(" ", "_")
        return f"{message_type}_{po_number}_{timestamp}.edi"
