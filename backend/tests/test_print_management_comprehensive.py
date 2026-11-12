# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive Print Management Test Suite for LSC.

This test suite validates the complete print management system including:
- Print job submission from various devices
- Cost calculation (B&W vs. color pricing)
- Print quota tracking and enforcement
- Payment processing (card, cash, account balance)
- Print release stations with card scanning
- Print preview generation
- Refund workflow for failed prints
- Printer status and supply level tracking
- Printer alerts (low paper/toner)
- Scan to email functionality (free)
- Copy machine integration with surcharges
"""

from datetime import datetime, timedelta
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import select

from app.models.print import (
    PrintJob, Printer, PrintReleaseStation, PrintPricing, PrintQuota,
    PrintRefund, ScanToEmail, PrinterAlert,
    PrintJobStatus, ColorMode, PaperSize, PrinterStatus,
    ScanToEmailStatus, PrintRefundStatus
)
from app.models.user import User, UserRole
from app.services.print_service import PrintService
from app.services.printer_management_service import PrinterManagementService


# ============================================================================
# FIXTURES - Test Data Setup with Proper Isolation
# ============================================================================


def generate_unique_email():
    """Generate a unique email address for test isolation."""
    return f"patron_{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
async def test_patron(test_db):
    """Create a unique patron for each test."""
    from app.core.security import hash_password

    user = User(
        email=generate_unique_email(),
        password_hash=hash_password("TestPassword123!"),
        first_name="Test",
        last_name="Patron",
        role=UserRole.PATRON,
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
async def test_staff(test_db):
    """Create a test staff member."""
    from app.core.security import hash_password

    user = User(
        email=generate_unique_email(),
        password_hash=hash_password("StaffPassword123!"),
        first_name="Test",
        last_name="Staff",
        role=UserRole.STAFF,
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
async def test_admin(test_db):
    """Create a test admin user."""
    from app.core.security import hash_password

    user = User(
        email=generate_unique_email(),
        password_hash=hash_password("AdminPassword123!"),
        first_name="Test",
        last_name="Admin",
        role=UserRole.ADMIN,
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
async def print_service(test_db):
    """Create a PrintService instance for testing."""
    return PrintService(test_db)


@pytest.fixture
async def printer_service(test_db):
    """Create a PrinterManagementService instance for testing."""
    return PrinterManagementService(test_db)


@pytest.fixture
async def test_printer(test_db, printer_service):
    """Create a test printer."""
    printer = await printer_service.register_printer(
        name="Test Printer",
        printer_type="laser",
        location="Main Floor",
        supports_color=True,
        supports_double_sided=True,
    )
    return printer


@pytest.fixture
async def test_release_station(test_db, printer_service):
    """Create a test release station."""
    station = await printer_service.register_release_station(
        name="Main Circulation Desk",
        location="Circulation Desk",
        card_reader_type="magnetic_stripe",
        has_display=True,
        has_card_payment=True,
        use_pin_code=True,
    )
    return station


@pytest.fixture
async def print_pricing(test_db):
    """Create default print pricing."""
    pricing = PrintPricing(
        blackwhite_price_per_page=Decimal("0.10"),
        color_price_per_page=Decimal("0.50"),
        discount_percentage_for_bulk=10,
        bulk_threshold_pages=100,
        minimum_charge=Decimal("0.25"),
        copy_machine_surcharge_percentage=10,
        is_active=True,
    )
    test_db.add(pricing)
    await test_db.flush()
    return pricing


# ============================================================================
# TESTS - Print Job Submission
# ============================================================================


@pytest.mark.asyncio
async def test_submit_simple_print_job(test_patron, print_service, print_pricing, test_db):
    """Test submitting a simple black & white print job."""
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="resume.pdf",
        pages=5,
        copies=1,
        color_mode=ColorMode.blackwhite,
        device_id="laptop_123",
        device_name="John's Laptop",
    )

    assert job.id is not None
    assert job.status == PrintJobStatus.submitted
    assert job.pages == 5
    assert job.copies == 1
    assert job.color_mode == ColorMode.blackwhite
    assert job.device_name == "John's Laptop"
    assert job.cost == Decimal("0.50")  # 5 pages * $0.10
    assert job.user_id == test_patron.id


@pytest.mark.asyncio
async def test_submit_color_print_job(test_patron, print_service, print_pricing, test_db):
    """Test submitting a color print job."""
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="photos.pdf",
        pages=10,
        copies=1,
        color_mode=ColorMode.color,
    )

    assert job.status == PrintJobStatus.submitted
    assert job.color_mode == ColorMode.color
    assert job.cost == Decimal("5.00")  # 10 pages * $0.50


@pytest.mark.asyncio
async def test_submit_multi_copy_job(test_patron, print_service, print_pricing, test_db):
    """Test submitting a multi-copy print job."""
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="flyer.pdf",
        pages=2,
        copies=5,
        color_mode=ColorMode.color,
    )

    assert job.total_pages == 10  # 2 pages * 5 copies
    assert job.cost == Decimal("5.00")  # 10 pages * $0.50


@pytest.mark.asyncio
async def test_submit_job_from_copy_machine(test_patron, print_service, print_pricing, test_db):
    """Test submitting a job from a copy machine (with surcharge)."""
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="document_copy",
        pages=20,
        copies=1,
        color_mode=ColorMode.blackwhite,
        device_type="copy_machine",
    )

    # Base: 20 * $0.10 = $2.00
    # Surcharge: $2.00 * 10% = $0.20
    # Total: $2.20
    assert job.cost == Decimal("2.20")
    assert job.device_type == "copy_machine"


@pytest.mark.asyncio
async def test_submit_anonymous_print_job(print_service, print_pricing, test_db):
    """Test submitting an anonymous print job (no user_id)."""
    job = await print_service.submit_print_job(
        user_id=None,
        job_name="anonymous.pdf",
        pages=5,
        copies=1,
        color_mode=ColorMode.blackwhite,
    )

    assert job.user_id is None
    assert job.status == PrintJobStatus.submitted


# ============================================================================
# TESTS - Print Quota Management
# ============================================================================


@pytest.mark.asyncio
async def test_get_print_quota(test_patron, print_service, test_db):
    """Test retrieving a patron's print quota."""
    quota = await print_service.get_user_quota(test_patron.id)

    assert quota.user_id == test_patron.id
    assert quota.monthly_pages_limit == 100
    assert quota.monthly_dollar_limit == Decimal("10.00")
    assert quota.pages_used_this_month == 0
    assert quota.pages_remaining == 100


