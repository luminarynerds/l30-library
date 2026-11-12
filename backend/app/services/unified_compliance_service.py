# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, case, delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit_log import AuditAction, AuditLog
from ..models.cipa_compliance import (
    CIPAComplianceReport, ComputerSession, FilterBypassRequest,
    InternetPolicyAcceptance,
)
from ..models.compliance_tracking import (
    ADACompliance, AuditReadinessChecklist, CIPACompliance, COPPACompliance,
    ComplianceDeadlineAlert, InsurancePolicy, PCICompliance, PolicyReview,
    SafetyInspection, StaffCertification, StateLibraryRequirement,
)
from ..models.law_enforcement_request import LawEnforcementRequest
from ..models.unified_compliance_audit import (
    AccessType, ComplianceIncident, ComplianceReport, UnifiedComplianceRequirement,
    ComplianceViolation, DataCategory, ImmutableAuditEntry, IncidentCategory,
    ComplianceIncidentSeverity, IncidentStatus, RegulationType, ReportStatus, ReportType,
    RequirementStatus, RetentionAction, RetentionPolicyRule, StaffAccessLog,
    VerificationMethod, ViolationSeverity, ViolationStatus,
)
from ..models.user import User, UserRole

logger = get_logger(__name__)


GENESIS_HASH = "0" * 64

_INCIDENT_VALID_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.reported: {IncidentStatus.triaging, IncidentStatus.investigating},
    IncidentStatus.triaging: {IncidentStatus.investigating, IncidentStatus.containing, IncidentStatus.resolved},
    IncidentStatus.investigating: {IncidentStatus.containing, IncidentStatus.remediating, IncidentStatus.resolved},
    IncidentStatus.containing: {IncidentStatus.remediating, IncidentStatus.resolved},
    IncidentStatus.remediating: {IncidentStatus.resolved},
    IncidentStatus.resolved: {IncidentStatus.closed},
    IncidentStatus.closed: set(),
}


