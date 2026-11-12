# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, time
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from ..models import (
    SignageDisplay,
    SignageContent,
    SignageTemplate,
    SignageSchedule,
    SignageEmergencyMessage,
    SignageAnalytics,
    SignageEventPromotion,
    SignageBranchContent,
    SignageWayfinderNode,
    User,
    Event,
)
from ..models.signage import (
    SignageDisplayStatus,
    SignageContentType,
    SignageApprovalStatus,
    SignageScheduleType,
)


class SignageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_display(
        self,
        name: str,
        location_description: str,
        display_type: str,
        status: str = SignageDisplayStatus.active.value,
        branch_id: Optional[int] = None,
        device_identifier: Optional[str] = None,
        mac_address: Optional[str] = None,
        width_pixels: int = 1920,
        height_pixels: int = 1080,
        user_id: Optional[int] = None,
        **kwargs,
    ) -> SignageDisplay:
        display = SignageDisplay(
            name=name,
            location_description=location_description,
            display_type=display_type,
            status=status,
            branch_id=branch_id,
            device_identifier=device_identifier,
            mac_address=mac_address,
            width_pixels=width_pixels,
            height_pixels=height_pixels,
            created_by_user_id=user_id,
            **{k: v for k, v in kwargs.items() if hasattr(SignageDisplay, k)},
        )
        self.db.add(display)
        await self.db.flush()
        await self.db.refresh(display)
        return display

    async def get_display(self, display_id: int) -> Optional[SignageDisplay]:
        stmt = select(SignageDisplay).where(SignageDisplay.id == display_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_display(self, display_id: int, **updates) -> Optional[SignageDisplay]:
        display = await self.get_display(display_id)
        if not display:
            return None

        for key, value in updates.items():
            if hasattr(display, key):
                setattr(display, key, value)

        await self.db.flush()
        await self.db.refresh(display)
        return display

    async def update_display_status(
        self, display_id: int, status: SignageDisplayStatus
    ) -> Optional[SignageDisplay]:
        display = await self.get_display(display_id)
        if not display:
            return None

        display.status = status
        if status == SignageDisplayStatus.offline:
            display.is_online = False
        elif status == SignageDisplayStatus.active:
            display.is_online = True
            display.last_heartbeat = datetime.now()

        await self.db.flush()
        await self.db.refresh(display)
        return display

    async def list_displays(
        self,
        status: Optional[str] = None,
        branch_id: Optional[int] = None,
        display_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[SignageDisplay], int]:
        stmt = select(SignageDisplay)

        if status:
            stmt = stmt.where(SignageDisplay.status == status)
        if branch_id:
            stmt = stmt.where(SignageDisplay.branch_id == branch_id)
        if display_type:
            stmt = stmt.where(SignageDisplay.display_type == display_type)

        # Count over the already-filtered stmt. A bare count() is required:
        # count(SignageDisplay.id) would re-add the table to the FROM clause
        # alongside the subquery, producing a cartesian product.
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.limit(limit).offset(offset).order_by(SignageDisplay.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def delete_display(self, display_id: int) -> bool:
        display = await self.get_display(display_id)
        if not display:
            return False

        await self.db.delete(display)
        return True

    async def record_heartbeat(self, display_id: int) -> Optional[SignageDisplay]:
        return await self.update_display(
            display_id,
            last_heartbeat=datetime.now(),
            is_online=True,
        )


class SignageContentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_content(
        self,
        title: str,
        content_type: str,
        user_id: Optional[int] = None,
        branch_id: Optional[int] = None,
        template_id: Optional[int] = None,
        html_content: Optional[str] = None,
        image_url: Optional[str] = None,
        video_url: Optional[str] = None,
        live_data_source: Optional[str] = None,
        display_duration_seconds: int = 30,
        **kwargs,
    ) -> SignageContent:
        content = SignageContent(
            title=title,
            content_type=content_type,
            created_by_user_id=user_id,
            branch_id=branch_id,
            template_id=template_id,
            html_content=html_content,
            image_url=image_url,
            video_url=video_url,
            live_data_source=live_data_source,
            display_duration_seconds=display_duration_seconds,
            approval_status=SignageApprovalStatus.draft.value,
            **{k: v for k, v in kwargs.items() if hasattr(SignageContent, k)},
        )
        self.db.add(content)
        await self.db.flush()
        await self.db.refresh(content)
        return content

    async def get_content(self, content_id: int) -> Optional[SignageContent]:
        stmt = (
            select(SignageContent)
            .where(SignageContent.id == content_id)
            .options(selectinload(SignageContent.template))
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def submit_for_approval(self, content_id: int) -> Optional[SignageContent]:
        content = await self.get_content(content_id)
        if not content or content.approval_status != SignageApprovalStatus.draft.value:
            return None

        content.approval_status = SignageApprovalStatus.pending_review.value
        await self.db.flush()
        await self.db.refresh(content)
        return content

    async def approve_content(self, content_id: int, reviewer_id: int) -> Optional[SignageContent]:
        content = await self.get_content(content_id)
        if not content:
            return None

        content.approval_status = SignageApprovalStatus.approved.value
        content.reviewed_by_user_id = reviewer_id
        content.reviewed_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(content)
        return content

    async def reject_content(
        self, content_id: int, reviewer_id: int, reason: str
    ) -> Optional[SignageContent]:
        content = await self.get_content(content_id)
        if not content:
            return None

        content.approval_status = SignageApprovalStatus.rejected.value
        content.reviewed_by_user_id = reviewer_id
        content.reviewed_at = datetime.now()
        content.rejection_reason = reason
        await self.db.flush()
        await self.db.refresh(content)
        return content

    async def list_content(
        self,
        approval_status: Optional[str] = None,
        content_type: Optional[str] = None,
        branch_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[SignageContent], int]:
        stmt = select(SignageContent)

        if approval_status:
            stmt = stmt.where(SignageContent.approval_status == approval_status)
        if content_type:
            stmt = stmt.where(SignageContent.content_type == content_type)
        if branch_id:
            stmt = stmt.where(SignageContent.branch_id == branch_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.limit(limit).offset(offset).order_by(SignageContent.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def update_content(self, content_id: int, **updates) -> Optional[SignageContent]:
        content = await self.get_content(content_id)
        if not content or content.approval_status != SignageApprovalStatus.draft.value:
            return None

        for key, value in updates.items():
            if hasattr(content, key) and key not in [
                "approval_status",
                "reviewed_by_user_id",
            ]:
                setattr(content, key, value)

        await self.db.flush()
        await self.db.refresh(content)
        return content

    async def delete_content(self, content_id: int) -> bool:
        content = await self.get_content(content_id)
        if not content:
            return False

        # Check if content is scheduled
        stmt = select(func.count(SignageSchedule.id)).where(
            SignageSchedule.content_id == content_id
        )
        result = await self.db.execute(stmt)
        if result.scalar() > 0:
            return False  # Cannot delete scheduled content

        await self.db.delete(content)
        return True


class SignageTemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_template(
        self,
        name: str,
        html_template: str,
        user_id: Optional[int] = None,
        is_public: bool = False,
        category: Optional[str] = None,
        template_variables: Optional[Dict[str, str]] = None,
        data_source_config: Optional[Dict[str, Any]] = None,
        css_styles: Optional[str] = None,
        **kwargs,
    ) -> SignageTemplate:
        template = SignageTemplate(
            name=name,
            html_template=html_template,
            created_by_user_id=user_id,
            is_public=is_public,
            category=category,
            template_variables=template_variables or {},
            data_source_config=data_source_config,
            css_styles=css_styles,
            **{k: v for k, v in kwargs.items() if hasattr(SignageTemplate, k)},
        )
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def get_template(self, template_id: int) -> Optional[SignageTemplate]:
        stmt = select(SignageTemplate).where(SignageTemplate.id == template_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_templates(
        self,
        category: Optional[str] = None,
        is_public: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[SignageTemplate], int]:
        stmt = select(SignageTemplate)

        if category:
            stmt = stmt.where(SignageTemplate.category == category)
        if is_public is not None:
            stmt = stmt.where(SignageTemplate.is_public == is_public)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.limit(limit).offset(offset).order_by(SignageTemplate.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def update_template(self, template_id: int, **updates) -> Optional[SignageTemplate]:
        template = await self.get_template(template_id)
        if not template:
            return None

        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)

        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def delete_template(self, template_id: int) -> bool:
        template = await self.get_template(template_id)
        if not template:
            return False

        await self.db.delete(template)
        return True


class SignageScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def schedule_content(
        self,
        display_id: int,
        content_id: int,
        start_datetime: datetime,
        schedule_type: str = SignageScheduleType.one_time.value,
        end_datetime: Optional[datetime] = None,
        event_id: Optional[int] = None,
        display_priority: int = 100,
        user_id: Optional[int] = None,
        **kwargs,
    ) -> SignageSchedule:
        schedule = SignageSchedule(
            display_id=display_id,
            content_id=content_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            schedule_type=schedule_type,
            event_id=event_id,
            display_priority=display_priority,
            created_by_user_id=user_id,
            **{k: v for k, v in kwargs.items() if hasattr(SignageSchedule, k)},
        )
        self.db.add(schedule)
        await self.db.flush()
        await self.db.refresh(schedule)
        return schedule

    async def get_schedule(self, schedule_id: int) -> Optional[SignageSchedule]:
        stmt = select(SignageSchedule).where(SignageSchedule.id == schedule_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_active_content_for_display(self, display_id: int) -> Optional[SignageContent]:
        # 1. Emergency override has top priority. Predicate matches
        # SignageEmergencyService.get_active_emergency_messages.
        emergency_stmt = (
            select(SignageEmergencyMessage)
            .where(
                and_(
                    SignageEmergencyMessage.is_active == True,
                    or_(
                        SignageEmergencyMessage.display_id == display_id,
                        SignageEmergencyMessage.applies_to_all_displays == True,
                    ),
                )
            )
            .order_by(SignageEmergencyMessage.activated_at.desc())
            .limit(1)
        )
        emergency_result = await self.db.execute(emergency_stmt)
        emergency = emergency_result.scalars().first()

        if emergency:
            # Transient SignageContent shaped for the current-content endpoint.
            # Not added to the session, never flushed.
            return SignageContent(
                id=emergency.id,
                title=emergency.message_title,
                html_content=emergency.message_content,
                content_type=SignageContentType.emergency.value,
                display_duration_seconds=60,
                approval_status=SignageApprovalStatus.approved.value,
            )

        # 2. Schedules: only return content that is approved.
        now = datetime.now()
        stmt = (
            select(SignageContent)
            .join(SignageSchedule, SignageSchedule.content_id == SignageContent.id)
            .where(
                and_(
                    SignageSchedule.display_id == display_id,
                    SignageSchedule.is_active == True,
                    SignageSchedule.start_datetime <= now,
                    or_(
                        SignageSchedule.end_datetime == None,
                        SignageSchedule.end_datetime >= now,
                    ),
                    SignageContent.approval_status == SignageApprovalStatus.approved.value,
                )
            )
            .order_by(SignageSchedule.display_priority.asc())
            .limit(1)
        )

        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_schedules_for_display(
        self, display_id: int, is_active: Optional[bool] = None
    ) -> List[SignageSchedule]:
        stmt = select(SignageSchedule).where(SignageSchedule.display_id == display_id)

        if is_active is not None:
            stmt = stmt.where(SignageSchedule.is_active == is_active)

        stmt = stmt.order_by(SignageSchedule.start_datetime.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_schedule(self, schedule_id: int, **updates) -> Optional[SignageSchedule]:
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            return None

        for key, value in updates.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)

        await self.db.flush()
        await self.db.refresh(schedule)
        return schedule

    async def delete_schedule(self, schedule_id: int) -> bool:
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            return False

        await self.db.delete(schedule)
        return True

    async def deactivate_expired_schedules(self) -> int:
        now = datetime.now()

        stmt = select(SignageSchedule).where(
            and_(
                SignageSchedule.is_active == True,
                SignageSchedule.end_datetime < now,
            )
        )

        result = await self.db.execute(stmt)
        schedules = result.scalars().all()

        for schedule in schedules:
            schedule.is_active = False

        await self.db.flush()
        return len(schedules)


class SignageEmergencyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_emergency_message(
        self,
        message_title: str,
        message_content: str,
        user_id: Optional[int] = None,
        display_id: Optional[int] = None,
        applies_to_all: bool = False,
        message_type: str = "warning",
        **kwargs,
    ) -> SignageEmergencyMessage:
        message = SignageEmergencyMessage(
            message_title=message_title,
            message_content=message_content,
            created_by_user_id=user_id,
            display_id=display_id,
            applies_to_all_displays=applies_to_all,
            message_type=message_type,
            **{k: v for k, v in kwargs.items() if hasattr(SignageEmergencyMessage, k)},
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_active_emergency_messages(
        self, display_id: Optional[int] = None
    ) -> List[SignageEmergencyMessage]:
        stmt = select(SignageEmergencyMessage).where(SignageEmergencyMessage.is_active == True)

        if display_id:
            stmt = stmt.where(
                or_(
                    SignageEmergencyMessage.display_id == display_id,
                    SignageEmergencyMessage.applies_to_all_displays == True,
                )
            )

        stmt = stmt.order_by(SignageEmergencyMessage.activated_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def deactivate_emergency_message(
        self, message_id: int
    ) -> Optional[SignageEmergencyMessage]:
        stmt = select(SignageEmergencyMessage).where(SignageEmergencyMessage.id == message_id)
        result = await self.db.execute(stmt)
        message = result.scalars().first()

        if not message:
            return None

        message.is_active = False
        message.deactivated_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(message)
        return message


class SignageAnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_event(
        self,
        display_id: int,
        content_id: int,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> SignageAnalytics:
        # Set the counter this event represents. get_display_analytics sums
        # these columns; leaving them at their 0 default made every display
        # report zero views forever. view_end closes the view that view_start
        # opened, so it must not count as a second view.
        event = SignageAnalytics(
            display_id=display_id,
            content_id=content_id,
            event_type=event_type,
            event_data=event_data,
            view_count=1 if event_type == "view_start" else 0,
            interaction_count=1 if event_type == "interaction" else 0,
            date=datetime.now().strftime("%Y-%m-%d"),
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_display_analytics(
        self,
        display_id: int,
        days: int = 30,
    ) -> Dict[str, Any]:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        stmt = select(SignageAnalytics).where(
            and_(
                SignageAnalytics.display_id == display_id,
                SignageAnalytics.date >= start_date,
            )
        )

        result = await self.db.execute(stmt)
        events = result.scalars().all()

        if not events:
            return {
                "display_id": display_id,
                "total_views": 0,
                "total_display_time": 0,
                "total_interactions": 0,
                "engagement_score": 0,
                "period_days": days,
            }

        total_views = sum(e.view_count for e in events)
        total_interactions = sum(e.interaction_count for e in events)
        total_display_time = sum(e.total_display_time_seconds for e in events)
        avg_display_time = total_display_time / len(events) if events else 0

        # Engagement score (0-100): interaction rate (0-50) + display time (0-50)
        interaction_score = (
            min((total_interactions / total_views * 100), 50) if total_views > 0 else 0
        )
        time_score = min(avg_display_time / 60 * 50, 50)  # 60s+ = full marks
        engagement_score = round(interaction_score + time_score, 1)

        return {
            "display_id": display_id,
            "total_views": total_views,
            "total_display_time": total_display_time,
            "total_interactions": total_interactions,
            "engagement_score": engagement_score,
            "period_days": days,
        }

    async def get_content_performance(
        self,
        content_id: int,
        days: int = 30,
    ) -> Dict[str, Any]:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        stmt = select(SignageAnalytics).where(
            and_(
                SignageAnalytics.content_id == content_id,
                SignageAnalytics.date >= start_date,
            )
        )

        result = await self.db.execute(stmt)
        events = result.scalars().all()

        if not events:
            return {
                "content_id": content_id,
                "total_impressions": 0,
                "total_display_time": 0,
                "engagement_rate": 0.0,
                "engagement_score": 0,
                "period_days": days,
            }

        total_impressions = sum(e.view_count for e in events)
        interactions = sum(e.interaction_count for e in events)
        total_display_time = sum(e.total_display_time_seconds for e in events)
        avg_display_time = total_display_time / len(events) if events else 0
        engagement_rate = (interactions / total_impressions * 100) if total_impressions > 0 else 0

        # Engagement score (0-100): interaction rate (0-50) + display time (0-50)
        interaction_score = min(engagement_rate, 50)
        time_score = min(avg_display_time / 60 * 50, 50)
        engagement_score = round(interaction_score + time_score, 1)

        return {
            "content_id": content_id,
            "total_impressions": total_impressions,
            "total_display_time": total_display_time,
            "engagement_rate": round(engagement_rate, 2),
            "engagement_score": engagement_score,
            "period_days": days,
        }


class SignageWayfinderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_wayfinder_node(
        self,
        location_name: str,
        user_id: Optional[int] = None,
        display_id: Optional[int] = None,
        location_type: Optional[str] = None,
        floor_number: Optional[int] = None,
        services_available: Optional[str] = None,
        room_info: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> SignageWayfinderNode:
        node = SignageWayfinderNode(
            location_name=location_name,
            created_by_user_id=user_id,
            display_id=display_id,
            location_type=location_type,
            floor_number=floor_number,
            services_available=services_available,
            room_info=room_info,
            **{k: v for k, v in kwargs.items() if hasattr(SignageWayfinderNode, k)},
        )
        self.db.add(node)
        await self.db.flush()
        await self.db.refresh(node)
        return node

    async def get_wayfinder_node(self, node_id: int) -> Optional[SignageWayfinderNode]:
        stmt = select(SignageWayfinderNode).where(SignageWayfinderNode.id == node_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_wayfinder_nodes(
        self, floor_number: Optional[int] = None, location_type: Optional[str] = None
    ) -> List[SignageWayfinderNode]:
        stmt = select(SignageWayfinderNode).where(SignageWayfinderNode.is_active == True)

        if floor_number is not None:
            stmt = stmt.where(SignageWayfinderNode.floor_number == floor_number)
        if location_type:
            stmt = stmt.where(SignageWayfinderNode.location_type == location_type)

        result = await self.db.execute(stmt)
        return result.scalars().all()


class SignageEventPromotionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_promotion(
        self,
        event_id: int,
        content_id: int,
        user_id: Optional[int] = None,
        display_id: Optional[int] = None,
        promotion_start: Optional[datetime] = None,
        promotion_end: Optional[datetime] = None,
        auto_schedule: bool = True,
        priority: int = 50,
        **kwargs,
    ) -> SignageEventPromotion:
        promotion = SignageEventPromotion(
            event_id=event_id,
            content_id=content_id,
            created_by_user_id=user_id,
            display_id=display_id,
            promotion_start=promotion_start,
            promotion_end=promotion_end,
            auto_schedule=auto_schedule,
            priority=priority,
            **{k: v for k, v in kwargs.items() if hasattr(SignageEventPromotion, k)},
        )
        self.db.add(promotion)
        await self.db.flush()
        await self.db.refresh(promotion)
        return promotion

    async def get_promotion(self, promotion_id: int) -> Optional[SignageEventPromotion]:
        stmt = select(SignageEventPromotion).where(SignageEventPromotion.id == promotion_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_promotions(
        self,
        event_id: Optional[int] = None,
        display_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[SignageEventPromotion], int]:
        stmt = select(SignageEventPromotion)

        if event_id:
            stmt = stmt.where(SignageEventPromotion.event_id == event_id)
        if display_id:
            stmt = stmt.where(SignageEventPromotion.display_id == display_id)
        if is_active is not None:
            stmt = stmt.where(SignageEventPromotion.is_active == is_active)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.limit(limit).offset(offset).order_by(SignageEventPromotion.id.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def get_promotions_for_event(self, event_id: int) -> List[SignageEventPromotion]:
        stmt = (
            select(SignageEventPromotion)
            .where(
                and_(
                    SignageEventPromotion.event_id == event_id,
                    SignageEventPromotion.is_active == True,
                )
            )
            .order_by(SignageEventPromotion.priority.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_promotion(
        self, promotion_id: int, **updates
    ) -> Optional[SignageEventPromotion]:
        promotion = await self.get_promotion(promotion_id)
        if not promotion:
            return None

        for key, value in updates.items():
            if hasattr(promotion, key):
                setattr(promotion, key, value)

        await self.db.flush()
        await self.db.refresh(promotion)
        return promotion

    async def deactivate_promotion(self, promotion_id: int) -> Optional[SignageEventPromotion]:
        promotion = await self.get_promotion(promotion_id)
        if not promotion:
            return None

        promotion.is_active = False
        await self.db.flush()
        await self.db.refresh(promotion)
        return promotion

    async def delete_promotion(self, promotion_id: int) -> bool:
        promotion = await self.get_promotion(promotion_id)
        if not promotion:
            return False

        await self.db.delete(promotion)
        return True


class SignageBranchContentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_branch_content(
        self,
        branch_id: int,
        content_id: int,
        user_id: Optional[int] = None,
        override_content: Optional[str] = None,
        is_localized: bool = False,
        display_priority: int = 100,
        **kwargs,
    ) -> SignageBranchContent:
        branch_content = SignageBranchContent(
            branch_id=branch_id,
            content_id=content_id,
            created_by_user_id=user_id,
            override_content=override_content,
            is_localized=is_localized,
            display_priority=display_priority,
            **{k: v for k, v in kwargs.items() if hasattr(SignageBranchContent, k)},
        )
        self.db.add(branch_content)
        await self.db.flush()
        await self.db.refresh(branch_content)
        return branch_content

    async def get_branch_content(self, branch_content_id: int) -> Optional[SignageBranchContent]:
        stmt = select(SignageBranchContent).where(SignageBranchContent.id == branch_content_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_branch_content(
        self,
        branch_id: Optional[int] = None,
        content_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[SignageBranchContent], int]:
        stmt = select(SignageBranchContent)

        if branch_id:
            stmt = stmt.where(SignageBranchContent.branch_id == branch_id)
        if content_id:
            stmt = stmt.where(SignageBranchContent.content_id == content_id)
        if is_active is not None:
            stmt = stmt.where(SignageBranchContent.is_active == is_active)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.limit(limit).offset(offset).order_by(SignageBranchContent.id.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def get_content_for_branch(self, branch_id: int) -> List[SignageBranchContent]:
        stmt = (
            select(SignageBranchContent)
            .where(
                and_(
                    SignageBranchContent.branch_id == branch_id,
                    SignageBranchContent.is_active == True,
                )
            )
            .order_by(SignageBranchContent.display_priority.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_branch_content(
        self, branch_content_id: int, **updates
    ) -> Optional[SignageBranchContent]:
        branch_content = await self.get_branch_content(branch_content_id)
        if not branch_content:
            return None

        for key, value in updates.items():
            if hasattr(branch_content, key):
                setattr(branch_content, key, value)

        await self.db.flush()
        await self.db.refresh(branch_content)
        return branch_content

    async def delete_branch_content(self, branch_content_id: int) -> bool:
        branch_content = await self.get_branch_content(branch_content_id)
        if not branch_content:
            return False

        await self.db.delete(branch_content)
        return True
