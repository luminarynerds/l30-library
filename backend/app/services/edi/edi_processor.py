# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json
from app.core.logging import get_logger
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.acquisition import PurchaseOrder, PurchaseOrderStatus
from app.models.edi import (
    EDIInvoice,
    EDIInvoiceStatus,
    EDIMessageType,
    EDIOrderResponse,
    EDIShipmentNotice,
    EDITransaction,
    EDITransactionStatus,
    VendorEDIProfile,
)
from .edi_generator import EDIGenerator
from .edi_parser import EDIParser, ParsedInvoice, ParsedOrderResponse, ParsedShipmentNotice
from .edi_transport import EDITransport

logger = get_logger(__name__)


class EDIProcessor:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = EDIParser()

    async def get_vendor_profile(self, vendor_id: int) -> VendorEDIProfile | None:
        result = await self.db.execute(
            select(VendorEDIProfile)
            .where(VendorEDIProfile.vendor_id == vendor_id)
            .options(selectinload(VendorEDIProfile.vendor))
        )
        return result.scalar_one_or_none()

    async def send_purchase_order(
        self, purchase_order_id: int
    ) -> tuple[bool, EDITransaction | None, str]:
        # Get purchase order with items
        result = await self.db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == purchase_order_id)
            .options(
                selectinload(PurchaseOrder.items),
                selectinload(PurchaseOrder.vendor),
                selectinload(PurchaseOrder.fund),
            )
        )
        po = result.scalar_one_or_none()

        if not po:
            return False, None, "Purchase order not found"

        if po.status not in [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.SUBMITTED]:
            return (
                False,
                None,
                f"Purchase order must be approved before sending. Current status: {po.status}",
            )

        # Get vendor EDI profile
        profile = await self.get_vendor_profile(po.vendor_id)

        if not profile:
            return False, None, "No EDI profile configured for this vendor"

        if not profile.is_enabled:
            return False, None, "EDI is not enabled for this vendor"

        if not profile.supports_orders:
            return False, None, "Vendor does not accept EDI orders"

        try:
            # Idempotency check: prevent duplicate orders for the same PO.
            # If a SENT or PENDING transaction already exists for this PO, don't resend.
            existing = await self.db.execute(
                select(EDITransaction).where(
                    EDITransaction.purchase_order_id == po.id,
                    EDITransaction.message_type == EDIMessageType.ORDERS,
                    EDITransaction.status.in_(
                        [EDITransactionStatus.SENT, EDITransactionStatus.PENDING]
                    ),
                )
            )
            if existing.scalar_one_or_none():
                return (
                    False,
                    None,
                    "An EDI order has already been sent or is pending for this purchase order",
                )

            # Generate EDI message
            generator = EDIGenerator(profile)
            message, control_number = generator.generate_orders_message(po)
            filename = generator.generate_filename(po)

            # Create transaction record
            transaction = EDITransaction(
                vendor_edi_profile_id=profile.id,
                purchase_order_id=po.id,
                message_type=EDIMessageType.ORDERS,
                direction="outbound",
                interchange_control_number=control_number,
                status=EDITransactionStatus.PENDING,
                raw_message=message,
                filename=filename,
            )
            self.db.add(transaction)
            # Flush to session (not DB yet) so transaction has an ID for references
            await self.db.flush()

            try:
                # Send via transport
                transport = EDITransport(profile)
                result = await transport.upload_file(message, filename)

                if result.success:
                    transaction.status = EDITransactionStatus.SENT
                    transaction.sent_at = datetime.now()
                    transaction.file_path = result.file_path

                    # Update PO status to submitted if not already
                    if po.status == PurchaseOrderStatus.APPROVED:
                        po.status = PurchaseOrderStatus.SUBMITTED

                    # Update profile last transmission
                    profile.last_transmission_at = datetime.now()
                    profile.last_successful_transmission_at = datetime.now()

                    await self.db.commit()
                    return True, transaction, "Order sent successfully"
                else:
                    transaction.status = EDITransactionStatus.FAILED
                    transaction.last_error = result.error
                    transaction.retry_count = 0
                    transaction.next_retry_at = datetime.now() + timedelta(
                        minutes=profile.retry_interval_minutes
                    )

                    profile.last_transmission_at = datetime.now()

                    await self.db.commit()
                    return False, transaction, f"Failed to send: {result.error}"
            except Exception:
                # Network call failed — rollback the flushed PENDING transaction so retries work
                await self.db.rollback()
                raise

        except Exception as e:
            logger.exception(f"Error sending EDI order: {e}")
            return False, None, str(e)

    async def retry_failed_transaction(self, transaction_id: int) -> tuple[bool, str]:
        result = await self.db.execute(
            select(EDITransaction)
            .where(EDITransaction.id == transaction_id)
            .options(selectinload(EDITransaction.vendor_edi_profile))
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            return False, "Transaction not found"

        if transaction.status not in [EDITransactionStatus.FAILED, EDITransactionStatus.RETRY]:
            return False, f"Cannot retry transaction with status: {transaction.status}"

        profile = transaction.vendor_edi_profile

        if not profile:
            return False, "Vendor EDI profile not found"

        if transaction.retry_count >= profile.max_retries:
            return False, f"Maximum retries ({profile.max_retries}) exceeded"

        try:
            # Resend the message
            transport = EDITransport(profile)
            result = await transport.upload_file(transaction.raw_message, transaction.filename)

            if result.success:
                transaction.status = EDITransactionStatus.SENT
                transaction.sent_at = datetime.now()
                transaction.file_path = result.file_path
                transaction.last_error = None
                transaction.next_retry_at = None

                profile.last_transmission_at = datetime.now()
                profile.last_successful_transmission_at = datetime.now()

                await self.db.commit()
                return True, "Transaction retry successful"
            else:
                transaction.retry_count += 1
                transaction.last_error = result.error
                transaction.status = EDITransactionStatus.RETRY

                if transaction.retry_count >= profile.max_retries:
                    transaction.status = EDITransactionStatus.FAILED
                    transaction.next_retry_at = None
                else:
                    transaction.next_retry_at = datetime.now() + timedelta(
                        minutes=profile.retry_interval_minutes * (2**transaction.retry_count)
                    )

                profile.last_transmission_at = datetime.now()

                await self.db.commit()
                return False, f"Retry failed: {result.error}"

        except Exception as e:
            logger.exception(f"Error retrying transaction: {e}")
            await self.db.rollback()
            return False, str(e)

    async def process_inbound_messages(self, vendor_id: int | None = None) -> dict[str, Any]:
        results = {
            "vendors_processed": 0,
            "files_processed": 0,
            "transactions_created": 0,
            "errors": [],
        }

        # Get enabled profiles
        query = (
            select(VendorEDIProfile)
            .where(VendorEDIProfile.is_enabled == True)
            .options(selectinload(VendorEDIProfile.vendor))
        )

        if vendor_id:
            query = query.where(VendorEDIProfile.vendor_id == vendor_id)

        profile_result = await self.db.execute(query)
        profiles = profile_result.scalars().all()

        for profile in profiles:
            try:
                vendor_results = await self._process_vendor_inbound(profile)
                results["vendors_processed"] += 1
                results["files_processed"] += vendor_results["files_processed"]
                results["transactions_created"] += vendor_results["transactions_created"]
                results["errors"].extend(vendor_results["errors"])
            except Exception as e:
                logger.exception(f"Error processing vendor {profile.vendor_id}: {e}")
                results["errors"].append({"vendor_id": profile.vendor_id, "error": str(e)})

        return results

    async def _process_vendor_inbound(self, profile: VendorEDIProfile) -> dict[str, Any]:
        results = {"files_processed": 0, "transactions_created": 0, "errors": []}

        transport = EDITransport(profile)

        # List files in inbound directory
        files, list_result = await transport.list_files(pattern="*.edi")

        if not list_result.success:
            results["errors"].append({"operation": "list_files", "error": list_result.error})
            return results

        for file_info in files:
            try:
                # Download file
                content, download_result = await transport.download_file(file_info.filename)

                if not download_result.success:
                    results["errors"].append(
                        {"filename": file_info.filename, "error": download_result.error}
                    )
                    continue

                if not content:
                    continue

                # Parse message
                parsed = self.parser.parse_message(content)

                if not parsed:
                    results["errors"].append(
                        {"filename": file_info.filename, "error": "Failed to parse message"}
                    )
                    continue

                # Create transaction and process
                transaction = await self._create_inbound_transaction(
                    profile, file_info.filename, content, parsed
                )

                if transaction:
                    results["transactions_created"] += 1

                    # Move processed file to archive
                    archive_dir = f"{profile.transport_directory_inbound}/processed"
                    await transport.move_file(
                        file_info.filename, profile.transport_directory_inbound, archive_dir
                    )

                results["files_processed"] += 1

            except Exception as e:
                logger.exception(f"Error processing file {file_info.filename}: {e}")
                results["errors"].append({"filename": file_info.filename, "error": str(e)})

        return results

    async def _create_inbound_transaction(
        self,
        profile: VendorEDIProfile,
        filename: str,
        content: str,
        parsed: ParsedOrderResponse | ParsedShipmentNotice | ParsedInvoice,
    ) -> EDITransaction | None:
        # Determine message type
        if isinstance(parsed, ParsedOrderResponse):
            message_type = EDIMessageType.ORDRSP
        elif isinstance(parsed, ParsedShipmentNotice):
            message_type = EDIMessageType.DESADV
        elif isinstance(parsed, ParsedInvoice):
            message_type = EDIMessageType.INVOIC
        else:
            return None

        # Find related purchase order
        po = None
        if parsed.purchase_order_number:
            po_result = await self.db.execute(
                select(PurchaseOrder).where(PurchaseOrder.po_number == parsed.purchase_order_number)
            )
            po = po_result.scalar_one_or_none()

        # Create transaction
        transaction = EDITransaction(
            vendor_edi_profile_id=profile.id,
            purchase_order_id=po.id if po else None,
            message_type=message_type,
            direction="inbound",
            interchange_control_number=parsed.interchange_control_number,
            message_reference_number=parsed.message_reference,
            status=EDITransactionStatus.PENDING,
            raw_message=content,
            parsed_data=json.dumps(self._serialize_parsed(parsed)),
            filename=filename,
            received_at=datetime.now(),
        )
        self.db.add(transaction)
        await self.db.flush()

        # Process based on message type
        if isinstance(parsed, ParsedOrderResponse):
            await self._process_order_response(transaction, parsed, profile, po)
        elif isinstance(parsed, ParsedShipmentNotice):
            await self._process_shipment_notice(transaction, parsed, profile, po)
        elif isinstance(parsed, ParsedInvoice):
            await self._process_invoice(transaction, parsed, profile, po)

        transaction.status = EDITransactionStatus.PROCESSED
        transaction.processed_at = datetime.now()

        await self.db.commit()
        return transaction

    def _serialize_parsed(self, parsed: Any) -> dict:
        if hasattr(parsed, "__dict__"):
            result = {}
            for key, value in parsed.__dict__.items():
                if key == "raw_segments":
                    continue  # Skip raw segments
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    result[key] = str(value)
                elif isinstance(value, list):
                    result[key] = [self._serialize_parsed(item) for item in value]
                elif hasattr(value, "__dict__"):
                    result[key] = self._serialize_parsed(value)
                else:
                    result[key] = value
            return result
        return {"value": str(parsed)}

    async def _process_order_response(
        self,
        transaction: EDITransaction,
        parsed: ParsedOrderResponse,
        profile: VendorEDIProfile,
        po: PurchaseOrder | None,
    ) -> None:
        # Count item statuses
        items_accepted = 0
        items_rejected = 0
        items_backordered = 0

        for item in parsed.line_items:
            if item.quantity_accepted:
                items_accepted += item.quantity_accepted
            if item.quantity_backordered:
                items_backordered += item.quantity_backordered
            if item.response_code == "RJ":
                items_rejected += 1

        # Create order response record
        order_response = EDIOrderResponse(
            edi_transaction_id=transaction.id,
            purchase_order_id=po.id if po else None,
            vendor_id=profile.vendor_id,
            vendor_order_number=parsed.vendor_order_number,
            response_date=parsed.response_date,
            response_code=parsed.response_code,
            response_description=parsed.response_description,
            items_accepted=items_accepted,
            items_rejected=items_rejected,
            items_backordered=items_backordered,
            expected_ship_date=parsed.expected_ship_date,
            expected_delivery_date=parsed.expected_delivery_date,
            line_items=json.dumps([self._serialize_parsed(item) for item in parsed.line_items]),
            is_processed=True,
            processed_at=datetime.now(),
        )
        self.db.add(order_response)

        # --- Integration Point 2: Update PO items from ORDRSP ---
        if not po:
            return  # Response recorded for audit; no PO to update

        # Reload PO with items and fund eagerly loaded
        po_result = await self.db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po.id)
            .options(
                selectinload(PurchaseOrder.items),
                selectinload(PurchaseOrder.fund),
            )
        )
        po = po_result.scalar_one()

        # Build ISBN lookup: normalized ISBN -> PO item
        isbn_lookup: dict[str, Any] = {}
        for po_item in po.items:
            if po_item.isbn:
                normalized = re.sub(r"[\s-]", "", po_item.isbn)
                isbn_lookup[normalized] = po_item

        total_price_adjustment = Decimal("0")

        for resp_item in parsed.line_items:
            if not resp_item.isbn:
                continue
            normalized_isbn = re.sub(r"[\s-]", "", resp_item.isbn)
            po_item = isbn_lookup.get(normalized_isbn)
            if not po_item:
                continue

            # EDI backorder tracking: record every time we hear a status
            # for this line, and self-correct backordered_quantity /
            # expected_ship_date to whatever this response reports (only
            # when the response addresses backorder at all -- None means
            # "this message didn't mention it," leave prior value alone).
            po_item.last_status_at = datetime.now(timezone.utc)
            if resp_item.quantity_backordered is not None:
                po_item.backordered_quantity = resp_item.quantity_backordered
                po_item.expected_ship_date = (
                    resp_item.expected_ship_date.date() if resp_item.expected_ship_date else None
                )

            old_line_total = po_item.line_total

            # Rejected
            if resp_item.response_code == "RJ":
                po_item.quantity = 0
                note = "[EDI] Rejected by vendor"
                if resp_item.response_description:
                    note += f": {resp_item.response_description}"
                po_item.notes = f"{po_item.notes}\n{note}" if po_item.notes else note
                total_price_adjustment += po_item.line_total - old_line_total
                continue

            # Backordered
            if resp_item.quantity_backordered and resp_item.quantity_backordered > 0:
                note = f"[EDI] {resp_item.quantity_backordered} backordered"
                if resp_item.expected_ship_date:
                    note += f", expected {resp_item.expected_ship_date.strftime('%Y-%m-%d')}"
                po_item.notes = f"{po_item.notes}\n{note}" if po_item.notes else note

            # Price change
            if resp_item.unit_price is not None and resp_item.unit_price != po_item.unit_price:
                old_price = po_item.unit_price
                po_item.unit_price = resp_item.unit_price
                note = f"[EDI] Price changed ${old_price} -> ${resp_item.unit_price}"
                po_item.notes = f"{po_item.notes}\n{note}" if po_item.notes else note
                total_price_adjustment += po_item.line_total - old_line_total

        # Adjust PO total
        if total_price_adjustment:
            po.total_amount = (po.total_amount or Decimal("0")) + total_price_adjustment

        # Adjust fund encumbrance for submitted POs
        if po.status == PurchaseOrderStatus.SUBMITTED and po.fund and total_price_adjustment:
            new_encumbered = (po.fund.encumbered_amount or Decimal("0")) + total_price_adjustment
            po.fund.encumbered_amount = max(new_encumbered, Decimal("0"))

        # Cancel PO if all items rejected
        if po.items and all(item.quantity == 0 for item in po.items):
            po.status = PurchaseOrderStatus.CANCELLED

        # Update expected delivery if provided
        if parsed.expected_delivery_date:
            po.expected_delivery = parsed.expected_delivery_date.date()

    async def _process_shipment_notice(
        self,
        transaction: EDITransaction,
        parsed: ParsedShipmentNotice,
        profile: VendorEDIProfile,
        po: PurchaseOrder | None,
    ) -> None:
        total_shipped = sum(item.quantity_shipped or 0 for item in parsed.line_items)

        # Create shipment notice record
        shipment = EDIShipmentNotice(
            edi_transaction_id=transaction.id,
            purchase_order_id=po.id if po else None,
            vendor_id=profile.vendor_id,
            shipment_number=parsed.shipment_number,
            ship_date=parsed.ship_date,
            expected_delivery_date=parsed.expected_delivery_date,
            carrier_name=parsed.carrier_name,
            carrier_code=parsed.carrier_code,
            tracking_number=parsed.tracking_number,
            package_count=parsed.package_count,
            total_weight=parsed.total_weight,
            weight_unit=parsed.weight_unit,
            shipped_items=json.dumps([self._serialize_parsed(item) for item in parsed.line_items]),
            total_items_shipped=total_shipped,
            is_processed=True,
            processed_at=datetime.now(),
        )
        self.db.add(shipment)

        # Update PO expected delivery
        if po and parsed.expected_delivery_date:
            po.expected_delivery = parsed.expected_delivery_date.date()

        # --- Auto-receive: match shipped items to PO items by ISBN ---
        if not po or po.status not in (
            PurchaseOrderStatus.SUBMITTED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
        ):
            return

        # Reload PO with items, fund, and vendor for receive logic
        from sqlalchemy.orm import selectinload as _sil

        po_result = await self.db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po.id)
            .options(
                _sil(PurchaseOrder.items),
                _sil(PurchaseOrder.fund),
                _sil(PurchaseOrder.vendor),
            )
        )
        po = po_result.scalars().first()
        if not po or not po.items:
            return

        # Build ISBN lookup: strip hyphens/spaces for normalization
        def _normalize_isbn(raw: str | None) -> str | None:
            if not raw:
                return None
            return raw.replace("-", "").replace(" ", "").strip()

        isbn_to_item = {}
        for po_item in po.items:
            norm = _normalize_isbn(po_item.isbn)
            if norm:
                isbn_to_item[norm] = po_item

        items_to_receive: list[dict] = []
        unmatched_isbns: list[str] = []

        for shipped in parsed.line_items:
            shipped_isbn = _normalize_isbn(shipped.isbn)
            if not shipped_isbn or shipped_isbn not in isbn_to_item:
                if shipped.isbn:
                    unmatched_isbns.append(shipped.isbn)
                continue

            matched_item = isbn_to_item[shipped_isbn]
            remaining = (matched_item.quantity or 0) - (matched_item.received_quantity or 0)
            qty = min(shipped.quantity_shipped or 0, remaining)
            if qty <= 0:
                continue

            items_to_receive.append(
                {
                    "item_id": matched_item.id,
                    "received_quantity": qty,
                }
            )

        if items_to_receive:
            # Lazy import to avoid circular dependency
            from app.services.po_facade_service import POFacadeService

            facade = POFacadeService(self.db)
            await facade.receive_order_from_edi(po, items_to_receive)
            logger.info(
                "Auto-received %d line items for PO %s from DESADV %s",
                len(items_to_receive),
                po.po_number,
                parsed.shipment_number,
            )

        if unmatched_isbns:
            logger.warning(
                "DESADV %s: %d shipped ISBNs not matched to PO %s: %s",
                parsed.shipment_number,
                len(unmatched_isbns),
                po.po_number if po else "???",
                ", ".join(unmatched_isbns),
            )

    async def _process_invoice(
        self,
        transaction: EDITransaction,
        parsed: ParsedInvoice,
        profile: VendorEDIProfile,
        po: PurchaseOrder | None,
    ) -> None:
        # Calculate variance if PO exists
        variance_amount = None
        if po and parsed.total_amount:
            variance_amount = parsed.total_amount - (po.total_amount or Decimal("0"))

        # Create invoice record
        invoice = EDIInvoice(
            edi_transaction_id=transaction.id,
            purchase_order_id=po.id if po else None,
            vendor_id=profile.vendor_id,
            invoice_number=parsed.invoice_number,
            invoice_date=parsed.invoice_date,
            due_date=parsed.due_date,
            subtotal=parsed.subtotal,
            tax_amount=parsed.tax_amount,
            shipping_amount=parsed.shipping_amount,
            discount_amount=parsed.discount_amount,
            total_amount=parsed.total_amount,
            currency_code=parsed.currency_code,
            status=EDIInvoiceStatus.PENDING,
            po_total=po.total_amount if po else None,
            variance_amount=variance_amount,
            total_line_items=len(parsed.line_items),
            line_items=json.dumps([self._serialize_parsed(item) for item in parsed.line_items]),
        )
        self.db.add(invoice)

    async def get_pending_retries(self) -> list[EDITransaction]:
        result = await self.db.execute(
            select(EDITransaction)
            .where(
                and_(
                    EDITransaction.status == EDITransactionStatus.RETRY,
                    EDITransaction.next_retry_at <= datetime.now(),
                )
            )
            .options(selectinload(EDITransaction.vendor_edi_profile))
        )
        return list(result.scalars().all())

    async def process_pending_retries(self) -> dict[str, Any]:
        results = {"processed": 0, "succeeded": 0, "failed": 0, "errors": []}

        transactions = await self.get_pending_retries()

        for transaction in transactions:
            results["processed"] += 1
            success, message = await self.retry_failed_transaction(transaction.id)
            if success:
                results["succeeded"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({"transaction_id": transaction.id, "error": message})

        return results

    async def get_statistics(self, vendor_id: int | None = None) -> dict[str, Any]:
        from sqlalchemy import func

        base_query = select(EDITransaction)
        if vendor_id:
            base_query = base_query.join(VendorEDIProfile).where(
                VendorEDIProfile.vendor_id == vendor_id
            )

        # Total transactions
        total_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = total_result.scalar() or 0

        # Pending transactions
        pending_result = await self.db.execute(
            select(func.count(EDITransaction.id)).where(
                EDITransaction.status == EDITransactionStatus.PENDING
            )
        )
        pending = pending_result.scalar() or 0

        # Failed transactions
        failed_result = await self.db.execute(
            select(func.count(EDITransaction.id)).where(
                EDITransaction.status == EDITransactionStatus.FAILED
            )
        )
        failed = failed_result.scalar() or 0

        # Last 24 hours
        last_24h = datetime.now() - timedelta(hours=24)
        recent_result = await self.db.execute(
            select(func.count(EDITransaction.id)).where(EDITransaction.sent_at >= last_24h)
        )
        recent = recent_result.scalar() or 0

        # Pending invoices
        pending_invoices_result = await self.db.execute(
            select(func.count(EDIInvoice.id)).where(EDIInvoice.status == EDIInvoiceStatus.PENDING)
        )
        pending_invoices = pending_invoices_result.scalar() or 0

        # Disputed invoices
        disputed_invoices_result = await self.db.execute(
            select(func.count(EDIInvoice.id)).where(EDIInvoice.status == EDIInvoiceStatus.DISPUTED)
        )
        disputed_invoices = disputed_invoices_result.scalar() or 0

        # Total invoice amount
        invoice_amount_result = await self.db.execute(
            select(func.coalesce(func.sum(EDIInvoice.total_amount), 0))
        )
        invoice_amount = invoice_amount_result.scalar() or Decimal("0")

        # By message type
        type_result = await self.db.execute(
            select(EDITransaction.message_type, func.count(EDITransaction.id)).group_by(
                EDITransaction.message_type
            )
        )
        by_type = {
            str(row[0].value if hasattr(row[0], "value") else row[0] or "unknown"): row[1]
            for row in type_result.all()
        }

        return {
            "total_transactions": total,
            "pending_transactions": pending,
            "failed_transactions": failed,
            "successful_transactions": total - pending - failed,
            "pending_invoices": pending_invoices,
            "disputed_invoices": disputed_invoices,
            "total_invoice_amount": str(invoice_amount),
            "last_24h_transactions": recent,
            "by_message_type": by_type,
        }
