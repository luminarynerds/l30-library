# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from ..models.compliance_tracking import (
    ADACompliance, CIPACompliance, COPPACompliance, PCICompliance,
    StateLibraryRequirement, InsurancePolicy, LiabilityIncident,
    SafetyInspection, StaffCertification, PolicyReview, AuditReadinessChecklist,
    ComplianceDeadlineAlert, ADAStatus, CIPAStatus, COPPAStatus, PCIStatus,
    StateComplianceStatus, InsuranceType, SafetyInspectionType, CertificationType,
    PolicyReviewStatus, AuditItemStatus, TrackingComplianceStatus
)
from ..models.user import User


class ComplianceService:

    @staticmethod
    async def get_compliance_dashboard(
        db: AsyncSession,
        organization_id: int
    ) -> Dict[str, Any]:
        dashboard = {
            "organization_id": organization_id,
            "generated_at": datetime.now().__str__(),
            "summary": {},
            "upcoming_deadlines": [],
            "critical_items": [],
            "compliance_scores": {}
        }

        # ADA Compliance status
        ada_result = await db.execute(
            select(ADACompliance).where(ADACompliance.organization_id == organization_id)
        )
        ada = ada_result.scalar_one_or_none()
        if ada:
            dashboard["summary"]["ada_status"] = str(ada.status)
            dashboard["compliance_scores"]["ada"] = _calculate_ada_score(ada)
            if ada.next_assessment_due:
                dashboard["upcoming_deadlines"].append({
                    "type": "ADA Assessment",
                    "due_date": ada.next_assessment_due.isoformat(),
                    "days_until": (ada.next_assessment_due - date.today()).days,
                    "priority": "high" if (ada.next_assessment_due - date.today()).days <= 30 else "normal"
                })

        # CIPA Compliance status
        cipa_result = await db.execute(
            select(CIPACompliance).where(CIPACompliance.organization_id == organization_id)
        )
        cipa = cipa_result.scalar_one_or_none()
        if cipa:
            dashboard["summary"]["cipa_status"] = str(cipa.status)
            if cipa.next_check_due:
                dashboard["upcoming_deadlines"].append({
                    "type": "CIPA Compliance Check",
                    "due_date": cipa.next_check_due.isoformat(),
                    "days_until": (cipa.next_check_due - date.today()).days,
                    "priority": "high" if (cipa.next_check_due - date.today()).days <= 30 else "normal"
                })

        # COPPA Compliance status
        coppa_result = await db.execute(
            select(COPPACompliance).where(COPPACompliance.organization_id == organization_id)
        )
        coppa = coppa_result.scalar_one_or_none()
        if coppa:
            dashboard["summary"]["coppa_status"] = str(coppa.status)
            if coppa.next_training_due:
                dashboard["upcoming_deadlines"].append({
                    "type": "COPPA Staff Training",
                    "due_date": coppa.next_training_due.isoformat(),
                    "days_until": (coppa.next_training_due - date.today()).days,
                    "priority": "high" if (coppa.next_training_due - date.today()).days <= 30 else "normal"
                })

        # PCI Compliance status
        pci_result = await db.execute(
            select(PCICompliance).where(PCICompliance.organization_id == organization_id)
        )
        pci = pci_result.scalar_one_or_none()
        if pci:
            dashboard["summary"]["pci_status"] = str(pci.status)
            if pci.next_assessment_due:
                dashboard["upcoming_deadlines"].append({
                    "type": "PCI Assessment",
                    "due_date": pci.next_assessment_due.isoformat(),
                    "days_until": (pci.next_assessment_due - date.today()).days,
                    "priority": "critical" if (pci.next_assessment_due - date.today()).days <= 14 else "high"
                })

        # State library requirements tracking
        state_result = await db.execute(
            select(StateLibraryRequirement).where(
                StateLibraryRequirement.organization_id == organization_id
            )
        )
        state_requirements = state_result.scalars().all()
        for requirement in state_requirements:
            if requirement.compliance_deadline:
                days_until = (requirement.compliance_deadline - date.today()).days
                if days_until <= 120:
                    dashboard["upcoming_deadlines"].append({
                        "type": "State Library Requirement",
                        "state": requirement.state_code,
                        "requirement": requirement.requirement_name,
                        "due_date": requirement.compliance_deadline.isoformat(),
                        "days_until": days_until,
                        "priority": "critical" if days_until <= 14 else "high" if days_until <= 30 else "normal"
                    })

            if requirement.annual_report_required and requirement.annual_report_due_date:
                days_until = (requirement.annual_report_due_date - date.today()).days
                if days_until <= 120 and not requirement.annual_report_submitted:
                    dashboard["upcoming_deadlines"].append({
                        "type": "State Annual Report",
                        "state": requirement.state_code,
                        "requirement": requirement.requirement_name,
                        "due_date": requirement.annual_report_due_date.isoformat(),
                        "days_until": days_until,
                        "priority": "critical" if days_until <= 14 else "high" if days_until <= 30 else "normal"
                    })

        # Insurance expiration tracking
        insurance_result = await db.execute(
            select(InsurancePolicy).where(
                and_(
                    InsurancePolicy.organization_id == organization_id,
                    InsurancePolicy.expiration_date >= date.today()
                )
            ).order_by(InsurancePolicy.expiration_date)
        )
        policies = insurance_result.scalars().all()
        for policy in policies:
            days_until = (policy.expiration_date - date.today()).days
            if days_until <= 90:  # Show if within 3 months
                dashboard["upcoming_deadlines"].append({
                    "type": f"{policy.policy_type} Insurance",
                    "policy_number": policy.policy_number,
                    "due_date": policy.expiration_date.isoformat(),
                    "days_until": days_until,
                    "priority": "critical" if days_until <= 30 else "high"
                })

        # Safety inspection tracking
        inspection_result = await db.execute(
            select(SafetyInspection).where(
                and_(
                    SafetyInspection.organization_id == organization_id,
                    SafetyInspection.next_inspection_due >= date.today()
                )
            ).order_by(SafetyInspection.next_inspection_due)
        )
        inspections = inspection_result.scalars().all()
        for inspection in inspections:
            days_until = (inspection.next_inspection_due - date.today()).days
            if days_until <= 60:  # Show if within 2 months
                dashboard["upcoming_deadlines"].append({
                    "type": f"{inspection.inspection_type} Inspection",
                    "location": inspection.location,
                    "due_date": inspection.next_inspection_due.isoformat(),
                    "days_until": days_until,
                    "priority": "critical" if days_until <= 14 else "high" if days_until <= 30 else "normal"
                })

        # Staff certification tracking
        cert_result = await db.execute(
            select(StaffCertification).where(
                and_(
                    StaffCertification.organization_id == organization_id,
                    StaffCertification.next_renewal_due.isnot(None),
                    StaffCertification.next_renewal_due >= date.today()
                )
            ).order_by(StaffCertification.next_renewal_due)
        )
        certs = cert_result.scalars().all()
        for cert in certs:
            if cert.next_renewal_due:
                days_until = (cert.next_renewal_due - date.today()).days
                if days_until <= 60:  # Show if within 2 months
                    dashboard["upcoming_deadlines"].append({
                        "type": "Staff Certification Renewal",
                        "certification": cert.certification_name,
                        "user_id": cert.user_id,
                        "due_date": cert.next_renewal_due.isoformat(),
                        "days_until": days_until,
                        "priority": "high" if days_until <= 30 else "normal"
                    })

        # Policy review schedule
        policy_result = await db.execute(
            select(PolicyReview).where(
                and_(
                    PolicyReview.organization_id == organization_id,
                    PolicyReview.next_review_due >= date.today()
                )
            ).order_by(PolicyReview.next_review_due)
        )
        policies_review = policy_result.scalars().all()
        for policy in policies_review:
            days_until = (policy.next_review_due - date.today()).days
            if days_until <= 60:  # Show if within 2 months
                dashboard["upcoming_deadlines"].append({
                    "type": "Policy Review Due",
                    "policy": policy.policy_name,
                    "due_date": policy.next_review_due.isoformat(),
                    "days_until": days_until,
                    "priority": "high" if days_until <= 30 else "normal"
                })

        # Audit readiness checklist schedule
        audit_result = await db.execute(
            select(AuditReadinessChecklist).where(
                and_(
                    AuditReadinessChecklist.organization_id == organization_id,
                    AuditReadinessChecklist.created_for_audit_date.isnot(None),
                    AuditReadinessChecklist.created_for_audit_date >= date.today(),
                    AuditReadinessChecklist.audit_completed == False,
                )
            ).order_by(AuditReadinessChecklist.created_for_audit_date)
        )
        audits = audit_result.scalars().all()
        for audit in audits:
            if audit.created_for_audit_date:
                days_until = (audit.created_for_audit_date - date.today()).days
                if days_until <= 120:
                    dashboard["upcoming_deadlines"].append({
                        "type": "Audit Readiness Check",
                        "audit_type": audit.audit_type,
                        "due_date": audit.created_for_audit_date.isoformat(),
                        "days_until": days_until,
                        "priority": "critical" if days_until <= 14 else "high" if days_until <= 30 else "normal",
                    })

        # Sort deadlines by days_until
        dashboard["upcoming_deadlines"] = sorted(
            dashboard["upcoming_deadlines"],
            key=lambda x: x["days_until"]
        )

        # Critical items (overdue or expiring within 7 days)
        dashboard["critical_items"] = [
            item for item in dashboard["upcoming_deadlines"]
            if item["days_until"] <= 7 or item["priority"] == "critical"
        ]

        return dashboard

    @staticmethod
    async def check_and_create_deadline_alerts(
        db: AsyncSession,
        organization_id: int
    ) -> List[ComplianceDeadlineAlert]:
        alerts_created = []
        today = date.today()

        # Core compliance framework deadlines
        ada_result = await db.execute(
            select(ADACompliance).where(
                and_(
                    ADACompliance.organization_id == organization_id,
                    ADACompliance.next_assessment_due.isnot(None),
                    ADACompliance.next_assessment_due >= today,
                    ADACompliance.next_assessment_due <= today + timedelta(days=120),
                )
            )
        )
        for ada in ada_result.scalars().all():
            alert = await _create_or_update_alert(
                db=db,
                organization_id=organization_id,
                alert_type="ada_assessment_due",
                source_model="ADACompliance",
                source_id=ada.id,
                deadline_date=ada.next_assessment_due,
                recipient_emails=[]
            )
            alerts_created.append(alert)

        cipa_result = await db.execute(
            select(CIPACompliance).where(
                and_(
                    CIPACompliance.organization_id == organization_id,
                    CIPACompliance.next_check_due.isnot(None),
                    CIPACompliance.next_check_due >= today,
                    CIPACompliance.next_check_due <= today + timedelta(days=120),
                )
            )
        )
        for cipa in cipa_result.scalars().all():
            alert = await _create_or_update_alert(
                db=db,
                organization_id=organization_id,
                alert_type="cipa_filtering_review_due",
                source_model="CIPACompliance",
                source_id=cipa.id,
                deadline_date=cipa.next_check_due,
                recipient_emails=[]
            )
            alerts_created.append(alert)

        coppa_result = await db.execute(
            select(COPPACompliance).where(
                and_(
                    COPPACompliance.organization_id == organization_id,
                    COPPACompliance.next_training_due.isnot(None),
                    COPPACompliance.next_training_due >= today,
                    COPPACompliance.next_training_due <= today + timedelta(days=120),
                )
            )
        )
        for coppa in coppa_result.scalars().all():
            alert = await _create_or_update_alert(
                db=db,
                organization_id=organization_id,
                alert_type="coppa_training_due",
                source_model="COPPACompliance",
                source_id=coppa.id,
                deadline_date=coppa.next_training_due,
                recipient_emails=[]
            )
            alerts_created.append(alert)

        pci_result = await db.execute(
            select(PCICompliance).where(
                and_(
                    PCICompliance.organization_id == organization_id,
                    PCICompliance.next_assessment_due.isnot(None),
                    PCICompliance.next_assessment_due >= today,
                    PCICompliance.next_assessment_due <= today + timedelta(days=120),
                )
            )
        )
        for pci in pci_result.scalars().all():
            alert = await _create_or_update_alert(
                db=db,
                organization_id=organization_id,
                alert_type="pci_assessment_due",
                source_model="PCICompliance",
                source_id=pci.id,
                deadline_date=pci.next_assessment_due,
                recipient_emails=[]
            )
            alerts_created.append(alert)

        # Check insurance policies
        insurance_result = await db.execute(
            select(InsurancePolicy).where(
                and_(
                    InsurancePolicy.organization_id == organization_id,
                    InsurancePolicy.expiration_date >= today,
                    InsurancePolicy.expiration_date <= today + timedelta(days=90)
                )
            )
        )
        for policy in insurance_result.scalars().all():
            alert = await _create_or_update_alert(
                db=db,
                organization_id=organization_id,
                alert_type=f"insurance_expiration_{policy.policy_type}",
                source_model="InsurancePolicy",
                source_id=policy.id,
                deadline_date=policy.expiration_date,
                recipient_emails=[]  # Will be populated from org settings
            )
            alerts_created.append(alert)

        # Check safety inspections
        inspection_result = await db.execute(
            select(SafetyInspection).where(
                and_(
                    SafetyInspection.organization_id == organization_id,
                    SafetyInspection.next_inspection_due >= today,
                    SafetyInspection.next_inspection_due <= today + timedelta(days=60)
                )
            )
        )
        for inspection in inspection_result.scalars().all():
            alert = await _create_or_update_alert(
                db=db,
                organization_id=organization_id,
                alert_type=f"inspection_due_{inspection.inspection_type}",
                source_model="SafetyInspection",
                source_id=inspection.id,
                deadline_date=inspection.next_inspection_due,
                recipient_emails=[]
            )
            alerts_created.append(alert)

        # Check staff certifications
        cert_result = await db.execute(
            select(StaffCertification).where(
                and_(
                    StaffCertification.organization_id == organization_id,
                    StaffCertification.next_renewal_due.isnot(None),
                    StaffCertification.next_renewal_due >= today,
                    StaffCertification.next_renewal_due <= today + timedelta(days=60)
                )
            )
        )
        for cert in cert_result.scalars().all():
            alert = await _create_or_update_alert(
                db=db,
                organization_id=organization_id,
                alert_type=f"cert_renewal_{cert.certification_type}",
                source_model="StaffCertification",
                source_id=cert.id,
                deadline_date=cert.next_renewal_due,
                recipient_emails=[]
            )
            alerts_created.append(alert)

        # Check policy reviews
        policy_result = await db.execute(
            select(PolicyReview).where(
                and_(
                    PolicyReview.organization_id == organization_id,
                    PolicyReview.next_review_due >= today,
                    PolicyReview.next_review_due <= today + timedelta(days=60)
                )
            )
        )
        for policy in policy_result.scalars().all():
            alert = await _create_or_update_alert(
                db=db,
                organization_id=organization_id,
                alert_type="policy_review_due",
                source_model="PolicyReview",
                source_id=policy.id,
                deadline_date=policy.next_review_due,
                recipient_emails=[]
            )
            alerts_created.append(alert)

        # State library requirements and filings
        state_result = await db.execute(
            select(StateLibraryRequirement).where(
                and_(
                    StateLibraryRequirement.organization_id == organization_id,
                    StateLibraryRequirement.compliance_deadline.isnot(None),
                    StateLibraryRequirement.compliance_deadline >= today,
                    StateLibraryRequirement.compliance_deadline <= today + timedelta(days=120),
                )
            )
        )
        for requirement in state_result.scalars().all():
            alert = await _create_or_update_alert(
                db=db,
                organization_id=organization_id,
                alert_type=f"state_requirement_due_{requirement.state_code.lower()}",
                source_model="StateLibraryRequirement",
                source_id=requirement.id,
                deadline_date=requirement.compliance_deadline,
                recipient_emails=[]
            )
            alerts_created.append(alert)

        annual_report_result = await db.execute(
            select(StateLibraryRequirement).where(
                and_(
                    StateLibraryRequirement.organization_id == organization_id,
                    StateLibraryRequirement.annual_report_required == True,
                    StateLibraryRequirement.annual_report_submitted == False,
                    StateLibraryRequirement.annual_report_due_date.isnot(None),
                    StateLibraryRequirement.annual_report_due_date >= today,
                    StateLibraryRequirement.annual_report_due_date <= today + timedelta(days=120),
                )
            )
        )
        for requirement in annual_report_result.scalars().all():
            alert = await _create_or_update_alert(
                db=db,
                organization_id=organization_id,
                alert_type=f"state_annual_report_due_{requirement.state_code.lower()}",
                source_model="StateLibraryRequirement",
                source_id=requirement.id,
                deadline_date=requirement.annual_report_due_date,
                recipient_emails=[]
            )
            alerts_created.append(alert)

        # Audit readiness schedule
        audit_result = await db.execute(
            select(AuditReadinessChecklist).where(
                and_(
                    AuditReadinessChecklist.organization_id == organization_id,
                    AuditReadinessChecklist.created_for_audit_date.isnot(None),
                    AuditReadinessChecklist.created_for_audit_date >= today,
                    AuditReadinessChecklist.created_for_audit_date <= today + timedelta(days=120),
                    AuditReadinessChecklist.audit_completed == False,
                )
            )
        )
        for checklist in audit_result.scalars().all():
            alert = await _create_or_update_alert(
                db=db,
                organization_id=organization_id,
                alert_type=f"audit_readiness_due_{checklist.audit_type.lower().replace(' ', '_')}",
                source_model="AuditReadinessChecklist",
                source_id=checklist.id,
                deadline_date=checklist.created_for_audit_date,
                recipient_emails=[]
            )
            alerts_created.append(alert)

        await db.commit()
        return alerts_created

    @staticmethod
    async def update_certification_renewal_date(
        db: AsyncSession,
        certification_id: int
    ) -> StaffCertification:
        result = await db.execute(
            select(StaffCertification).where(StaffCertification.id == certification_id)
        )
        cert = result.scalar_one_or_none()
        if not cert:
            raise ValueError(f"Certification {certification_id} not found")

        if cert.renewal_frequency_months and cert.obtained_date:
            # Calculate next renewal from last renewal or obtained date
            last_renewal = cert.obtained_date
            if cert.expiration_date:
                last_renewal = cert.expiration_date - timedelta(days=1)

            cert.next_renewal_due = last_renewal + timedelta(
                days=30 * cert.renewal_frequency_months
            )

        await db.commit()
        return cert

    @staticmethod
    async def check_staff_certifications_expiring(
        db: AsyncSession,
        organization_id: int,
        days_until: int = 30
    ) -> List[StaffCertification]:
        today = date.today()
        deadline = today + timedelta(days=days_until)

        result = await db.execute(
            select(StaffCertification).where(
                and_(
                    StaffCertification.organization_id == organization_id,
                    StaffCertification.expiration_date.isnot(None),
                    StaffCertification.expiration_date >= today,
                    StaffCertification.expiration_date <= deadline,
                    StaffCertification.is_active == True
                )
            ).order_by(StaffCertification.expiration_date)
        )
        return result.scalars().all()

    @staticmethod
    async def check_policy_reviews_overdue(
        db: AsyncSession,
        organization_id: int
    ) -> List[PolicyReview]:
        today = date.today()

        result = await db.execute(
            select(PolicyReview).where(
                and_(
                    PolicyReview.organization_id == organization_id,
                    PolicyReview.next_review_due < today,
                    PolicyReview.status.in_([
                        PolicyReviewStatus.current,
                        PolicyReviewStatus.pending_review
                    ])
                )
            ).order_by(PolicyReview.next_review_due)
        )
        return result.scalars().all()

    @staticmethod
    async def check_safety_inspections_overdue(
        db: AsyncSession,
        organization_id: int
    ) -> List[SafetyInspection]:
        today = date.today()

        result = await db.execute(
            select(SafetyInspection).where(
                and_(
                    SafetyInspection.organization_id == organization_id,
                    SafetyInspection.next_inspection_due < today
                )
            ).order_by(SafetyInspection.next_inspection_due)
        )
        return result.scalars().all()

    @staticmethod
    async def get_insurance_expiring_soon(
        db: AsyncSession,
        organization_id: int,
        days_until: int = 60
    ) -> List[InsurancePolicy]:
        today = date.today()
        deadline = today + timedelta(days=days_until)

        result = await db.execute(
            select(InsurancePolicy).where(
                and_(
                    InsurancePolicy.organization_id == organization_id,
                    InsurancePolicy.expiration_date >= today,
                    InsurancePolicy.expiration_date <= deadline
                )
            ).order_by(InsurancePolicy.expiration_date)
        )
        return result.scalars().all()

    @staticmethod
    async def get_audit_readiness_summary(
        db: AsyncSession,
        organization_id: int,
        audit_type: str
    ) -> Optional[AuditReadinessChecklist]:
        result = await db.execute(
            select(AuditReadinessChecklist).where(
                and_(
                    AuditReadinessChecklist.organization_id == organization_id,
                    AuditReadinessChecklist.audit_type == audit_type
                )
            ).order_by(AuditReadinessChecklist.created_for_audit_date.desc())
        )
        return result.scalars().first()

    @staticmethod
    async def update_audit_checklist_item(
        db: AsyncSession,
        checklist_id: int,
        item_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> AuditReadinessChecklist:
        result = await db.execute(
            select(AuditReadinessChecklist).where(
                AuditReadinessChecklist.id == checklist_id
            )
        )
        checklist = result.scalar_one_or_none()
        if not checklist:
            raise ValueError(f"Audit checklist {checklist_id} not found")

        if checklist.items and item_id in checklist.items:
            checklist.items[item_id]["status"] = status
            if notes:
                checklist.items[item_id]["notes"] = notes

            # Recalculate completion percentage
            total = len(checklist.items)
            if total > 0:
                completed = sum(1 for item in checklist.items.values()
                               if item.get("status") == "ready")
                checklist.completion_percentage = (completed / total) * 100
                checklist.items_complete = completed
                checklist.items_total = total
                checklist.overall_ready = completed == total

        checklist.checklist_last_updated_date = datetime.now().date()
        await db.commit()
        return checklist

    @staticmethod
    async def create_liability_incident(
        db: AsyncSession,
        organization_id: int,
        incident_date: date,
        incident_type: str,
        incident_description: str,
        location: str,
        **kwargs
    ) -> LiabilityIncident:
        incident = LiabilityIncident(
            organization_id=organization_id,
            incident_date=incident_date,
            incident_type=incident_type,
            incident_description=incident_description,
            location=location,
            incident_reported_date=date.today(),
            **kwargs
        )
        db.add(incident)
        await db.commit()
        await db.refresh(incident)
        return incident


# Helper functions

def _calculate_ada_score(ada: ADACompliance) -> float:
    if ada.status == ADAStatus.compliant:
        return 100.0
    elif ada.status == ADAStatus.partial:
        # Count number of accessibility features implemented
        features = [
            ada.physical_accessibility,
            ada.adaptive_technology,
            ada.accessible_bathrooms,
            ada.accessible_parking,
            ada.service_animal_policy,
            ada.braille_materials,
            ada.large_print_available,
            ada.audio_formats_available,
            ada.accessible_website,
            ada.accessible_catalog
        ]
        completed = sum(features)
        return (completed / len(features)) * 70 + 30
    elif ada.status == ADAStatus.under_remediation:
        return 50.0
    else:
        return 0.0


async def _create_or_update_alert(
    db: AsyncSession,
    organization_id: int,
    alert_type: str,
    source_model: str,
    source_id: int,
    deadline_date: date,
    recipient_emails: List[str]
) -> ComplianceDeadlineAlert:
    # Check if alert already exists
    result = await db.execute(
        select(ComplianceDeadlineAlert).where(
            and_(
                ComplianceDeadlineAlert.organization_id == organization_id,
                ComplianceDeadlineAlert.alert_type == alert_type,
                ComplianceDeadlineAlert.source_id == source_id,
                ComplianceDeadlineAlert.item_completed == False
            )
        )
    )
    alert = result.scalar_one_or_none()

    if alert:
        # Update existing alert
        alert.days_until_deadline = (deadline_date - date.today()).days
        alert.updated_at = datetime.now(datetime.timezone.utc)
    else:
        # Create new alert
        alert = ComplianceDeadlineAlert(
            organization_id=organization_id,
            alert_type=alert_type,
            source_model=source_model,
            source_id=source_id,
            deadline_date=deadline_date,
            days_until_deadline=(deadline_date - date.today()).days,
            recipient_emails=recipient_emails,
            alert_triggered=True
        )
        db.add(alert)

    await db.commit()
    return alert
