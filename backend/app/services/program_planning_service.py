# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.program import Program, ProgramStatus
from app.models.program_planning import (
    ProgramTemplate, TemplateBudgetItem, TemplateSupplyItem,
    TemplateMarketingMilestone, ProgramPlan, ProgramBudgetItem,
    ProgramSupplyItem, ProgramRoomBooking, ProgramEquipmentBooking,
    ProgramMarketingMilestone, ProgramVolunteerAssignment,
    ProgramEvaluation, VenueBookingStatus, SupplyItemStatus,
    VolunteerAssignmentStatus, MarketingMilestoneType,
)
from app.models.room import Room
from app.models.equipment import Equipment

logger = get_logger(__name__)


class ProgramPlanningService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Template Operations
    # ========================================================================

    async def list_templates(
        self,
        category: str | None = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ProgramTemplate]:
        query = select(ProgramTemplate).options(
            selectinload(ProgramTemplate.template_budget_items),
            selectinload(ProgramTemplate.template_supply_items),
            selectinload(ProgramTemplate.template_marketing_milestones),
        )
        if active_only:
            query = query.where(ProgramTemplate.is_active == True)
        if category:
            query = query.where(ProgramTemplate.category == category)
        query = query.order_by(ProgramTemplate.times_used.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_template(self, template_id: int) -> ProgramTemplate | None:
        query = select(ProgramTemplate).where(
            ProgramTemplate.id == template_id
        ).options(
            selectinload(ProgramTemplate.template_budget_items),
            selectinload(ProgramTemplate.template_supply_items),
            selectinload(ProgramTemplate.template_marketing_milestones),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_template(self, data: dict, user_id: int) -> ProgramTemplate:
        budget_items_data = data.pop("budget_items", None) or []
        supply_items_data = data.pop("supply_items", None) or []
        marketing_milestones_data = data.pop("marketing_milestones", None) or []

        template = ProgramTemplate(**data, created_by_id=user_id)
        self.db.add(template)
        await self.db.flush()

        for item_data in budget_items_data:
            item = TemplateBudgetItem(**item_data, template_id=template.id)
            self.db.add(item)

        for item_data in supply_items_data:
            item = TemplateSupplyItem(**item_data, template_id=template.id)
            self.db.add(item)

        for item_data in marketing_milestones_data:
            item = TemplateMarketingMilestone(**item_data, template_id=template.id)
            self.db.add(item)

        await self.db.commit()
        return await self.get_template(template.id)

    async def update_template(self, template_id: int, data: dict) -> ProgramTemplate | None:
        template = await self.get_template(template_id)
        if not template:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(template, key, value)
        await self.db.commit()
        return await self.get_template(template_id)

    async def delete_template(self, template_id: int) -> bool:
        template = await self.get_template(template_id)
        if not template:
            return False
        template.is_active = False
        await self.db.commit()
        return True

    async def create_template_from_program(
        self, program_id: int, template_name: str, user_id: int
    ) -> ProgramTemplate | None:
        program = await self.db.get(Program, program_id)
        if not program:
            return None

        # Get existing plan if one exists
        plan_result = await self.db.execute(
            select(ProgramPlan).where(ProgramPlan.program_id == program_id).options(
                selectinload(ProgramPlan.budget_items),
                selectinload(ProgramPlan.supply_items),
                selectinload(ProgramPlan.marketing_milestones),
            )
        )
        plan = plan_result.scalar_one_or_none()

        template = ProgramTemplate(
            name=template_name,
            description=f"Template based on: {program.title}",
            category=str(program.program_type) if program.program_type else "other",
            target_audience=str(program.audience) if program.audience else "all_ages",
            program_type=str(program.program_type) if program.program_type else "other",
            recommended_capacity=program.max_capacity,
            registration_required=program.registration_required,
            target_attendance=program.actual_attendance or program.expected_attendance,
            source_program_id=program_id,
            created_by_id=user_id,
        )

        if plan:
            template.estimated_budget = plan.total_budget

            for budget_item in plan.budget_items:
                tb = TemplateBudgetItem(
                    description=budget_item.description,
                    category=budget_item.category,
                    estimated_amount=budget_item.actual_amount or budget_item.estimated_amount,
                )
                template.template_budget_items.append(tb)

            for supply_item in plan.supply_items:
                ts = TemplateSupplyItem(
                    item_name=supply_item.item_name,
                    quantity=supply_item.quantity_needed,
                    unit=supply_item.unit,
                    estimated_cost=supply_item.actual_cost or supply_item.estimated_cost,
                    vendor_suggestion=supply_item.vendor,
                )
                template.template_supply_items.append(ts)

            for milestone in plan.marketing_milestones:
                # Convert due_date to days_before_program
                if milestone.due_date and program.program_date:
                    days_before = (program.program_date - milestone.due_date).days
                else:
                    days_before = 7
                tm = TemplateMarketingMilestone(
                    milestone_type=milestone.milestone_type,
                    description=milestone.description,
                    days_before_program=max(0, days_before),
                )
                template.template_marketing_milestones.append(tm)

        self.db.add(template)
        await self.db.commit()
        return await self.get_template(template.id)

    # ========================================================================
    # Program Plan Operations
    # ========================================================================

    async def create_plan(self, data: dict, user_id: int) -> ProgramPlan:
        template_id = data.get("template_id")
        copied_from_id = data.get("copied_from_program_id")

        plan = ProgramPlan(
            program_id=data["program_id"],
            template_id=template_id,
            copied_from_program_id=copied_from_id,
            planning_notes=data.get("planning_notes"),
            created_by_id=user_id,
        )
        self.db.add(plan)
        await self.db.flush()

        # If using a template, copy template items
        if template_id:
            template = await self.get_template(template_id)
            if template:
                template.times_used += 1
                program = await self.db.get(Program, data["program_id"])
                program_date = program.program_date if program else None
                await self._apply_template_to_plan(plan, template, program_date)

        # If copying from a previous program, copy its plan data
        if copied_from_id:
            await self._copy_plan_from_program(plan, copied_from_id)

        await self.db.commit()
        return await self.get_plan(plan.id)

    async def get_plan(self, plan_id: int) -> ProgramPlan | None:
        query = select(ProgramPlan).where(ProgramPlan.id == plan_id).options(
            selectinload(ProgramPlan.budget_items),
            selectinload(ProgramPlan.supply_items),
            selectinload(ProgramPlan.room_bookings),
            selectinload(ProgramPlan.equipment_bookings),
            selectinload(ProgramPlan.marketing_milestones),
            selectinload(ProgramPlan.volunteer_assignments),
            selectinload(ProgramPlan.evaluation),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_plan_by_program(self, program_id: int) -> ProgramPlan | None:
        query = select(ProgramPlan).where(ProgramPlan.program_id == program_id).options(
            selectinload(ProgramPlan.budget_items),
            selectinload(ProgramPlan.supply_items),
            selectinload(ProgramPlan.room_bookings),
            selectinload(ProgramPlan.equipment_bookings),
            selectinload(ProgramPlan.marketing_milestones),
            selectinload(ProgramPlan.volunteer_assignments),
            selectinload(ProgramPlan.evaluation),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_plan(self, plan_id: int, data: dict) -> ProgramPlan | None:
        plan = await self.get_plan(plan_id)
        if not plan:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(plan, key, value)
        if data.get("planning_complete"):
            plan.planning_completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        return await self.get_plan(plan_id)

    async def copy_program(self, data: dict, user_id: int) -> dict:
        source_program = await self.db.get(Program, data["source_program_id"])
        if not source_program:
            return {"error": "Source program not found"}

        # Create new program based on source
        new_program = Program(
            title=data["new_title"],
            description=source_program.description,
            program_type=source_program.program_type,
            audience=source_program.audience,
            program_date=data["new_program_date"],
            start_time=time.fromisoformat(data["new_start_time"]),
            end_time=time.fromisoformat(data["new_end_time"]) if data.get("new_end_time") else source_program.end_time,
            branch_id=data.get("branch_id") or source_program.branch_id,
            location_name=source_program.location_name,
            is_virtual=source_program.is_virtual,
            virtual_link=source_program.virtual_link,
            max_capacity=source_program.max_capacity,
            registration_required=source_program.registration_required,
            expected_attendance=source_program.actual_attendance or source_program.expected_attendance,
            status=ProgramStatus.PLANNED,
            created_by_id=user_id,
        )
        self.db.add(new_program)
        await self.db.flush()

        # Create plan linked to new program
        plan = ProgramPlan(
            program_id=new_program.id,
            copied_from_program_id=data["source_program_id"],
            planning_notes=data.get("notes"),
            created_by_id=user_id,
        )
        self.db.add(plan)
        await self.db.flush()

        # Copy plan data from source
        if data.get("copy_budget", True) or data.get("copy_supplies", True) or data.get("copy_marketing_timeline", True) or data.get("copy_volunteer_roles", True):
            await self._copy_plan_from_program(
                plan, data["source_program_id"],
                copy_budget=data.get("copy_budget", True),
                copy_supplies=data.get("copy_supplies", True),
                copy_marketing=data.get("copy_marketing_timeline", True),
                copy_volunteers=data.get("copy_volunteer_roles", True),
                new_program_date=data["new_program_date"],
            )

        await self.db.commit()
        return {"program_id": new_program.id, "plan_id": plan.id}

    # ========================================================================
    # Budget Operations
    # ========================================================================

    async def add_budget_item(self, data: dict) -> ProgramBudgetItem:
        item = ProgramBudgetItem(**data)
        self.db.add(item)
        await self.db.flush()
        await self._recalculate_budget(data["plan_id"])
        await self.db.commit()
        return item

    async def update_budget_item(self, item_id: int, data: dict) -> ProgramBudgetItem | None:
        item = await self.db.get(ProgramBudgetItem, item_id)
        if not item:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(item, key, value)
        await self._recalculate_budget(item.plan_id)
        await self.db.commit()
        return item

    async def delete_budget_item(self, item_id: int) -> bool:
        item = await self.db.get(ProgramBudgetItem, item_id)
        if not item:
            return False
        plan_id = item.plan_id
        await self.db.delete(item)
        await self._recalculate_budget(plan_id)
        await self.db.commit()
        return True

    # ========================================================================
    # Supply Checklist Operations
    # ========================================================================

    async def add_supply_item(self, data: dict) -> ProgramSupplyItem:
        item = ProgramSupplyItem(**data)
        self.db.add(item)
        await self.db.commit()
        return item

    async def update_supply_item(self, item_id: int, data: dict) -> ProgramSupplyItem | None:
        item = await self.db.get(ProgramSupplyItem, item_id)
        if not item:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(item, key, value)
        await self.db.commit()
        return item

    async def delete_supply_item(self, item_id: int) -> bool:
        item = await self.db.get(ProgramSupplyItem, item_id)
        if not item:
            return False
        await self.db.delete(item)
        await self.db.commit()
        return True

    async def get_supply_checklist(self, plan_id: int) -> list[ProgramSupplyItem]:
        result = await self.db.execute(
            select(ProgramSupplyItem)
            .where(ProgramSupplyItem.plan_id == plan_id)
            .order_by(ProgramSupplyItem.status, ProgramSupplyItem.item_name)
        )
        return list(result.scalars().all())

    # ========================================================================
    # Room & Equipment Auto-Booking
    # ========================================================================

    async def auto_book_room(self, plan_id: int, room_id: int | None = None) -> ProgramRoomBooking | None:
        plan = await self.get_plan(plan_id)
        if not plan:
            return None

        program = await self.db.get(Program, plan.program_id)
        if not program:
            return None

        if not room_id and plan.template:
            # Try to find a matching room
            room_type = plan.template.room_type_needed if plan.template else None
            room_id = await self._find_available_room(
                program.program_date,
                program.start_time,
                program.end_time,
                room_type=room_type,
                capacity_needed=program.max_capacity,
            )

        booking = ProgramRoomBooking(
            plan_id=plan_id,
            room_id=room_id,
            status=VenueBookingStatus.CONFIRMED if room_id else VenueBookingStatus.PENDING,
        )
        self.db.add(booking)
        await self.db.commit()
        return booking

    async def add_equipment_booking(self, data: dict) -> ProgramEquipmentBooking:
        booking = ProgramEquipmentBooking(**data)
        self.db.add(booking)
        await self.db.commit()
        return booking

    async def update_equipment_booking(self, booking_id: int, data: dict) -> ProgramEquipmentBooking | None:
        booking = await self.db.get(ProgramEquipmentBooking, booking_id)
        if not booking:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(booking, key, value)
        await self.db.commit()
        return booking

    # ========================================================================
    # Marketing Timeline
    # ========================================================================

    async def add_marketing_milestone(self, data: dict) -> ProgramMarketingMilestone:
        milestone = ProgramMarketingMilestone(**data)
        self.db.add(milestone)
        await self.db.commit()
        return milestone

    async def update_marketing_milestone(
        self, milestone_id: int, data: dict, user_id: int | None = None
    ) -> ProgramMarketingMilestone | None:
        milestone = await self.db.get(ProgramMarketingMilestone, milestone_id)
        if not milestone:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(milestone, key, value)
        if data.get("completed") and not milestone.completed_at:
            milestone.completed_at = datetime.now(timezone.utc)
            milestone.completed_by_id = user_id
        await self.db.commit()
        return milestone

    async def get_upcoming_marketing_reminders(
        self, days_ahead: int = 7
    ) -> list[ProgramMarketingMilestone]:
        cutoff = date.today() + timedelta(days=days_ahead)
        result = await self.db.execute(
            select(ProgramMarketingMilestone)
            .where(
                and_(
                    ProgramMarketingMilestone.completed == False,
                    ProgramMarketingMilestone.due_date <= cutoff,
                    ProgramMarketingMilestone.due_date >= date.today(),
                )
            )
            .order_by(ProgramMarketingMilestone.due_date)
        )
        return list(result.scalars().all())

    # ========================================================================
    # Volunteer Assignment
    # ========================================================================

    async def assign_volunteer(self, data: dict) -> ProgramVolunteerAssignment:
        assignment = ProgramVolunteerAssignment(**data)
        self.db.add(assignment)
        await self.db.commit()
        return assignment

    async def update_volunteer_assignment(
        self, assignment_id: int, data: dict
    ) -> ProgramVolunteerAssignment | None:
        assignment = await self.db.get(ProgramVolunteerAssignment, assignment_id)
        if not assignment:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(assignment, key, value)
        if data.get("status") == VolunteerAssignmentStatus.CONFIRMED.value:
            assignment.confirmed_at = datetime.now(timezone.utc)
        await self.db.commit()
        return assignment

    async def delete_volunteer_assignment(self, assignment_id: int) -> bool:
        assignment = await self.db.get(ProgramVolunteerAssignment, assignment_id)
        if not assignment:
            return False
        await self.db.delete(assignment)
        await self.db.commit()
        return True

    # ========================================================================
    # Evaluation
    # ========================================================================

    async def create_evaluation(self, data: dict, user_id: int) -> ProgramEvaluation:
        eval_obj = ProgramEvaluation(**data, evaluated_by_id=user_id, evaluated_at=datetime.now(timezone.utc))
        self.db.add(eval_obj)
        await self.db.commit()
        return eval_obj

    async def update_evaluation(
        self, eval_id: int, data: dict, user_id: int
    ) -> ProgramEvaluation | None:
        eval_obj = await self.db.get(ProgramEvaluation, eval_id)
        if not eval_obj:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(eval_obj, key, value)
        eval_obj.evaluated_by_id = user_id
        eval_obj.evaluated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return eval_obj

    async def get_evaluation(self, plan_id: int) -> ProgramEvaluation | None:
        result = await self.db.execute(
            select(ProgramEvaluation).where(ProgramEvaluation.plan_id == plan_id)
        )
        return result.scalar_one_or_none()

    # ========================================================================
    # Success Metrics Comparison
    # ========================================================================

    async def compare_success_metrics(
        self,
        program_ids: list[int] | None = None,
        program_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 20,
    ) -> list[dict]:
        query = (
            select(Program, ProgramPlan, ProgramEvaluation)
            .outerjoin(ProgramPlan, ProgramPlan.program_id == Program.id)
            .outerjoin(ProgramEvaluation, ProgramEvaluation.plan_id == ProgramPlan.id)
            .where(Program.status == ProgramStatus.COMPLETED)
        )

        if program_ids:
            query = query.where(Program.id.in_(program_ids))
        if program_type:
            query = query.where(Program.program_type == program_type)
        if date_from:
            query = query.where(Program.program_date >= date_from)
        if date_to:
            query = query.where(Program.program_date <= date_to)

        query = query.order_by(Program.program_date.desc()).limit(limit)
        result = await self.db.execute(query)
        rows = result.all()

        comparisons = []
        for program, plan, evaluation in rows:
            comparison = {
                "program_id": program.id,
                "program_title": program.title,
                "program_date": program.program_date,
                "attendance": program.actual_attendance,
                "target_attendance": program.expected_attendance,
                "attendance_rate": (
                    round(program.actual_attendance / program.expected_attendance * 100, 1)
                    if program.expected_attendance and program.actual_attendance
                    else None
                ),
                "total_budget": plan.total_budget if plan else None,
                "total_spent": plan.total_spent if plan else None,
                "cost_per_attendee": (
                    evaluation.cost_per_attendee if evaluation else None
                ),
                "overall_rating": (
                    str(evaluation.overall_rating) if evaluation and evaluation.overall_rating else None
                ),
                "recommend_repeat": evaluation.recommend_repeat if evaluation else None,
            }
            comparisons.append(comparison)

        return comparisons

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    async def _recalculate_budget(self, plan_id: int) -> None:
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(ProgramBudgetItem.estimated_amount), 0),
                func.coalesce(func.sum(ProgramBudgetItem.actual_amount), 0),
            ).where(ProgramBudgetItem.plan_id == plan_id)
        )
        row = result.one()
        plan = await self.db.get(ProgramPlan, plan_id)
        if plan:
            plan.total_budget = row[0]
            plan.total_spent = row[1]

    async def _apply_template_to_plan(
        self, plan: ProgramPlan, template: ProgramTemplate, program_date: date | None
    ) -> None:
        for tb in template.template_budget_items:
            item = ProgramBudgetItem(
                plan_id=plan.id,
                description=tb.description,
                category=tb.category,
                estimated_amount=tb.estimated_amount,
            )
            self.db.add(item)

        for ts in template.template_supply_items:
            item = ProgramSupplyItem(
                plan_id=plan.id,
                item_name=ts.item_name,
                quantity_needed=ts.quantity,
                unit=ts.unit,
                estimated_cost=ts.estimated_cost,
                vendor=ts.vendor_suggestion,
                status=SupplyItemStatus.NEEDED,
            )
            self.db.add(item)

        for tm in template.template_marketing_milestones:
            due = (
                program_date - timedelta(days=tm.days_before_program)
                if program_date
                else date.today() + timedelta(days=tm.days_before_program)
            )
            milestone = ProgramMarketingMilestone(
                plan_id=plan.id,
                milestone_type=tm.milestone_type,
                description=tm.description,
                due_date=due,
            )
            self.db.add(milestone)

        if template.estimated_budget:
            plan.total_budget = template.estimated_budget

    async def _copy_plan_from_program(
        self,
        target_plan: ProgramPlan,
        source_program_id: int,
        copy_budget: bool = True,
        copy_supplies: bool = True,
        copy_marketing: bool = True,
        copy_volunteers: bool = True,
        new_program_date: date | None = None,
    ) -> None:
        source_plan_result = await self.db.execute(
            select(ProgramPlan).where(ProgramPlan.program_id == source_program_id).options(
                selectinload(ProgramPlan.budget_items),
                selectinload(ProgramPlan.supply_items),
                selectinload(ProgramPlan.marketing_milestones),
                selectinload(ProgramPlan.volunteer_assignments),
            )
        )
        source_plan = source_plan_result.scalar_one_or_none()
        if not source_plan:
            return

        source_program = await self.db.get(Program, source_program_id)

        if copy_budget:
            for item in source_plan.budget_items:
                new_item = ProgramBudgetItem(
                    plan_id=target_plan.id,
                    description=item.description,
                    category=item.category,
                    estimated_amount=item.actual_amount or item.estimated_amount,
                    vendor=item.vendor,
                    notes=item.notes,
                )
                self.db.add(new_item)

        if copy_supplies:
            for item in source_plan.supply_items:
                new_item = ProgramSupplyItem(
                    plan_id=target_plan.id,
                    item_name=item.item_name,
                    quantity_needed=item.quantity_needed,
                    unit=item.unit,
                    estimated_cost=item.actual_cost or item.estimated_cost,
                    vendor=item.vendor,
                    status=SupplyItemStatus.NEEDED,
                )
                self.db.add(new_item)

        if copy_marketing and new_program_date and source_program:
            for milestone in source_plan.marketing_milestones:
                # Recalculate dates relative to new program date
                if milestone.due_date and source_program.program_date:
                    days_before = (source_program.program_date - milestone.due_date).days
                    new_due = new_program_date - timedelta(days=max(0, days_before))
                else:
                    new_due = new_program_date - timedelta(days=7)
                new_milestone = ProgramMarketingMilestone(
                    plan_id=target_plan.id,
                    milestone_type=milestone.milestone_type,
                    description=milestone.description,
                    due_date=new_due,
                )
                self.db.add(new_milestone)

        if copy_volunteers:
            for assignment in source_plan.volunteer_assignments:
                new_assignment = ProgramVolunteerAssignment(
                    plan_id=target_plan.id,
                    role=assignment.role,
                    status=VolunteerAssignmentStatus.REQUESTED,
                    notes=f"Role copied from program #{source_program_id}",
                )
                self.db.add(new_assignment)

    async def _find_available_room(
        self,
        program_date: date,
        start_time: time | None,
        end_time: time | None,
        room_type: str | None = None,
        capacity_needed: int | None = None,
    ) -> int | None:
        query = select(Room).where(Room.is_active == True)
        if room_type:
            query = query.where(Room.room_type == room_type)
        if capacity_needed:
            query = query.where(Room.capacity >= capacity_needed)
        query = query.order_by(Room.capacity)

        result = await self.db.execute(query)
        rooms = result.scalars().all()

        for room in rooms:
            # Check for existing reservations that overlap
            # Simplified check: just return first room with enough capacity
            return room.id

        return None
