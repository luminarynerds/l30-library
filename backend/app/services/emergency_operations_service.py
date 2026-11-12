# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, desc, func, select
from sqlalchemy.orm import selectinload

from ..models import (
    OfflineMode, OfflineModeStatus, PaperBackupForm, PaperBackupSubmission,
    DataSyncQueue, EmergencyContactCascade, OperationContactCascade,
    CascadeExecutionLog, CascadeContactNotification, BuildingClosure,
    BuildingClosureReason, ServiceContinuityPriority, CollectionRecoveryProject,
    DamagedItem, DamageAssessmentStatus, InsuranceDocumentation,
    PostDisasterAssessment, DisasterAssessmentPhase, CommunityResourceHub,
    User, UserRole
)
from ..core.config import get_settings
from app.core.datetime_utils import utc_now

settings = get_settings()


class OfflineModeService:

    @staticmethod
    async def activate_offline_mode(
        db: AsyncSession,
        reason: str,
        affected_services: List[str],
        affected_branches: Optional[List[int]],
        activated_by_id: int,
        recovery_priority: str = "normal",
        estimated_restoration: Optional[datetime] = None
    ) -> OfflineMode:
        offline_mode = OfflineMode(
            status=OfflineModeStatus.OFFLINE,
            activated_at=utc_now(),
            reason=reason,
            affected_services=affected_services,
            affected_branches=affected_branches,
            activated_by_id=activated_by_id,
            recovery_priority=recovery_priority,
            estimated_restoration_time=estimated_restoration
        )
        db.add(offline_mode)
        await db.flush()
        await db.refresh(offline_mode)
        return offline_mode

    @staticmethod
    async def deactivate_offline_mode(
        db: AsyncSession,
        offline_mode_id: int,
        deactivated_by_id: int
    ) -> OfflineMode:
        result = await db.execute(
            select(OfflineMode).where(OfflineMode.id == offline_mode_id)
        )
        offline_mode = result.scalars().first()

        if not offline_mode:
            raise ValueError(f"Offline mode {offline_mode_id} not found")

        offline_mode.status = OfflineModeStatus.RECOVERY
        offline_mode.deactivated_at = utc_now()
        offline_mode.deactivated_by_id = deactivated_by_id

        await db.flush()
        await db.refresh(offline_mode)
        return offline_mode

    @staticmethod
    async def get_current_offline_mode(db: AsyncSession) -> Optional[OfflineMode]:
        result = await db.execute(
            select(OfflineMode)
            .where(OfflineMode.status.in_([OfflineModeStatus.OFFLINE, OfflineModeStatus.DEGRADED]))
            .order_by(desc(OfflineMode.activated_at))
        )
        return result.scalars().first()

    @staticmethod
    async def get_offline_mode_status(db: AsyncSession) -> Dict[str, Any]:
        current_mode = await OfflineModeService.get_current_offline_mode(db)

        if not current_mode:
            return {
                "is_offline": False,
                "status": OfflineModeStatus.ONLINE,
                "mode_details": None
            }

        # Count pending sync items
        pending_sync_count = (await db.execute(
            select(func.count(DataSyncQueue.id)).where(
                DataSyncQueue.status == "pending"
            )
        )).scalar()

        # Count paper submissions waiting for sync
        paper_submissions_pending = (await db.execute(
            select(func.count(PaperBackupSubmission.id)).where(
                and_(
                    PaperBackupSubmission.synced == False,
                    PaperBackupSubmission.transaction_date >= current_mode.activated_at
                )
            )
        )).scalar()

        return {
            "is_offline": True,
            "status": current_mode.status,
            "activated_at": current_mode.activated_at,
            "reason": current_mode.reason,
            "affected_services": current_mode.affected_services,
            "affected_branches": current_mode.affected_branches,
            "estimated_restoration": current_mode.estimated_restoration_time,
            "recovery_priority": current_mode.recovery_priority,
            "pending_sync_items": pending_sync_count,
            "paper_submissions_pending": paper_submissions_pending
        }


