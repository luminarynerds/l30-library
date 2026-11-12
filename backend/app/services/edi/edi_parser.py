# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

logger = get_logger(__name__)


@dataclass
class ParsedLineItem:
    line_number: int = 0
    isbn: str | None = None
    title: str | None = None
    author: str | None = None
    quantity: int = 0
    unit_price: Decimal | None = None
    line_total: Decimal | None = None
    response_code: str | None = None  # For ORDRSP
    response_description: str | None = None
    quantity_accepted: int | None = None
    quantity_backordered: int | None = None
    quantity_shipped: int | None = None
    expected_ship_date: datetime | None = None


@dataclass
class ParsedOrderResponse:
    message_type: str = "ORDRSP"
    interchange_control_number: str | None = None
    message_reference: str | None = None
    purchase_order_number: str | None = None
    vendor_order_number: str | None = None
    response_date: datetime | None = None
    response_code: str | None = None
    response_description: str | None = None
    expected_ship_date: datetime | None = None
    expected_delivery_date: datetime | None = None
    line_items: list[ParsedLineItem] = field(default_factory=list)
    raw_segments: list[str] = field(default_factory=list)


@dataclass
class ParsedShipmentNotice:
    message_type: str = "DESADV"
    interchange_control_number: str | None = None
    message_reference: str | None = None
    purchase_order_number: str | None = None
    shipment_number: str | None = None
    ship_date: datetime | None = None
    expected_delivery_date: datetime | None = None
    carrier_name: str | None = None
    carrier_code: str | None = None
    tracking_number: str | None = None
    package_count: int = 1
    total_weight: Decimal | None = None
    weight_unit: str = "LB"
    line_items: list[ParsedLineItem] = field(default_factory=list)
    raw_segments: list[str] = field(default_factory=list)


@dataclass
class ParsedInvoice:
    message_type: str = "INVOIC"
    interchange_control_number: str | None = None
    message_reference: str | None = None
    purchase_order_number: str | None = None
    invoice_number: str | None = None
    invoice_date: datetime | None = None
    due_date: datetime | None = None
    currency_code: str = "USD"
    subtotal: Decimal | None = None
    tax_amount: Decimal = Decimal("0.00")
    shipping_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    total_amount: Decimal | None = None
    line_items: list[ParsedLineItem] = field(default_factory=list)
    raw_segments: list[str] = field(default_factory=list)


