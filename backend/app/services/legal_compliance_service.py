# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.legal_compliance import (
    LegalDocument, LegalComplianceRequirement, DocumentReviewCycle,
    ComplianceAlert, ComplianceDashboardMetric,
    LegalDocumentStatus, ComplianceStatus, ReviewStatus,
    LegalAlertSeverity, AlertStatus
)


class LegalComplianceService:

    @staticmethod
    async def calculate_dashboard_metrics(
        db: AsyncSession,
        metric_date: date = None
    ) -> Dict:
        target_date = metric_date or date.today()

        # Document metrics
        total_docs = await db.execute(select(func.count(LegalDocument.id)))
        total_documents = total_docs.scalar() or 0

        active_docs = await db.execute(
            select(func.count(LegalDocument.id)).where(
                LegalDocument.status == LegalDocumentStatus.active
            )
        )
        active_documents = active_docs.scalar() or 0

        pending_review = await db.execute(
            select(func.count(LegalDocument.id)).where(
                and_(
                    LegalDocument.next_review_date.isnot(None),
                    LegalDocument.next_review_date <= target_date + timedelta(days=30),
                    LegalDocument.next_review_date >= target_date
                )
            )
        )
        documents_pending_review = pending_review.scalar() or 0

        overdue_review = await db.execute(
            select(func.count(LegalDocument.id)).where(
                and_(
                    LegalDocument.next_review_date.isnot(None),
                    LegalDocument.next_review_date < target_date
                )
            )
        )
        documents_overdue_review = overdue_review.scalar() or 0

        expiring = await db.execute(
            select(func.count(LegalDocument.id)).where(
                and_(
                    LegalDocument.expiration_date.isnot(None),
                    LegalDocument.expiration_date <= target_date + timedelta(days=60),
                    LegalDocument.expiration_date >= target_date
                )
            )
        )
        documents_expiring_soon = expiring.scalar() or 0

        # Compliance metrics
        total_reqs = await db.execute(select(func.count(LegalComplianceRequirement.id)))
        total_requirements = total_reqs.scalar() or 0

        compliant = await db.execute(
            select(func.count(LegalComplianceRequirement.id)).where(
                LegalComplianceRequirement.compliance_status == ComplianceStatus.compliant
            )
        )
        compliant_requirements = compliant.scalar() or 0

        non_compliant = await db.execute(
            select(func.count(LegalComplianceRequirement.id)).where(
                LegalComplianceRequirement.compliance_status == ComplianceStatus.non_compliant
            )
        )
        non_compliant_requirements = non_compliant.scalar() or 0

        pending = await db.execute(
            select(func.count(LegalComplianceRequirement.id)).where(
                LegalComplianceRequirement.compliance_status.in_([
                    ComplianceStatus.under_review,
                    ComplianceStatus.pending_action
                ])
            )
        )
        pending_requirements = pending.scalar() or 0

        # Calculate compliance rate
        compliance_rate = (
            (compliant_requirements / total_requirements * 100)
            if total_requirements > 0 else 0.0
        )

        # Review metrics
        scheduled = await db.execute(
            select(func.count(DocumentReviewCycle.id)).where(
                and_(
                    DocumentReviewCycle.scheduled_date <= target_date + timedelta(days=30),
                    DocumentReviewCycle.scheduled_date >= target_date
                )
            )
        )
        scheduled_reviews = scheduled.scalar() or 0

        completed = await db.execute(
            select(func.count(DocumentReviewCycle.id)).where(
                and_(
                    DocumentReviewCycle.status == ReviewStatus.completed,
                    DocumentReviewCycle.completed_date >= target_date - timedelta(days=30)
                )
            )
        )
        completed_reviews = completed.scalar() or 0

        overdue = await db.execute(
            select(func.count(DocumentReviewCycle.id)).where(
                and_(
                    DocumentReviewCycle.due_date < target_date,
                    DocumentReviewCycle.status.in_([ReviewStatus.pending, ReviewStatus.in_progress])
                )
            )
        )
        overdue_reviews = overdue.scalar() or 0

        # Alert metrics
        active_alerts = await db.execute(
            select(func.count(ComplianceAlert.id)).where(
                ComplianceAlert.status == AlertStatus.active
            )
        )
        active_alerts_count = active_alerts.scalar() or 0

        critical_alerts = await db.execute(
            select(func.count(ComplianceAlert.id)).where(
                and_(
                    ComplianceAlert.status == AlertStatus.active,
                    ComplianceAlert.severity == LegalAlertSeverity.critical
                )
            )
        )
        critical_alerts_count = critical_alerts.scalar() or 0

        return {
            "total_documents": total_documents,
            "active_documents": active_documents,
            "documents_pending_review": documents_pending_review,
            "documents_overdue_review": documents_overdue_review,
            "documents_expiring_soon": documents_expiring_soon,
            "total_requirements": total_requirements,
            "compliant_requirements": compliant_requirements,
            "non_compliant_requirements": non_compliant_requirements,
            "pending_requirements": pending_requirements,
            "compliance_rate": round(compliance_rate, 2),
            "scheduled_reviews": scheduled_reviews,
            "completed_reviews": completed_reviews,
            "overdue_reviews": overdue_reviews,
            "active_alerts": active_alerts_count,
            "critical_alerts": critical_alerts_count
        }

    @staticmethod
    async def generate_review_alerts(db: AsyncSession) -> List[ComplianceAlert]:
        alerts = []
        today = date.today()

        # Find documents with reviews due within 30 days
        upcoming_query = select(LegalDocument).where(
            and_(
                LegalDocument.next_review_date.isnot(None),
                LegalDocument.next_review_date <= today + timedelta(days=30),
                LegalDocument.next_review_date > today
            )
        )
        result = await db.execute(upcoming_query)
        upcoming_docs = result.scalars().all()

        for doc in upcoming_docs:
            days_until = (doc.next_review_date - today).days
            severity = LegalAlertSeverity.high if days_until <= 7 else LegalAlertSeverity.medium

            alert = ComplianceAlert(
                title=f"Document Review Due Soon: {doc.title}",
                message=f"Document review is due in {days_until} days on {doc.next_review_date}",
                severity=severity,
                alert_type="review_upcoming",
                document_id=doc.id,
                due_date=doc.next_review_date,
                action_required=f"Schedule and conduct review for document {doc.document_number}",
                assigned_to_id=doc.owner_id
            )
            alerts.append(alert)

        # Find overdue reviews
        overdue_query = select(LegalDocument).where(
            and_(
                LegalDocument.next_review_date.isnot(None),
                LegalDocument.next_review_date < today
            )
        )
        result = await db.execute(overdue_query)
        overdue_docs = result.scalars().all()

        for doc in overdue_docs:
            days_overdue = (today - doc.next_review_date).days

            alert = ComplianceAlert(
                title=f"OVERDUE: Document Review - {doc.title}",
                message=f"Document review is {days_overdue} days overdue (was due {doc.next_review_date})",
                severity=LegalAlertSeverity.critical,
                alert_type="review_overdue",
                document_id=doc.id,
                due_date=doc.next_review_date,
                action_required=f"URGENT: Complete overdue review for document {doc.document_number}",
                assigned_to_id=doc.owner_id
            )
            alerts.append(alert)

        return alerts

    @staticmethod
    async def generate_compliance_alerts(db: AsyncSession) -> List[ComplianceAlert]:
        alerts = []
        today = date.today()

        # Find requirements with upcoming deadlines
        upcoming_query = select(LegalComplianceRequirement).where(
            and_(
                LegalComplianceRequirement.deadline_date.isnot(None),
                LegalComplianceRequirement.deadline_date <= today + timedelta(days=30),
                LegalComplianceRequirement.deadline_date > today,
                LegalComplianceRequirement.compliance_status != ComplianceStatus.compliant
            )
        )
        result = await db.execute(upcoming_query)
        upcoming_reqs = result.scalars().all()

        for req in upcoming_reqs:
            days_until = (req.deadline_date - today).days
            severity = LegalAlertSeverity.critical if days_until <= 7 else LegalAlertSeverity.high

            alert = ComplianceAlert(
                title=f"Compliance Deadline Approaching: {req.title}",
                message=f"Compliance deadline in {days_until} days on {req.deadline_date}",
                severity=severity,
                alert_type="compliance_deadline",
                requirement_id=req.id,
                due_date=req.deadline_date,
                action_required=f"Ensure compliance with requirement {req.requirement_code}",
                assigned_to_id=req.compliance_officer_id
            )
            alerts.append(alert)

        # Find non-compliant requirements
        non_compliant_query = select(LegalComplianceRequirement).where(
            LegalComplianceRequirement.compliance_status == ComplianceStatus.non_compliant
        )
        result = await db.execute(non_compliant_query)
        non_compliant_reqs = result.scalars().all()

        for req in non_compliant_reqs:
            alert = ComplianceAlert(
                title=f"Non-Compliant Requirement: {req.title}",
                message=f"Requirement {req.requirement_code} is currently non-compliant",
                severity=LegalAlertSeverity.critical if req.risk_level == "Critical" else LegalAlertSeverity.high,
                alert_type="non_compliant",
                requirement_id=req.id,
                due_date=req.deadline_date,
                action_required=f"Take corrective action for requirement {req.requirement_code}",
                assigned_to_id=req.compliance_officer_id
            )
            alerts.append(alert)

        return alerts

    @staticmethod
    async def generate_expiration_alerts(db: AsyncSession) -> List[ComplianceAlert]:
        alerts = []
        today = date.today()

        # Find documents expiring within 60 days
        expiring_query = select(LegalDocument).where(
            and_(
                LegalDocument.expiration_date.isnot(None),
                LegalDocument.expiration_date <= today + timedelta(days=60),
                LegalDocument.expiration_date > today,
                LegalDocument.status == LegalDocumentStatus.active
            )
        )
        result = await db.execute(expiring_query)
        expiring_docs = result.scalars().all()

        for doc in expiring_docs:
            days_until = (doc.expiration_date - today).days

            if days_until <= 14:
                severity = LegalAlertSeverity.critical
            elif days_until <= 30:
                severity = LegalAlertSeverity.high
            else:
                severity = LegalAlertSeverity.medium

            alert = ComplianceAlert(
                title=f"Document Expiring: {doc.title}",
                message=f"Document expires in {days_until} days on {doc.expiration_date}",
                severity=severity,
                alert_type="expiring_document",
                document_id=doc.id,
                due_date=doc.expiration_date,
                action_required=f"Review and renew/update document {doc.document_number}",
                assigned_to_id=doc.owner_id
            )
            alerts.append(alert)

        return alerts

    @staticmethod
    async def run_alert_generation(db: AsyncSession) -> int:
        # Check for existing active alerts to avoid duplicates
        existing_alerts_query = select(ComplianceAlert).where(
            ComplianceAlert.status == AlertStatus.active
        )
        result = await db.execute(existing_alerts_query)
        existing_alerts = result.scalars().all()

        # Create a set of existing alert signatures
        existing_signatures = set()
        for alert in existing_alerts:
            sig = f"{alert.alert_type}:{alert.document_id}:{alert.requirement_id}"
            existing_signatures.add(sig)

        # Generate new alerts
        review_alerts = await LegalComplianceService.generate_review_alerts(db)
        compliance_alerts = await LegalComplianceService.generate_compliance_alerts(db)
        expiration_alerts = await LegalComplianceService.generate_expiration_alerts(db)

        all_new_alerts = review_alerts + compliance_alerts + expiration_alerts

        # Filter out duplicates
        alerts_to_add = []
        for alert in all_new_alerts:
            sig = f"{alert.alert_type}:{alert.document_id}:{alert.requirement_id}"
            if sig not in existing_signatures:
                alerts_to_add.append(alert)
                existing_signatures.add(sig)

        # Add new alerts to database
        if alerts_to_add:
            db.add_all(alerts_to_add)
            await db.commit()

        return len(alerts_to_add)

    @staticmethod
    async def get_compliance_trends(
        db: AsyncSession,
        days: int = 90
    ) -> Dict:
        start_date = date.today() - timedelta(days=days)

        # Get historical compliance rates
        # This would query ComplianceDashboardMetric table for historical data
        query = select(
            ComplianceDashboardMetric.metric_date,
            ComplianceDashboardMetric.compliance_rate,
            ComplianceDashboardMetric.total_requirements,
            ComplianceDashboardMetric.compliant_requirements
        ).where(
            and_(
                ComplianceDashboardMetric.metric_date >= start_date,
                ComplianceDashboardMetric.metric_type == "daily"
            )
        ).order_by(ComplianceDashboardMetric.metric_date)

        result = await db.execute(query)
        metrics = result.all()

        trend_data = {
            "dates": [],
            "compliance_rates": [],
            "total_requirements": [],
            "compliant_requirements": []
        }

        for metric in metrics:
            trend_data["dates"].append(metric.metric_date.isoformat())
            trend_data["compliance_rates"].append(metric.compliance_rate)
            trend_data["total_requirements"].append(metric.total_requirements)
            trend_data["compliant_requirements"].append(metric.compliant_requirements)

        return trend_data

    @staticmethod
    async def get_document_health_score(
        db: AsyncSession,
        document_id: int
    ) -> Dict:
        query = select(LegalDocument).where(LegalDocument.id == document_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            return {"error": "Document not found"}

        score = 100
        issues = []

        # Check if review is overdue
        if document.next_review_date and document.next_review_date < date.today():
            days_overdue = (date.today() - document.next_review_date).days
            score -= min(30, days_overdue * 2)
            issues.append(f"Review overdue by {days_overdue} days")

        # Check if expiration is approaching
        if document.expiration_date:
            days_until_expiration = (document.expiration_date - date.today()).days
            if days_until_expiration < 0:
                score -= 40
                issues.append("Document expired")
            elif days_until_expiration <= 30:
                score -= 20
                issues.append(f"Expiring in {days_until_expiration} days")

        # Check if approved
        if document.status == LegalDocumentStatus.draft:
            score -= 15
            issues.append("Document still in draft")

        # Check if has current version
        if not document.current_version_id:
            score -= 10
            issues.append("No current version")

        # Check if has owner
        if not document.owner_id:
            score -= 5
            issues.append("No owner assigned")

        return {
            "document_id": document_id,
            "health_score": max(0, score),
            "issues": issues,
            "status": "healthy" if score >= 80 else "needs_attention" if score >= 50 else "critical"
        }
