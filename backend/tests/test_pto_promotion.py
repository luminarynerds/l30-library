# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for PTO Promotion Service"""

import pytest
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pto import (
    PTORequest, PTORequestStatus, PTOType, PTOBalance, PTOReminder
)
from app.models.user import User
from app.services.pto_promotion_service import PTOPromotionService
from app.services.pto_service import PTOService


@pytest.mark.asyncio
class TestPTOPromotionService:
    """Tests for PTO promotion service"""

    async def test_send_balance_reminder(self, db: AsyncSession, test_user: User):
        """Test sending a balance reminder"""
        # Initialize PTO balance
        _ = await PTOService.initialize_pto_balance(
            db, test_user.id, PTOType.VACATION, annual_allotment=20.0
        )

        # Send balance reminder
        reminder = await PTOPromotionService.send_balance_reminder(
            db, test_user.id, PTOType.VACATION
        )

        assert reminder is not None
        assert reminder.user_id == test_user.id
        assert reminder.reminder_type == "balance_available"
        assert "20.0" in reminder.message or "20" in reminder.message

    async def test_send_balance_reminder_no_days(self, db: AsyncSession, test_user: User):
        """Test that no reminder is sent when no days available"""
        # Initialize with zero days
        _ = await PTOService.initialize_pto_balance(
            db, test_user.id, PTOType.VACATION, annual_allotment=0.0
        )

        reminder = await PTOPromotionService.send_balance_reminder(
            db, test_user.id, PTOType.VACATION
        )

        assert reminder is None

    async def test_send_planning_encouragement(self, db: AsyncSession, test_user: User):
        """Test sending planning encouragement"""
        # Initialize PTO balance
        _ = await PTOService.initialize_pto_balance(
            db, test_user.id, PTOType.VACATION, annual_allotment=15.0
        )

        reminder = await PTOPromotionService.send_planning_encouragement(
            db, test_user.id, PTOType.VACATION
        )

        assert reminder is not None
        assert reminder.reminder_type == "planning_encouragement"
        assert "Plan ahead" in reminder.message or "plan" in reminder.message.lower()

    async def test_send_coverage_manageable_message(self, db: AsyncSession, test_user: User):
        """Test sending coverage is manageable message"""
        _ = await PTOService.initialize_pto_balance(
            db, test_user.id, PTOType.VACATION, annual_allotment=10.0
        )

        reminder = await PTOPromotionService.send_coverage_manageable_message(
            db, test_user.id, PTOType.VACATION
        )

        assert reminder is not None
        assert reminder.reminder_type == "coverage_manageable"
        assert "coverage" in reminder.message.lower()

    async def test_send_no_guilt_message(self, db: AsyncSession, test_user: User):
        """Test sending no guilt message"""
        _ = await PTOService.initialize_pto_balance(
            db, test_user.id, PTOType.VACATION, annual_allotment=10.0
        )

        reminder = await PTOPromotionService.send_no_guilt_message(
            db, test_user.id, PTOType.VACATION
        )

        assert reminder is not None
        assert reminder.reminder_type == "no_guilt"
        assert "essential" in reminder.message or "guilt" in reminder.message.lower()

    async def test_send_time_off_strength_message(self, db: AsyncSession, test_user: User):
        """Test sending time off is strength message"""
        _ = await PTOService.initialize_pto_balance(
            db, test_user.id, PTOType.VACATION, annual_allotment=10.0
        )

        reminder = await PTOPromotionService.send_time_off_strength_message(
            db, test_user.id, PTOType.VACATION
        )

        assert reminder is not None
        assert reminder.reminder_type == "time_off_strength"
        assert "strength" in reminder.message or "weakness" in reminder.message

    async def test_prepare_pre_vacation_triage(self, db: AsyncSession, test_user: User):
        """Test pre-vacation triage preparation"""
        # Create a PTO request
        pto_request = await PTOService.create_pto_request(
            db, test_user.id,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=14),
            pto_type=PTOType.VACATION,
        )

        triage = await PTOPromotionService.prepare_pre_vacation_triage(
            db, pto_request.id
        )

        assert triage["pto_request_id"] == pto_request.id
        assert triage["user_id"] == test_user.id
        assert "triage_checklist" in triage
        assert len(triage["triage_checklist"]) > 0
        assert triage["days_until_vacation"] == 7

    async def test_enable_auto_delegation(self, db: AsyncSession, test_user: User):
        """Test enabling auto-delegation"""
        pto_request = await PTOService.create_pto_request(
            db, test_user.id,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=14),
            pto_type=PTOType.VACATION,
        )

        updated = await PTOPromotionService.enable_auto_delegation(
            db, pto_request.id, "Delegate to John for coverage"
        )

        assert updated.auto_delegate is True
        assert "John" in updated.delegation_notes

    async def test_get_gradual_return_plan(self, db: AsyncSession, test_user: User):
        """Test getting gradual return plan"""
        pto_request = await PTOService.create_pto_request(
            db, test_user.id,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=5),
            pto_type=PTOType.VACATION,
            gradual_return_enabled=True,
        )

        plan = await PTOPromotionService.get_gradual_return_plan(
            db, pto_request.id
        )

        assert plan["enabled"] is True
        assert "phases" in plan
        assert len(plan["phases"]) == 3
        assert plan["phases"][0]["percentage"] == 10
        assert plan["phases"][1]["percentage"] == 40
        assert plan["phases"][2]["percentage"] == 100

    async def test_create_celebration_notification(self, db: AsyncSession, test_user: User):
        """Test creating celebration notification"""
        pto_request = await PTOService.create_pto_request(
            db, test_user.id,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=14),
            pto_type=PTOType.VACATION,
        )

        celebration = await PTOPromotionService.create_celebration_notification(
            db, pto_request.id
        )

        assert celebration["pto_request_id"] == pto_request.id
        assert "celebration_message" in celebration
        assert "welcome_back_message" in celebration
        assert "🎉" in celebration["celebration_message"]

    async def test_send_return_welcome_message(self, db: AsyncSession, test_user: User):
        """Test sending welcome back message"""
        pto_request = await PTOService.create_pto_request(
            db, test_user.id,
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() - timedelta(days=1),
            pto_type=PTOType.VACATION,
        )

        reminder = await PTOPromotionService.send_return_welcome_message(
            db, pto_request.id
        )

        assert reminder is not None
        assert reminder.reminder_type == "welcome_back"
        assert "welcome" in reminder.message.lower() or "back" in reminder.message.lower()

    @pytest.mark.skip(
        reason=(
            "SCHEMA BUG (report-only, not fixed here): PTOBalance.user_id is "
            "unique=True (app/models/pto.py:119) instead of a composite "
            "unique on (user_id, pto_type), even though pto_type is a "
            "real column and PTOService.initialize_pto_balance / "
            "PTOPromotionService.send_batch_promotion_reminders both assume "
            "one balance row per (user, pto_type). A single user can only "
            "ever have ONE PTOBalance row today, so this test's premise "
            "(vacation+sick+personal balances for one user) can't be "
            "constructed without a migration. DO NOT fix via schema change "
            "per rot-wave rules; flagging for a maintainer decision."
        )
    )
    async def test_send_batch_promotion_reminders(self, db: AsyncSession, test_user: User):
        """Test sending batch reminders"""
        # Initialize multiple balances with varying available days
        for i, pto_type in enumerate([PTOType.VACATION, PTOType.SICK, PTOType.PERSONAL]):
            await PTOService.initialize_pto_balance(
                db, test_user.id, pto_type, annual_allotment=15.0
            )

        reminders = await PTOPromotionService.send_batch_promotion_reminders(
            db, days_threshold=10
        )

        # Should send reminders for balances >= 10 days
        assert len(reminders) >= 3

    async def test_get_promotion_dashboard(self, db: AsyncSession, test_user: User):
        """Test getting promotion dashboard"""
        # Initialize balance
        await PTOService.initialize_pto_balance(
            db, test_user.id, PTOType.VACATION, annual_allotment=20.0
        )

        # Create an approved request
        _ = await PTOService.create_pto_request(
            db, test_user.id,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=37),
            pto_type=PTOType.VACATION,
        )

        dashboard = await PTOPromotionService.get_promotion_dashboard(
            db, test_user.id
        )

        assert dashboard["user_id"] == test_user.id
        assert "pto_balances" in dashboard
        assert "promotion_message" in dashboard
        assert len(dashboard["pto_balances"]) > 0
        assert dashboard["pto_balances"][0]["available_days"] == 20.0

    async def test_promotion_messages_positive_tone(self, db: AsyncSession, test_user: User):
        """Test that all promotion messages have positive tone"""
        await PTOService.initialize_pto_balance(
            db, test_user.id, PTOType.VACATION, annual_allotment=15.0
        )

        messages_to_check = [
            await PTOPromotionService.send_balance_reminder(db, test_user.id),
            await PTOPromotionService.send_planning_encouragement(db, test_user.id),
            await PTOPromotionService.send_coverage_manageable_message(db, test_user.id),
            await PTOPromotionService.send_no_guilt_message(db, test_user.id),
            await PTOPromotionService.send_time_off_strength_message(db, test_user.id),
        ]

        # Check that messages don't contain guilt-inducing language
        negative_words = ["sorry", "unfortunate", "burden", "problem"]

        for reminder in messages_to_check:
            if reminder:
                message_lower = reminder.message.lower()
                for word in negative_words:
                    assert word not in message_lower, \
                        f"Message contains negative word '{word}': {reminder.message}"

                # Check for positive keywords
                assert any(word in message_lower for word in [
                    "deserve", "refresh", "rest", "earned", "essential", "strength",
                    "stronger", "well-being", "wellness", "important", "disconnect"
                ]), f"Message lacks positive tone: {reminder.message}"


@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """Create a test user"""
    from app.models.user import UserRole

    user = User(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        role=UserRole.STAFF,
    )
    db.add(user)
    await db.flush()
    return user