class EDIParser:

    def __init__(self):
        # Default EDIFACT delimiters (can be overridden by UNA segment)
        self.component_sep = ":"
        self.data_sep = "+"
        self.decimal_notation = "."
        self.escape_char = "?"
        self.segment_term = "'"

    def _detect_delimiters(self, message: str) -> None:
        if message.startswith("UNA"):
            self.component_sep = message[3]
            self.data_sep = message[4]
            self.decimal_notation = message[5]
            self.escape_char = message[6]
            # Position 7 is reserved
            self.segment_term = message[8] if len(message) > 8 else "'"

    def _split_segments(self, message: str) -> list[str]:
        # Remove UNA if present
        if message.startswith("UNA"):
            message = message[9:] if len(message) > 9 else ""

        # Split by segment terminator, handling escapes
        segments = []
        current = []
        i = 0
        while i < len(message):
            if message[i] == self.escape_char and i + 1 < len(message):
                # Escaped character - include both
                current.append(message[i])
                current.append(message[i + 1])
                i += 2
            elif message[i] == self.segment_term:
                # Segment terminator
                segment = "".join(current).strip()
                if segment:
                    segments.append(segment)
                current = []
                i += 1
            else:
                current.append(message[i])
                i += 1

        # Handle last segment if no terminator
        final = "".join(current).strip()
        if final:
            segments.append(final)

        return segments

    def _split_elements(self, segment: str) -> list[str]:
        elements = []
        current = []
        i = 0
        while i < len(segment):
            if segment[i] == self.escape_char and i + 1 < len(segment):
                current.append(segment[i + 1])
                i += 2
            elif segment[i] == self.data_sep:
                elements.append("".join(current))
                current = []
                i += 1
            else:
                current.append(segment[i])
                i += 1
        elements.append("".join(current))
        return elements

    def _split_components(self, element: str) -> list[str]:
        components = []
        current = []
        i = 0
        while i < len(element):
            if element[i] == self.escape_char and i + 1 < len(element):
                current.append(element[i + 1])
                i += 2
            elif element[i] == self.component_sep:
                components.append("".join(current))
                current = []
                i += 1
            else:
                current.append(element[i])
                i += 1
        components.append("".join(current))
        return components

    def _parse_date(self, date_str: str, format_code: str = "102") -> datetime | None:
        if not date_str:
            return None

        try:
            if format_code == "102" and len(date_str) >= 8:
                return datetime.strptime(date_str[:8], "%Y%m%d")
            elif format_code == "203" and len(date_str) >= 12:
                return datetime.strptime(date_str[:12], "%Y%m%d%H%M")
            else:
                # Try common formats
                for fmt in ["%Y%m%d", "%Y%m%d%H%M", "%y%m%d"]:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        logger.debug("EDI date %s did not match format %s", date_str, fmt)
                        continue
        except ValueError as e:
            logger.warning(f"Failed to parse date {date_str}: {e}")

        return None

    def _parse_decimal(self, value: str) -> Decimal | None:
        if not value:
            return None
        try:
            # Replace EDIFACT decimal notation with standard
            value = value.replace(self.decimal_notation, ".")
            return Decimal(value)
        except InvalidOperation:
            logger.warning(f"Failed to parse decimal: {value}")
            return None

    def detect_message_type(self, message: str) -> str | None:
        self._detect_delimiters(message)
        segments = self._split_segments(message)

        for segment in segments:
            elements = self._split_elements(segment)
            if elements and elements[0] == "UNH":
                if len(elements) >= 3:
                    components = self._split_components(elements[2])
                    if components:
                        return components[0].upper()
        return None

    def parse_message(self, message: str) -> ParsedOrderResponse | ParsedShipmentNotice | ParsedInvoice | None:
        message_type = self.detect_message_type(message)

        if message_type == "ORDRSP":
            return self.parse_ordrsp(message)
        elif message_type == "DESADV":
            return self.parse_desadv(message)
        elif message_type == "INVOIC":
            return self.parse_invoic(message)
        else:
            logger.warning(f"Unknown or unsupported message type: {message_type}")
            return None

    def parse_ordrsp(self, message: str) -> ParsedOrderResponse:
        self._detect_delimiters(message)
        segments = self._split_segments(message)

        result = ParsedOrderResponse()
        result.raw_segments = segments

        current_item: ParsedLineItem | None = None

        for segment in segments:
            elements = self._split_elements(segment)
            if not elements:
                continue

            segment_id = elements[0]

            if segment_id == "UNB":
                # Interchange header - extract control number
                if len(elements) >= 6:
                    result.interchange_control_number = elements[5]

            elif segment_id == "UNH":
                # Message header
                if len(elements) >= 2:
                    result.message_reference = elements[1]

            elif segment_id == "BGM":
                # Beginning of message
                if len(elements) >= 3:
                    result.vendor_order_number = elements[2]
                if len(elements) >= 4:
                    result.response_code = elements[3]

            elif segment_id == "DTM":
                # Date/time
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        qualifier = components[0]
                        date_str = components[1]
                        format_code = components[2] if len(components) >= 3 else "102"
                        parsed_date = self._parse_date(date_str, format_code)

                        if qualifier == "137":  # Document date
                            result.response_date = parsed_date
                        elif qualifier == "2":  # Delivery date
                            result.expected_delivery_date = parsed_date
                        elif qualifier == "11":  # Ship date
                            result.expected_ship_date = parsed_date

            elif segment_id == "RFF":
                # Reference
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        qualifier = components[0]
                        reference = components[1]
                        if qualifier in ["ON", "PO"]:  # Order number
                            result.purchase_order_number = reference

            elif segment_id == "LIN":
                # Line item - start new item
                if current_item:
                    result.line_items.append(current_item)

                current_item = ParsedLineItem()
                if len(elements) >= 2:
                    try:
                        current_item.line_number = int(elements[1])
                    except ValueError:
                        logger.warning("Failed to parse EDI line number: %s", elements[1])

                if len(elements) >= 4:
                    components = self._split_components(elements[3])
                    if components:
                        current_item.isbn = components[0]

            elif segment_id == "PIA" and current_item:
                # Additional product ID
                if len(elements) >= 3:
                    components = self._split_components(elements[2])
                    if len(components) >= 2:
                        if components[1] in ["IB", "EN"]:  # ISBN
                            current_item.isbn = components[0]

            elif segment_id == "IMD" and current_item:
                # Item description
                if len(elements) >= 4:
                    components = self._split_components(elements[3])
                    if len(components) >= 4:
                        current_item.title = components[3]

            elif segment_id == "QTY" and current_item:
                # Quantity
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        qualifier = components[0]
                        try:
                            qty = int(components[1])
                            if qualifier == "21":  # Ordered
                                current_item.quantity = qty
                            elif qualifier == "47":  # Accepted
                                current_item.quantity_accepted = qty
                            elif qualifier == "83":  # Backorder
                                current_item.quantity_backordered = qty
                        except ValueError:
                            logger.warning("Failed to parse EDI quantity value: %s", components[1])

            elif segment_id == "FTX" and current_item:
                # Free text - response description
                if len(elements) >= 5:
                    current_item.response_description = elements[4]

        # Add last item
        if current_item:
            result.line_items.append(current_item)

        return result

    def parse_desadv(self, message: str) -> ParsedShipmentNotice:
        self._detect_delimiters(message)
        segments = self._split_segments(message)

        result = ParsedShipmentNotice()
        result.raw_segments = segments

        current_item: ParsedLineItem | None = None

        for segment in segments:
            elements = self._split_elements(segment)
            if not elements:
                continue

            segment_id = elements[0]

            if segment_id == "UNB":
                if len(elements) >= 6:
                    result.interchange_control_number = elements[5]

            elif segment_id == "UNH":
                if len(elements) >= 2:
                    result.message_reference = elements[1]

            elif segment_id == "BGM":
                if len(elements) >= 3:
                    result.shipment_number = elements[2]

            elif segment_id == "DTM":
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        qualifier = components[0]
                        date_str = components[1]
                        format_code = components[2] if len(components) >= 3 else "102"
                        parsed_date = self._parse_date(date_str, format_code)

                        if qualifier in ["11", "137"]:  # Ship date / document date
                            result.ship_date = parsed_date
                        elif qualifier == "2":  # Delivery date
                            result.expected_delivery_date = parsed_date

            elif segment_id == "RFF":
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        qualifier = components[0]
                        reference = components[1]
                        if qualifier in ["ON", "PO"]:
                            result.purchase_order_number = reference

            elif segment_id == "TDT":
                # Transport details
                if len(elements) >= 4:
                    components = self._split_components(elements[3])
                    if components:
                        result.carrier_code = components[0]
                if len(elements) >= 5:
                    components = self._split_components(elements[4])
                    if components:
                        result.carrier_name = components[0]

            elif segment_id == "EQD":
                # Equipment details (tracking)
                if len(elements) >= 3:
                    result.tracking_number = elements[2]

            elif segment_id == "PAC":
                # Package
                if len(elements) >= 2:
                    try:
                        result.package_count = int(elements[1])
                    except ValueError:
                        logger.warning("Failed to parse EDI package count: %s", elements[1])

            elif segment_id == "MEA":
                # Measurements (weight). EDIFACT D96A composite C174:
                # position 010 = Measure unit qualifier (6411), position 020 =
                # Measurement value (6314). Unit comes FIRST, value SECOND.
                if len(elements) >= 4:
                    components = self._split_components(elements[3])
                    if components:
                        result.weight_unit = components[0] or "LB"
                        if len(components) >= 2:
                            # _parse_decimal returns None silently for empty
                            # values and logs a warning for unparseable ones.
                            result.total_weight = self._parse_decimal(components[1])

            elif segment_id == "LIN":
                if current_item:
                    result.line_items.append(current_item)

                current_item = ParsedLineItem()
                if len(elements) >= 2:
                    try:
                        current_item.line_number = int(elements[1])
                    except ValueError:
                        logger.warning("Failed to parse EDI shipping line number: %s", elements[1])

                if len(elements) >= 4:
                    components = self._split_components(elements[3])
                    if components:
                        current_item.isbn = components[0]

            elif segment_id == "PIA" and current_item:
                if len(elements) >= 3:
                    components = self._split_components(elements[2])
                    if len(components) >= 2 and components[1] in ["IB", "EN"]:
                        current_item.isbn = components[0]

            elif segment_id == "IMD" and current_item:
                if len(elements) >= 4:
                    components = self._split_components(elements[3])
                    if len(components) >= 4:
                        current_item.title = components[3]

            elif segment_id == "QTY" and current_item:
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        qualifier = components[0]
                        try:
                            qty = int(components[1])
                            if qualifier == "12":  # Despatched
                                current_item.quantity_shipped = qty
                        except ValueError:
                            logger.warning("Failed to parse EDI shipped quantity: %s", components[1])

        if current_item:
            result.line_items.append(current_item)

        return result

    def parse_invoic(self, message: str) -> ParsedInvoice:
        self._detect_delimiters(message)
        segments = self._split_segments(message)

        result = ParsedInvoice()
        result.raw_segments = segments

        current_item: ParsedLineItem | None = None
        in_summary_section = False

        for segment in segments:
            elements = self._split_elements(segment)
            if not elements:
                continue

            segment_id = elements[0]

            if segment_id == "UNB":
                if len(elements) >= 6:
                    result.interchange_control_number = elements[5]

            elif segment_id == "UNH":
                if len(elements) >= 2:
                    result.message_reference = elements[1]

            elif segment_id == "BGM":
                if len(elements) >= 3:
                    result.invoice_number = elements[2]

            elif segment_id == "DTM":
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        qualifier = components[0]
                        date_str = components[1]
                        format_code = components[2] if len(components) >= 3 else "102"
                        parsed_date = self._parse_date(date_str, format_code)

                        if qualifier == "137":  # Invoice date
                            result.invoice_date = parsed_date
                        elif qualifier == "13":  # Due date
                            result.due_date = parsed_date

            elif segment_id == "RFF":
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        qualifier = components[0]
                        reference = components[1]
                        if qualifier in ["ON", "PO"]:
                            result.purchase_order_number = reference

            elif segment_id == "CUX":
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        result.currency_code = components[1]

            elif segment_id == "UNS":
                # Summary section marker
                in_summary_section = True
                if current_item:
                    result.line_items.append(current_item)
                    current_item = None

            elif segment_id == "LIN" and not in_summary_section:
                if current_item:
                    result.line_items.append(current_item)

                current_item = ParsedLineItem()
                if len(elements) >= 2:
                    try:
                        current_item.line_number = int(elements[1])
                    except ValueError:
                        logger.warning("Failed to parse EDI invoice line number: %s", elements[1])

                if len(elements) >= 4:
                    components = self._split_components(elements[3])
                    if components:
                        current_item.isbn = components[0]

            elif segment_id == "PIA" and current_item:
                if len(elements) >= 3:
                    components = self._split_components(elements[2])
                    if len(components) >= 2 and components[1] in ["IB", "EN"]:
                        current_item.isbn = components[0]

            elif segment_id == "IMD" and current_item:
                if len(elements) >= 4:
                    components = self._split_components(elements[3])
                    if len(components) >= 4:
                        current_item.title = components[3]

            elif segment_id == "QTY":
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        qualifier = components[0]
                        try:
                            qty = int(components[1])
                            if current_item and qualifier in ["47", "46"]:  # Invoiced
                                current_item.quantity = qty
                        except ValueError:
                            logger.warning("Failed to parse EDI invoice quantity: %s", components[1])

            elif segment_id == "MOA":
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        qualifier = components[0]
                        amount = self._parse_decimal(components[1])

                        if in_summary_section:
                            # Summary amounts
                            if qualifier == "79":  # Total line items
                                result.subtotal = amount
                            elif qualifier == "124":  # Tax
                                result.tax_amount = amount or Decimal("0.00")
                            elif qualifier == "125":  # Total due
                                result.total_amount = amount
                            elif qualifier == "176":  # Shipping
                                result.shipping_amount = amount or Decimal("0.00")
                            elif qualifier == "260":  # Discount
                                result.discount_amount = amount or Decimal("0.00")
                        elif current_item:
                            # Line item amounts
                            if qualifier == "203":  # Line amount
                                current_item.line_total = amount

            elif segment_id == "PRI" and current_item:
                if len(elements) >= 2:
                    components = self._split_components(elements[1])
                    if len(components) >= 2:
                        current_item.unit_price = self._parse_decimal(components[1])

        # Add last item if we haven't already
        if current_item and current_item not in result.line_items:
            result.line_items.append(current_item)

        # Calculate totals if not provided
        if result.subtotal is None and result.line_items:
            result.subtotal = sum(
                item.line_total or Decimal("0")
                for item in result.line_items
            )

        if result.total_amount is None and result.subtotal is not None:
            result.total_amount = (
                result.subtotal +
                (result.tax_amount or Decimal("0")) +
                (result.shipping_amount or Decimal("0")) -
                (result.discount_amount or Decimal("0"))
            )

        return result
