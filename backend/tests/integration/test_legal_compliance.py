# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration Tests for Legal Compliance Module

Tests all 4 phases:
- Phase 1: Document management
- Phase 2: Compliance tracking
- Phase 3: Review cycles and audit logging
- Phase 4: Alerts, metrics, and regulatory tracking
"""

import pytest
from datetime import date, datetime, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_compliance import (
    LegalDocument,
    DocumentVersion,
    LegalComplianceRequirement,
    ComplianceDocumentLink,
    ComplianceChecklistItem,
    DocumentReviewCycle,
    DocumentReview,
    ComplianceAlert,
    RegulatoryChange,
    PolicyEnforcementTracking,
    ComplianceDashboardMetric,
    DocumentAuditLog,
    LegalDocumentType,
    DocumentCategory,
    LegalDocumentStatus,
    RequirementType,
    ComplianceStatus,
    ReviewFrequency,
    ReviewStatus,
    LegalAlertSeverity,
    AlertStatus,
    LegalChangeType,
)
from app.core.security import create_access_token
from app.models.user import User


@pytest.fixture
def staff_token(test_staff) -> str:
    """Bearer token string for the staff fixture user."""
    return create_access_token(subject=str(test_staff.id))


# ============================================================================
# Phase 1: Document Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_legal_document(client: AsyncClient, staff_token: str):
    """Test creating a legal document."""
    response = await client.post(
        "/api/v1/legal/documents",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={
            "title": "Test Privacy Policy",
            "document_type": "policy",
            "category": "privacy_data",
            "description": "Test policy for data privacy",
            "purpose": "Ensure patron data protection",
            "effective_date": date.today().isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Privacy Policy"
    assert "document_number" in data
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test listing legal documents with filters."""
    # Create test documents
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc1 = LegalDocument(
        title="Policy A",
        document_number="DOC-TEST-001",
        document_type=LegalDocumentType.policy,
        category=DocumentCategory.privacy_data,
        status=LegalDocumentStatus.active,
        owner_id=user.id,
        created_by_id=user.id,
    )
    doc2 = LegalDocument(
        title="Policy B",
        document_number="DOC-TEST-002",
        document_type=LegalDocumentType.guideline,
        category=DocumentCategory.accessibility,
        status=LegalDocumentStatus.draft,
        owner_id=user.id,
        created_by_id=user.id,
    )
    db.add_all([doc1, doc2])
    await db.commit()

    # Test listing all documents
    response = await client.get(
        "/api/v1/legal/documents", headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) >= 2

    # Test filtering by status
    response = await client.get(
        "/api/v1/legal/documents?status=active", headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(d["status"] == "active" for d in data["documents"])


@pytest.mark.asyncio
async def test_get_document_details(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test getting document details."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc = LegalDocument(
        title="Detailed Policy",
        document_number="DOC-DETAIL-001",
        document_type=LegalDocumentType.policy,
        category=DocumentCategory.governance,
        description="Detailed test policy",
        status=LegalDocumentStatus.active,
        owner_id=user.id,
        created_by_id=user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    response = await client.get(
        f"/api/v1/legal/documents/{doc.id}", headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Detailed Policy"
    assert data["document_number"] == "DOC-DETAIL-001"
    assert data["description"] == "Detailed test policy"


@pytest.mark.asyncio
async def test_update_document(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test updating a document."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc = LegalDocument(
        title="Original Title",
        document_number="DOC-UPDATE-001",
        document_type=LegalDocumentType.policy,
        category=DocumentCategory.hr_employment,
        status=LegalDocumentStatus.draft,
        owner_id=user.id,
        created_by_id=user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    response = await client.put(
        f"/api/v1/legal/documents/{doc.id}",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={"title": "Updated Title", "description": "Updated description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_create_document_version(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test creating a new document version."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc = LegalDocument(
        title="Versioned Policy",
        document_number="DOC-VER-001",
        document_type=LegalDocumentType.policy,
        category=DocumentCategory.technology,
        status=LegalDocumentStatus.active,
        owner_id=user.id,
        created_by_id=user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    response = await client.post(
        f"/api/v1/legal/documents/{doc.id}/versions",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={
            "version_number": "2.0",
            "change_summary": "Major update to policy",
            "content": "Updated policy content",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["version_number"] == "2.0"
    assert data["change_summary"] == "Major update to policy"


@pytest.mark.asyncio
async def test_approve_document(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test approving a document."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc = LegalDocument(
        title="Approval Test",
        document_number="DOC-APPROVE-001",
        document_type=LegalDocumentType.policy,
        category=DocumentCategory.finance,
        status=LegalDocumentStatus.draft,
        owner_id=user.id,
        created_by_id=user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    response = await client.post(
        f"/api/v1/legal/documents/{doc.id}/approve",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={"approval_notes": "Approved after review"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert "approved_at" in data


# ============================================================================
# Phase 2: Compliance Tracking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_compliance_requirement(client: AsyncClient, staff_token: str):
    """Test creating a compliance requirement."""
    response = await client.post(
        "/api/v1/legal/compliance/requirements",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={
            "title": "Test Compliance Requirement",
            "requirement_type": "federal_law",
            "description": "Test requirement for compliance",
            "effective_date": date.today().isoformat(),
            "risk_level": "High",
            "jurisdiction": "Federal",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Compliance Requirement"
    assert "requirement_code" in data


@pytest.mark.asyncio
async def test_list_compliance_requirements(
    client: AsyncClient, staff_token: str, db: AsyncSession
):
    """Test listing compliance requirements."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    req = LegalComplianceRequirement(
        title="ADA Compliance",
        requirement_code="REQ-TEST-001",
        requirement_type=RequirementType.federal_law,
        description="Test ADA requirement",
        effective_date=date.today(),
        compliance_status=ComplianceStatus.compliant,
        compliance_officer_id=user.id,
        created_by_id=user.id,
    )
    db.add(req)
    await db.commit()

    response = await client.get(
        "/api/v1/legal/compliance/requirements", headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["requirements"]) >= 1


@pytest.mark.asyncio
async def test_update_requirement_status(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test updating compliance requirement status."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    req = LegalComplianceRequirement(
        title="Status Update Test",
        requirement_code="REQ-STATUS-001",
        requirement_type=RequirementType.state_law,
        description="Test status update",
        effective_date=date.today(),
        compliance_status=ComplianceStatus.under_review,
        compliance_officer_id=user.id,
        created_by_id=user.id,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    response = await client.put(
        f"/api/v1/legal/compliance/requirements/{req.id}/status",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={"compliance_status": "compliant", "assessment_notes": "Verified compliance"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_status"] == "compliant"


@pytest.mark.asyncio
async def test_link_document_to_requirement(
    client: AsyncClient, staff_token: str, db: AsyncSession
):
    """Test linking a document to a requirement."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc = LegalDocument(
        title="Link Test Doc",
        document_number="DOC-LINK-001",
        document_type=LegalDocumentType.policy,
        category=DocumentCategory.privacy_data,
        status=LegalDocumentStatus.active,
        owner_id=user.id,
        created_by_id=user.id,
    )
    req = LegalComplianceRequirement(
        title="Link Test Req",
        requirement_code="REQ-LINK-001",
        requirement_type=RequirementType.internal_policy,
        description="Test linking",
        effective_date=date.today(),
        compliance_officer_id=user.id,
        created_by_id=user.id,
    )
    db.add_all([doc, req])
    await db.commit()
    await db.refresh(doc)
    await db.refresh(req)

    response = await client.post(
        f"/api/v1/legal/compliance/requirements/{req.id}/documents",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={
            "document_id": doc.id,
            "relationship_type": "implements",
            "notes": "Document implements requirement",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["requirement_id"] == req.id
    assert data["document_id"] == doc.id


@pytest.mark.asyncio
async def test_add_checklist_item(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test adding a checklist item to a requirement."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    req = LegalComplianceRequirement(
        title="Checklist Test",
        requirement_code="REQ-CHECK-001",
        requirement_type=RequirementType.accreditation,
        description="Test checklist",
        effective_date=date.today(),
        compliance_officer_id=user.id,
        created_by_id=user.id,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    response = await client.post(
        f"/api/v1/legal/compliance/requirements/{req.id}/checklist",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={"item_text": "Verify documentation is complete", "item_order": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["item_text"] == "Verify documentation is complete"


@pytest.mark.asyncio
async def test_complete_checklist_item(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test completing a checklist item."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    req = LegalComplianceRequirement(
        title="Complete Test",
        requirement_code="REQ-COMPLETE-001",
        requirement_type=RequirementType.grant_requirement,
        description="Test completion",
        effective_date=date.today(),
        compliance_officer_id=user.id,
        created_by_id=user.id,
    )
    db.add(req)
    await db.flush()

    item = ComplianceChecklistItem(
        requirement_id=req.id, item_text="Complete this item", item_order=1
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    response = await client.put(
        f"/api/v1/legal/compliance/checklist-items/{item.id}/complete",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={"notes": "Completed successfully"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_completed"] is True


# ============================================================================
# Phase 3: Review Cycles and Audit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_review_cycle(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test creating a review cycle."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc = LegalDocument(
        title="Review Cycle Test",
        document_number="DOC-REVIEW-001",
        document_type=LegalDocumentType.policy,
        category=DocumentCategory.collections,
        status=LegalDocumentStatus.active,
        owner_id=user.id,
        created_by_id=user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    response = await client.post(
        "/api/v1/legal/reviews/cycles",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={
            "document_id": doc.id,
            "review_frequency": "annual",
            "scheduled_date": date.today().isoformat(),
            "assigned_to_id": user.id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc.id
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_start_review_cycle(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test starting a review cycle."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc = LegalDocument(
        title="Start Review Test",
        document_number="DOC-START-001",
        document_type=LegalDocumentType.procedure,
        category=DocumentCategory.safety_security,
        status=LegalDocumentStatus.active,
        owner_id=user.id,
        created_by_id=user.id,
    )
    db.add(doc)
    await db.flush()

    cycle = DocumentReviewCycle(
        document_id=doc.id,
        review_frequency=ReviewFrequency.annual,
        scheduled_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=ReviewStatus.pending,
        assigned_to_id=user.id,
        created_by_id=user.id,
    )
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)

    response = await client.post(
        f"/api/v1/legal/reviews/cycles/{cycle.id}/start",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_add_review_to_cycle(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test adding a review to a cycle."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc = LegalDocument(
        title="Add Review Test",
        document_number="DOC-ADDREV-001",
        document_type=LegalDocumentType.guideline,
        category=DocumentCategory.youth_services,
        status=LegalDocumentStatus.active,
        owner_id=user.id,
        created_by_id=user.id,
    )
    db.add(doc)
    await db.flush()

    cycle = DocumentReviewCycle(
        document_id=doc.id,
        review_frequency=ReviewFrequency.annual,
        scheduled_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=ReviewStatus.in_progress,
        assigned_to_id=user.id,
        created_by_id=user.id,
    )
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)

    response = await client.post(
        f"/api/v1/legal/reviews/cycles/{cycle.id}/reviews",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={
            "findings": "Document reviewed and found accurate",
            "recommendations": "Minor updates recommended",
            "approved": True,
            "legal_accuracy_rating": 5,
            "clarity_rating": 4,
            "completeness_rating": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["approved"] is True


@pytest.mark.asyncio
async def test_complete_review_cycle(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test completing a review cycle."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc = LegalDocument(
        title="Complete Review Test",
        document_number="DOC-COMPREV-001",
        document_type=LegalDocumentType.policy,
        category=DocumentCategory.facilities,
        status=LegalDocumentStatus.active,
        owner_id=user.id,
        created_by_id=user.id,
    )
    db.add(doc)
    await db.flush()

    cycle = DocumentReviewCycle(
        document_id=doc.id,
        review_frequency=ReviewFrequency.annual,
        scheduled_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=ReviewStatus.in_progress,
        assigned_to_id=user.id,
        created_by_id=user.id,
    )
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)

    response = await client.post(
        f"/api/v1/legal/reviews/cycles/{cycle.id}/complete",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={"outcome_summary": "Review completed successfully"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_get_audit_log(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test retrieving audit log."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc = LegalDocument(
        title="Audit Test",
        document_number="DOC-AUDIT-001",
        document_type=LegalDocumentType.policy,
        category=DocumentCategory.governance,
        status=LegalDocumentStatus.active,
        owner_id=user.id,
        created_by_id=user.id,
    )
    db.add(doc)
    await db.flush()

    # Create audit log entry
    from app.models.legal_compliance import DocumentAuditLog, AuditEventType

    audit = DocumentAuditLog(
        document_id=doc.id,
        event_type=AuditEventType.created,
        event_description="Document created",
        user_id=user.id,
        user_role="admin",
    )
    db.add(audit)
    await db.commit()

    response = await client.get(
        f"/api/v1/legal/reviews/audit-log?document_id={doc.id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["audit_logs"]) >= 1


# ============================================================================
# Phase 4: Alerts, Metrics, and Reporting Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_dashboard_metrics(client: AsyncClient, staff_token: str):
    """Test getting dashboard metrics."""
    response = await client.get(
        "/api/v1/legal/reporting/dashboard", headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "compliance" in data
    assert "reviews" in data
    assert "alerts" in data


@pytest.mark.asyncio
async def test_create_alert(client: AsyncClient, staff_token: str):
    """Test creating a compliance alert."""
    response = await client.post(
        "/api/v1/legal/reporting/alerts",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={
            "title": "Test Alert",
            "message": "This is a test alert",
            "severity": "high",
            "alert_type": "test_alert",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Alert"
    assert data["severity"] == "high"


@pytest.mark.asyncio
async def test_acknowledge_alert(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test acknowledging an alert."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    alert = ComplianceAlert(
        title="Acknowledge Test",
        message="Test alert to acknowledge",
        severity=LegalAlertSeverity.medium,
        alert_type="test",
        status=AlertStatus.active,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    response = await client.put(
        f"/api/v1/legal/reporting/alerts/{alert.id}/acknowledge",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_resolve_alert(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test resolving an alert."""
    alert = ComplianceAlert(
        title="Resolve Test",
        message="Test alert to resolve",
        severity=LegalAlertSeverity.low,
        alert_type="test",
        status=AlertStatus.acknowledged,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    response = await client.put(
        f"/api/v1/legal/reporting/alerts/{alert.id}/resolve",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={"resolution_notes": "Alert resolved"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"


@pytest.mark.asyncio
async def test_create_regulatory_change(client: AsyncClient, staff_token: str):
    """Test creating a regulatory change record."""
    response = await client.post(
        "/api/v1/legal/reporting/regulatory-changes",
        headers={"Authorization": f"Bearer {staff_token}"},
        params={
            "title": "Test Regulatory Change",
            "change_type": "amendment",
            "description": "Test regulation amendment",
            "announcement_date": date.today().isoformat(),
            "jurisdiction": "Federal",
            "impact_level": "High",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Regulatory Change"
    assert data["change_type"] == "amendment"


@pytest.mark.asyncio
async def test_list_regulatory_changes(client: AsyncClient, staff_token: str, db: AsyncSession):
    """Test listing regulatory changes."""
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    change = RegulatoryChange(
        title="Test Change",
        change_type=LegalChangeType.new_regulation,
        description="Test regulatory change",
        announcement_date=date.today(),
        jurisdiction="State",
        impact_level="Medium",
        created_by_id=user.id,
    )
    db.add(change)
    await db.commit()

    response = await client.get(
        "/api/v1/legal/reporting/regulatory-changes",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["regulatory_changes"]) >= 1


@pytest.mark.asyncio
async def test_get_compliance_summary(client: AsyncClient, staff_token: str):
    """Test getting compliance summary."""
    response = await client.get(
        "/api/v1/legal/reporting/compliance-summary",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "requirements" in data
    assert "documents" in data
    assert "reviews" in data
    assert "alerts" in data


# ============================================================================
# Service Tests
# ============================================================================


@pytest.mark.asyncio
async def test_legal_compliance_service_metrics(db: AsyncSession):
    """Test legal compliance service metric calculations."""
    from app.services.legal_compliance_service import LegalComplianceService

    metrics = await LegalComplianceService.calculate_dashboard_metrics(db)

    assert "total_documents" in metrics
    assert "total_requirements" in metrics
    assert "compliance_rate" in metrics
    assert "scheduled_reviews" in metrics
    assert "active_alerts" in metrics


@pytest.mark.asyncio
async def test_alert_generation(db: AsyncSession):
    """Test automated alert generation."""
    from app.services.legal_compliance_service import LegalComplianceService

    alerts_count = await LegalComplianceService.run_alert_generation(db)
    assert isinstance(alerts_count, int)
    assert alerts_count >= 0


@pytest.mark.asyncio
async def test_document_health_score(db: AsyncSession, test_staff):
    """Test document health score calculation."""
    from app.services.legal_compliance_service import LegalComplianceService

    # Every other test in this file depends on `staff_token` (-> test_staff),
    # which guarantees at least one User row exists for the ambient
    # `select(User).limit(1)` lookup below. This test was missing that
    # dependency, so on a DB with no other seeded users it raised
    # NoResultFound.
    user = await db.execute(select(User).limit(1))
    user = user.scalar_one()

    doc = LegalDocument(
        title="Health Score Test",
        document_number="DOC-HEALTH-001",
        document_type=LegalDocumentType.policy,
        category=DocumentCategory.privacy_data,
        status=LegalDocumentStatus.active,
        owner_id=user.id,
        created_by_id=user.id,
        next_review_date=date.today() + timedelta(days=60),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    health = await LegalComplianceService.get_document_health_score(db, doc.id)

    assert "health_score" in health
    assert "issues" in health
    assert "status" in health
    assert health["health_score"] >= 0
    assert health["health_score"] <= 100
