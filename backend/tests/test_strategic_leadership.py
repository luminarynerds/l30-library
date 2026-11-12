# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprehensive tests for Strategic Leadership - ALL 5 PHASES."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategic import (
    # Core
    StrategicPlan,
    # Phase 1
    StrategicInitiative, InitiativeMilestone, BoardDecisionLink,
    # Phase 2
    StrategicKPI, KPIValue, KPIDashboard, KPIAlert,
    # Phase 3
    StrategicBudget, BudgetItem, BudgetAllocation, BudgetTransaction,
    # Phase 4
    StrategicRisk, RiskAssessment, RiskMitigationStrategy, RiskReview,
    # Phase 5
    ExecutiveDashboard, DashboardWidget, ExecutiveReport, ReportSchedule,
)
from app.models.user import User, UserRole
from app.services.strategic_leadership_service import (
    # Phase 1
    create_initiative, get_initiatives_for_plan, link_board_decision,
    # Phase 2
    create_kpi, record_kpi_value, get_kpi_dashboard_data,
    # Phase 3
    create_budget, record_budget_transaction, get_budget_summary,
    # Phase 4
    create_risk, create_mitigation_strategy, conduct_risk_assessment, get_risk_register,
    # Phase 5
    create_executive_dashboard, add_dashboard_widget, generate_executive_report, get_executive_summary,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test admin user."""
    user = User(
        email="test_admin@l30.org",
        password_hash="hashed",
        first_name="Test",
        last_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_plan(db_session: AsyncSession, test_user: User):
    """Create a test strategic plan."""
    plan = StrategicPlan(
        title="Test Strategic Plan 2025-2028",
        description="Test plan for automated testing",
        period_start=datetime(2025, 1, 1),
        period_end=datetime(2028, 12, 31),
        mission="Test mission",
        vision="Test vision",
        status="active",
        created_by_id=test_user.id
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


# ============================================================================
# PHASE 1: Strategic Initiatives Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_initiative(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test creating a strategic initiative."""
    initiative_data = {
        "title": "Test Initiative",
        "description": "A test initiative",
        "business_case": "Testing business case",
        "status": "planning",
        "estimated_budget": Decimal("100000.00"),
        "priority": 1
    }

    initiative = await create_initiative(db_session, test_plan.id, initiative_data, test_user.id)

    assert initiative.id is not None
    assert initiative.title == "Test Initiative"
    assert initiative.plan_id == test_plan.id
    assert initiative.status == "planning"


@pytest.mark.asyncio
async def test_initiative_milestones(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test adding milestones to an initiative."""
    initiative = await create_initiative(
        db_session,
        test_plan.id,
        {"title": "Test Initiative", "status": "in_progress"},
        test_user.id
    )

    milestone = InitiativeMilestone(
        initiative_id=initiative.id,
        title="First Milestone",
        description="Complete phase 1",
        target_date=datetime.utcnow() + timedelta(days=30),
        completed=False
    )
    db_session.add(milestone)
    await db_session.commit()

    # Verify milestone created
    result = await db_session.execute(
        select(InitiativeMilestone).where(InitiativeMilestone.initiative_id == initiative.id)
    )
    milestones = result.scalars().all()
    assert len(milestones) == 1
    assert milestones[0].title == "First Milestone"


@pytest.mark.asyncio
async def test_board_decision_link(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test linking board decisions to initiatives."""
    initiative = await create_initiative(
        db_session,
        test_plan.id,
        {"title": "Test Initiative", "status": "planning"},
        test_user.id
    )

    decision_data = {
        "meeting_date": datetime(2025, 1, 15),
        "meeting_reference": "Board Meeting Jan 2025",
        "decision_type": "approval",
        "decision_summary": "Approved with full funding",
        "vote_result": "Unanimous"
    }

    link = await link_board_decision(db_session, initiative.id, decision_data)

    assert link.id is not None
    assert link.initiative_id == initiative.id
    assert link.decision_type == "approval"

    # Verify initiative was updated
    await db_session.refresh(initiative)
    assert initiative.board_approved is True


@pytest.mark.asyncio
async def test_get_initiatives_for_plan(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test retrieving initiatives for a plan."""
    # Create multiple initiatives
    await create_initiative(db_session, test_plan.id, {"title": "Init 1", "status": "in_progress"}, test_user.id)
    await create_initiative(db_session, test_plan.id, {"title": "Init 2", "status": "planning"}, test_user.id)
    await create_initiative(db_session, test_plan.id, {"title": "Init 3", "status": "in_progress"}, test_user.id)

    # Get all initiatives
    all_initiatives = await get_initiatives_for_plan(db_session, test_plan.id)
    assert len(all_initiatives) == 3

    # Get filtered by status
    in_progress = await get_initiatives_for_plan(db_session, test_plan.id, status="in_progress")
    assert len(in_progress) == 2


# ============================================================================
# PHASE 2: KPI Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_kpi(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test creating a KPI."""
    kpi_data = {
        "name": "Test KPI",
        "description": "A test KPI",
        "category": "Operational",
        "unit_of_measure": "%",
        "target_value": Decimal("90.0"),
        "baseline_value": Decimal("75.0"),
        "current_value": Decimal("80.0"),
        "frequency": "monthly"
    }

    kpi = await create_kpi(db_session, test_plan.id, kpi_data, test_user.id)

    assert kpi.id is not None
    assert kpi.name == "Test KPI"
    assert kpi.target_value == Decimal("90.0")


@pytest.mark.asyncio
async def test_record_kpi_value(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test recording KPI values."""
    kpi = await create_kpi(
        db_session,
        test_plan.id,
        {
            "name": "Test KPI",
            "unit_of_measure": "%",
            "target_value": Decimal("100.0"),
            "baseline_value": Decimal("50.0")
        },
        test_user.id
    )

    # Record a value
    value = await record_kpi_value(
        db_session,
        kpi.id,
        Decimal("75.0"),
        test_user.id,
        notes="Monthly update"
    )

    assert value.id is not None
    assert value.value == Decimal("75.0")
    assert value.notes == "Monthly update"

    # Verify KPI was updated
    await db_session.refresh(kpi)
    assert kpi.current_value == Decimal("75.0")
    assert kpi.trend_direction in ["up", "down", "stable"]


@pytest.mark.asyncio
async def test_kpi_threshold_alerts(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test that KPI threshold violations create alerts."""
    kpi = await create_kpi(
        db_session,
        test_plan.id,
        {
            "name": "Test KPI",
            "unit_of_measure": "%",
            "target_value": Decimal("90.0"),
            "threshold_yellow": Decimal("70.0"),
            "threshold_red": Decimal("50.0"),
            "baseline_value": Decimal("80.0")
        },
        test_user.id
    )

    # Record value below yellow threshold
    await record_kpi_value(db_session, kpi.id, Decimal("65.0"), test_user.id)

    # Check for alert
    result = await db_session.execute(
        select(KPIAlert).where(KPIAlert.kpi_id == kpi.id)
    )
    alerts = result.scalars().all()
    assert len(alerts) >= 1
    assert alerts[0].severity in ["warning", "critical"]


@pytest.mark.asyncio
async def test_kpi_dashboard(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test KPI dashboard creation and data retrieval."""
    # Create KPIs
    kpi1 = await create_kpi(db_session, test_plan.id, {"name": "KPI 1", "unit_of_measure": "%"}, test_user.id)
    kpi2 = await create_kpi(db_session, test_plan.id, {"name": "KPI 2", "unit_of_measure": "count"}, test_user.id)

    # Create dashboard
    dashboard = KPIDashboard(
        name="Test Dashboard",
        audience="Board",
        kpi_ids=[kpi1.id, kpi2.id],
        created_by_id=test_user.id
    )
    db_session.add(dashboard)
    await db_session.commit()
    await db_session.refresh(dashboard)

    # Get dashboard data
    data = await get_kpi_dashboard_data(db_session, dashboard.id)

    assert data["name"] == "Test Dashboard"
    assert len(data["kpis"]) == 2


# ============================================================================
# PHASE 3: Budget Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_budget(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test creating a strategic budget."""
    budget_data = {
        "name": "Test Budget FY2025",
        "fiscal_year": 2025,
        "total_budget": Decimal("500000.00")
    }

    budget = await create_budget(db_session, test_plan.id, budget_data, test_user.id)

    assert budget.id is not None
    assert budget.name == "Test Budget FY2025"
    assert budget.total_budget == Decimal("500000.00")
    assert budget.available_amount == Decimal("500000.00")


@pytest.mark.asyncio
async def test_budget_transactions(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test recording budget transactions."""
    budget = await create_budget(
        db_session,
        test_plan.id,
        {"name": "Test Budget", "fiscal_year": 2025, "total_budget": Decimal("100000.00")},
        test_user.id
    )

    # Record expense transaction
    transaction_data = {
        "transaction_type": "expense",
        "description": "Test expense",
        "amount": Decimal("5000.00"),
        "transaction_date": datetime.utcnow(),
        "category": "Technology"
    }

    transaction = await record_budget_transaction(db_session, budget.id, transaction_data, test_user.id)

    assert transaction.id is not None
    assert transaction.amount == Decimal("5000.00")

    # Verify budget was updated
    await db_session.refresh(budget)
    assert budget.spent_amount == Decimal("5000.00")
    assert budget.available_amount == Decimal("95000.00")


@pytest.mark.asyncio
async def test_budget_summary(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test budget summary generation."""
    budget = await create_budget(
        db_session,
        test_plan.id,
        {"name": "Test Budget", "fiscal_year": 2025, "total_budget": Decimal("100000.00")},
        test_user.id
    )

    # Add budget items
    item1 = BudgetItem(
        budget_id=budget.id,
        category="Technology",
        budgeted_amount=Decimal("50000.00"),
        spent_amount=Decimal("10000.00")
    )
    item2 = BudgetItem(
        budget_id=budget.id,
        category="Personnel",
        budgeted_amount=Decimal("30000.00"),
        spent_amount=Decimal("5000.00")
    )
    db_session.add_all([item1, item2])
    await db_session.commit()

    # Get summary
    summary = await get_budget_summary(db_session, budget.id)

    assert summary["total_budget"] == 100000.0
    assert "Technology" in summary["category_breakdown"]
    assert "Personnel" in summary["category_breakdown"]


# ============================================================================
# PHASE 4: Risk Management Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_risk(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test creating a strategic risk."""
    risk_data = {
        "title": "Test Risk",
        "description": "A test risk",
        "category": "Financial",
        "likelihood": "high",
        "impact": "medium"
    }

    risk = await create_risk(db_session, test_plan.id, risk_data, test_user.id)

    assert risk.id is not None
    assert risk.title == "Test Risk"
    assert risk.risk_level in ["low", "medium", "high", "critical"]
    assert risk.risk_score > 0


@pytest.mark.asyncio
async def test_risk_mitigation_strategy(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test creating mitigation strategies for risks."""
    risk = await create_risk(
        db_session,
        test_plan.id,
        {"title": "Test Risk", "likelihood": "high", "impact": "high"},
        test_user.id
    )

    strategy_data = {
        "title": "Test Mitigation",
        "description": "Mitigation strategy",
        "strategy_type": "reduce",
        "responsible_person_id": test_user.id
    }

    strategy = await create_mitigation_strategy(db_session, risk.id, strategy_data)

    assert strategy.id is not None
    assert strategy.title == "Test Mitigation"

    # Verify risk status updated
    await db_session.refresh(risk)
    assert risk.status == "mitigating"


@pytest.mark.asyncio
async def test_risk_assessment(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test conducting risk assessments."""
    risk = await create_risk(
        db_session,
        test_plan.id,
        {"title": "Test Risk", "likelihood": "medium", "impact": "medium"},
        test_user.id
    )

    assessment_data = {
        "likelihood": "low",
        "impact": "medium",
        "assessment_notes": "Risk has decreased"
    }

    assessment = await conduct_risk_assessment(db_session, risk.id, assessment_data, test_user.id)

    assert assessment.id is not None
    assert assessment.likelihood == "low"

    # Verify risk was updated
    await db_session.refresh(risk)
    assert risk.likelihood == "low"


@pytest.mark.asyncio
async def test_risk_register(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test risk register generation."""
    # Create risks at different levels
    await create_risk(db_session, test_plan.id, {"title": "Risk 1", "likelihood": "high", "impact": "high"}, test_user.id)
    await create_risk(db_session, test_plan.id, {"title": "Risk 2", "likelihood": "low", "impact": "medium"}, test_user.id)
    await create_risk(db_session, test_plan.id, {"title": "Risk 3", "likelihood": "medium", "impact": "low"}, test_user.id)

    register = await get_risk_register(db_session, test_plan.id)

    assert register["total_risks"] == 3
    assert "by_level" in register
    assert "status_breakdown" in register


# ============================================================================
# PHASE 5: Executive Dashboard & Reporting Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_executive_dashboard(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test creating an executive dashboard."""
    dashboard_data = {
        "name": "Test Executive Dashboard",
        "description": "Dashboard for testing",
        "dashboard_type": "overview",
        "audience": "Board"
    }

    dashboard = await create_executive_dashboard(db_session, test_plan.id, dashboard_data, test_user.id)

    assert dashboard.id is not None
    assert dashboard.name == "Test Executive Dashboard"
    assert dashboard.plan_id == test_plan.id


@pytest.mark.asyncio
async def test_dashboard_widgets(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test adding widgets to dashboards."""
    dashboard = await create_executive_dashboard(
        db_session,
        test_plan.id,
        {"name": "Test Dashboard", "dashboard_type": "overview"},
        test_user.id
    )

    widget_data = {
        "title": "Test Widget",
        "widget_type": "chart",
        "data_source_type": "kpi",
        "config": {"chart_type": "bar"}
    }

    widget = await add_dashboard_widget(db_session, dashboard.id, widget_data)

    assert widget.id is not None
    assert widget.title == "Test Widget"
    assert widget.dashboard_id == dashboard.id


@pytest.mark.asyncio
async def test_generate_executive_report(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test generating executive reports."""
    period_start = datetime(2025, 1, 1)
    period_end = datetime(2025, 3, 31)

    report = await generate_executive_report(
        db_session,
        test_plan.id,
        period_start,
        period_end,
        test_user.id,
        report_type="quarterly"
    )

    assert report.id is not None
    assert report.report_type == "quarterly"
    assert "kpi_snapshot" in report.__dict__
    assert "initiative_snapshot" in report.__dict__


@pytest.mark.asyncio
async def test_executive_summary(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test getting executive summary."""
    # Create some data
    await create_initiative(db_session, test_plan.id, {"title": "Init 1", "status": "in_progress"}, test_user.id)
    await create_kpi(db_session, test_plan.id, {"name": "KPI 1", "unit_of_measure": "%"}, test_user.id)
    await create_budget(db_session, test_plan.id, {"name": "Budget", "fiscal_year": 2025, "total_budget": Decimal("100000")}, test_user.id)
    await create_risk(db_session, test_plan.id, {"title": "Risk 1", "likelihood": "medium", "impact": "medium"}, test_user.id)

    summary = await get_executive_summary(db_session, test_plan.id)

    assert summary["plan_id"] == test_plan.id
    assert "health_score" in summary
    assert "initiatives" in summary
    assert "kpis" in summary
    assert "budgets" in summary
    assert "risks" in summary
    assert 0 <= summary["health_score"] <= 100


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_full_strategic_workflow(db_session: AsyncSession, test_plan: StrategicPlan, test_user: User):
    """Test complete strategic planning workflow across all 5 phases."""

    # PHASE 1: Create initiative
    initiative = await create_initiative(
        db_session,
        test_plan.id,
        {
            "title": "Digital Transformation",
            "status": "in_progress",
            "estimated_budget": Decimal("250000.00")
        },
        test_user.id
    )

    # PHASE 2: Create KPI to track initiative
    kpi = await create_kpi(
        db_session,
        test_plan.id,
        {
            "name": "Digital Adoption Rate",
            "unit_of_measure": "%",
            "target_value": Decimal("80.0"),
            "baseline_value": Decimal("50.0")
        },
        test_user.id
    )

    # PHASE 3: Create budget for initiative
    budget = await create_budget(
        db_session,
        test_plan.id,
        {
            "name": "Digital Transformation Budget",
            "fiscal_year": 2025,
            "total_budget": Decimal("250000.00")
        },
        test_user.id
    )

    # PHASE 4: Identify risks
    risk = await create_risk(
        db_session,
        test_plan.id,
        {
            "title": "Technology Adoption Risk",
            "likelihood": "medium",
            "impact": "high"
        },
        test_user.id
    )

    # PHASE 5: Create executive dashboard
    dashboard = await create_executive_dashboard(
        db_session,
        test_plan.id,
        {
            "name": "Strategic Overview",
            "dashboard_type": "overview"
        },
        test_user.id
    )

    # Verify all components created
    assert initiative.id is not None
    assert kpi.id is not None
    assert budget.id is not None
    assert risk.id is not None
    assert dashboard.id is not None

    # Get executive summary to verify integration
    summary = await get_executive_summary(db_session, test_plan.id)

    assert summary["initiatives"]["total"] >= 1
    assert summary["kpis"]["total"] >= 1
    assert summary["budgets"]["total"] >= 1
    assert summary["risks"]["total"] >= 1