class PaperBackupService:

    @staticmethod
    async def create_paper_form_template(
        db: AsyncSession,
        form_type: str,
        form_name: str,
        form_template: str,
        pages_required: int = 1,
        barcode_required: bool = True,
        signature_required: bool = True
    ) -> PaperBackupForm:
        form = PaperBackupForm(
            form_type=form_type,
            form_name=form_name,
            form_template=form_template,
            pages_required=pages_required,
            barcode_required=barcode_required,
            signature_required=signature_required
        )
        db.add(form)
        await db.flush()
        await db.refresh(form)
        return form

    @staticmethod
    async def submit_paper_form(
        db: AsyncSession,
        form_id: int,
        transaction_date: datetime,
        staff_initials: str,
        form_data: Dict[str, Any],
        patron_id: Optional[int] = None,
        item_barcode: Optional[str] = None,
        patron_name: Optional[str] = None,
        notes: Optional[str] = None,
        created_by_id: Optional[int] = None
    ) -> PaperBackupSubmission:
        result = await db.execute(
            select(PaperBackupForm).where(PaperBackupForm.id == form_id)
        )
        form = result.scalars().first()

        if not form:
            raise ValueError(f"Form template {form_id} not found")

        submission = PaperBackupSubmission(
            form_id=form_id,
            form_type=form.form_type,
            transaction_date=transaction_date,
            staff_initials=staff_initials,
            form_data=form_data,
            patron_id=patron_id,
            item_barcode=item_barcode,
            patron_name=patron_name,
            notes=notes,
            created_by_id=created_by_id
        )
        db.add(submission)
        await db.flush()
        await db.refresh(submission)
        return submission

    @staticmethod
    async def get_pending_paper_submissions(
        db: AsyncSession,
        form_type: Optional[str] = None,
        limit: int = 50
    ) -> List[PaperBackupSubmission]:
        stmt = select(PaperBackupSubmission).where(
            PaperBackupSubmission.synced == False
        )

        if form_type:
            stmt = stmt.where(PaperBackupSubmission.form_type == form_type)

        stmt = stmt.order_by(
            PaperBackupSubmission.transaction_date
        ).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def mark_submission_synced(
        db: AsyncSession,
        submission_id: int,
        sync_resolution: str = "auto_accepted"
    ) -> PaperBackupSubmission:
        result = await db.execute(
            select(PaperBackupSubmission).where(
                PaperBackupSubmission.id == submission_id
            )
        )
        submission = result.scalars().first()

        if not submission:
            raise ValueError(f"Submission {submission_id} not found")

        submission.synced = True
        submission.synced_at = utc_now()
        submission.sync_resolution = sync_resolution

        await db.flush()
        await db.refresh(submission)
        return submission


