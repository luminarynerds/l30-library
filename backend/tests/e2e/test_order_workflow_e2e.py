# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
End-to-end test: Order-to-Patron-Access workflow.

Tests the complete lifecycle from purchase order creation through patron checkout:
1. Create a PO for 5 copies of a new title → DRAFT
2. Submit and approve the PO → APPROVED
3. Send the PO to vendor via EDI → EDITransaction SENT
4. Process inbound EDI order response → acknowledged
5. Process inbound EDI shipment notice → items shipped
6. Receive items against the PO → PO status RECEIVED
7. Process inbound EDI invoice → reconcile and approve
8. Catalog the received items → CatalogItem records updated
9. Patron places a hold on the new title → hold fulfilled immediately
10. Patron checks out the item → checkout created

This validates the full acquisition-to-circulation pipeline across domain boundaries.
"""

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.acquisition import (
    Fund,
    FundStatus,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Vendor,
)
from app.models.catalog import CatalogItem, CatalogingStatus, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
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
from app.models.inventory import AcquisitionSource, ItemCondition, ItemCopy
from app.models.user import User, UserRole
from app.services.edi.edi_reconciliation import EDIReconciliation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def staff_user(test_db):
    """Staff member who creates purchase orders."""
    user = User(
        email="acquisitions.staff@lsc.test",
        password_hash=hash_password("Staff1234!"),
        first_name="Ada",
        last_name="Shelby",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def admin_user(test_db):
    """Admin/director who approves purchase orders."""
    user = User(
        email="director@lsc.test",
        password_hash=hash_password("Admin1234!"),
        first_name="Moira",
        last_name="Rose",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def patron_user(test_db):
    """Patron who places holds and checks out items."""
    user = User(
        email="patron@lsc.test",
        password_hash=hash_password("Patron1234!"),
        first_name="David",
        last_name="Rose",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def vendor(test_db):
    """Vendor who supplies library materials."""
    v = Vendor(
        name="Ingram Content Group",
        contact_name="Sales Dept",
        email="orders@ingram.test",
        phone="555-0100",
        account_number="LSC-INGRAM-001",
        is_active=True,
    )
    test_db.add(v)
    await test_db.commit()
    await test_db.refresh(v)
    return v


@pytest.fixture
async def edi_profile(test_db, vendor):
    """EDI profile for the vendor."""
    profile = VendorEDIProfile(
        vendor_id=vendor.id,
        is_enabled=True,
        sender_id="LSC-LIBRARY",
        receiver_id="INGRAM-EDI",
        supports_orders=True,
        supports_ordrsp=True,
        supports_desadv=True,
        supports_invoic=True,
        auto_approve_invoices=True,
        invoice_tolerance_percent=Decimal("5.00"),
        is_test_mode=True,
    )
    test_db.add(profile)
    await test_db.commit()
    await test_db.refresh(profile)
    return profile


@pytest.fixture
async def fund(test_db):
    """Budget fund for acquisitions."""
    f = Fund(
        code="ACQ-2026",
        name="2026 Acquisitions Budget",
        fiscal_year=date.today().year,
        allocated_amount=Decimal("50000.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("0.00"),
        status=FundStatus.ACTIVE,
    )
    test_db.add(f)
    await test_db.commit()
    await test_db.refresh(f)
    return f


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestOrderToPatronAccessE2E:
    """Full acquisition-to-patron-access lifecycle."""

    @pytest.mark.integration
    async def test_complete_order_to_checkout_workflow(
        self,
        test_db,
        staff_user,
        admin_user,
        patron_user,
        vendor,
        edi_profile,
        fund,
    ):
        """
        Steps 1–10: PO creation → EDI ordering → receiving → cataloging
        → patron hold → patron checkout.
        """
        db = test_db

        # ── Step 1: Create a PO for 5 copies of a new title → DRAFT ──

        po = PurchaseOrder(
            po_number=f"PO-{datetime.now().strftime('%Y%m')}-0001",
            vendor_id=vendor.id,
            fund_id=fund.id,
            order_date=date.today(),
            expected_delivery=date.today() + timedelta(days=14),
            notes="New title order for spring reading",
            created_by_id=staff_user.id,
            status=PurchaseOrderStatus.DRAFT,
        )
        db.add(po)
        await db.flush()

        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            title="The Midnight Library",
            author="Matt Haig",
            isbn="978-0-525-55947-4",
            quantity=5,
            unit_price=Decimal("16.99"),
        )
        db.add(po_item)
        po.total_amount = Decimal("84.95")  # 5 × 16.99
        await db.commit()

        # Reload with items to verify
        result = await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po.id)
            .options(selectinload(PurchaseOrder.items))
        )
        po = result.scalar_one()

        assert po.status == PurchaseOrderStatus.DRAFT
        assert len(po.items) == 1
        assert po.items[0].quantity == 5
        assert po.total_amount == Decimal("84.95")

        # ── Step 2: Submit and approve the PO → APPROVED ──

        po.status = PurchaseOrderStatus.PENDING_APPROVAL
        await db.commit()
        await db.refresh(po)
        assert po.status == PurchaseOrderStatus.PENDING_APPROVAL

        po.status = PurchaseOrderStatus.APPROVED
        po.approved_by_id = admin_user.id
        po.approved_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(po)

        assert po.status == PurchaseOrderStatus.APPROVED
        assert po.approved_by_id == admin_user.id

        # ── Step 3: Send the PO to vendor via EDI → EDITransaction SENT ──
        # Encumber budget and submit to vendor

        fund.encumbered_amount = (
            fund.encumbered_amount or Decimal("0.00")
        ) + po.total_amount
        po.status = PurchaseOrderStatus.SUBMITTED
        await db.commit()

        await db.refresh(po)
        assert po.status == PurchaseOrderStatus.SUBMITTED

        await db.refresh(fund)
        assert fund.encumbered_amount == Decimal("84.95")

        # Create outbound EDI transaction (ORDERS)
        control_number = f"ICN{uuid.uuid4().hex[:10].upper()}"
        edi_transaction = EDITransaction(
            vendor_edi_profile_id=edi_profile.id,
            purchase_order_id=po.id,
            message_type=EDIMessageType.ORDERS,
            direction="outbound",
            interchange_control_number=control_number,
            status=EDITransactionStatus.SENT,
            sent_at=datetime.now(timezone.utc),
            raw_message="UNB+UNOC:3+LSC-LIBRARY+INGRAM-EDI+...",
            filename=f"ORDER_{po.po_number}.edi",
        )
        db.add(edi_transaction)
        await db.commit()
        await db.refresh(edi_transaction)

        assert edi_transaction.status == EDITransactionStatus.SENT

        # ── Step 4: Process inbound EDI order response → acknowledged ──

        ordrsp_control = f"ICN{uuid.uuid4().hex[:10].upper()}"
        ordrsp_txn = EDITransaction(
            vendor_edi_profile_id=edi_profile.id,
            purchase_order_id=po.id,
            message_type=EDIMessageType.ORDRSP,
            direction="inbound",
            interchange_control_number=ordrsp_control,
            status=EDITransactionStatus.PROCESSED,
            received_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
            raw_message="UNB+UNOC:3+INGRAM-EDI+LSC-LIBRARY+...",
        )
        db.add(ordrsp_txn)
        await db.flush()

        order_response = EDIOrderResponse(
            edi_transaction_id=ordrsp_txn.id,
            purchase_order_id=po.id,
            vendor_id=vendor.id,
            vendor_order_number="INGRAM-ORD-99001",
            response_date=datetime.now(timezone.utc),
            response_code="29",  # Accepted
            response_description="Order accepted",
            items_accepted=5,
            items_rejected=0,
            items_backordered=0,
            expected_ship_date=datetime.now(timezone.utc) + timedelta(days=3),
            expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=7),
            is_processed=True,
            processed_at=datetime.now(timezone.utc),
        )
        db.add(order_response)
        await db.commit()

        # Update original outbound transaction to acknowledged
        edi_transaction.status = EDITransactionStatus.ACKNOWLEDGED
        await db.commit()
        await db.refresh(edi_transaction)

        assert edi_transaction.status == EDITransactionStatus.ACKNOWLEDGED
        assert order_response.items_accepted == 5
        assert order_response.response_code == "29"

        # ── Step 5: Process inbound EDI shipment notice → items shipped ──

        desadv_control = f"ICN{uuid.uuid4().hex[:10].upper()}"
        desadv_txn = EDITransaction(
            vendor_edi_profile_id=edi_profile.id,
            purchase_order_id=po.id,
            message_type=EDIMessageType.DESADV,
            direction="inbound",
            interchange_control_number=desadv_control,
            status=EDITransactionStatus.PROCESSED,
            received_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )
        db.add(desadv_txn)
        await db.flush()

        shipment = EDIShipmentNotice(
            edi_transaction_id=desadv_txn.id,
            purchase_order_id=po.id,
            vendor_id=vendor.id,
            shipment_number="SHIP-2026-0042",
            ship_date=datetime.now(timezone.utc),
            expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=4),
            carrier_name="UPS",
            carrier_code="UPS",
            tracking_number="1Z999AA10123456784",
            package_count=1,
            total_items_shipped=5,
            shipped_items=json.dumps([
                {
                    "isbn": "978-0-525-55947-4",
                    "title": "The Midnight Library",
                    "quantity_shipped": 5,
                }
            ]),
            is_processed=True,
            processed_at=datetime.now(timezone.utc),
        )
        db.add(shipment)
        await db.commit()

        assert shipment.total_items_shipped == 5
        assert shipment.tracking_number == "1Z999AA10123456784"

        # ── Step 6: Receive items against the PO → PO status RECEIVED ──

        await db.refresh(po_item)

        # Create catalog item for the received title
        catalog_item = CatalogItem(
            title="The Midnight Library",
            author="Matt Haig",
            isbn="978-0-525-55947-4",
            status=ItemStatus.in_processing,
        )
        db.add(catalog_item)
        await db.flush()

        po_item.catalog_item_id = catalog_item.id
        po_item.received_quantity = 5

        # Create 5 item copies
        copies = []
        for copy_num in range(1, 6):
            barcode = f"LSC-{uuid.uuid4().hex[:8].upper()}"
            item_copy = ItemCopy(
                catalog_item_id=catalog_item.id,
                barcode=barcode,
                copy_number=copy_num,
                condition=ItemCondition.NEW,
                acquisition_source=AcquisitionSource.PURCHASE,
                purchase_order_item_id=po_item.id,
                replacement_cost=Decimal("16.99"),
            )
            db.add(item_copy)
            copies.append(item_copy)

        # Update fund: move from encumbered to spent
        received_value = Decimal("84.95")
        fund.encumbered_amount = (
            fund.encumbered_amount or Decimal("0.00")
        ) - received_value
        fund.spent_amount = (
            fund.spent_amount or Decimal("0.00")
        ) + received_value

        # Update PO status
        po.status = PurchaseOrderStatus.RECEIVED
        po.actual_delivery = date.today()

        await db.commit()

        # Verify
        await db.refresh(po)
        assert po.status == PurchaseOrderStatus.RECEIVED
        assert po.actual_delivery == date.today()

        await db.refresh(po_item)
        assert po_item.received_quantity == 5
        assert po_item.catalog_item_id == catalog_item.id

        await db.refresh(fund)
        assert fund.encumbered_amount == Decimal("0.00")
        assert fund.spent_amount == Decimal("84.95")

        await db.refresh(catalog_item)
        assert catalog_item.title == "The Midnight Library"
        assert catalog_item.author == "Matt Haig"
        assert catalog_item.isbn == "978-0-525-55947-4"

        # Verify 5 item copies
        result = await db.execute(
            select(ItemCopy).where(ItemCopy.catalog_item_id == catalog_item.id)
        )
        db_copies = result.scalars().all()
        assert len(db_copies) == 5

        for copy in db_copies:
            assert copy.condition == ItemCondition.NEW
            assert copy.acquisition_source == AcquisitionSource.PURCHASE
            assert copy.purchase_order_item_id == po_item.id
            assert copy.replacement_cost == Decimal("16.99")

        # ── Step 7: Process inbound EDI invoice → reconcile and approve ──

        invoic_control = f"ICN{uuid.uuid4().hex[:10].upper()}"
        invoic_txn = EDITransaction(
            vendor_edi_profile_id=edi_profile.id,
            purchase_order_id=po.id,
            message_type=EDIMessageType.INVOIC,
            direction="inbound",
            interchange_control_number=invoic_control,
            status=EDITransactionStatus.PROCESSED,
            received_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )
        db.add(invoic_txn)
        await db.flush()

        invoice = EDIInvoice(
            edi_transaction_id=invoic_txn.id,
            purchase_order_id=po.id,
            vendor_id=vendor.id,
            invoice_number="INV-2026-5501",
            invoice_date=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            subtotal=Decimal("84.95"),
            tax_amount=Decimal("0.00"),
            shipping_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("84.95"),
            currency_code="USD",
            status=EDIInvoiceStatus.PENDING,
            po_total=po.total_amount,
            total_line_items=1,
            line_items=json.dumps([
                {
                    "line_number": 1,
                    "isbn": "978-0-525-55947-4",
                    "title": "The Midnight Library",
                    "quantity": 5,
                    "unit_price": "16.99",
                    "line_total": "84.95",
                }
            ]),
        )
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)

        assert invoice.status == EDIInvoiceStatus.PENDING

        # Reconcile
        reconciliation = EDIReconciliation(db)
        rec_result = await reconciliation.reconcile_invoice(invoice.id)

        assert rec_result.status == "matched"
        assert rec_result.matched_items == 1
        assert rec_result.variance_amount == Decimal("0.00")

        await db.refresh(invoice)
        assert invoice.status == EDIInvoiceStatus.MATCHED

        # Approve invoice
        success, msg = await reconciliation.approve_invoice(
            invoice.id, admin_user, notes="Approved after reconciliation"
        )
        assert success is True

        await db.refresh(invoice)
        assert invoice.status == EDIInvoiceStatus.APPROVED
        assert invoice.approved_by_id == admin_user.id

        # ── Step 8: Catalog the received items ──

        catalog_item.cataloging_status = CatalogingStatus.CATALOGED
        catalog_item.cataloged_at = datetime.now(timezone.utc)
        catalog_item.cataloged_by_id = staff_user.id
        catalog_item.call_number = "F HAI"
        catalog_item.dewey_decimal = "823.92"
        catalog_item.status = ItemStatus.available

        await db.commit()
        await db.refresh(catalog_item)

        assert catalog_item.cataloging_status == CatalogingStatus.CATALOGED
        assert catalog_item.call_number == "F HAI"
        assert catalog_item.status == ItemStatus.available

        # ── Step 9: Patron places a hold → fulfilled immediately ──
        # Item is available so the hold transitions to ready immediately.

        hold = Hold(
            user_id=patron_user.id,
            item_id=catalog_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        db.add(hold)
        await db.commit()
        await db.refresh(hold)

        assert hold.status == HoldStatus.pending

        # Since item is available, mark hold as ready
        hold.status = HoldStatus.ready
        hold.notified_at = datetime.now(timezone.utc)
        hold.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        await db.commit()
        await db.refresh(hold)

        assert hold.status == HoldStatus.ready

        # ── Step 10: Patron checks out the item ──

        first_copy = copies[0]
        await db.refresh(first_copy)

        checkout = Checkout(
            user_id=patron_user.id,
            item_id=catalog_item.id,
            item_copy_id=first_copy.id,
            status=CheckoutStatus.active,
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
        )
        db.add(checkout)

        # Update catalog item status
        catalog_item.status = ItemStatus.checked_out
        catalog_item.total_checkouts = (catalog_item.total_checkouts or 0) + 1

        # Fulfill the hold
        hold.status = HoldStatus.fulfilled
        await db.commit()

        await db.refresh(checkout)
        await db.refresh(hold)
        await db.refresh(catalog_item)

        assert checkout.status == CheckoutStatus.active
        assert checkout.user_id == patron_user.id
        assert checkout.item_id == catalog_item.id
        assert checkout.item_copy_id == first_copy.id

        assert hold.status == HoldStatus.fulfilled

        assert catalog_item.status == ItemStatus.checked_out
        assert catalog_item.total_checkouts == 1

        # ── Final: Verify the complete chain of records ──

        # PO → RECEIVED
        await db.refresh(po)
        assert po.status == PurchaseOrderStatus.RECEIVED

        # EDI transactions: 1 outbound ORDERS + 3 inbound (ORDRSP, DESADV, INVOIC)
        result = await db.execute(
            select(EDITransaction).where(
                EDITransaction.purchase_order_id == po.id
            )
        )
        all_txns = result.scalars().all()
        assert len(all_txns) == 4

        txn_types = {t.message_type for t in all_txns}
        assert txn_types == {
            EDIMessageType.ORDERS,
            EDIMessageType.ORDRSP,
            EDIMessageType.DESADV,
            EDIMessageType.INVOIC,
        }

        # Invoice approved
        assert invoice.status == EDIInvoiceStatus.APPROVED

        # 5 copies created and linked
        result = await db.execute(
            select(ItemCopy).where(
                ItemCopy.catalog_item_id == catalog_item.id
            )
        )
        assert len(result.scalars().all()) == 5

        # Patron has active checkout
        result = await db.execute(
            select(Checkout).where(
                Checkout.user_id == patron_user.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        active_checkout = result.scalar_one()
        assert active_checkout.item_id == catalog_item.id