class UnifiedComplianceService:

    # ========================================================================
    # Immutable Audit Trail
    # ========================================================================

    @staticmethod
    async def create_audit_entry(
        db: AsyncSession,
        organization_id: int,
        actor_id: Optional[int],
        actor_role: Optional[str],
        actor_email: Optional[str],
        action: str,
        action_category: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_description: Optional[str] = None,
        justification: Optional[str] = None,
        regulation_context: Optional[str] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        data_category: Optional[DataCategory] = None,
        involves_minor: bool = False,
        involves_pii: bool = False,
    ) -> ImmutableAuditEntry:
        # Get the previous entry's hash for chaining
        prev_result = await db.execute(
            select(ImmutableAuditEntry.entry_hash, ImmutableAuditEntry.sequence_number)
            .where(ImmutableAuditEntry.organization_id == organization_id)
            .order_by(desc(ImmutableAuditEntry.sequence_number))
            .limit(1)
        )
        prev_row = prev_result.first()
        previous_hash = prev_row[0] if prev_row else GENESIS_HASH
        sequence_number = (prev_row[1] + 1) if prev_row else 1

        now = datetime.now(timezone.utc)

        entry_hash = ImmutableAuditEntry.compute_hash(
            previous_hash=previous_hash,
            timestamp=now.isoformat(),
            actor_id=str(actor_id or "system"),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id or ""),
            ip_address=str(ip_address or ""),
        )

        entry = ImmutableAuditEntry(
            organization_id=organization_id,
            entry_hash=entry_hash,
            previous_hash=previous_hash,
            sequence_number=sequence_number,
            actor_id=actor_id,
            actor_role=actor_role,
            actor_email=actor_email,
            action=action,
            action_category=action_category,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_description=resource_description,
            justification=justification,
            regulation_context=regulation_context,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            session_id=session_id,
            data_category=data_category,
            involves_minor=involves_minor,
            involves_pii=involves_pii,
        )
        db.add(entry)
        return entry

    @staticmethod
    async def verify_audit_chain_integrity(
        db: AsyncSession,
        organization_id: int,
        start_sequence: int = 1,
        end_sequence: Optional[int] = None,
    ) -> Dict[str, Any]:
        query = (
            select(ImmutableAuditEntry)
            .where(ImmutableAuditEntry.organization_id == organization_id)
            .where(ImmutableAuditEntry.sequence_number >= start_sequence)
        )
        if end_sequence:
            query = query.where(
                ImmutableAuditEntry.sequence_number <= end_sequence
            )
        query = query.order_by(ImmutableAuditEntry.sequence_number)

        result = await db.execute(query)
        entries = result.scalars().all()

        if not entries:
            return {"valid": True, "entries_checked": 0, "tampered_entries": []}

        tampered = []
        expected_prev_hash = GENESIS_HASH

        if entries[0].sequence_number > 1:
            prev_result = await db.execute(
                select(ImmutableAuditEntry.entry_hash)
                .where(
                    ImmutableAuditEntry.organization_id == organization_id,
                    ImmutableAuditEntry.sequence_number == entries[0].sequence_number - 1,
                )
            )
            prev_row = prev_result.first()
            if prev_row:
                expected_prev_hash = prev_row[0]

        for entry in entries:
            if entry.previous_hash != expected_prev_hash:
                tampered.append({
                    "sequence_number": entry.sequence_number,
                    "entry_id": entry.id,
                    "expected_previous_hash": expected_prev_hash,
                    "actual_previous_hash": entry.previous_hash,
                })

            recomputed = ImmutableAuditEntry.compute_hash(
                previous_hash=entry.previous_hash,
                timestamp=entry.created_at.isoformat() if entry.created_at else "",
                actor_id=str(entry.actor_id or "system"),
                action=entry.action,
                resource_type=entry.resource_type,
                resource_id=str(entry.resource_id or ""),
                ip_address=str(entry.ip_address or ""),
            )
            if recomputed != entry.entry_hash:
                tampered.append({
                    "sequence_number": entry.sequence_number,
                    "entry_id": entry.id,
                    "issue": "hash_mismatch",
                    "expected_hash": recomputed,
                    "actual_hash": entry.entry_hash,
                })

            expected_prev_hash = entry.entry_hash

        return {
            "valid": len(tampered) == 0,
            "entries_checked": len(entries),
            "tampered_entries": tampered,
        }

    # ========================================================================
    # Staff Access Logging
    # ========================================================================

    @staticmethod
    async def log_staff_access(
        db: AsyncSession,
        organization_id: int,
        staff_id: int,
        staff_role: str,
        access_type: AccessType,
        data_category: DataCategory,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_description: Optional[str] = None,
        target_patron_id: Optional[int] = None,
        target_is_minor: bool = False,
        justification: Optional[str] = None,
        endpoint: Optional[str] = None,
        query_parameters: Optional[Dict] = None,
        records_accessed_count: int = 1,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> StaffAccessLog:
        now = datetime.now(timezone.utc)
        hour = now.hour
        is_after_hours = hour < 6 or hour > 22

        is_bulk = records_accessed_count > 50

        log_entry = StaffAccessLog(
            organization_id=organization_id,
            staff_id=staff_id,
            staff_role=staff_role,
            access_type=access_type,
            data_category=data_category,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_description=resource_description,
            target_patron_id=target_patron_id,
            target_is_minor=target_is_minor,
            justification=justification,
            endpoint=endpoint,
            query_parameters=query_parameters,
            records_accessed_count=records_accessed_count,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            session_id=session_id,
            is_after_hours=is_after_hours,
            is_bulk_access=is_bulk,
            is_flagged=is_after_hours and is_bulk,
            flag_reason=(
                "After-hours bulk access" if is_after_hours and is_bulk
                else "After-hours access" if is_after_hours and target_is_minor
                else None
            ),
        )
        db.add(log_entry)
        return log_entry

    @staticmethod
    async def get_staff_access_summary(
        db: AsyncSession,
        organization_id: int,
        staff_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

        base_filter = and_(
            StaffAccessLog.organization_id == organization_id,
            StaffAccessLog.accessed_at >= start_dt,
            StaffAccessLog.accessed_at <= end_dt,
        )
        if staff_id:
            base_filter = and_(base_filter, StaffAccessLog.staff_id == staff_id)

        # Total access count
        total_result = await db.execute(
            select(func.count(StaffAccessLog.id)).where(base_filter)
        )
        total = total_result.scalar() or 0

        # By data category
        cat_result = await db.execute(
            select(
                StaffAccessLog.data_category,
                func.count(StaffAccessLog.id),
            )
            .where(base_filter)
            .group_by(StaffAccessLog.data_category)
        )
        by_category = {
            row[0].value if row[0] else "unknown": row[1]
            for row in cat_result.all()
        }

        # By access type
        type_result = await db.execute(
            select(
                StaffAccessLog.access_type,
                func.count(StaffAccessLog.id),
            )
            .where(base_filter)
            .group_by(StaffAccessLog.access_type)
        )
        by_type = {
            row[0].value if row[0] else "unknown": row[1]
            for row in type_result.all()
        }

        # Flagged count
        flagged_result = await db.execute(
            select(func.count(StaffAccessLog.id))
            .where(base_filter)
            .where(StaffAccessLog.is_flagged == True)
        )
        flagged_count = flagged_result.scalar() or 0

        # Minor data access count
        minor_result = await db.execute(
            select(func.count(StaffAccessLog.id))
            .where(base_filter)
            .where(StaffAccessLog.target_is_minor == True)
        )
        minor_access_count = minor_result.scalar() or 0

        # Top staff accessors (if not filtered to one staff)
        top_staff = []
        if not staff_id:
            staff_result = await db.execute(
                select(
                    StaffAccessLog.staff_id,
                    func.count(StaffAccessLog.id).label("access_count"),
                )
                .where(base_filter)
                .group_by(StaffAccessLog.staff_id)
                .order_by(desc("access_count"))
                .limit(10)
            )
            top_staff = [
                {"staff_id": row[0], "access_count": row[1]}
                for row in staff_result.all()
            ]

        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_accesses": total,
            "by_category": by_category,
            "by_type": by_type,
            "flagged_count": flagged_count,
            "minor_data_accesses": minor_access_count,
            "top_staff_accessors": top_staff,
        }

    # ========================================================================
    # Automated Compliance Scanning
    # ========================================================================

    @staticmethod
    async def run_compliance_scan(
        db: AsyncSession,
        organization_id: int,
    ) -> Dict[str, Any]:
        scan_id = f"scan-{uuid.uuid4().hex[:12]}"
        violations_found = []
        now = datetime.now(timezone.utc)
        today = date.today()

        # 1. Check for overdue requirement verifications
        overdue_reqs = await db.execute(
            select(UnifiedComplianceRequirement).where(
                and_(
                    UnifiedComplianceRequirement.organization_id == organization_id,
                    UnifiedComplianceRequirement.is_active == True,
                    UnifiedComplianceRequirement.next_verification_due.isnot(None),
                    UnifiedComplianceRequirement.next_verification_due < today,
                    UnifiedComplianceRequirement.status.in_([
                        RequirementStatus.implemented,
                        RequirementStatus.verified,
                    ]),
                )
            )
        )
        for req in overdue_reqs.scalars().all():
            days_overdue = (today - req.next_verification_due).days
            severity = (
                ViolationSeverity.critical if days_overdue > 90
                else ViolationSeverity.high if days_overdue > 30
                else ViolationSeverity.medium
            )
            violation = ComplianceViolation(
                organization_id=organization_id,
                requirement_id=req.id,
                title=f"Overdue verification: {req.requirement_title}",
                description=(
                    f"Requirement '{req.requirement_code}' verification is "
                    f"{days_overdue} days overdue. Last verified: "
                    f"{req.last_verified_date}. Due: {req.next_verification_due}."
                ),
                severity=severity,
                status=ViolationStatus.detected,
                detected_by="automated_scan",
                detection_method="scheduled_compliance_scan",
                scan_id=scan_id,
            )
            db.add(violation)
            violations_found.append({
                "type": "overdue_verification",
                "requirement": req.requirement_code,
                "severity": severity.value,
                "days_overdue": days_overdue,
            })

        # 2. Check expired staff certifications
        expired_certs = await db.execute(
            select(StaffCertification).where(
                and_(
                    StaffCertification.organization_id == organization_id,
                    StaffCertification.is_active == True,
                    StaffCertification.expiration_date.isnot(None),
                    StaffCertification.expiration_date < today,
                )
            )
        )
        # Find or create requirement for staff certs
        cert_req_result = await db.execute(
            select(UnifiedComplianceRequirement).where(
                and_(
                    UnifiedComplianceRequirement.organization_id == organization_id,
                    UnifiedComplianceRequirement.requirement_code == "STAFF-CERT-CURRENT",
                )
            )
        )
        cert_req = cert_req_result.scalar_one_or_none()

        for cert in expired_certs.scalars().all():
            if cert_req:
                violation = ComplianceViolation(
                    organization_id=organization_id,
                    requirement_id=cert_req.id,
                    title=f"Expired certification: {cert.certification_name}",
                    description=(
                        f"Staff certification '{cert.certification_name}' for "
                        f"user {cert.user_id} expired on {cert.expiration_date}."
                    ),
                    severity=ViolationSeverity.high,
                    status=ViolationStatus.detected,
                    detected_by="automated_scan",
                    detection_method="scheduled_compliance_scan",
                    scan_id=scan_id,
                    affected_users_count=1,
                )
                db.add(violation)
                violations_found.append({
                    "type": "expired_certification",
                    "certification": cert.certification_name,
                    "user_id": cert.user_id,
                    "severity": "high",
                })

        # 3. Check expired insurance policies
        expired_insurance = await db.execute(
            select(InsurancePolicy).where(
                and_(
                    InsurancePolicy.organization_id == organization_id,
                    InsurancePolicy.expiration_date < today,
                )
            )
        )
        for policy in expired_insurance.scalars().all():
            violations_found.append({
                "type": "expired_insurance",
                "policy": policy.policy_name,
                "expired": policy.expiration_date.isoformat(),
                "severity": "critical",
            })

        # 4. Check overdue safety inspections
        overdue_inspections = await db.execute(
            select(SafetyInspection).where(
                and_(
                    SafetyInspection.organization_id == organization_id,
                    SafetyInspection.next_inspection_due < today,
                )
            )
        )
        for inspection in overdue_inspections.scalars().all():
            violations_found.append({
                "type": "overdue_inspection",
                "inspection_type": str(inspection.inspection_type),
                "location": inspection.location,
                "severity": "high",
            })

        # 5. Check overdue policy reviews
        overdue_policies = await db.execute(
            select(PolicyReview).where(
                and_(
                    PolicyReview.organization_id == organization_id,
                    PolicyReview.next_review_due < today,
                )
            )
        )
        for policy in overdue_policies.scalars().all():
            violations_found.append({
                "type": "overdue_policy_review",
                "policy": policy.policy_name,
                "due_date": policy.next_review_due.isoformat(),
                "severity": "medium",
            })

        # 6. Check retention policy execution status
        overdue_retention = await db.execute(
            select(RetentionPolicyRule).where(
                and_(
                    RetentionPolicyRule.organization_id == organization_id,
                    RetentionPolicyRule.is_active == True,
                    RetentionPolicyRule.next_execution_at.isnot(None),
                    RetentionPolicyRule.next_execution_at < now,
                )
            )
        )
        for rule in overdue_retention.scalars().all():
            violations_found.append({
                "type": "overdue_retention_execution",
                "rule": rule.rule_name,
                "severity": "medium",
            })

        scan_result = {
            "scan_id": scan_id,
            "organization_id": organization_id,
            "scanned_at": now.isoformat(),
            "violations_found": len(violations_found),
            "violations": violations_found,
        }

        logger.info(
            f"Compliance scan {scan_id} complete: "
            f"{len(violations_found)} violations found"
        )
        return scan_result

    # ========================================================================
    # Retention Policy Enforcement
    # ========================================================================

    @staticmethod
    async def enforce_retention_policies(
        db: AsyncSession,
        organization_id: int,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        results = {"rules_executed": 0, "actions": []}

        due_rules = await db.execute(
            select(RetentionPolicyRule).where(
                and_(
                    RetentionPolicyRule.organization_id == organization_id,
                    RetentionPolicyRule.is_active == True,
                    or_(
                        RetentionPolicyRule.next_execution_at.is_(None),
                        RetentionPolicyRule.next_execution_at <= now,
                    ),
                )
            )
        )

        for rule in due_rules.scalars().all():
            rule.last_executed_at = now
            rule.next_execution_at = now + timedelta(
                hours=rule.execution_frequency_hours
            )

            results["actions"].append({
                "rule_id": rule.id,
                "rule_name": rule.rule_name,
                "action": str(rule.expiry_action),
                "data_category": str(rule.data_category),
                "target_table": rule.target_table,
            })
            results["rules_executed"] += 1

            logger.info(
                f"Retention policy '{rule.rule_name}' executed: "
                f"{rule.expiry_action} on {rule.target_table}"
            )

        if results["rules_executed"] > 0:
            await db.commit()

        return results

    # ========================================================================
    # Incident Management
    # ========================================================================

    @staticmethod
    async def create_incident(
        db: AsyncSession,
        organization_id: int,
        reported_by_id: int,
        category: IncidentCategory,
        severity: ComplianceIncidentSeverity,
        title: str,
        description: str,
        discovery_date: Optional[datetime] = None,
        **kwargs,
    ) -> ComplianceIncident:
        now = datetime.now(timezone.utc)
        incident_number = f"INC-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        incident = ComplianceIncident(
            organization_id=organization_id,
            incident_number=incident_number,
            category=category,
            severity=severity,
            status=IncidentStatus.reported,
            title=title,
            description=description,
            discovery_date=discovery_date or now,
            reported_by_id=reported_by_id,
            **kwargs,
        )
        db.add(incident)

        if severity in (ComplianceIncidentSeverity.critical, ComplianceIncidentSeverity.major):
            if category == IncidentCategory.data_breach:
                incident.notification_required = True
                incident.notification_deadline = now + timedelta(hours=72)

        await db.flush()
        return incident

    @staticmethod
    async def update_incident_status(
        db: AsyncSession,
        incident_id: int,
        new_status: IncidentStatus,
        updated_by_id: int,
        notes: Optional[str] = None,
    ) -> ComplianceIncident:
        result = await db.execute(
            select(ComplianceIncident).where(ComplianceIncident.id == incident_id).with_for_update()
        )
        incident = result.scalar_one_or_none()
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        allowed = _INCIDENT_VALID_TRANSITIONS.get(incident.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {incident.status.value!r} -> {new_status.value!r}. "
                f"Allowed next statuses: {[s.value for s in allowed] or 'none (terminal)'}"
            )

        now = datetime.now(timezone.utc)
        incident.status = new_status

        if new_status == IncidentStatus.triaging:
            incident.triaged_at = now
        elif new_status == IncidentStatus.containing:
            incident.contained_at = now
            incident.is_contained = True
        elif new_status == IncidentStatus.resolved:
            incident.resolved_at = now
        elif new_status == IncidentStatus.closed:
            incident.closed_at = now

        if notes:
            incident.notes = (
                f"{incident.notes}\n\n[{now.isoformat()}] {notes}"
                if incident.notes else f"[{now.isoformat()}] {notes}"
            )

        return incident

    # ========================================================================
    # Report Generation
    # ========================================================================

    @staticmethod
    async def generate_report(
        db: AsyncSession,
        organization_id: int,
        report_type: ReportType,
        period_start: date,
        period_end: date,
        generated_by_id: int,
    ) -> ComplianceReport:
        report_data = {}
        title = ""

        start_dt = datetime.combine(
            period_start, datetime.min.time(), tzinfo=timezone.utc
        )
        end_dt = datetime.combine(
            period_end, datetime.max.time(), tzinfo=timezone.utc
        )

        if report_type == ReportType.board_executive:
            title = f"Board Executive Compliance Summary ({period_start} - {period_end})"
            report_data = await _build_board_executive_report(
                db, organization_id, start_dt, end_dt
            )

        elif report_type == ReportType.cipa_erate:
            title = f"CIPA E-Rate Compliance Report ({period_start} - {period_end})"
            report_data = await _build_cipa_report(
                db, organization_id, start_dt, end_dt
            )

        elif report_type == ReportType.law_enforcement_transparency:
            title = f"Law Enforcement Transparency Report ({period_start} - {period_end})"
            report_data = await _build_law_enforcement_report(
                db, organization_id, start_dt, end_dt
            )

        elif report_type == ReportType.staff_access_review:
            title = f"Staff Data Access Review ({period_start} - {period_end})"
            report_data = await _build_staff_access_report(
                db, organization_id, start_dt, end_dt
            )

        elif report_type == ReportType.incident_summary:
            title = f"Compliance Incident Summary ({period_start} - {period_end})"
            report_data = await _build_incident_report(
                db, organization_id, start_dt, end_dt
            )

        elif report_type == ReportType.violation_summary:
            title = f"Compliance Violation Summary ({period_start} - {period_end})"
            report_data = await _build_violation_report(
                db, organization_id, start_dt, end_dt
            )

        elif report_type == ReportType.data_retention:
            title = f"Data Retention Compliance Report ({period_start} - {period_end})"
            report_data = await _build_retention_report(
                db, organization_id, start_dt, end_dt
            )

        else:
            title = f"Compliance Report ({period_start} - {period_end})"
            report_data = {"note": "Report type not yet implemented"}

        # Calculate compliance score
        req_result = await db.execute(
            select(
                func.count(UnifiedComplianceRequirement.id).label("total"),
                func.count(
                    case(
                        (UnifiedComplianceRequirement.status.in_([
                            RequirementStatus.verified,
                            RequirementStatus.implemented,
                        ]), UnifiedComplianceRequirement.id),
                    )
                ).label("compliant"),
                func.count(
                    case(
                        (UnifiedComplianceRequirement.status == RequirementStatus.non_compliant,
                         UnifiedComplianceRequirement.id),
                    )
                ).label("non_compliant"),
            ).where(
                and_(
                    UnifiedComplianceRequirement.organization_id == organization_id,
                    UnifiedComplianceRequirement.is_active == True,
                )
            )
        )
        counts = req_result.first()
        total_reqs = counts[0] or 0
        compliant = counts[1] or 0
        non_compliant = counts[2] or 0
        score = (compliant / total_reqs * 100) if total_reqs > 0 else 0.0

        # Count violations and incidents
        violations_result = await db.execute(
            select(func.count(ComplianceViolation.id)).where(
                and_(
                    ComplianceViolation.organization_id == organization_id,
                    ComplianceViolation.detected_at >= start_dt,
                    ComplianceViolation.detected_at <= end_dt,
                )
            )
        )
        violations_count = violations_result.scalar() or 0

        incidents_result = await db.execute(
            select(func.count(ComplianceIncident.id)).where(
                and_(
                    ComplianceIncident.organization_id == organization_id,
                    ComplianceIncident.reported_at >= start_dt,
                    ComplianceIncident.reported_at <= end_dt,
                )
            )
        )
        incidents_count = incidents_result.scalar() or 0

        report = ComplianceReport(
            organization_id=organization_id,
            report_type=report_type,
            title=title,
            period_start=period_start,
            period_end=period_end,
            status=ReportStatus.generated,
            report_data=report_data,
            total_requirements=total_reqs,
            compliant_count=compliant,
            non_compliant_count=non_compliant,
            violations_count=violations_count,
            incidents_count=incidents_count,
            compliance_score=round(score, 1),
            generated_by_id=generated_by_id,
        )
        db.add(report)
        await db.flush()
        return report

    # ========================================================================
    # Compliance Officer Dashboard
    # ========================================================================

    @staticmethod
    async def get_officer_dashboard(
        db: AsyncSession,
        organization_id: int,
    ) -> Dict[str, Any]:
        today = date.today()
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # Overall requirement status
        req_stats = await db.execute(
            select(
                UnifiedComplianceRequirement.status,
                func.count(UnifiedComplianceRequirement.id),
            )
            .where(
                and_(
                    UnifiedComplianceRequirement.organization_id == organization_id,
                    UnifiedComplianceRequirement.is_active == True,
                )
            )
            .group_by(UnifiedComplianceRequirement.status)
        )
        requirement_counts = {
            row[0].value: row[1] for row in req_stats.all()
        }
        total_reqs = sum(requirement_counts.values())
        compliant_reqs = (
            requirement_counts.get("verified", 0)
            + requirement_counts.get("implemented", 0)
        )

        # Requirements by regulation
        reg_stats = await db.execute(
            select(
                UnifiedComplianceRequirement.regulation_type,
                func.count(UnifiedComplianceRequirement.id),
                func.count(
                    case(
                        (UnifiedComplianceRequirement.status.in_([
                            RequirementStatus.verified,
                            RequirementStatus.implemented,
                        ]), UnifiedComplianceRequirement.id),
                    )
                ),
            )
            .where(
                and_(
                    UnifiedComplianceRequirement.organization_id == organization_id,
                    UnifiedComplianceRequirement.is_active == True,
                )
            )
            .group_by(UnifiedComplianceRequirement.regulation_type)
        )
        by_regulation = {
            row[0].value: {
                "total": row[1],
                "compliant": row[2],
                "score": round(row[2] / row[1] * 100, 1) if row[1] > 0 else 0.0,
            }
            for row in reg_stats.all()
        }

        # Open violations
        open_violations = await db.execute(
            select(
                ComplianceViolation.severity,
                func.count(ComplianceViolation.id),
            )
            .where(
                and_(
                    ComplianceViolation.organization_id == organization_id,
                    ComplianceViolation.status.notin_([
                        ViolationStatus.resolved,
                        ViolationStatus.false_positive,
                        ViolationStatus.accepted_risk,
                    ]),
                )
            )
            .group_by(ComplianceViolation.severity)
        )
        violation_counts = {
            row[0].value: row[1] for row in open_violations.all()
        }

        # Open incidents
        open_incidents = await db.execute(
            select(
                ComplianceIncident.severity,
                func.count(ComplianceIncident.id),
            )
            .where(
                and_(
                    ComplianceIncident.organization_id == organization_id,
                    ComplianceIncident.status.notin_([
                        IncidentStatus.resolved,
                        IncidentStatus.closed,
                    ]),
                )
            )
            .group_by(ComplianceIncident.severity)
        )
        incident_counts = {
            row[0].value: row[1] for row in open_incidents.all()
        }

        # Upcoming deadlines (next 30 days)
        upcoming_verifications = await db.execute(
            select(UnifiedComplianceRequirement)
            .where(
                and_(
                    UnifiedComplianceRequirement.organization_id == organization_id,
                    UnifiedComplianceRequirement.is_active == True,
                    UnifiedComplianceRequirement.next_verification_due.isnot(None),
                    UnifiedComplianceRequirement.next_verification_due <= today + timedelta(days=30),
                )
            )
            .order_by(UnifiedComplianceRequirement.next_verification_due)
            .limit(10)
        )
        upcoming = [
            {
                "type": "verification",
                "title": req.requirement_title,
                "regulation": str(req.regulation_type),
                "due_date": req.next_verification_due.isoformat(),
                "days_until": (req.next_verification_due - today).days,
                "overdue": req.next_verification_due < today,
            }
            for req in upcoming_verifications.scalars().all()
        ]

        # Recent staff access flags
        flagged_access = await db.execute(
            select(func.count(StaffAccessLog.id)).where(
                and_(
                    StaffAccessLog.organization_id == organization_id,
                    StaffAccessLog.is_flagged == True,
                    StaffAccessLog.accessed_at >= thirty_days_ago,
                )
            )
        )
        flagged_count = flagged_access.scalar() or 0

        # Law enforcement requests
        le_pending = await db.execute(
            select(func.count(LawEnforcementRequest.id)).where(
                LawEnforcementRequest.workflow_status.notin_([
                    "completed", "rejected", "withdrawn"
                ])
            )
        )
        le_pending_count = le_pending.scalar() or 0

        # Notification deadlines (incidents requiring notification)
        pending_notifications = await db.execute(
            select(func.count(ComplianceIncident.id)).where(
                and_(
                    ComplianceIncident.organization_id == organization_id,
                    ComplianceIncident.notification_required == True,
                    ComplianceIncident.notification_sent == False,
                )
            )
        )
        pending_notification_count = pending_notifications.scalar() or 0

        compliance_score = (
            round(compliant_reqs / total_reqs * 100, 1)
            if total_reqs > 0 else 0.0
        )

        return {
            "organization_id": organization_id,
            "generated_at": now.isoformat(),
            "compliance_score": compliance_score,
            "requirements": {
                "total": total_reqs,
                "by_status": requirement_counts,
                "by_regulation": by_regulation,
            },
            "violations": {
                "open_by_severity": violation_counts,
                "total_open": sum(violation_counts.values()),
            },
            "incidents": {
                "open_by_severity": incident_counts,
                "total_open": sum(incident_counts.values()),
                "pending_notifications": pending_notification_count,
            },
            "staff_access": {
                "flagged_last_30_days": flagged_count,
            },
            "law_enforcement": {
                "pending_requests": le_pending_count,
            },
            "upcoming_deadlines": upcoming,
        }


# ============================================================================
# Private Report Builders
# ============================================================================

async def _build_board_executive_report(
    db: AsyncSession, org_id: int, start: datetime, end: datetime
) -> Dict[str, Any]:
    # Requirement status snapshot
    req_result = await db.execute(
        select(
            UnifiedComplianceRequirement.regulation_type,
            UnifiedComplianceRequirement.status,
            func.count(UnifiedComplianceRequirement.id),
        )
        .where(
            and_(
                UnifiedComplianceRequirement.organization_id == org_id,
                UnifiedComplianceRequirement.is_active == True,
            )
        )
        .group_by(UnifiedComplianceRequirement.regulation_type, UnifiedComplianceRequirement.status)
    )
    regulation_status = {}
    for row in req_result.all():
        reg = row[0].value
        status = row[1].value
        if reg not in regulation_status:
            regulation_status[reg] = {}
        regulation_status[reg][status] = row[2]

    # Violation trend
    violation_result = await db.execute(
        select(
            ComplianceViolation.severity,
            func.count(ComplianceViolation.id),
        )
        .where(
            and_(
                ComplianceViolation.organization_id == org_id,
                ComplianceViolation.detected_at >= start,
                ComplianceViolation.detected_at <= end,
            )
        )
        .group_by(ComplianceViolation.severity)
    )
    violations_by_severity = {
        row[0].value: row[1] for row in violation_result.all()
    }

    # Incident summary
    incident_result = await db.execute(
        select(
            ComplianceIncident.category,
            func.count(ComplianceIncident.id),
        )
        .where(
            and_(
                ComplianceIncident.organization_id == org_id,
                ComplianceIncident.reported_at >= start,
                ComplianceIncident.reported_at <= end,
            )
        )
        .group_by(ComplianceIncident.category)
    )
    incidents_by_category = {
        row[0].value: row[1] for row in incident_result.all()
    }

    return {
        "regulation_status": regulation_status,
        "violations_by_severity": violations_by_severity,
        "incidents_by_category": incidents_by_category,
    }


async def _build_cipa_report(
    db: AsyncSession, org_id: int, start: datetime, end: datetime
) -> Dict[str, Any]:
    # Session statistics
    session_result = await db.execute(
        select(
            func.count(ComputerSession.id).label("total"),
            func.count(
                case((ComputerSession.is_minor == True, ComputerSession.id))
            ).label("minor"),
            func.count(
                case((ComputerSession.is_minor == False, ComputerSession.id))
            ).label("adult"),
            func.count(
                case((ComputerSession.patron_id.is_(None), ComputerSession.id))
            ).label("guest"),
        ).where(
            and_(
                ComputerSession.started_at >= start,
                ComputerSession.started_at <= end,
            )
        )
    )
    sessions = session_result.first()

    # Policy acceptances
    acceptance_result = await db.execute(
        select(
            func.count(InternetPolicyAcceptance.id).label("total"),
            func.count(
                case(
                    (InternetPolicyAcceptance.is_minor == True,
                     InternetPolicyAcceptance.id)
                )
            ).label("minor"),
        ).where(
            and_(
                InternetPolicyAcceptance.accepted_at >= start,
                InternetPolicyAcceptance.accepted_at <= end,
            )
        )
    )
    acceptances = acceptance_result.first()

    # Filter bypasses
    bypass_result = await db.execute(
        select(
            func.count(FilterBypassRequest.id).label("total"),
            FilterBypassRequest.reason,
        )
        .where(
            and_(
                FilterBypassRequest.created_at >= start,
                FilterBypassRequest.created_at <= end,
            )
        )
        .group_by(FilterBypassRequest.reason)
    )
    bypasses = {
        row[1].value if row[1] else "unknown": row[0]
        for row in bypass_result.all()
    }

    return {
        "sessions": {
            "total": sessions[0] if sessions else 0,
            "minor": sessions[1] if sessions else 0,
            "adult": sessions[2] if sessions else 0,
            "guest": sessions[3] if sessions else 0,
        },
        "policy_acceptances": {
            "total": acceptances[0] if acceptances else 0,
            "minor": acceptances[1] if acceptances else 0,
        },
        "filter_bypasses": bypasses,
        "filtering_active": True,
    }


async def _build_law_enforcement_report(
    db: AsyncSession, org_id: int, start: datetime, end: datetime
) -> Dict[str, Any]:
    le_result = await db.execute(
        select(
            LawEnforcementRequest.request_type,
            LawEnforcementRequest.workflow_status,
            func.count(LawEnforcementRequest.id),
        )
        .where(
            and_(
                LawEnforcementRequest.date_received >= start,
                LawEnforcementRequest.date_received <= end,
            )
        )
        .group_by(
            LawEnforcementRequest.request_type,
            LawEnforcementRequest.workflow_status,
        )
    )

    by_type = {}
    for row in le_result.all():
        rtype = row[0].value if row[0] else "unknown"
        status = row[1].value if row[1] else "unknown"
        if rtype not in by_type:
            by_type[rtype] = {}
        by_type[rtype][status] = row[2]

    total_result = await db.execute(
        select(func.count(LawEnforcementRequest.id)).where(
            and_(
                LawEnforcementRequest.date_received >= start,
                LawEnforcementRequest.date_received <= end,
            )
        )
    )
    total = total_result.scalar() or 0

    return {
        "total_requests": total,
        "by_type_and_status": by_type,
    }


async def _build_staff_access_report(
    db: AsyncSession, org_id: int, start: datetime, end: datetime
) -> Dict[str, Any]:
    # Access by staff member
    staff_result = await db.execute(
        select(
            StaffAccessLog.staff_id,
            StaffAccessLog.data_category,
            func.count(StaffAccessLog.id),
        )
        .where(
            and_(
                StaffAccessLog.organization_id == org_id,
                StaffAccessLog.accessed_at >= start,
                StaffAccessLog.accessed_at <= end,
            )
        )
        .group_by(StaffAccessLog.staff_id, StaffAccessLog.data_category)
    )

    by_staff = {}
    for row in staff_result.all():
        sid = str(row[0])
        cat = row[1].value if row[1] else "unknown"
        if sid not in by_staff:
            by_staff[sid] = {}
        by_staff[sid][cat] = row[2]

    # Flagged accesses
    flagged_result = await db.execute(
        select(
            StaffAccessLog.staff_id,
            StaffAccessLog.flag_reason,
            func.count(StaffAccessLog.id),
        )
        .where(
            and_(
                StaffAccessLog.organization_id == org_id,
                StaffAccessLog.is_flagged == True,
                StaffAccessLog.accessed_at >= start,
                StaffAccessLog.accessed_at <= end,
            )
        )
        .group_by(StaffAccessLog.staff_id, StaffAccessLog.flag_reason)
    )
    flagged = [
        {"staff_id": row[0], "reason": row[1], "count": row[2]}
        for row in flagged_result.all()
    ]

    return {
        "access_by_staff": by_staff,
        "flagged_accesses": flagged,
    }


async def _build_incident_report(
    db: AsyncSession, org_id: int, start: datetime, end: datetime
) -> Dict[str, Any]:
    result = await db.execute(
        select(
            ComplianceIncident.category,
            ComplianceIncident.severity,
            ComplianceIncident.status,
            func.count(ComplianceIncident.id),
        )
        .where(
            and_(
                ComplianceIncident.organization_id == org_id,
                ComplianceIncident.reported_at >= start,
                ComplianceIncident.reported_at <= end,
            )
        )
        .group_by(
            ComplianceIncident.category,
            ComplianceIncident.severity,
            ComplianceIncident.status,
        )
    )
    incidents = [
        {
            "category": row[0].value,
            "severity": row[1].value,
            "status": row[2].value,
            "count": row[3],
        }
        for row in result.all()
    ]

    return {"incidents": incidents}


async def _build_violation_report(
    db: AsyncSession, org_id: int, start: datetime, end: datetime
) -> Dict[str, Any]:
    result = await db.execute(
        select(
            ComplianceViolation.severity,
            ComplianceViolation.status,
            func.count(ComplianceViolation.id),
        )
        .where(
            and_(
                ComplianceViolation.organization_id == org_id,
                ComplianceViolation.detected_at >= start,
                ComplianceViolation.detected_at <= end,
            )
        )
        .group_by(ComplianceViolation.severity, ComplianceViolation.status)
    )
    violations = [
        {
            "severity": row[0].value,
            "status": row[1].value,
            "count": row[2],
        }
        for row in result.all()
    ]

    return {"violations": violations}


async def _build_retention_report(
    db: AsyncSession, org_id: int, start: datetime, end: datetime
) -> Dict[str, Any]:
    rules_result = await db.execute(
        select(RetentionPolicyRule).where(
            RetentionPolicyRule.organization_id == org_id
        )
    )
    rules = [
        {
            "rule_name": rule.rule_name,
            "data_category": str(rule.data_category),
            "retention_days": rule.retention_days,
            "action": str(rule.expiry_action),
            "is_active": rule.is_active,
            "last_executed": (
                rule.last_executed_at.isoformat()
                if rule.last_executed_at else None
            ),
        }
        for rule in rules_result.scalars().all()
    ]

    return {"retention_rules": rules}