class DataSyncService:

    @staticmethod
    async def queue_sync_item(
        db: AsyncSession,
        sync_source: str,
        entity_type: str,
        entity_data: Dict[str, Any],
        priority: int = 0,
        entity_id: Optional[str] = None,
        created_by_id: Optional[int] = None
    ) -> DataSyncQueue:
        sync_item = DataSyncQueue(
            sync_source=sync_source,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_data=entity_data,
            priority=priority,
            created_by_id=created_by_id
        )
        db.add(sync_item)
        await db.flush()
        await db.refresh(sync_item)
        return sync_item

    @staticmethod
    async def get_pending_sync_items(
        db: AsyncSession,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[DataSyncQueue]:
        stmt = select(DataSyncQueue).where(
            DataSyncQueue.status == "pending"
        )

        if entity_type:
            stmt = stmt.where(DataSyncQueue.entity_type == entity_type)

        stmt = stmt.order_by(
            desc(DataSyncQueue.priority),
            DataSyncQueue.id
        ).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def mark_sync_complete(
        db: AsyncSession,
        sync_item_id: int,
        processed_by_id: Optional[int] = None
    ) -> DataSyncQueue:
        result = await db.execute(
            select(DataSyncQueue).where(DataSyncQueue.id == sync_item_id)
        )
        sync_item = result.scalars().first()

        if not sync_item:
            raise ValueError(f"Sync item {sync_item_id} not found")

        sync_item.status = "synced"
        sync_item.processed_at = utc_now()
        sync_item.processed_by_id = processed_by_id

        await db.flush()
        await db.refresh(sync_item)
        return sync_item

    @staticmethod
    async def mark_sync_failed(
        db: AsyncSession,
        sync_item_id: int,
        error_message: str
    ) -> DataSyncQueue:
        result = await db.execute(
            select(DataSyncQueue).where(DataSyncQueue.id == sync_item_id)
        )
        sync_item = result.scalars().first()

        if not sync_item:
            raise ValueError(f"Sync item {sync_item_id} not found")

        sync_item.last_error = error_message
        sync_item.last_error_at = utc_now()
        sync_item.retry_count += 1

        if sync_item.retry_count >= sync_item.max_retries:
            sync_item.status = "failed"

        await db.flush()
        await db.refresh(sync_item)
        return sync_item

    @staticmethod
    async def get_sync_statistics(db: AsyncSession) -> Dict[str, Any]:
        total = (await db.execute(
            select(func.count(DataSyncQueue.id))
        )).scalar()

        pending = (await db.execute(
            select(func.count(DataSyncQueue.id)).where(
                DataSyncQueue.status == "pending"
            )
        )).scalar()

        synced = (await db.execute(
            select(func.count(DataSyncQueue.id)).where(
                DataSyncQueue.status == "synced"
            )
        )).scalar()

        failed = (await db.execute(
            select(func.count(DataSyncQueue.id)).where(
                DataSyncQueue.status == "failed"
            )
        )).scalar()

        return {
            "total_items": total,
            "pending": pending,
            "synced": synced,
            "failed": failed,
            "pending_percentage": (pending / total * 100) if total > 0 else 0
        }


class EmergencyContactService:

    @staticmethod
    async def create_cascade(
        db: AsyncSession,
        cascade_name: str,
        auto_trigger_events: List[str],
        message_template: str,
        manual_approval_required: bool = True,
        max_contact_levels: int = 5
    ) -> EmergencyContactCascade:
        cascade = EmergencyContactCascade(
            cascade_name=cascade_name,
            auto_trigger_events=auto_trigger_events,
            message_template=message_template,
            manual_approval_required=manual_approval_required,
            max_contact_levels=max_contact_levels
        )
        db.add(cascade)
        await db.flush()
        await db.refresh(cascade)
        return cascade

    @staticmethod
    async def add_contact_to_cascade(
        db: AsyncSession,
        cascade_id: int,
        level: int,
        contact_role: str,
        contact_name: str,
        contact_email: Optional[str],
        contact_phone: Optional[str],
        contact_method: str = "email",
        wait_time_seconds: int = 0,
        retry_attempts: int = 2
    ) -> OperationContactCascade:
        result = await db.execute(
            select(EmergencyContactCascade).where(
                EmergencyContactCascade.id == cascade_id
            )
        )
        cascade = result.scalars().first()

        if not cascade:
            raise ValueError(f"Cascade {cascade_id} not found")

        contact = OperationContactCascade(
            cascade_id=cascade_id,
            level=level,
            contact_role=contact_role,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            contact_method=contact_method,
            wait_time_seconds=wait_time_seconds,
            retry_attempts=retry_attempts,
            order_index=level
        )
        db.add(contact)
        await db.flush()
        await db.refresh(contact)
        return contact

    @staticmethod
    async def execute_cascade(
        db: AsyncSession,
        cascade_id: int,
        trigger_reason: str,
        initiated_by_id: int
    ) -> CascadeExecutionLog:
        result = await db.execute(
            select(EmergencyContactCascade)
            .options(selectinload(EmergencyContactCascade.contacts))
            .where(EmergencyContactCascade.id == cascade_id)
        )
        cascade = result.scalars().first()

        if not cascade:
            raise ValueError(f"Cascade {cascade_id} not found")

        # Create execution log
        execution_log = CascadeExecutionLog(
            cascade_id=cascade_id,
            trigger_reason=trigger_reason,
            initiated_by_id=initiated_by_id,
            total_contacts_to_reach=len(cascade.contacts)
        )
        db.add(execution_log)
        await db.flush()
        await db.refresh(execution_log)

        # Create notification records for each contact
        for contact in sorted(cascade.contacts, key=lambda c: c.level):
            notification = CascadeContactNotification(
                execution_log_id=execution_log.id,
                contact_id=contact.id
            )
            db.add(notification)

        await db.flush()
        return execution_log

    @staticmethod
    async def get_active_cascades(db: AsyncSession) -> List[EmergencyContactCascade]:
        result = await db.execute(
            select(EmergencyContactCascade)
            .where(EmergencyContactCascade.is_active == True)
            .order_by(EmergencyContactCascade.cascade_name)
        )
        return result.scalars().all()


class BuildingClosureService:

    @staticmethod
    async def create_closure(
        db: AsyncSession,
        closure_reason: BuildingClosureReason,
        reason_details: str,
        closure_start: datetime,
        estimated_reopening: Optional[datetime] = None,
        branches_affected: Optional[List[int]] = None,
        areas_affected: Optional[List[str]] = None,
        severity_level: str = "moderate",
        created_by_id: Optional[int] = None
    ) -> BuildingClosure:
        closure = BuildingClosure(
            closure_reason=closure_reason,
            reason_details=reason_details,
            closure_start=closure_start,
            estimated_reopening=estimated_reopening,
            branches_affected=branches_affected,
            areas_affected=areas_affected,
            severity_level=severity_level,
            created_by_id=created_by_id
        )
        db.add(closure)
        await db.flush()
        await db.refresh(closure)
        return closure

    @staticmethod
    async def notify_patrons(
        db: AsyncSession,
        closure_id: int,
        message: str
    ) -> BuildingClosure:
        result = await db.execute(
            select(BuildingClosure).where(BuildingClosure.id == closure_id)
        )
        closure = result.scalars().first()

        if not closure:
            raise ValueError(f"Closure {closure_id} not found")

        closure.patrons_notified = True
        closure.patron_message = message
        closure.email_sent = True

        # In production, this would integrate with notification service

        await db.flush()
        await db.refresh(closure)
        return closure

    @staticmethod
    async def close_building(
        db: AsyncSession,
        closure_id: int,
        updated_by_id: int
    ) -> BuildingClosure:
        result = await db.execute(
            select(BuildingClosure).where(BuildingClosure.id == closure_id)
        )
        closure = result.scalars().first()

        if not closure:
            raise ValueError(f"Closure {closure_id} not found")

        closure.is_active = True
        closure.updated_by_id = updated_by_id

        await db.flush()
        await db.refresh(closure)
        return closure

    @staticmethod
    async def reopen_building(
        db: AsyncSession,
        closure_id: int,
        updated_by_id: int
    ) -> BuildingClosure:
        result = await db.execute(
            select(BuildingClosure).where(BuildingClosure.id == closure_id)
        )
        closure = result.scalars().first()

        if not closure:
            raise ValueError(f"Closure {closure_id} not found")

        closure.is_active = False
        closure.actual_reopening = utc_now()
        closure.updated_by_id = updated_by_id

        await db.flush()
        await db.refresh(closure)
        return closure

    @staticmethod
    async def get_active_closures(db: AsyncSession) -> List[BuildingClosure]:
        result = await db.execute(
            select(BuildingClosure)
            .where(BuildingClosure.is_active == True)
            .order_by(desc(BuildingClosure.closure_start))
        )
        return result.scalars().all()


class ServiceContinuityService:

    @staticmethod
    async def create_service_priority(
        db: AsyncSession,
        service_name: str,
        service_category: str,
        priority: str,
        rto_minutes: int,
        rpo_minutes: int,
        max_acceptable_downtime: int,
        manual_workaround: Optional[str] = None,
        required_staff_roles: Optional[List[str]] = None,
        critical_forms: Optional[List[str]] = None
    ) -> ServiceContinuityPriority:
        service = ServiceContinuityPriority(
            service_name=service_name,
            service_category=service_category,
            priority=priority,
            rto_minutes=rto_minutes,
            rpo_minutes=rpo_minutes,
            max_acceptable_downtime=max_acceptable_downtime,
            manual_workaround=manual_workaround,
            required_staff_roles=required_staff_roles,
            critical_forms=critical_forms
        )
        db.add(service)
        await db.flush()
        await db.refresh(service)
        return service

    @staticmethod
    async def get_priority_by_severity(db: AsyncSession, priority: str) -> List[ServiceContinuityPriority]:
        result = await db.execute(
            select(ServiceContinuityPriority)
            .where(ServiceContinuityPriority.priority == priority)
            .order_by(ServiceContinuityPriority.service_name)
        )
        return result.scalars().all()

    @staticmethod
    async def get_services_requiring_recovery(
        db: AsyncSession,
        max_downtime_minutes: int
    ) -> List[ServiceContinuityPriority]:
        result = await db.execute(
            select(ServiceContinuityPriority)
            .where(ServiceContinuityPriority.rto_minutes <= max_downtime_minutes)
            .order_by(ServiceContinuityPriority.priority)
        )
        return result.scalars().all()


class CollectionRecoveryService:

    @staticmethod
    async def create_recovery_project(
        db: AsyncSession,
        project_name: str,
        disaster_type: str,
        disaster_date: datetime,
        affected_areas: List[str],
        estimated_items_affected: Optional[int] = None,
        lead_staff_id: Optional[int] = None
    ) -> CollectionRecoveryProject:
        project = CollectionRecoveryProject(
            project_name=project_name,
            disaster_type=disaster_type,
            disaster_date=disaster_date,
            affected_areas=affected_areas,
            estimated_items_affected=estimated_items_affected,
            lead_staff_id=lead_staff_id
        )
        db.add(project)
        await db.flush()
        await db.refresh(project)
        return project

    @staticmethod
    async def add_damaged_item(
        db: AsyncSession,
        project_id: int,
        item_barcode: str,
        damage_type: str,
        damage_severity: str,
        damage_description: str,
        title: Optional[str] = None,
        author: Optional[str] = None
    ) -> DamagedItem:
        result = await db.execute(
            select(CollectionRecoveryProject).where(
                CollectionRecoveryProject.id == project_id
            )
        )
        project = result.scalars().first()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        item = DamagedItem(
            project_id=project_id,
            item_barcode=item_barcode,
            damage_type=damage_type,
            damage_severity=damage_severity,
            damage_description=damage_description,
            title=title,
            author=author,
            assessment_status=DamageAssessmentStatus.NOT_ASSESSED
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item

    @staticmethod
    async def assess_damaged_item(
        db: AsyncSession,
        item_id: int,
        is_salvageable: bool,
        salvage_method: Optional[str] = None,
        estimated_repair_cost: Optional[float] = None,
        replacement_cost: Optional[float] = None,
        assessed_by_id: Optional[int] = None
    ) -> DamagedItem:
        result = await db.execute(
            select(DamagedItem).where(DamagedItem.id == item_id)
        )
        item = result.scalars().first()

        if not item:
            raise ValueError(f"Item {item_id} not found")

        item.is_salvageable = is_salvageable
        item.salvage_method = salvage_method
        item.estimated_repair_cost = estimated_repair_cost
        item.replacement_cost = replacement_cost
        item.assessed_by_id = assessed_by_id
        item.date_assessed = utc_now()

        if is_salvageable:
            item.assessment_status = DamageAssessmentStatus.SALVAGEABLE
            item.recovery_status = "pending"
        else:
            item.assessment_status = DamageAssessmentStatus.UNSALVAGEABLE
            item.recovery_status = "disposed"

        await db.flush()
        await db.refresh(item)
        return item

    @staticmethod
    async def get_project_recovery_statistics(
        db: AsyncSession,
        project_id: int
    ) -> Dict[str, Any]:
        result = await db.execute(
            select(CollectionRecoveryProject).where(
                CollectionRecoveryProject.id == project_id
            )
        )
        project = result.scalars().first()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        total_items = (await db.execute(
            select(func.count(DamagedItem.id)).where(
                DamagedItem.project_id == project_id
            )
        )).scalar()

        salvageable = (await db.execute(
            select(func.count(DamagedItem.id)).where(
                and_(
                    DamagedItem.project_id == project_id,
                    DamagedItem.is_salvageable == True
                )
            )
        )).scalar()

        unsalvageable = (await db.execute(
            select(func.count(DamagedItem.id)).where(
                and_(
                    DamagedItem.project_id == project_id,
                    DamagedItem.is_salvageable == False
                )
            )
        )).scalar()

        total_repair_cost = (await db.execute(
            select(func.sum(DamagedItem.estimated_repair_cost)).where(
                and_(
                    DamagedItem.project_id == project_id,
                    DamagedItem.is_salvageable == True
                )
            )
        )).scalar()

        total_replacement_cost = (await db.execute(
            select(func.sum(DamagedItem.replacement_cost)).where(
                and_(
                    DamagedItem.project_id == project_id,
                    DamagedItem.is_salvageable == False
                )
            )
        )).scalar()

        return {
            "total_items": total_items,
            "salvageable": salvageable,
            "unsalvageable": unsalvageable,
            "total_repair_cost": total_repair_cost or 0,
            "total_replacement_cost": total_replacement_cost or 0,
            "salvage_rate": (salvageable / total_items * 100) if total_items > 0 else 0
        }


class CommunityResourceHubService:

    @staticmethod
    async def create_hub(
        db: AsyncSession,
        hub_name: str,
        branch_id: int,
        location_description: str,
        hub_purposes: List[str],
        emergency_types: List[str],
        max_capacity: int,
        volunteer_coordinator_id: Optional[int] = None
    ) -> CommunityResourceHub:
        hub = CommunityResourceHub(
            hub_name=hub_name,
            branch_id=branch_id,
            location_description=location_description,
            hub_purposes=hub_purposes,
            emergency_types=emergency_types,
            max_capacity=max_capacity,
            volunteer_coordinator_id=volunteer_coordinator_id
        )
        db.add(hub)
        await db.flush()
        await db.refresh(hub)
        return hub

    @staticmethod
    async def activate_hub(
        db: AsyncSession,
        hub_id: int,
        activation_reason: str,
        activation_message: str,
        activated_by_id: int
    ) -> CommunityResourceHub:
        result = await db.execute(
            select(CommunityResourceHub).where(CommunityResourceHub.id == hub_id)
        )
        hub = result.scalars().first()

        if not hub:
            raise ValueError(f"Hub {hub_id} not found")

        hub.is_active = True
        hub.activated_at = utc_now()
        hub.activation_reason = activation_reason
        hub.activation_message = activation_message
        hub.activated_by_id = activated_by_id

        await db.flush()
        await db.refresh(hub)
        return hub

    @staticmethod
    async def deactivate_hub(db: AsyncSession, hub_id: int) -> CommunityResourceHub:
        result = await db.execute(
            select(CommunityResourceHub).where(CommunityResourceHub.id == hub_id)
        )
        hub = result.scalars().first()

        if not hub:
            raise ValueError(f"Hub {hub_id} not found")

        hub.is_active = False
        hub.deactivated_at = utc_now()

        await db.flush()
        await db.refresh(hub)
        return hub

    @staticmethod
    async def get_active_hubs(db: AsyncSession) -> List[CommunityResourceHub]:
        result = await db.execute(
            select(CommunityResourceHub).where(
                CommunityResourceHub.is_active == True
            )
        )
        return result.scalars().all()

    @staticmethod
    async def update_hub_visitor_count(
        db: AsyncSession,
        hub_id: int,
        count_increment: int
    ) -> CommunityResourceHub:
        result = await db.execute(
            select(CommunityResourceHub).where(CommunityResourceHub.id == hub_id)
        )
        hub = result.scalars().first()

        if not hub:
            raise ValueError(f"Hub {hub_id} not found")

        hub.visitors_served_count += count_increment

        await db.flush()
        await db.refresh(hub)
        return hub
