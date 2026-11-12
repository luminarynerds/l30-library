# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.acquisition import PurchaseOrder, PurchaseOrderItem
from app.models.edi import EDIInvoice, EDIInvoiceStatus, VendorEDIProfile
from app.models.user import User

logger = get_logger(__name__)


@dataclass
class LineItemMatch:
    invoice_line_number: int
    po_item_id: int | None = None
    isbn: str | None = None
    title: str | None = None
    invoice_quantity: int = 0
    po_quantity: int = 0
    invoice_unit_price: Decimal | None = None
    po_unit_price: Decimal | None = None
    invoice_line_total: Decimal | None = None
    po_line_total: Decimal | None = None
    match_status: str = "unmatched"  # matched, price_variance, quantity_variance, unmatched
    variance_amount: Decimal | None = None
    variance_reason: str | None = None


@dataclass
class ReconciliationResult:
    invoice_id: int
    purchase_order_id: int | None = None
    po_number: str | None = None
    status: str = "unmatched"  # matched, partial_match, disputed, unmatched
    matched_items: int = 0
    total_items: int = 0
    po_total: Decimal | None = None
    invoice_total: Decimal | None = None
    variance_amount: Decimal | None = None
    variance_percent: float | None = None
    line_matches: list[LineItemMatch] = field(default_factory=list)
    discrepancies: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class EDIReconciliation:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def reconcile_invoice(
        self,
        invoice_id: int
    ) -> ReconciliationResult:
        # Get invoice with line items
        result = await self.db.execute(
            select(EDIInvoice)
            .where(EDIInvoice.id == invoice_id)
            .options(selectinload(EDIInvoice.vendor))
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            return ReconciliationResult(
                invoice_id=invoice_id,
                status="error",
                discrepancies=[{"error": "Invoice not found"}]
            )

        # Parse invoice line items
        invoice_items = []
        if invoice.line_items:
            try:
                invoice_items = json.loads(invoice.line_items)
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse invoice line items JSON for invoice %s: %s", invoice_id, e)

        # Initialize result
        rec_result = ReconciliationResult(
            invoice_id=invoice_id,
            purchase_order_id=invoice.purchase_order_id,
            invoice_total=invoice.total_amount,
            total_items=len(invoice_items)
        )

        # If no PO linked, try to find one
        po = None
        if invoice.purchase_order_id:
            po_result = await self.db.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.id == invoice.purchase_order_id)
                .options(selectinload(PurchaseOrder.items))
            )
            po = po_result.scalar_one_or_none()

        if not po:
            # Try to find PO by vendor and approximate total
            po = await self._find_matching_po(invoice)

        if not po:
            rec_result.status = "unmatched"
            rec_result.discrepancies.append({
                "type": "no_po",
                "message": "No matching purchase order found"
            })
            rec_result.recommendations.append(
                "Manually link this invoice to a purchase order"
            )
            return rec_result

        rec_result.purchase_order_id = po.id
        rec_result.po_number = po.po_number
        rec_result.po_total = po.total_amount

        # Calculate overall variance
        if invoice.total_amount and po.total_amount:
            rec_result.variance_amount = invoice.total_amount - po.total_amount
            if po.total_amount > 0:
                rec_result.variance_percent = float(
                    (rec_result.variance_amount / po.total_amount) * 100
                )

        # Match line items
        rec_result.line_matches = await self._match_line_items(invoice_items, po.items)

        # Count matches
        for match in rec_result.line_matches:
            if match.match_status == "matched":
                rec_result.matched_items += 1
            elif match.match_status in ["price_variance", "quantity_variance"]:
                rec_result.discrepancies.append({
                    "type": match.match_status,
                    "line_number": match.invoice_line_number,
                    "isbn": match.isbn,
                    "title": match.title,
                    "variance": str(match.variance_amount) if match.variance_amount else None,
                    "reason": match.variance_reason
                })
            else:
                rec_result.discrepancies.append({
                    "type": "unmatched_item",
                    "line_number": match.invoice_line_number,
                    "isbn": match.isbn,
                    "title": match.title,
                    "message": "No matching PO line item found"
                })

        # Determine overall status
        if rec_result.matched_items == rec_result.total_items and not rec_result.discrepancies:
            rec_result.status = "matched"
        elif rec_result.matched_items > 0:
            rec_result.status = "partial_match"
        elif rec_result.discrepancies:
            rec_result.status = "disputed"
        else:
            rec_result.status = "unmatched"

        # Add recommendations
        rec_result.recommendations = self._generate_recommendations(rec_result)

        # Update invoice record
        invoice.purchase_order_id = po.id
        invoice.po_total = po.total_amount
        invoice.variance_amount = rec_result.variance_amount
        invoice.matched_line_items = rec_result.matched_items
        invoice.variance_reason = self._summarize_discrepancies(rec_result.discrepancies)

        if rec_result.status == "matched":
            invoice.status = EDIInvoiceStatus.MATCHED
        elif rec_result.status == "partial_match":
            invoice.status = EDIInvoiceStatus.PARTIAL_MATCH
        else:
            invoice.status = EDIInvoiceStatus.DISPUTED

        await self.db.commit()

        return rec_result

    async def _find_matching_po(self, invoice: EDIInvoice) -> PurchaseOrder | None:
        if not invoice.vendor_id:
            return None

        # Look for PO from same vendor with similar total
        tolerance = Decimal("0.10")  # 10%

        query = select(PurchaseOrder).where(
            PurchaseOrder.vendor_id == invoice.vendor_id
        ).options(selectinload(PurchaseOrder.items))

        result = await self.db.execute(query)
        candidates = result.scalars().all()

        for po in candidates:
            if not po.total_amount or not invoice.total_amount:
                continue

            # Check if totals are within tolerance
            variance = abs(invoice.total_amount - po.total_amount)
            if po.total_amount > 0:
                variance_pct = variance / po.total_amount
                if variance_pct <= tolerance:
                    return po

        return None

    async def _match_line_items(
        self,
        invoice_items: list[dict],
        po_items: list[PurchaseOrderItem]
    ) -> list[LineItemMatch]:
        matches = []

        # Build ISBN lookup for PO items
        po_by_isbn = {}
        po_by_id = {}
        for item in po_items:
            if item.isbn:
                clean_isbn = item.isbn.replace("-", "").replace(" ", "")
                po_by_isbn[clean_isbn] = item
            po_by_id[item.id] = item

        # Track which PO items have been matched
        matched_po_items = set()

        for idx, inv_item in enumerate(invoice_items, start=1):
            match = LineItemMatch(
                invoice_line_number=inv_item.get("line_number", idx),
                isbn=inv_item.get("isbn"),
                title=inv_item.get("title"),
                invoice_quantity=inv_item.get("quantity", 0),
                invoice_unit_price=self._to_decimal(inv_item.get("unit_price")),
                invoice_line_total=self._to_decimal(inv_item.get("line_total"))
            )

            # Try to find matching PO item
            po_item = None

            # First try by ISBN
            if match.isbn:
                clean_isbn = match.isbn.replace("-", "").replace(" ", "")
                po_item = po_by_isbn.get(clean_isbn)

            # Try by explicit PO item ID if present
            if not po_item and inv_item.get("po_item_id"):
                po_item = po_by_id.get(inv_item["po_item_id"])

            if po_item and po_item.id not in matched_po_items:
                matched_po_items.add(po_item.id)
                match.po_item_id = po_item.id
                match.po_quantity = po_item.quantity
                match.po_unit_price = po_item.unit_price
                match.po_line_total = po_item.line_total

                # Check for variances
                variances = []

                # Quantity variance
                if match.invoice_quantity != match.po_quantity:
                    variances.append(
                        f"Quantity: invoice={match.invoice_quantity}, PO={match.po_quantity}"
                    )

                # Price variance
                if match.invoice_unit_price and match.po_unit_price:
                    price_diff = abs(match.invoice_unit_price - match.po_unit_price)
                    if price_diff > Decimal("0.01"):
                        variances.append(
                            f"Unit price: invoice=${match.invoice_unit_price}, PO=${match.po_unit_price}"
                        )

                if variances:
                    match.match_status = "price_variance" if "price" in str(variances) else "quantity_variance"
                    match.variance_reason = "; ".join(variances)

                    # Calculate variance amount
                    if match.invoice_line_total and match.po_line_total:
                        match.variance_amount = match.invoice_line_total - match.po_line_total
                else:
                    match.match_status = "matched"
            else:
                match.match_status = "unmatched"

            matches.append(match)

        return matches

    def _to_decimal(self, value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _generate_recommendations(self, result: ReconciliationResult) -> list[str]:
        recommendations = []

        if result.status == "matched":
            recommendations.append("Invoice matches PO - recommend approval")
        elif result.status == "partial_match":
            if result.variance_percent and abs(result.variance_percent) < 5:
                recommendations.append(
                    "Minor variance detected - may qualify for auto-approval"
                )
            else:
                recommendations.append("Review unmatched items before approval")

        if result.discrepancies:
            price_variances = [d for d in result.discrepancies if d.get("type") == "price_variance"]
            if price_variances:
                recommendations.append(
                    f"Review {len(price_variances)} price discrepancies"
                )

            unmatched = [d for d in result.discrepancies if d.get("type") == "unmatched_item"]
            if unmatched:
                recommendations.append(
                    f"Investigate {len(unmatched)} unmatched invoice items"
                )

        if result.variance_amount and result.variance_amount > 0:
            recommendations.append(
                f"Invoice exceeds PO by ${result.variance_amount:.2f}"
            )
        elif result.variance_amount and result.variance_amount < 0:
            recommendations.append(
                f"Invoice is ${abs(result.variance_amount):.2f} less than PO"
            )

        return recommendations

    def _summarize_discrepancies(self, discrepancies: list[dict]) -> str | None:
        if not discrepancies:
            return None

        summary_parts = []
        types = {}
        for d in discrepancies:
            t = d.get("type", "unknown")
            types[t] = types.get(t, 0) + 1

        for t, count in types.items():
            summary_parts.append(f"{count} {t.replace('_', ' ')}")

        return ", ".join(summary_parts)

    async def batch_reconcile(
        self,
        invoice_ids: list[int] | None = None
    ) -> dict[str, Any]:
        results = {
            "total_processed": 0,
            "matched": 0,
            "partial_match": 0,
            "disputed": 0,
            "errors": 0,
            "results": []
        }

        # Get invoices to process
        query = select(EDIInvoice)

        if invoice_ids:
            query = query.where(EDIInvoice.id.in_(invoice_ids))
        else:
            query = query.where(EDIInvoice.status == EDIInvoiceStatus.PENDING)

        invoice_result = await self.db.execute(query)
        invoices = invoice_result.scalars().all()

        for invoice in invoices:
            try:
                rec_result = await self.reconcile_invoice(invoice.id)
                results["total_processed"] += 1

                if rec_result.status == "matched":
                    results["matched"] += 1
                elif rec_result.status == "partial_match":
                    results["partial_match"] += 1
                elif rec_result.status in ["disputed", "unmatched"]:
                    results["disputed"] += 1

                results["results"].append({
                    "invoice_id": rec_result.invoice_id,
                    "purchase_order_id": rec_result.purchase_order_id,
                    "status": rec_result.status,
                    "matched_items": rec_result.matched_items,
                    "total_items": rec_result.total_items,
                    "variance_amount": str(rec_result.variance_amount) if rec_result.variance_amount else None,
                    "discrepancies": len(rec_result.discrepancies)
                })

            except Exception as e:
                logger.exception(f"Error reconciling invoice {invoice.id}: {e}")
                results["errors"] += 1

        return results

    async def auto_approve_invoices(
        self,
        vendor_id: int | None = None
    ) -> dict[str, Any]:
        results = {
            "processed": 0,
            "approved": 0,
            "skipped": 0,
            "details": []
        }

        # Get matched invoices
        query = select(EDIInvoice).where(
            EDIInvoice.status.in_([EDIInvoiceStatus.MATCHED, EDIInvoiceStatus.PARTIAL_MATCH])
        )

        if vendor_id:
            query = query.where(EDIInvoice.vendor_id == vendor_id)

        invoice_result = await self.db.execute(
            query.options(selectinload(EDIInvoice.vendor))
        )
        invoices = invoice_result.scalars().all()

        for invoice in invoices:
            results["processed"] += 1

            # Get vendor EDI profile for tolerance
            profile_result = await self.db.execute(
                select(VendorEDIProfile)
                .where(VendorEDIProfile.vendor_id == invoice.vendor_id)
            )
            profile = profile_result.scalar_one_or_none()

            if not profile or not profile.auto_approve_invoices:
                results["skipped"] += 1
                results["details"].append({
                    "invoice_id": invoice.id,
                    "status": "skipped",
                    "reason": "Auto-approval not enabled"
                })
                continue

            # Check variance against tolerance
            tolerance_pct = float(profile.invoice_tolerance_percent or Decimal("5.00"))

            if invoice.variance_amount and invoice.po_total:
                variance_pct = abs(float(invoice.variance_amount / invoice.po_total) * 100)
                if variance_pct > tolerance_pct:
                    results["skipped"] += 1
                    results["details"].append({
                        "invoice_id": invoice.id,
                        "status": "skipped",
                        "reason": f"Variance {variance_pct:.2f}% exceeds tolerance {tolerance_pct}%"
                    })
                    continue

            # Approve invoice
            invoice.status = EDIInvoiceStatus.APPROVED
            invoice.approved_at = datetime.now()
            invoice.notes = f"Auto-approved within {tolerance_pct}% tolerance"

            results["approved"] += 1
            results["details"].append({
                "invoice_id": invoice.id,
                "status": "approved",
                "variance_percent": f"{variance_pct:.2f}%" if 'variance_pct' in dir() else "0%"
            })

        await self.db.commit()
        return results

    async def approve_invoice(
        self,
        invoice_id: int,
        user: User,
        notes: str | None = None
    ) -> tuple[bool, str]:
        result = await self.db.execute(
            select(EDIInvoice).where(EDIInvoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            return False, "Invoice not found"

        if invoice.status == EDIInvoiceStatus.APPROVED:
            return False, "Invoice already approved"

        if invoice.status == EDIInvoiceStatus.PAID:
            return False, "Invoice already paid"

        invoice.status = EDIInvoiceStatus.APPROVED
        invoice.approved_by_id = user.id
        invoice.approved_at = datetime.now()
        if notes:
            invoice.notes = notes

        await self.db.commit()
        return True, "Invoice approved"

    async def dispute_invoice(
        self,
        invoice_id: int,
        reason: str
    ) -> tuple[bool, str]:
        result = await self.db.execute(
            select(EDIInvoice).where(EDIInvoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            return False, "Invoice not found"

        if invoice.status in [EDIInvoiceStatus.APPROVED, EDIInvoiceStatus.PAID]:
            return False, "Cannot dispute approved/paid invoice"

        invoice.status = EDIInvoiceStatus.DISPUTED
        invoice.rejection_reason = reason
        invoice.variance_reason = reason

        await self.db.commit()
        return True, "Invoice marked as disputed"