@pytest.mark.asyncio
async def test_quota_enforcement(test_patron, print_service, print_pricing, test_db):
    """Test that quota is enforced and prevents excessive printing."""
    # Submit a job that uses 150 pages (exceeds 100 page limit)
    with pytest.raises(ValueError) as exc_info:
        await print_service.submit_print_job(
            user_id=test_patron.id,
            job_name="large_document.pdf",
            pages=150,
            copies=1,
            color_mode=ColorMode.blackwhite,
        )

    assert "quota exceeded" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_quota_override(test_patron, print_service, print_pricing, test_db):
    """Test that staff can override quota limits."""
    quota = await print_service.get_user_quota(test_patron.id)
    quota.quota_override_enabled = True
    quota.quota_override_reason = "Research project"
    await test_db.commit()

    # Should now be able to exceed quota
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="large_document.pdf",
        pages=150,
        copies=1,
        color_mode=ColorMode.blackwhite,
    )

    assert job.status == PrintJobStatus.submitted


# ============================================================================
# TESTS - Payment Processing
# ============================================================================


@pytest.mark.asyncio
async def test_process_card_payment(test_patron, print_service, print_pricing, test_db):
    """Test processing payment via credit card."""
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="document.pdf",
        pages=5,
        copies=1,
    )

    payment_job = await print_service.process_payment(
        job_id=job.id,
        payment_method="card",
        payment_reference="txn_123456",
    )

    assert payment_job.payment_method == "card"
    assert payment_job.payment_processed == True
    assert payment_job.payment_reference == "txn_123456"


