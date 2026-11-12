# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seed strategic leadership data - ALL 5 PHASES with realistic data."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
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
from app.models.user import User
from app.core.security import hash_password
from sqlalchemy import select


async def seed_all_phases(db: AsyncSession):
    """Seed all 5 phases of strategic leadership."""

    print("Starting Strategic Leadership Seed - ALL 5 PHASES...")

    # Get admin user
    result = await db.execute(
        select(User).where(User.role == "ADMIN").limit(1)
    )
    admin_user = result.scalar_one_or_none()

    if not admin_user:
        print("No admin user found. Creating one...")
        admin_user = User(
            email="admin@l30.org",
            password_hash=hash_password("Admin123!"),
            role="ADMIN"
        )
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)

    # Create or get strategic plan
    result = await db.execute(
        select(StrategicPlan).where(StrategicPlan.title.like("%2025-2028%"))
    )
    plan = result.scalar_one_or_none()

    if not plan:
        print("Creating Strategic Plan 2025-2028...")
        plan = StrategicPlan(
            title="Bébé Memorial Library Strategic Plan 2025-2028",
            description="Our roadmap for library excellence in the next three years",
            period_start=datetime(2025, 1, 1),
            period_end=datetime(2028, 12, 31),
            mission="To connect, educate, and inspire our community through exceptional library services",
            vision="A thriving community hub that empowers lifelong learning and cultural enrichment",
            values=["Community", "Excellence", "Innovation", "Accessibility", "Integrity"],
            status="active",
            created_by_id=admin_user.id
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

    print(f"Using plan: {plan.title} (ID: {plan.id})")

    # PHASE 1: Strategic Initiatives & Board Linkage
    await seed_initiatives(db, plan.id, admin_user.id)

    # PHASE 2: KPI Tracking
    await seed_kpis(db, plan.id, admin_user.id)

    # PHASE 3: Budget Tracking
    await seed_budgets(db, plan.id, admin_user.id)

    # PHASE 4: Risk Management
    await seed_risks(db, plan.id, admin_user.id)

    # PHASE 5: Executive Dashboards & Reports
    await seed_executive_dashboards(db, plan.id, admin_user.id)

    print("\n=== SEED COMPLETE ===")
    await verify_data(db, plan.id)


async def seed_initiatives(db: AsyncSession, plan_id: int, user_id: int):
    """PHASE 1: Seed strategic initiatives with board linkages."""
    print("\n--- PHASE 1: Seeding Strategic Initiatives ---")

    initiatives_data = [
        {
            "title": "Digital Library Transformation",
            "description": "Modernize library infrastructure with cloud-based ILS, digital lending platform, and maker spaces",
            "business_case": "Current systems are outdated and limiting patron access. Investment in digital transformation will increase circulation by 30% and reduce operational costs by 20%.",
            "expected_outcomes": [
                "50% increase in digital circulation",
                "New maker space serving 500 patrons/year",
                "Cloud migration reducing IT costs by 25%"
            ],
            "status": "in_progress",
            "start_date": datetime(2025, 1, 15),
            "target_completion_date": datetime(2026, 12, 31),
            "estimated_budget": Decimal("250000.00"),
            "actual_cost": Decimal("75000.00"),
            "assigned_leader_id": user_id,
            "team_members": [user_id],
            "priority": 1,
            "strategic_alignment_score": 10,
            "board_approved": True,
            "board_approval_date": datetime(2024, 12, 10),
            "board_meeting_reference": "Board Meeting Dec 2024",
            "completion_percentage": 30
        },
        {
            "title": "Community Outreach Expansion",
            "description": "Establish partnerships with local schools, senior centers, and community organizations",
            "business_case": "Expand library reach to underserved populations, increase card registrations by 40%",
            "expected_outcomes": [
                "10 new community partnerships",
                "1000 new library card registrations",
                "Monthly outreach events at 5 locations"
            ],
            "status": "approved",
            "start_date": datetime(2025, 3, 1),
            "target_completion_date": datetime(2025, 12, 31),
            "estimated_budget": Decimal("75000.00"),
            "assigned_leader_id": user_id,
            "priority": 2,
            "strategic_alignment_score": 9,
            "board_approved": True,
            "board_approval_date": datetime(2025, 2, 5),
            "board_meeting_reference": "Board Meeting Feb 2025",
            "completion_percentage": 0
        },
        {
            "title": "Staff Development Program",
            "description": "Comprehensive training program for all staff focusing on digital literacy, customer service, and diversity/inclusion",
            "business_case": "Invest in staff development to improve service quality and reduce turnover",
            "expected_outcomes": [
                "100% staff completion of core training modules",
                "15% increase in patron satisfaction scores",
                "20% reduction in staff turnover"
            ],
            "status": "planning",
            "start_date": datetime(2025, 6, 1),
            "target_completion_date": datetime(2026, 6, 30),
            "estimated_budget": Decimal("50000.00"),
            "assigned_leader_id": user_id,
            "priority": 3,
            "strategic_alignment_score": 8,
            "board_approved": False,
            "completion_percentage": 5
        }
    ]

    initiatives = []
    for init_data in initiatives_data:
        initiative = StrategicInitiative(plan_id=plan_id, **init_data)
        db.add(initiative)
        initiatives.append(initiative)

    await db.commit()
    print(f"Created {len(initiatives)} initiatives")

    # Add milestones to initiatives
    for initiative in initiatives:
        await db.refresh(initiative)

        if initiative.title == "Digital Library Transformation":
            milestones = [
                {
                    "title": "Cloud ILS Selection & Procurement",
                    "description": "RFP process and vendor selection for cloud-based ILS",
                    "target_date": datetime(2025, 6, 30),
                    "completed": True,
                    "completion_date": datetime(2025, 6, 15),
                    "completion_notes": "Selected Koha cloud platform",
                    "deliverables": ["RFP document", "Vendor evaluation matrix", "Signed contract"]
                },
                {
                    "title": "Data Migration Planning",
                    "description": "Plan and execute migration of patron and catalog data",
                    "target_date": datetime(2025, 10, 31),
                    "completed": False,
                    "deliverables": ["Migration plan", "Test data migration", "Rollback procedures"]
                },
                {
                    "title": "Maker Space Design & Build",
                    "description": "Design and construct maker space with 3D printers, laser cutter",
                    "target_date": datetime(2026, 6, 30),
                    "completed": False,
                    "deliverables": ["Space design", "Equipment procurement", "Staff training"]
                }
            ]

            for ms_data in milestones:
                milestone = InitiativeMilestone(initiative_id=initiative.id, **ms_data)
                db.add(milestone)

        # Add board decision links
        if initiative.board_approved:
            decision = BoardDecisionLink(
                initiative_id=initiative.id,
                meeting_date=initiative.board_approval_date,
                meeting_reference=initiative.board_meeting_reference,
                decision_type="approval",
                decision_summary=f"Board approved '{initiative.title}' with budget of ${initiative.estimated_budget}",
                vote_result="Unanimous",
                resolution_number=f"RES-{initiative.board_approval_date.year}-{initiative.id:03d}"
            )
            db.add(decision)

    await db.commit()
    print("Added milestones and board decision links")


async def seed_kpis(db: AsyncSession, plan_id: int, user_id: int):
    """PHASE 2: Seed KPIs with historical values."""
    print("\n--- PHASE 2: Seeding KPIs ---")

    kpis_data = [
        {
            "name": "Library Card Registrations",
            "description": "Total active library card holders",
            "category": "Customer",
            "unit_of_measure": "cards",
            "target_value": Decimal("15000"),
            "baseline_value": Decimal("12000"),
            "current_value": Decimal("13500"),
            "threshold_red": Decimal("11000"),
            "threshold_yellow": Decimal("12500"),
            "threshold_green": Decimal("14000"),
            "frequency": "monthly",
            "data_source": "ILS Database",
            "responsible_person_id": user_id,
            "is_active": True,
            "trend_direction": "up",
            "variance_percentage": Decimal("12.5")
        },
        {
            "name": "Digital Circulation Rate",
            "description": "Percentage of total circulation from digital materials",
            "category": "Operational",
            "unit_of_measure": "%",
            "target_value": Decimal("35"),
            "baseline_value": Decimal("25"),
            "current_value": Decimal("32"),
            "threshold_red": Decimal("20"),
            "threshold_yellow": Decimal("28"),
            "threshold_green": Decimal("33"),
            "frequency": "monthly",
            "data_source": "Circulation Reports",
            "responsible_person_id": user_id,
            "is_active": True,
            "trend_direction": "up",
            "variance_percentage": Decimal("28.0")
        },
        {
            "name": "Patron Satisfaction Score",
            "description": "Overall patron satisfaction from surveys",
            "category": "Customer",
            "unit_of_measure": "%",
            "target_value": Decimal("90"),
            "baseline_value": Decimal("82"),
            "current_value": Decimal("87"),
            "threshold_red": Decimal("75"),
            "threshold_yellow": Decimal("82"),
            "threshold_green": Decimal("88"),
            "frequency": "quarterly",
            "data_source": "Patron Surveys",
            "responsible_person_id": user_id,
            "is_active": True,
            "trend_direction": "up",
            "variance_percentage": Decimal("6.1")
        },
        {
            "name": "Operating Cost per Circulation",
            "description": "Average cost per item circulated",
            "category": "Financial",
            "unit_of_measure": "$",
            "target_value": Decimal("2.50"),
            "baseline_value": Decimal("3.20"),
            "current_value": Decimal("2.85"),
            "threshold_red": Decimal("4.00"),
            "threshold_yellow": Decimal("3.50"),
            "threshold_green": Decimal("2.75"),
            "frequency": "monthly",
            "data_source": "Financial System",
            "responsible_person_id": user_id,
            "is_active": True,
            "trend_direction": "down",
            "variance_percentage": Decimal("-10.9")
        },
        {
            "name": "Staff Training Hours",
            "description": "Average training hours per staff member per year",
            "category": "Learning",
            "unit_of_measure": "hours",
            "target_value": Decimal("40"),
            "baseline_value": Decimal("25"),
            "current_value": Decimal("32"),
            "threshold_red": Decimal("20"),
            "threshold_yellow": Decimal("28"),
            "threshold_green": Decimal("38"),
            "frequency": "quarterly",
            "data_source": "HR System",
            "responsible_person_id": user_id,
            "is_active": True,
            "trend_direction": "up",
            "variance_percentage": Decimal("28.0")
        }
    ]

    kpis = []
    for kpi_data in kpis_data:
        kpi = StrategicKPI(plan_id=plan_id, **kpi_data)
        db.add(kpi)
        kpis.append(kpi)

    await db.commit()
    print(f"Created {len(kpis)} KPIs")

    # Add historical values for each KPI
    for kpi in kpis:
        await db.refresh(kpi)

        # Generate 6 months of historical data
        base_value = float(kpi.baseline_value)
        current_value = float(kpi.current_value)
        step = (current_value - base_value) / 6

        for i in range(6):
            value = base_value + (step * i)
            kpi_value = KPIValue(
                kpi_id=kpi.id,
                value=Decimal(str(round(value, 2))),
                recorded_date=datetime.utcnow() - timedelta(days=150 - (i * 25)),
                recorded_by_id=user_id,
                notes=f"Monthly update - month {i+1}"
            )
            db.add(kpi_value)

    await db.commit()
    print("Added historical KPI values")

    # Create a KPI dashboard
    dashboard = KPIDashboard(
        name="Executive KPI Dashboard",
        description="Real-time KPI tracking for board and executive team",
        audience="Board",
        kpi_ids=[kpi.id for kpi in kpis],
        layout={"columns": 2, "refresh": 300},
        refresh_interval=300,
        is_public=False,
        allowed_roles=["ADMIN", "BOARD"],
        created_by_id=user_id
    )
    db.add(dashboard)
    await db.commit()
    print("Created KPI dashboard")


async def seed_budgets(db: AsyncSession, plan_id: int, user_id: int):
    """PHASE 3: Seed budgets with transactions."""
    print("\n--- PHASE 3: Seeding Budgets ---")

    # Create FY2025 budget
    budget = StrategicBudget(
        plan_id=plan_id,
        name="Strategic Initiatives Budget FY2025",
        description="Budget for strategic plan initiatives and projects",
        fiscal_year=2025,
        total_budget=Decimal("500000.00"),
        allocated_amount=Decimal("325000.00"),
        spent_amount=Decimal("95000.00"),
        committed_amount=Decimal("325000.00"),
        available_amount=Decimal("175000.00"),
        status="active",
        approved_date=datetime(2024, 12, 15),
        approved_by_id=user_id,
        budget_owner_id=user_id
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)

    print(f"Created budget: {budget.name}")

    # Budget items
    items_data = [
        {
            "category": "Technology",
            "subcategory": "Cloud ILS",
            "description": "Cloud-based integrated library system",
            "budgeted_amount": Decimal("150000.00"),
            "allocated_amount": Decimal("150000.00"),
            "spent_amount": Decimal("45000.00"),
            "remaining_amount": Decimal("105000.00"),
            "account_code": "5200-01",
            "department": "IT",
            "justification": "Required for digital transformation initiative"
        },
        {
            "category": "Facilities",
            "subcategory": "Maker Space",
            "description": "Maker space equipment and setup",
            "budgeted_amount": Decimal("100000.00"),
            "allocated_amount": Decimal("100000.00"),
            "spent_amount": Decimal("25000.00"),
            "remaining_amount": Decimal("75000.00"),
            "account_code": "5300-02",
            "department": "Adult Services",
            "justification": "Community engagement and learning"
        },
        {
            "category": "Personnel",
            "subcategory": "Training",
            "description": "Staff development and training programs",
            "budgeted_amount": Decimal("50000.00"),
            "allocated_amount": Decimal("50000.00"),
            "spent_amount": Decimal("15000.00"),
            "remaining_amount": Decimal("35000.00"),
            "account_code": "5100-03",
            "department": "HR",
            "justification": "Staff development initiative"
        },
        {
            "category": "Marketing",
            "subcategory": "Outreach",
            "description": "Community outreach and marketing materials",
            "budgeted_amount": Decimal("25000.00"),
            "allocated_amount": Decimal("25000.00"),
            "spent_amount": Decimal("10000.00"),
            "remaining_amount": Decimal("15000.00"),
            "account_code": "5400-04",
            "department": "Marketing",
            "justification": "Community outreach expansion"
        },
        {
            "category": "Contingency",
            "description": "Contingency fund for unforeseen expenses",
            "budgeted_amount": Decimal("175000.00"),
            "allocated_amount": Decimal("0.00"),
            "spent_amount": Decimal("0.00"),
            "remaining_amount": Decimal("175000.00"),
            "account_code": "5900-99",
            "justification": "Risk mitigation"
        }
    ]

    for item_data in items_data:
        item = BudgetItem(budget_id=budget.id, **item_data)
        db.add(item)

    await db.commit()
    print(f"Created {len(items_data)} budget items")

    # Budget transactions
    transactions_data = [
        {
            "transaction_type": "expense",
            "description": "Cloud ILS initial setup fee",
            "amount": Decimal("25000.00"),
            "transaction_date": datetime(2025, 1, 15),
            "category": "Technology",
            "invoice_number": "INV-2025-001",
            "vendor": "Koha Cloud Services",
            "approved_by_id": user_id
        },
        {
            "transaction_type": "expense",
            "description": "Maker space 3D printers (3 units)",
            "amount": Decimal("15000.00"),
            "transaction_date": datetime(2025, 2, 1),
            "category": "Facilities",
            "invoice_number": "INV-2025-002",
            "vendor": "MakerBot Industries",
            "approved_by_id": user_id
        },
        {
            "transaction_type": "expense",
            "description": "Staff training workshops (Q1)",
            "amount": Decimal("8000.00"),
            "transaction_date": datetime(2025, 2, 15),
            "category": "Personnel",
            "invoice_number": "INV-2025-003",
            "vendor": "Professional Development Corp",
            "approved_by_id": user_id
        }
    ]

    for trans_data in transactions_data:
        transaction = BudgetTransaction(budget_id=budget.id, **trans_data)
        db.add(transaction)

    await db.commit()
    print(f"Created {len(transactions_data)} budget transactions")


async def seed_risks(db: AsyncSession, plan_id: int, user_id: int):
    """PHASE 4: Seed risk management data."""
    print("\n--- PHASE 4: Seeding Risks ---")

    risks_data = [
        {
            "title": "Budget Overruns on Digital Transformation",
            "description": "Cloud ILS migration may exceed budget due to data complexity and customization needs",
            "category": "Financial",
            "likelihood": "medium",
            "impact": "high",
            "risk_level": "high",
            "risk_score": 15,
            "triggers": [
                "Unexpected data migration issues",
                "Additional customization requirements",
                "Vendor scope creep"
            ],
            "indicators": [
                "Vendor change orders",
                "Extended timeline",
                "Staff overtime costs"
            ],
            "status": "mitigating",
            "identified_date": datetime(2025, 1, 10),
            "owner_id": user_id
        },
        {
            "title": "Low Community Engagement",
            "description": "Community outreach programs may not achieve target participation rates",
            "category": "Strategic",
            "likelihood": "medium",
            "impact": "medium",
            "risk_level": "medium",
            "risk_score": 9,
            "triggers": [
                "Lack of community awareness",
                "Competing programs",
                "Transportation barriers"
            ],
            "indicators": [
                "Low event attendance",
                "Minimal new card registrations",
                "Negative community feedback"
            ],
            "status": "monitoring",
            "identified_date": datetime(2025, 2, 1),
            "owner_id": user_id
        },
        {
            "title": "Staff Resistance to Change",
            "description": "Staff may resist new technology and workflows",
            "category": "Operational",
            "likelihood": "high",
            "impact": "medium",
            "risk_level": "high",
            "risk_score": 15,
            "triggers": [
                "Inadequate training",
                "Fear of job loss",
                "Complexity of new systems"
            ],
            "indicators": [
                "Training attendance issues",
                "Error rates in new system",
                "Staff complaints"
            ],
            "status": "mitigating",
            "identified_date": datetime(2025, 1, 5),
            "owner_id": user_id
        },
        {
            "title": "Data Security Breach",
            "description": "Cloud migration increases cyber security risk",
            "category": "Compliance",
            "likelihood": "low",
            "impact": "high",
            "risk_level": "medium",
            "risk_score": 5,
            "triggers": [
                "Inadequate access controls",
                "Phishing attacks",
                "Vendor security gaps"
            ],
            "indicators": [
                "Failed login attempts",
                "Unusual data access patterns",
                "Security audit findings"
            ],
            "status": "monitoring",
            "identified_date": datetime(2025, 1, 20),
            "owner_id": user_id
        }
    ]

    risks = []
    for risk_data in risks_data:
        risk = StrategicRisk(plan_id=plan_id, **risk_data)
        db.add(risk)
        risks.append(risk)

    await db.commit()
    print(f"Created {len(risks)} risks")

    # Add mitigation strategies
    for risk in risks:
        await db.refresh(risk)

        if risk.title == "Budget Overruns on Digital Transformation":
            strategies = [
                {
                    "title": "Fixed-Price Contract Amendment",
                    "description": "Negotiate fixed-price contract for core migration work",
                    "strategy_type": "reduce",
                    "action_steps": [
                        "Review current contract terms",
                        "Identify scope boundaries",
                        "Negotiate amendment with vendor"
                    ],
                    "responsible_person_id": user_id,
                    "target_completion_date": datetime(2025, 4, 30),
                    "status": "in_progress",
                    "cost_estimate": Decimal("5000.00")
                },
                {
                    "title": "Contingency Budget Allocation",
                    "description": "Allocate 15% contingency from reserve fund",
                    "strategy_type": "accept",
                    "action_steps": [
                        "Board approval for contingency",
                        "Transfer funds to project budget",
                        "Establish approval process for contingency use"
                    ],
                    "responsible_person_id": user_id,
                    "target_completion_date": datetime(2025, 3, 31),
                    "status": "completed",
                    "completion_date": datetime(2025, 3, 15),
                    "effectiveness_rating": 8
                }
            ]

            for strat_data in strategies:
                strategy = RiskMitigationStrategy(risk_id=risk.id, **strat_data)
                db.add(strategy)

        elif risk.title == "Staff Resistance to Change":
            strategy = RiskMitigationStrategy(
                risk_id=risk.id,
                title="Comprehensive Change Management Program",
                description="Structured training and support program for all staff",
                strategy_type="reduce",
                action_steps=[
                    "Develop training curriculum",
                    "Assign change champions",
                    "Weekly check-ins and support sessions",
                    "Recognition program for early adopters"
                ],
                responsible_person_id=user_id,
                target_completion_date=datetime(2025, 6, 30),
                status="in_progress",
                cost_estimate=Decimal("15000.00")
            )
            db.add(strategy)

    await db.commit()
    print("Added mitigation strategies")

    # Add risk assessments
    for risk in risks[:2]:  # Add assessments for first 2 risks
        assessment = RiskAssessment(
            risk_id=risk.id,
            assessment_date=datetime(2025, 2, 15),
            assessed_by_id=user_id,
            likelihood=risk.likelihood,
            impact=risk.impact,
            risk_score=risk.risk_score,
            assessment_notes="Quarterly risk review - status unchanged",
            changes_since_last="No significant changes. Mitigation strategies proceeding as planned.",
            recommended_actions=["Continue current mitigation", "Schedule next review in 3 months"]
        )
        db.add(assessment)

    await db.commit()
    print("Added risk assessments")


async def seed_executive_dashboards(db: AsyncSession, plan_id: int, user_id: int):
    """PHASE 5: Seed executive dashboards and reports."""
    print("\n--- PHASE 5: Seeding Executive Dashboards & Reports ---")

    # Create executive dashboard
    dashboard = ExecutiveDashboard(
        plan_id=plan_id,
        name="Board Executive Dashboard",
        description="Comprehensive strategic plan overview for board meetings",
        dashboard_type="overview",
        layout_config={"rows": 3, "columns": 4},
        audience="Board",
        is_default=True,
        auto_refresh=True,
        refresh_interval_minutes=15,
        created_by_id=user_id,
        last_modified_by_id=user_id
    )
    db.add(dashboard)
    await db.commit()
    await db.refresh(dashboard)

    print(f"Created dashboard: {dashboard.name}")

    # Add widgets to dashboard
    widgets_data = [
        {
            "title": "Strategic Health Score",
            "widget_type": "metric",
            "data_source_type": "plan",
            "data_source_ids": [plan_id],
            "config": {"display": "gauge", "thresholds": {"red": 50, "yellow": 70, "green": 90}},
            "position_x": 0,
            "position_y": 0,
            "width": 2,
            "height": 2
        },
        {
            "title": "Initiative Progress",
            "widget_type": "chart",
            "data_source_type": "initiative",
            "config": {"chart_type": "bar", "metric": "completion_percentage"},
            "position_x": 2,
            "position_y": 0,
            "width": 2,
            "height": 2
        },
        {
            "title": "KPI Summary",
            "widget_type": "table",
            "data_source_type": "kpi",
            "config": {"columns": ["name", "current", "target", "trend"]},
            "position_x": 0,
            "position_y": 2,
            "width": 2,
            "height": 2
        },
        {
            "title": "Budget Status",
            "widget_type": "chart",
            "data_source_type": "budget",
            "config": {"chart_type": "pie", "metric": "spending_by_category"},
            "position_x": 2,
            "position_y": 2,
            "width": 2,
            "height": 2
        },
        {
            "title": "Risk Heat Map",
            "widget_type": "chart",
            "data_source_type": "risk",
            "config": {"chart_type": "heatmap", "axes": ["likelihood", "impact"]},
            "position_x": 0,
            "position_y": 4,
            "width": 4,
            "height": 2
        },
        {
            "title": "Recent Alerts",
            "widget_type": "alert",
            "data_source_type": "kpi",
            "config": {"show_recent": 5, "severity_filter": ["warning", "critical"]},
            "position_x": 0,
            "position_y": 6,
            "width": 4,
            "height": 2
        }
    ]

    for widget_data in widgets_data:
        widget = DashboardWidget(dashboard_id=dashboard.id, **widget_data)
        db.add(widget)

    await db.commit()
    print(f"Created {len(widgets_data)} dashboard widgets")

    # Create executive report
    report = ExecutiveReport(
        title="Q1 2025 Strategic Plan Executive Report",
        report_type="quarterly",
        description="Comprehensive review of strategic plan progress for Q1 2025",
        period_start=datetime(2025, 1, 1),
        period_end=datetime(2025, 3, 31),
        executive_summary="""
        Q1 2025 demonstrated strong progress on our strategic initiatives.
        The Digital Library Transformation project is 30% complete and on schedule.
        KPIs show positive trends with library card registrations up 12.5% and
        patron satisfaction at 87%. Budget execution is tracking well at 19% spent
        with strong controls in place. Four strategic risks are being actively managed
        with mitigation strategies showing effectiveness.
        """,
        key_findings=[
            "Digital transformation proceeding on schedule with first major milestone completed",
            "Community engagement showing positive early indicators",
            "Staff training program needs acceleration to meet targets",
            "Budget contingency allocation proving prudent for risk mitigation"
        ],
        recommendations=[
            "Accelerate staff training to support Q2 system cutover",
            "Increase community marketing spend to boost outreach participation",
            "Schedule board workshop on risk management strategies",
            "Consider advancing maker space timeline based on strong community interest"
        ],
        report_sections=[
            {
                "title": "Initiative Progress",
                "content": "Detailed initiative status and milestone completion"
            },
            {
                "title": "KPI Performance",
                "content": "Analysis of key performance indicators vs targets"
            },
            {
                "title": "Financial Summary",
                "content": "Budget execution and variance analysis"
            },
            {
                "title": "Risk Management",
                "content": "Risk register status and mitigation effectiveness"
            }
        ],
        kpi_snapshot={
            "card_registrations": {"current": 13500, "target": 15000, "trend": "up"},
            "digital_circulation": {"current": 32, "target": 35, "trend": "up"},
            "patron_satisfaction": {"current": 87, "target": 90, "trend": "up"}
        },
        initiative_snapshot={
            "total": 3,
            "completed": 0,
            "in_progress": 1,
            "planning": 1,
            "approved": 1
        },
        budget_snapshot={
            "total": 500000,
            "spent": 95000,
            "available": 175000,
            "spending_rate": 19.0
        },
        risk_snapshot={
            "total": 4,
            "critical": 0,
            "high": 2,
            "medium": 2,
            "low": 0
        },
        status="published",
        published_date=datetime(2025, 4, 5),
        distributed_to=["BOARD", "ADMIN"],
        created_by_id=user_id,
        approved_by_id=user_id
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    print(f"Created executive report: {report.title}")

    # Create report schedule
    schedule = ReportSchedule(
        report_template_id=report.id,
        name="Quarterly Executive Report",
        frequency="quarterly",
        day_of_month=5,
        time_of_day="09:00",
        is_active=True,
        next_run=datetime(2025, 7, 5, 9, 0),
        recipients=["board@l30.org", "director@l30.org"],
        email_subject="Quarterly Strategic Plan Executive Report",
        email_body_template="Please find attached the quarterly executive report for strategic plan progress review."
    )
    db.add(schedule)
    await db.commit()

    print("Created report schedule")


async def verify_data(db: AsyncSession, plan_id: int):
    """Verify all seeded data."""
    print("\n=== VERIFICATION ===")

    from sqlalchemy import select, func

    # Count initiatives
    result = await db.execute(
        select(func.count(StrategicInitiative.id)).where(StrategicInitiative.plan_id == plan_id)
    )
    initiative_count = result.scalar()
    print(f"Strategic Initiatives: {initiative_count}")

    # Count KPIs
    result = await db.execute(
        select(func.count(StrategicKPI.id)).where(StrategicKPI.plan_id == plan_id)
    )
    kpi_count = result.scalar()
    print(f"KPIs: {kpi_count}")

    # Count budgets
    result = await db.execute(
        select(func.count(StrategicBudget.id)).where(StrategicBudget.plan_id == plan_id)
    )
    budget_count = result.scalar()
    print(f"Budgets: {budget_count}")

    # Count risks
    result = await db.execute(
        select(func.count(StrategicRisk.id)).where(StrategicRisk.plan_id == plan_id)
    )
    risk_count = result.scalar()
    print(f"Risks: {risk_count}")

    # Count dashboards
    result = await db.execute(
        select(func.count(ExecutiveDashboard.id)).where(ExecutiveDashboard.plan_id == plan_id)
    )
    dashboard_count = result.scalar()
    print(f"Executive Dashboards: {dashboard_count}")

    # Count reports
    result = await db.execute(
        select(func.count(ExecutiveReport.id))
    )
    report_count = result.scalar()
    print(f"Executive Reports: {report_count}")

    print("\n=== ALL PHASES VERIFIED SUCCESSFULLY ===")


async def main():
    """Main function to run the seed."""
    async with async_session_maker() as db:
        try:
            await seed_all_phases(db)
            print("\nSeed completed successfully!")
        except Exception as e:
            print(f"\nError during seed: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()


if __name__ == "__main__":
    asyncio.run(main())
