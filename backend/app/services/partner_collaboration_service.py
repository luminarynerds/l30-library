# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import and_, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ..models.partner_collaboration import (
    SharedEvent, SharedEventStatus, SharedEventType,
    ResourceSharingRequest, ResourceRequestStatus, ResourceRequestType,
    CoSponsoredProgram, CoSponsoredProgramStatus, ProgramSession,
    PartnerContactDirectory,
    PartnershipMeeting, MeetingType,
    PartnershipAgreement, MOUStatus, AgreementAmendment,
    JointGrantOpportunity, GrantOpportunityStatus,
    PartnerImpactReport, ImpactMetric, ImpactMetricType,
    PartnerRecognition, RecognitionType,
    ThankYouMessage
)
from ..models.user import User
from ..models.outreach import OutreachPartner

logger = get_logger(__name__)


# ============================================================================
# Shared Event Calendar Service
# ============================================================================

class SharedEventService:

    @staticmethod
    async def create_event(
        db: AsyncSession,
        title: str,
        event_type: str,
        event_date: str,
        organizing_partner_id: int,
        created_by_id: int,
        **kwargs
    ) -> SharedEvent:
        event = SharedEvent(
            title=title,
            event_type=SharedEventType(event_type),
            event_date=datetime.fromisoformat(event_date).date(),
            organizing_partner_id=organizing_partner_id,
            created_by_id=created_by_id,
            **kwargs
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def get_partner_events(
        db: AsyncSession,
        partner_id: int,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[SharedEvent]:
        query = select(SharedEvent).where(
            SharedEvent.organizing_partner_id == partner_id
        )

        if status:
            query = query.where(SharedEvent.status == SharedEventStatus(status))

        if start_date:
            start = datetime.fromisoformat(start_date).date()
            query = query.where(SharedEvent.event_date >= start)

        if end_date:
            end = datetime.fromisoformat(end_date).date()
            query = query.where(SharedEvent.event_date <= end)

        result = await db.execute(query.order_by(SharedEvent.event_date))
        return result.scalars().all()

    @staticmethod
    async def update_event(
        db: AsyncSession,
        event_id: int,
        **kwargs
    ) -> SharedEvent:
        result = await db.execute(select(SharedEvent).where(SharedEvent.id == event_id))
        event = result.scalar_one_or_none()

        if not event:
            raise ValueError(f"Event {event_id} not found")

        for key, value in kwargs.items():
            if hasattr(event, key):
                setattr(event, key, value)

        event.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(event)
        return event


# ============================================================================
# Resource Sharing Service
# ============================================================================

class ResourceSharingService:

    @staticmethod
    async def create_request(
        db: AsyncSession,
        title: str,
        description: str,
        resource_type: str,
        requesting_partner_id: int,
        start_date: str,
        requester_user_id: Optional[int] = None,
        **kwargs
    ) -> ResourceSharingRequest:
        request = ResourceSharingRequest(
            title=title,
            description=description,
            resource_type=ResourceRequestType(resource_type),
            requesting_partner_id=requesting_partner_id,
            start_date=datetime.fromisoformat(start_date).date(),
            requester_user_id=requester_user_id,
            **kwargs
        )
        db.add(request)
        await db.commit()
        await db.refresh(request)
        return request

    @staticmethod
    async def get_requests_by_partner(
        db: AsyncSession,
        partner_id: int,
        status: Optional[str] = None,
        role: str = "requester"  # requester or provider
    ) -> List[ResourceSharingRequest]:
        if role == "requester":
            query = select(ResourceSharingRequest).where(
                ResourceSharingRequest.requesting_partner_id == partner_id
            )
        else:
            query = select(ResourceSharingRequest).where(
                ResourceSharingRequest.providing_partner_id == partner_id
            )

        if status:
            query = query.where(
                ResourceSharingRequest.status == ResourceRequestStatus(status)
            )

        result = await db.execute(query.order_by(desc(ResourceSharingRequest.created_at)))
        return result.scalars().all()

    @staticmethod
    async def approve_request(
        db: AsyncSession,
        request_id: int,
        approved_by_id: int,
        approval_notes: Optional[str] = None
    ) -> ResourceSharingRequest:
        result = await db.execute(
            select(ResourceSharingRequest).where(ResourceSharingRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if not request:
            raise ValueError(f"Request {request_id} not found")

        request.status = ResourceRequestStatus.approved
        request.approved_by_id = approved_by_id
        request.approved_at = datetime.now(timezone.utc)
        if approval_notes:
            request.approval_notes = approval_notes

        await db.commit()
        await db.refresh(request)
        return request

    @staticmethod
    async def update_request(
        db: AsyncSession,
        request_id: int,
        **kwargs
    ) -> ResourceSharingRequest:
        result = await db.execute(
            select(ResourceSharingRequest).where(ResourceSharingRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if not request:
            raise ValueError(f"Resource request {request_id} not found")

        for key, value in kwargs.items():
            if hasattr(request, key) and key not in ("id", "created_at", "status", "approved_by_id", "approved_at", "requester_user_id", "requesting_partner_id"):
                setattr(request, key, value)

        await db.commit()
        await db.refresh(request)
        return request


# ============================================================================
# Co-Sponsored Program Service
# ============================================================================

class CoSponsoredProgramService:

    @staticmethod
    async def create_program(
        db: AsyncSession,
        name: str,
        lead_partner_id: int,
        start_date: str,
        created_by_id: int,
        **kwargs
    ) -> CoSponsoredProgram:
        program = CoSponsoredProgram(
            name=name,
            lead_partner_id=lead_partner_id,
            start_date=datetime.fromisoformat(start_date).date(),
            created_by_id=created_by_id,
            **kwargs
        )
        db.add(program)
        await db.commit()
        await db.refresh(program)
        return program

    @staticmethod
    async def get_partner_programs(
        db: AsyncSession,
        partner_id: int,
        status: Optional[str] = None
    ) -> List[CoSponsoredProgram]:
        query = select(CoSponsoredProgram).where(
            (CoSponsoredProgram.lead_partner_id == partner_id)
        )

        if status:
            query = query.where(
                CoSponsoredProgram.status == CoSponsoredProgramStatus(status)
            )

        result = await db.execute(
            query.options(selectinload(CoSponsoredProgram.sessions))
            .order_by(desc(CoSponsoredProgram.start_date))
        )
        return result.unique().scalars().all()

    @staticmethod
    async def add_session(
        db: AsyncSession,
        program_id: int,
        title: str,
        session_date: str,
        **kwargs
    ) -> ProgramSession:
        session = ProgramSession(
            program_id=program_id,
            title=title,
            session_date=datetime.fromisoformat(session_date).date(),
            **kwargs
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session


# ============================================================================
# Contact Directory Service
# ============================================================================

class ContactDirectoryService:

    @staticmethod
    async def add_contact(
        db: AsyncSession,
        partner_id: int,
        first_name: str,
        last_name: str,
        **kwargs
    ) -> PartnerContactDirectory:
        contact = PartnerContactDirectory(
            partner_id=partner_id,
            first_name=first_name,
            last_name=last_name,
            **kwargs
        )
        db.add(contact)
        await db.commit()
        await db.refresh(contact)
        return contact

    @staticmethod
    async def get_partner_contacts(
        db: AsyncSession,
        partner_id: int,
        is_primary: Optional[bool] = None
    ) -> List[PartnerContactDirectory]:
        query = select(PartnerContactDirectory).where(
            PartnerContactDirectory.partner_id == partner_id
        )

        if is_primary is not None:
            query = query.where(PartnerContactDirectory.is_primary == is_primary)

        result = await db.execute(
            query.order_by(PartnerContactDirectory.last_name, PartnerContactDirectory.first_name)
        )
        return result.scalars().all()

    @staticmethod
    async def update_contact(
        db: AsyncSession,
        contact_id: int,
        **kwargs
    ) -> PartnerContactDirectory:
        result = await db.execute(
            select(PartnerContactDirectory).where(PartnerContactDirectory.id == contact_id)
        )
        contact = result.scalar_one_or_none()

        if not contact:
            raise ValueError(f"Contact {contact_id} not found")

        for key, value in kwargs.items():
            if hasattr(contact, key):
                setattr(contact, key, value)

        contact.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(contact)
        return contact


# ============================================================================
# Partnership Meeting Service
# ============================================================================

class PartnershipMeetingService:

    @staticmethod
    async def create_meeting(
        db: AsyncSession,
        partner_id: int,
        meeting_type: str,
        title: str,
        meeting_date: str,
        meeting_notes: str,
        recorded_by_id: int,
        **kwargs
    ) -> PartnershipMeeting:
        meeting = PartnershipMeeting(
            partner_id=partner_id,
            meeting_type=MeetingType(meeting_type),
            title=title,
            meeting_date=datetime.fromisoformat(meeting_date).date(),
            meeting_notes=meeting_notes,
            recorded_by_id=recorded_by_id,
            **kwargs
        )
        db.add(meeting)
        await db.commit()
        await db.refresh(meeting)
        return meeting

    @staticmethod
    async def get_partner_meetings(
        db: AsyncSession,
        partner_id: int,
        meeting_type: Optional[str] = None,
        limit: int = 50
    ) -> List[PartnershipMeeting]:
        query = select(PartnershipMeeting).where(
            PartnershipMeeting.partner_id == partner_id
        )

        if meeting_type:
            query = query.where(PartnershipMeeting.meeting_type == MeetingType(meeting_type))

        result = await db.execute(
            query.order_by(desc(PartnershipMeeting.meeting_date))
            .limit(limit)
        )
        return result.scalars().all()


# ============================================================================
# Partnership Agreement Service
# ============================================================================

class PartnershipAgreementService:

    @staticmethod
    async def create_agreement(
        db: AsyncSession,
        partner_id: int,
        agreement_type: str,
        title: str,
        start_date: str,
        created_by_id: int,
        **kwargs
    ) -> PartnershipAgreement:
        agreement = PartnershipAgreement(
            partner_id=partner_id,
            agreement_type=agreement_type,
            title=title,
            start_date=datetime.fromisoformat(start_date).date(),
            created_by_id=created_by_id,
            **kwargs
        )
        db.add(agreement)
        await db.commit()
        await db.refresh(agreement)
        return agreement

    @staticmethod
    async def get_active_agreements(
        db: AsyncSession,
        partner_id: int
    ) -> List[PartnershipAgreement]:
        result = await db.execute(
            select(PartnershipAgreement)
            .where(
                (PartnershipAgreement.partner_id == partner_id) &
                (PartnershipAgreement.status == MOUStatus.active)
            )
            .order_by(desc(PartnershipAgreement.start_date))
        )
        return result.scalars().all()

    @staticmethod
    async def sign_agreement(
        db: AsyncSession,
        agreement_id: int,
        approved_by_id: int
    ) -> PartnershipAgreement:
        result = await db.execute(
            select(PartnershipAgreement).where(PartnershipAgreement.id == agreement_id)
        )
        agreement = result.scalar_one_or_none()

        if not agreement:
            raise ValueError(f"Agreement {agreement_id} not found")

        agreement.status = MOUStatus.active
        agreement.signed_at = datetime.now(timezone.utc)
        agreement.approved_by_id = approved_by_id

        await db.commit()
        await db.refresh(agreement)
        return agreement


# ============================================================================
# Joint Grant Opportunities Service
# ============================================================================

class JointGrantService:

    @staticmethod
    async def create_grant_opportunity(
        db: AsyncSession,
        title: str,
        funding_source: str,
        created_by_id: int,
        **kwargs
    ) -> JointGrantOpportunity:
        grant = JointGrantOpportunity(
            title=title,
            funding_source=funding_source,
            created_by_id=created_by_id,
            **kwargs
        )
        db.add(grant)
        await db.commit()
        await db.refresh(grant)
        return grant

    @staticmethod
    async def get_active_opportunities(
        db: AsyncSession,
        exclude_statuses: Optional[List[str]] = None
    ) -> List[JointGrantOpportunity]:
        query = select(JointGrantOpportunity)

        if exclude_statuses:
            statuses = [GrantOpportunityStatus(s) for s in exclude_statuses]
            query = query.where(~JointGrantOpportunity.status.in_(statuses))

        result = await db.execute(
            query.order_by(desc(JointGrantOpportunity.grant_deadline))
        )
        return result.scalars().all()


# ============================================================================
# Impact Reporting Service
# ============================================================================

class ImpactReportingService:

    @staticmethod
    async def create_report(
        db: AsyncSession,
        partner_id: int,
        reporting_period_start: str,
        reporting_period_end: str,
        created_by_id: int,
        **kwargs
    ) -> PartnerImpactReport:
        report = PartnerImpactReport(
            partner_id=partner_id,
            reporting_period_start=datetime.fromisoformat(reporting_period_start).date(),
            reporting_period_end=datetime.fromisoformat(reporting_period_end).date(),
            created_by_id=created_by_id,
            **kwargs
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    @staticmethod
    async def add_metric(
        db: AsyncSession,
        report_id: int,
        metric_type: str,
        metric_name: str,
        actual_value: float,
        **kwargs
    ) -> ImpactMetric:
        metric = ImpactMetric(
            report_id=report_id,
            metric_type=ImpactMetricType(metric_type),
            metric_name=metric_name,
            actual_value=actual_value,
            **kwargs
        )
        db.add(metric)
        await db.commit()
        await db.refresh(metric)
        return metric

    @staticmethod
    async def get_partner_reports(
        db: AsyncSession,
        partner_id: int,
        limit: int = 10
    ) -> List[PartnerImpactReport]:
        result = await db.execute(
            select(PartnerImpactReport)
            .where(PartnerImpactReport.partner_id == partner_id)
            .options(selectinload(PartnerImpactReport.metrics))
            .order_by(desc(PartnerImpactReport.reporting_period_start))
            .limit(limit)
        )
        return result.unique().scalars().all()


# ============================================================================
# Partner Recognition Service
# ============================================================================

class PartnerRecognitionService:

    @staticmethod
    async def create_recognition(
        db: AsyncSession,
        partner_id: int,
        recognition_type: str,
        title: str,
        reason: str,
        recognition_date: str,
        created_by_id: int,
        **kwargs
    ) -> PartnerRecognition:
        recognition = PartnerRecognition(
            partner_id=partner_id,
            recognition_type=RecognitionType(recognition_type),
            title=title,
            reason=reason,
            recognition_date=datetime.fromisoformat(recognition_date).date(),
            created_by_id=created_by_id,
            **kwargs
        )
        db.add(recognition)
        await db.commit()
        await db.refresh(recognition)
        return recognition

    @staticmethod
    async def send_thank_you(
        db: AsyncSession,
        partner_id: int,
        subject: str,
        message_body: str,
        sent_by_id: int,
        sent_date: str,
        contact_id: Optional[int] = None,
        **kwargs
    ) -> ThankYouMessage:
        message = ThankYouMessage(
            partner_id=partner_id,
            subject=subject,
            message_body=message_body,
            sent_by_id=sent_by_id,
            sent_date=datetime.fromisoformat(sent_date).date(),
            contact_id=contact_id,
            **kwargs
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_partner_recognition(
        db: AsyncSession,
        partner_id: int,
        limit: int = 20
    ) -> List[PartnerRecognition]:
        result = await db.execute(
            select(PartnerRecognition)
            .where(PartnerRecognition.partner_id == partner_id)
            .order_by(desc(PartnerRecognition.recognition_date))
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_thank_you_messages(
        db: AsyncSession,
        partner_id: int,
        limit: int = 50
    ) -> List[ThankYouMessage]:
        result = await db.execute(
            select(ThankYouMessage)
            .where(ThankYouMessage.partner_id == partner_id)
            .order_by(desc(ThankYouMessage.sent_date))
            .limit(limit)
        )
        return result.scalars().all()