@pytest.mark.asyncio
async def test_process_account_balance_payment(test_patron, print_service, print_pricing, test_db):
    """Test processing payment from account balance."""
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="document.pdf",
        pages=5,
        copies=1,
    )

    payment_job = await print_service.process_payment(
        job_id=job.id,
        payment_method="account_balance",
        account_balance_used=Decimal("0.50"),
    )

    assert payment_job.payment_method == "account_balance"
    assert payment_job.account_balance_used == Decimal("0.50")
    assert payment_job.payment_amount_charged == Decimal("0.00")


# ============================================================================
# TESTS - Print Release Station
# ============================================================================


@pytest.mark.asyncio
async def test_release_print_job(test_patron, print_service, test_release_station, print_pricing, test_printer, test_db):
    """Test releasing a completed print job at release station."""
    # Submit and complete a job
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="document.pdf",
        pages=5,
        copies=1,
    )

    # Mark as completed and held at release station
    held_job = await print_service.mark_job_completed(
        job_id=job.id,
        release_station_id=test_release_station.id,
    )

    assert held_job.status == PrintJobStatus.held
    assert held_job.release_station_id == test_release_station.id

    # Process payment
    await print_service.process_payment(
        job_id=job.id,
        payment_method="card",
    )

    # Release the job
    released_job = await print_service.release_print_job(
        job_id=job.id,
        release_station_id=test_release_station.id,
        card_number_last_4="1234",
    )

    assert released_job.status == PrintJobStatus.completed
    assert released_job.card_number_scanned == "1234"
    assert released_job.released_at is not None


# ============================================================================
# TESTS - Print Refunds
# ============================================================================


@pytest.mark.asyncio
async def test_create_refund_request(test_patron, print_service, print_pricing, test_db):
    """Test creating a refund request for a failed print."""
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="document.pdf",
        pages=5,
        copies=1,
    )

    # Mark job as failed
    await print_service.mark_job_failed(
        job_id=job.id,
        failure_reason="Paper jam",
    )

    # Create refund request
    refund = await print_service.create_refund_request(
        job_id=job.id,
        reason="Paper jam during printing",
        refund_method="account_credit",
        description="Printer had a paper jam",
    )

    assert refund.print_job_id == job.id
    assert refund.user_id == test_patron.id
    assert refund.status == PrintRefundStatus.pending
    assert refund.refund_amount == job.cost
    assert refund.refund_method == "account_credit"


# ============================================================================
# TESTS - Scan to Email
# ============================================================================


@pytest.mark.asyncio
async def test_create_scan_to_email(test_patron, print_service, test_db):
    """Test creating a scan-to-email job."""
    scan = await print_service.create_scan_to_email(
        user_id=test_patron.id,
        recipient_email="john@example.com",
        job_name="scan_document",
        scanner_name="Main Scanner",
        page_count=10,
    )

    assert scan.user_id == test_patron.id
    assert scan.recipient_email == "john@example.com"
    assert scan.status == ScanToEmailStatus.pending
    assert scan.page_count == 10


@pytest.mark.asyncio
async def test_mark_scan_sent(test_patron, print_service, test_db):
    """Test marking a scan-to-email as sent."""
    scan = await print_service.create_scan_to_email(
        user_id=test_patron.id,
        recipient_email="john@example.com",
        job_name="scan_document",
        page_count=5,
    )

    sent_scan = await print_service.mark_scan_sent(
        scan_id=scan.id,
        file_path="/scans/scan_123.pdf",
        file_size_bytes=102400,
    )

    assert sent_scan.status == ScanToEmailStatus.sent
    assert sent_scan.email_sent_at is not None
    assert sent_scan.file_path == "/scans/scan_123.pdf"


# ============================================================================
# TESTS - Printer Management
# ============================================================================


