# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..models.staff_safety import (
    StaffPanicAlert, StaffPanicAlertStatus,
    StaffIncidentReport, IncidentStatus, AnonymityLevel,
    AnonymousIncidentPattern,
    RetaliationPreventionPolicy,
    StaffProtectionMeasure,
    StaffSupportResource,
    DataRetentionPolicy
)
from ..models.user import User, UserRole
from ..models.notification import Notification, NotificationType

logger = get_logger(__name__)
settings = get_settings()


class StaffSafetyService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== PANIC ALERTS ====================

    async def activate_panic_alert(
        self,
        staff_id: int,
        location: Optional[str] = None
    ) -> StaffPanicAlert:
        alert = StaffPanicAlert(
            staff_id=staff_id,
            location=location,
            status=StaffPanicAlertStatus.ACTIVATED
        )
        self.db.add(alert)
        await self.db.flush()

        # Notify responders (admins/directors)
        await self._notify_responders_panic_alert(alert)

        # Check if union notification required
        staff = await self.db.get(User, staff_id)
        if staff and staff.role == UserRole.STAFF:
            alert.union_notified = True
            alert.union_notified_at = datetime.now(timezone.utc)
            # Notify union representatives of incident
            logger.info(f"Union notification triggered for {alert}")

        await self.db.commit()
        return alert

    async def acknowledge_panic_alert(
        self,
        alert_id: int,
        responder_id: int
    ) -> StaffPanicAlert:
        alert = await self.db.get(StaffPanicAlert, alert_id)
        alert.responder_id = responder_id
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.status = StaffPanicAlertStatus.ACKNOWLEDGED

        # Notify the staff member who triggered the alert
        responder = await self.db.get(User, responder_id)
        responder_name = responder.full_name if responder else "A manager"
        notification = Notification(
            user_id=alert.staff_id,
            notification_type=NotificationType.PANIC_ALERT,
            subject="Your panic alert has been acknowledged",
            message=f"{responder_name} has acknowledged your panic alert. Help is on the way.",
        )
        self.db.add(notification)

        await self.db.commit()
        return alert

    async def resolve_panic_alert(
        self,
        alert_id: int,
        response_notes: Optional[str] = None,
        is_false_alarm: bool = False
    ) -> StaffPanicAlert:
        alert = await self.db.get(StaffPanicAlert, alert_id)
        alert.resolved_at = datetime.now(timezone.utc)
        alert.response_notes = response_notes
        alert.status = (
            StaffPanicAlertStatus.FALSE_ALARM if is_false_alarm
            else StaffPanicAlertStatus.RESOLVED
        )

        # Set data retention expiration
        alert.data_retention_expires_at = datetime.now(timezone.utc) + timedelta(days=365*3)

        await self.db.commit()
        return alert

    async def get_staff_panic_alerts(
        self,
        staff_id: int,
        limit: int = 50
    ) -> List[StaffPanicAlert]:
        result = await self.db.execute(
            select(StaffPanicAlert)
            .where(StaffPanicAlert.staff_id == staff_id)
            .where(StaffPanicAlert.is_deleted == False)
            .order_by(StaffPanicAlert.activated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    # ==================== INCIDENT REPORTING ====================

    async def file_incident_report(
        self,
        reporting_staff_id: int,
        incident_type: str,
        incident_date: datetime,
        description: str,
        location: Optional[str] = None,
        witness_ids: Optional[List[int]] = None,
        anonymity_level: str = AnonymityLevel.IDENTIFIED,
        severity: Optional[str] = None
    ) -> StaffIncidentReport:
        report = StaffIncidentReport(
            reporting_staff_id=reporting_staff_id,
            incident_type=incident_type,
            incident_date=incident_date,
            incident_location=location,
            description=description,
            witness_ids=witness_ids,
            anonymity_level=anonymity_level,
            is_good_faith=True,
            status=IncidentStatus.REPORTED
        )
        self.db.add(report)
        await self.db.flush()

        # Set data retention expiration
        report.data_retention_expires_at = datetime.now(timezone.utc) + timedelta(days=365*3)

        # Notify management
        await self._notify_management_incident(report)

        # Check if union notification required
        staff = await self.db.get(User, reporting_staff_id)
        if staff and staff.role == UserRole.STAFF:
            report.union_notified = True
            report.union_notified_at = datetime.now(timezone.utc)
            # Notify union representatives of incident
            logger.info(f"Union notification triggered for {report}")

        await self.db.commit()
        return report

    async def update_incident_status(
        self,
        report_id: int,
        new_status: str,
        management_response: Optional[str] = None,
        responded_by_id: Optional[int] = None
    ) -> StaffIncidentReport:
        report = await self.db.get(StaffIncidentReport, report_id)
        report.status = new_status
        if management_response:
            report.management_response = management_response
            report.management_response_date = datetime.now(timezone.utc)
        if responded_by_id:
            report.responded_by_id = responded_by_id

        await self.db.commit()
        return report

    async def can_staff_view_incident(
        self,
        user_id: int,
        report: StaffIncidentReport
    ) -> bool:
        user = await self.db.get(User, user_id)

        # Owner can always view own report
        if report.reporting_staff_id == user_id:
            return True

        # Admin/Director can view
        if user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
            return True

        return False

    async def get_staff_incident_history(
        self,
        staff_id: int,
        limit: int = 50
    ) -> List[StaffIncidentReport]:
        result = await self.db.execute(
            select(StaffIncidentReport)
            .where(StaffIncidentReport.reporting_staff_id == staff_id)
            .where(StaffIncidentReport.is_deleted == False)
            .order_by(StaffIncidentReport.incident_date.desc())
            .limit(limit)
        )
        return result.scalars().all()

    # ==================== ANONYMOUS PATTERNS ====================

    async def create_anonymous_pattern(
        self,
        incident_type: str,
        date_start: datetime,
        date_end: datetime,
        location: Optional[str] = None
    ) -> AnonymousIncidentPattern:
        # Count incidents in period (anonymized)
        result = await self.db.execute(
            select(func.count(StaffIncidentReport.id))
            .where(StaffIncidentReport.incident_type == incident_type)
            .where(StaffIncidentReport.incident_date >= date_start)
            .where(StaffIncidentReport.incident_date <= date_end)
            .where(StaffIncidentReport.is_deleted == False)
            .where(
                location is None or
                StaffIncidentReport.incident_location == location
            )
        )
        report_count = result.scalar() or 0

        pattern = AnonymousIncidentPattern(
            incident_type=incident_type,
            location=location,
            date_start=date_start,
            date_end=date_end,
            report_count=report_count
        )
        self.db.add(pattern)
        await self.db.commit()
        return pattern

    async def get_incident_patterns(
        self,
        days_back: int = 30
    ) -> List[AnonymousIncidentPattern]:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        result = await self.db.execute(
            select(AnonymousIncidentPattern)
            .where(AnonymousIncidentPattern.date_start >= cutoff_date)
            .order_by(AnonymousIncidentPattern.date_start.desc())
        )
        return result.scalars().all()

    # ==================== RETALIATION PREVENTION ====================

    async def get_retaliation_policies(self) -> List[RetaliationPreventionPolicy]:
        result = await self.db.execute(
            select(RetaliationPreventionPolicy)
            .where(RetaliationPreventionPolicy.is_active == True)
            .order_by(RetaliationPreventionPolicy.effective_date.desc())
        )
        return result.scalars().all()

    async def create_retaliation_policy(
        self,
        name: str,
        description: str,
        policy_type: str,
        created_by_id: int,
        key_provisions: Optional[List[str]] = None,
        applicable_to_roles: Optional[List[str]] = None,
        union_agreement_reference: Optional[str] = None
    ) -> RetaliationPreventionPolicy:
        policy = RetaliationPreventionPolicy(
            name=name,
            description=description,
            policy_type=policy_type,
            effective_date=datetime.now(timezone.utc),
            created_by_id=created_by_id,
            key_provisions=key_provisions,
            applicable_to_roles=applicable_to_roles,
            union_agreement_reference=union_agreement_reference
        )
        self.db.add(policy)
        await self.db.commit()
        return policy

    # ==================== PROTECTION MEASURES ====================

    async def create_protection_measure(
        self,
        staff_id: int,
        measure_type: str,
        description: str,
        approved_by_id: int,
        incident_report_id: Optional[int] = None,
        expected_end_date: Optional[datetime] = None
    ) -> StaffProtectionMeasure:
        measure = StaffProtectionMeasure(
            staff_id=staff_id,
            measure_type=measure_type,
            description=description,
            approved_by_id=approved_by_id,
            incident_report_id=incident_report_id,
            effective_date=datetime.now(timezone.utc),
            expected_end_date=expected_end_date
        )
        self.db.add(measure)
        await self.db.commit()
        return measure

    async def get_staff_protection_measures(
        self,
        staff_id: int
    ) -> List[StaffProtectionMeasure]:
        result = await self.db.execute(
            select(StaffProtectionMeasure)
            .where(StaffProtectionMeasure.staff_id == staff_id)
            .where(StaffProtectionMeasure.is_active == True)
        )
        return result.scalars().all()

    # ==================== SUPPORT RESOURCES ====================

    async def get_support_resources(
        self,
        resource_type: Optional[str] = None
    ) -> List[StaffSupportResource]:
        query = select(StaffSupportResource).where(StaffSupportResource.is_active == True)

        if resource_type:
            query = query.where(StaffSupportResource.resource_type == resource_type)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_support_resource(
        self,
        name: str,
        description: str,
        resource_type: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None,
        is_available_24_7: bool = False,
        is_anonymous: bool = False,
        is_union_resource: bool = False
    ) -> StaffSupportResource:
        resource = StaffSupportResource(
            name=name,
            description=description,
            resource_type=resource_type,
            phone=phone,
            email=email,
            website=website,
            is_available_24_7=is_available_24_7,
            is_anonymous=is_anonymous,
            is_union_resource=is_union_resource
        )
        self.db.add(resource)
        await self.db.commit()
        return resource

    # ==================== DATA RETENTION ====================

    async def enforce_data_retention(self) -> Tuple[int, int]:
        now = datetime.now(timezone.utc)

        # Soft delete expired panic alerts
        panic_result = await self.db.execute(
            select(StaffPanicAlert)
            .where(StaffPanicAlert.data_retention_expires_at <= now)
            .where(StaffPanicAlert.is_deleted == False)
        )
        panic_alerts = panic_result.scalars().all()
        panic_count = len(panic_alerts)

        for alert in panic_alerts:
            alert.is_deleted = True

        # Soft delete expired incident reports
        incident_result = await self.db.execute(
            select(StaffIncidentReport)
            .where(StaffIncidentReport.data_retention_expires_at <= now)
            .where(StaffIncidentReport.is_deleted == False)
        )
        incidents = incident_result.scalars().all()
        incident_count = len(incidents)

        for incident in incidents:
            incident.is_deleted = True

        await self.db.commit()
        logger.info(f"Data retention cleanup: {panic_count} alerts, {incident_count} reports")

        return panic_count, incident_count

    # ==================== AUDIT TRAIL ====================

    async def log_incident_access(
        self,
        report_id: int,
        accessed_by_id: int
    ) -> None:
        report = await self.db.get(StaffIncidentReport, report_id)

        if report.accessed_by_ids is None:
            report.accessed_by_ids = []

        report.accessed_by_ids.append({
            "user_id": accessed_by_id,
            "accessed_at": datetime.now(timezone.utc).isoformat()
        })

        await self.db.commit()

    # ==================== PRIVATE HELPER METHODS ====================

    async def _notify_responders_panic_alert(self, alert: StaffPanicAlert) -> None:
        result = await self.db.execute(
            select(User).where(
                User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR])
            )
        )
        responders = result.scalars().all()

        for responder in responders:
            notification = Notification(
                user_id=responder.id,
                notification_type=NotificationType.STAFF_ALERT,
                subject="STAFF PANIC ALERT",
                html_body=f"""
                <h2>PANIC ALERT ACTIVATED</h2>
                <p><strong>Staff:</strong> {alert.staff.first_name} {alert.staff.last_name}</p>
                <p><strong>Location:</strong> {alert.location or 'Not specified'}</p>
                <p><strong>Time:</strong> {alert.activated_at}</p>
                <p>Please respond immediately.</p>
                """
            )
            self.db.add(notification)

        await self.db.commit()

    async def _notify_management_incident(self, report: StaffIncidentReport) -> None:
        result = await self.db.execute(
            select(User).where(
                User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR])
            )
        )
        managers = result.scalars().all()

        for manager in managers:
            notification = Notification(
                user_id=manager.id,
                notification_type=NotificationType.STAFF_ALERT,
                subject="New Incident Report Filed",
                html_body=f"""
                <h2>Incident Report</h2>
                <p><strong>Type:</strong> {report.incident_type}</p>
                <p><strong>Severity:</strong> {report.severity}</p>
                <p><strong>Location:</strong> {report.incident_location or 'Not specified'}</p>
                <p><strong>Date:</strong> {report.incident_date}</p>
                <p>Please review and respond.</p>
                """
            )
            self.db.add(notification)

        await self.db.commit()