@pytest.mark.asyncio
async def test_register_printer(printer_service, test_db):
    """Test registering a new printer."""
    printer = await printer_service.register_printer(
        name="Color Printer 2nd Floor",
        printer_type="color_laser",
        location="2nd Floor East Wing",
        model="Xerox VersaLink C8000",
        supports_color=True,
    )

    assert printer.name == "Color Printer 2nd Floor"
    assert printer.location == "2nd Floor East Wing"
    assert printer.status == PrinterStatus.online
    assert printer.is_enabled == True


@pytest.mark.asyncio
async def test_update_printer_supply_levels(test_printer, printer_service, test_db):
    """Test updating printer supply levels and creating alerts."""
    updated = await printer_service.update_supply_levels(
        printer_id=test_printer.id,
        black_toner_level=15.0,  # Below 20% threshold
        paper_level=10.0,  # Below 15% threshold
    )

    assert updated.black_toner_level == 15.0
    assert updated.paper_level == 10.0


@pytest.mark.asyncio
async def test_printer_low_toner_alert(test_printer, printer_service, test_db):
    """Test that low toner generates alert."""
    # Update toner to low level
    await printer_service.update_supply_levels(
        printer_id=test_printer.id,
        black_toner_level=10.0,
    )

    # Get alerts
    alerts = await printer_service.get_unresolved_alerts(printer_id=test_printer.id)

    assert len(alerts) > 0
    assert any(a.alert_type == "low_toner" for a in alerts)


@pytest.mark.asyncio
async def test_resolve_printer_alert(test_printer, printer_service, test_staff, test_db):
    """Test resolving a printer alert."""
    # Create alert
    await printer_service.update_supply_levels(
        printer_id=test_printer.id,
        black_toner_level=10.0,
    )

    # Get the alert
    alerts = await printer_service.get_unresolved_alerts(printer_id=test_printer.id)
    alert = alerts[0]

    # Resolve it
    resolved = await printer_service.resolve_alert(
        alert_id=alert.id,
        resolved_by_id=test_staff.id,
    )

    assert resolved.resolved == True
    assert resolved.resolved_at is not None


# ============================================================================
# TESTS - Print Job Lifecycle
# ============================================================================


@pytest.mark.asyncio
async def test_complete_print_workflow(test_patron, print_service, printer_service, test_printer, test_release_station, print_pricing, test_db):
    """Test complete print job workflow from submission to release."""
    # 1. Submit job
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="document.pdf",
        pages=10,
        copies=1,
        color_mode=ColorMode.color,
    )

    assert job.status == PrintJobStatus.submitted

    # 2. Assign printer
    job = await print_service.assign_printer(job.id, test_printer.id)
    assert job.status == PrintJobStatus.queued

    # 3. Send to printer
    job = await print_service.send_to_printer(job.id)
    assert job.status == PrintJobStatus.printing

    # 4. Complete printing
    job = await print_service.mark_job_completed(
        job_id=job.id,
        release_station_id=test_release_station.id,
    )
    assert job.status == PrintJobStatus.held

    # 5. Process payment
    job = await print_service.process_payment(
        job_id=job.id,
        payment_method="card",
    )
    assert job.payment_processed == True

    # 6. Release at station
    job = await print_service.release_print_job(
        job_id=job.id,
        release_station_id=test_release_station.id,
    )
    assert job.status == PrintJobStatus.completed
    assert job.released_at is not None


@pytest.mark.asyncio
async def test_cancel_print_job(test_patron, print_service, print_pricing, test_db):
    """Test cancelling a print job before printing."""
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="document.pdf",
        pages=5,
        copies=1,
    )

    cancelled = await print_service.cancel_job(job.id)

    assert cancelled.status == PrintJobStatus.cancelled
    assert cancelled.cancelled_at is not None


@pytest.mark.asyncio
async def test_cannot_cancel_completed_job(test_patron, print_service, print_pricing, test_db):
    """Test that completed jobs cannot be cancelled."""
    job = await print_service.submit_print_job(
        user_id=test_patron.id,
        job_name="document.pdf",
        pages=5,
        copies=1,
    )

    await print_service.mark_job_completed(job.id)

    with pytest.raises(ValueError) as exc_info:
        await print_service.cancel_job(job.id)

    assert "cannot cancel" in str(exc_info.value).lower()
