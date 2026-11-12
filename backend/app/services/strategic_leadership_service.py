# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.strategic import (
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
    # Existing
    StrategicPlan, StrategicGoal,
)


# ============================================================================
# PHASE 1: Strategic Initiatives Service
# ============================================================================

async def create_initiative(
    db: AsyncSession,
    plan_id: int,
    data: Dict[str, Any],
    user_id: int
) -> StrategicInitiative:
    initiative = StrategicInitiative(
        plan_id=plan_id,
        **data
    )
    db.add(initiative)
    await db.commit()
    await db.refresh(initiative)
    return initiative


async def get_initiatives_for_plan(
    db: AsyncSession,
    plan_id: int,
    status: Optional[str] = None
) -> List[StrategicInitiative]:
    query = select(StrategicInitiative).where(StrategicInitiative.plan_id == plan_id)

    if status:
        query = query.where(StrategicInitiative.status == status)

    query = query.options(
        selectinload(StrategicInitiative.milestones),
        selectinload(StrategicInitiative.board_decisions),
        selectinload(StrategicInitiative.assigned_leader)
    )

    result = await db.execute(query)
    return result.scalars().all()


async def create_milestone(
    db: AsyncSession,
    initiative_id: int,
    data: Dict[str, Any]
) -> InitiativeMilestone:
    milestone = InitiativeMilestone(
        initiative_id=initiative_id,
        **data
    )
    db.add(milestone)
    await db.commit()
    await db.refresh(milestone)
    return milestone


async def complete_milestone(
    db: AsyncSession,
    milestone_id: int,
    completion_notes: Optional[str] = None
) -> InitiativeMilestone:
    result = await db.execute(
        select(InitiativeMilestone).where(InitiativeMilestone.id == milestone_id)
    )
    milestone = result.scalar_one()
    milestone.completed = True
    milestone.completion_date = datetime.utcnow()
    if completion_notes is not None:
        milestone.completion_notes = completion_notes
    await db.commit()
    await db.refresh(milestone)
    return milestone


async def link_board_decision(
    db: AsyncSession,
    initiative_id: int,
    decision_data: Dict[str, Any]
) -> BoardDecisionLink:
    link = BoardDecisionLink(
        initiative_id=initiative_id,
        **decision_data
    )
    db.add(link)

    # Update initiative approval status if it's an approval decision
    if decision_data.get('decision_type') == 'approval':
        result = await db.execute(
            select(StrategicInitiative).where(StrategicInitiative.id == initiative_id)
        )
        initiative = result.scalar_one()
        initiative.board_approved = True
        initiative.board_approval_date = decision_data.get('meeting_date')
        initiative.board_meeting_reference = decision_data.get('meeting_reference')

    await db.commit()
    await db.refresh(link)
    return link


# ============================================================================
# PHASE 2: KPI Service
# ============================================================================

async def create_kpi(
    db: AsyncSession,
    plan_id: int,
    kpi_data: Dict[str, Any],
    user_id: int
) -> StrategicKPI:
    kpi = StrategicKPI(
        plan_id=plan_id,
        responsible_person_id=user_id,
        **kpi_data
    )
    db.add(kpi)
    await db.commit()
    await db.refresh(kpi)
    return kpi


async def record_kpi_value(
    db: AsyncSession,
    kpi_id: int,
    value: Decimal,
    user_id: int,
    notes: Optional[str] = None,
    is_estimated: bool = False
) -> KPIValue:
    kpi_value = KPIValue(
        kpi_id=kpi_id,
        value=value,
        recorded_date=datetime.now(timezone.utc),
        recorded_by_id=user_id,
        notes=notes,
        is_estimated=is_estimated
    )
    db.add(kpi_value)

    # Update KPI current value and check thresholds
    result = await db.execute(select(StrategicKPI).where(StrategicKPI.id == kpi_id))
    kpi = result.scalar_one()
    kpi.current_value = value
    kpi.last_updated = datetime.now(timezone.utc)

    # Calculate trend
    if kpi.baseline_value:
        variance = ((float(value) - float(kpi.baseline_value)) / float(kpi.baseline_value)) * 100
        kpi.variance_percentage = Decimal(str(round(variance, 2)))

        if variance > 5:
            kpi.trend_direction = "up"
        elif variance < -5:
            kpi.trend_direction = "down"
        else:
            kpi.trend_direction = "stable"

    # Check thresholds and create alerts
    await _check_kpi_thresholds(db, kpi, value)

    await db.commit()
    await db.refresh(kpi_value)
    return kpi_value


async def _check_kpi_thresholds(
    db: AsyncSession,
    kpi: StrategicKPI,
    value: Decimal
):
    severity = None
    threshold_violated = None
    expected_value = kpi.target_value

    if kpi.threshold_red and value < kpi.threshold_red:
        severity = "critical"
        threshold_violated = "red"
    elif kpi.threshold_yellow and value < kpi.threshold_yellow:
        severity = "warning"
        threshold_violated = "yellow"
    elif kpi.target_value and value < kpi.target_value:
        severity = "info"
        threshold_violated = "target_missed"

    if severity:
        alert = KPIAlert(
            kpi_id=kpi.id,
            severity=severity,
            message=f"KPI '{kpi.name}' is {threshold_violated}: {value} {kpi.unit_of_measure}",
            triggered_at=datetime.now(timezone.utc),
            threshold_violated=threshold_violated,
            actual_value=value,
            expected_value=expected_value,
            acknowledged=False,
            resolved=False
        )
        db.add(alert)


async def get_kpi_dashboard_data(
    db: AsyncSession,
    dashboard_id: int
) -> Dict[str, Any]:
    # Get dashboard configuration
    result = await db.execute(
        select(KPIDashboard).where(KPIDashboard.id == dashboard_id)
    )
    dashboard = result.scalar_one()

    # Get KPI data
    kpi_ids = dashboard.kpi_ids
    result = await db.execute(
        select(StrategicKPI)
        .where(StrategicKPI.id.in_(kpi_ids))
        .options(selectinload(StrategicKPI.values))
    )
    kpis = result.scalars().all()

    dashboard_data = {
        "id": dashboard.id,
        "name": dashboard.name,
        "description": dashboard.description,
        "audience": dashboard.audience,
        "kpis": []
    }

    for kpi in kpis:
        # Get recent values
        recent_values = sorted(kpi.values, key=lambda x: x.recorded_date, reverse=True)[:10]

        kpi_data = {
            "id": kpi.id,
            "name": kpi.name,
            "category": kpi.category,
            "current_value": float(kpi.current_value) if kpi.current_value else 0,
            "target_value": float(kpi.target_value) if kpi.target_value else 0,
            "unit_of_measure": kpi.unit_of_measure,
            "trend_direction": kpi.trend_direction,
            "variance_percentage": float(kpi.variance_percentage) if kpi.variance_percentage else 0,
            "recent_values": [
                {
                    "value": float(v.value),
                    "date": v.recorded_date.isoformat(),
                    "notes": v.notes
                }
                for v in recent_values
            ]
        }
        dashboard_data["kpis"].append(kpi_data)

    return dashboard_data


# ============================================================================
# PHASE 3: Budget Service
# ============================================================================

async def create_budget(
    db: AsyncSession,
    plan_id: int,
    budget_data: Dict[str, Any],
    user_id: int
) -> StrategicBudget:
    budget = StrategicBudget(
        plan_id=plan_id,
        budget_owner_id=user_id,
        available_amount=budget_data['total_budget'],
        **budget_data
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


async def record_budget_transaction(
    db: AsyncSession,
    budget_id: int,
    transaction_data: Dict[str, Any],
    user_id: int
) -> BudgetTransaction:
    transaction = BudgetTransaction(
        budget_id=budget_id,
        approved_by_id=user_id,
        **transaction_data
    )
    db.add(transaction)

    # Update budget totals
    result = await db.execute(
        select(StrategicBudget).where(StrategicBudget.id == budget_id)
    )
    budget = result.scalar_one()

    transaction_type = transaction_data['transaction_type']
    amount = transaction_data['amount']

    if transaction_type == 'expense':
        budget.spent_amount += amount
        budget.available_amount -= amount
    elif transaction_type == 'allocation':
        budget.allocated_amount += amount
        budget.committed_amount += amount
        budget.available_amount -= amount
    elif transaction_type == 'refund':
        budget.spent_amount -= amount
        budget.available_amount += amount

    await db.commit()
    await db.refresh(transaction)
    return transaction


async def get_budget_summary(
    db: AsyncSession,
    budget_id: int
) -> Dict[str, Any]:
    result = await db.execute(
        select(StrategicBudget)
        .where(StrategicBudget.id == budget_id)
        .options(
            selectinload(StrategicBudget.items),
            selectinload(StrategicBudget.transactions),
            selectinload(StrategicBudget.allocations)
        )
    )
    budget = result.scalar_one()

    # Calculate category breakdown
    category_breakdown = {}
    for item in budget.items:
        if item.category not in category_breakdown:
            category_breakdown[item.category] = {
                "budgeted": 0,
                "spent": 0,
                "remaining": 0
            }
        category_breakdown[item.category]["budgeted"] += float(item.budgeted_amount)
        category_breakdown[item.category]["spent"] += float(item.spent_amount)
        category_breakdown[item.category]["remaining"] += float(item.remaining_amount)

    # Calculate spending rate
    total_spent = float(budget.spent_amount)
    total_budget = float(budget.total_budget)
    spending_rate = (total_spent / total_budget * 100) if total_budget > 0 else 0

    # Recent transactions
    recent_transactions = sorted(budget.transactions, key=lambda x: x.transaction_date, reverse=True)[:10]

    return {
        "id": budget.id,
        "name": budget.name,
        "fiscal_year": budget.fiscal_year,
        "status": budget.status,
        "total_budget": total_budget,
        "allocated_amount": float(budget.allocated_amount),
        "spent_amount": total_spent,
        "committed_amount": float(budget.committed_amount),
        "available_amount": float(budget.available_amount),
        "spending_rate_percentage": round(spending_rate, 2),
        "category_breakdown": category_breakdown,
        "recent_transactions": [
            {
                "id": t.id,
                "type": t.transaction_type,
                "description": t.description,
                "amount": float(t.amount),
                "date": t.transaction_date.isoformat(),
                "category": t.category
            }
            for t in recent_transactions
        ]
    }


# ============================================================================
# PHASE 4: Risk Management Service
# ============================================================================

async def create_risk(
    db: AsyncSession,
    plan_id: int,
    risk_data: Dict[str, Any],
    user_id: int
) -> StrategicRisk:
    # Calculate risk score
    likelihood_scores = {"low": 1, "medium": 3, "high": 5}
    impact_scores = {"low": 1, "medium": 3, "high": 5}

    likelihood = risk_data.get('likelihood', 'medium')
    impact = risk_data.get('impact', 'medium')

    risk_score = likelihood_scores.get(likelihood, 3) * impact_scores.get(impact, 3)

    # Determine risk level
    if risk_score >= 15:
        risk_level = "critical"
    elif risk_score >= 9:
        risk_level = "high"
    elif risk_score >= 4:
        risk_level = "medium"
    else:
        risk_level = "low"

    risk = StrategicRisk(
        plan_id=plan_id,
        owner_id=user_id,
        identified_date=datetime.now(timezone.utc),
        risk_score=risk_score,
        risk_level=risk_level,
        **risk_data
    )
    db.add(risk)
    await db.commit()
    await db.refresh(risk)
    return risk


async def create_mitigation_strategy(
    db: AsyncSession,
    risk_id: int,
    strategy_data: Dict[str, Any]
) -> RiskMitigationStrategy:
    strategy = RiskMitigationStrategy(
        risk_id=risk_id,
        **strategy_data
    )
    db.add(strategy)

    # Update risk status
    result = await db.execute(select(StrategicRisk).where(StrategicRisk.id == risk_id))
    risk = result.scalar_one()
    risk.status = "mitigating"

    await db.commit()
    await db.refresh(strategy)
    return strategy


async def conduct_risk_assessment(
    db: AsyncSession,
    risk_id: int,
    assessment_data: Dict[str, Any],
    user_id: int
) -> RiskAssessment:
    # Calculate new risk score
    likelihood_scores = {"low": 1, "medium": 3, "high": 5}
    impact_scores = {"low": 1, "medium": 3, "high": 5}

    likelihood = assessment_data.get('likelihood', 'medium')
    impact = assessment_data.get('impact', 'medium')

    risk_score = likelihood_scores.get(likelihood, 3) * impact_scores.get(impact, 3)

    assessment = RiskAssessment(
        risk_id=risk_id,
        assessed_by_id=user_id,
        assessment_date=datetime.now(timezone.utc),
        risk_score=risk_score,
        **assessment_data
    )
    db.add(assessment)

    # Update risk with new ratings
    result = await db.execute(select(StrategicRisk).where(StrategicRisk.id == risk_id))
    risk = result.scalar_one()
    risk.likelihood = likelihood
    risk.impact = impact
    risk.risk_score = risk_score

    await db.commit()
    await db.refresh(assessment)
    return assessment


async def get_risk_register(
    db: AsyncSession,
    plan_id: int
) -> Dict[str, Any]:
    result = await db.execute(
        select(StrategicRisk)
        .where(StrategicRisk.plan_id == plan_id)
        .options(
            selectinload(StrategicRisk.mitigation_strategies),
            selectinload(StrategicRisk.assessments),
            selectinload(StrategicRisk.owner)
        )
    )
    risks = result.scalars().all()

    # Categorize risks
    risk_breakdown = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": []
    }

    for risk in risks:
        risk_data = {
            "id": risk.id,
            "title": risk.title,
            "category": risk.category,
            "risk_level": risk.risk_level,
            "risk_score": risk.risk_score,
            "likelihood": risk.likelihood,
            "impact": risk.impact,
            "status": risk.status,
            "owner": risk.owner.email if risk.owner else None,
            "mitigation_count": len(risk.mitigation_strategies)
        }
        risk_breakdown[risk.risk_level].append(risk_data)

    return {
        "total_risks": len(risks),
        "by_level": {
            "critical": len(risk_breakdown["critical"]),
            "high": len(risk_breakdown["high"]),
            "medium": len(risk_breakdown["medium"]),
            "low": len(risk_breakdown["low"])
        },
        "risks": risk_breakdown,
        "status_breakdown": {
            "identified": sum(1 for r in risks if r.status == "identified"),
            "assessing": sum(1 for r in risks if r.status == "assessing"),
            "mitigating": sum(1 for r in risks if r.status == "mitigating"),
            "monitoring": sum(1 for r in risks if r.status == "monitoring"),
            "resolved": sum(1 for r in risks if r.status == "resolved")
        }
    }


# ============================================================================
# PHASE 5: Executive Dashboard & Reporting Service
# ============================================================================

async def create_executive_dashboard(
    db: AsyncSession,
    plan_id: int,
    dashboard_data: Dict[str, Any],
    user_id: int
) -> ExecutiveDashboard:
    dashboard = ExecutiveDashboard(
        plan_id=plan_id,
        created_by_id=user_id,
        **dashboard_data
    )
    db.add(dashboard)
    await db.commit()
    await db.refresh(dashboard)
    return dashboard


async def add_dashboard_widget(
    db: AsyncSession,
    dashboard_id: int,
    widget_data: Dict[str, Any]
) -> DashboardWidget:
    widget = DashboardWidget(
        dashboard_id=dashboard_id,
        **widget_data
    )
    db.add(widget)
    await db.commit()
    await db.refresh(widget)
    return widget


async def generate_executive_report(
    db: AsyncSession,
    plan_id: int,
    period_start: datetime,
    period_end: datetime,
    user_id: int,
    report_type: str = "monthly"
) -> ExecutiveReport:
    # Get plan
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == plan_id)
        .options(
            selectinload(StrategicPlan.initiatives),
            selectinload(StrategicPlan.kpis),
            selectinload(StrategicPlan.budgets),
            selectinload(StrategicPlan.risks)
        )
    )
    plan = result.scalar_one()

    # Gather KPI snapshot
    kpi_snapshot = {}
    for kpi in plan.kpis:
        kpi_snapshot[kpi.name] = {
            "current": float(kpi.current_value) if kpi.current_value else 0,
            "target": float(kpi.target_value) if kpi.target_value else 0,
            "unit": kpi.unit_of_measure,
            "trend": kpi.trend_direction
        }

    # Gather initiative snapshot
    initiative_snapshot = {
        "total": len(plan.initiatives),
        "completed": sum(1 for i in plan.initiatives if i.status == "completed"),
        "in_progress": sum(1 for i in plan.initiatives if i.status == "in_progress"),
        "on_hold": sum(1 for i in plan.initiatives if i.status == "on_hold")
    }

    # Gather budget snapshot
    budget_snapshot = {}
    for budget in plan.budgets:
        budget_snapshot[budget.name] = {
            "total": float(budget.total_budget),
            "spent": float(budget.spent_amount),
            "available": float(budget.available_amount),
            "spending_rate": (float(budget.spent_amount) / float(budget.total_budget) * 100) if budget.total_budget > 0 else 0
        }

    # Gather risk snapshot
    risk_snapshot = {
        "total": len(plan.risks),
        "critical": sum(1 for r in plan.risks if r.risk_level == "critical"),
        "high": sum(1 for r in plan.risks if r.risk_level == "high"),
        "medium": sum(1 for r in plan.risks if r.risk_level == "medium"),
        "low": sum(1 for r in plan.risks if r.risk_level == "low")
    }

    # Generate key findings
    key_findings = []

    # Check initiative progress
    completion_rate = (initiative_snapshot["completed"] / initiative_snapshot["total"] * 100) if initiative_snapshot["total"] > 0 else 0
    key_findings.append(f"Initiative completion rate: {completion_rate:.1f}%")

    # Check budget health
    for name, data in budget_snapshot.items():
        if data["spending_rate"] > 90:
            key_findings.append(f"Budget '{name}' is at {data['spending_rate']:.1f}% utilization")

    # Check risk levels
    if risk_snapshot["critical"] > 0:
        key_findings.append(f"{risk_snapshot['critical']} critical risks require immediate attention")

    # Create report
    report = ExecutiveReport(
        title=f"{report_type.title()} Executive Report - {period_start.strftime('%Y-%m')}",
        report_type=report_type,
        period_start=period_start,
        period_end=period_end,
        created_by_id=user_id,
        kpi_snapshot=kpi_snapshot,
        initiative_snapshot=initiative_snapshot,
        budget_snapshot=budget_snapshot,
        risk_snapshot=risk_snapshot,
        key_findings=key_findings,
        status="draft"
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def get_executive_summary(
    db: AsyncSession,
    plan_id: int
) -> Dict[str, Any]:
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == plan_id)
        .options(
            selectinload(StrategicPlan.initiatives),
            selectinload(StrategicPlan.kpis),
            selectinload(StrategicPlan.budgets),
            selectinload(StrategicPlan.risks),
            selectinload(StrategicPlan.goals)
        )
    )
    plan = result.scalar_one()

    # Calculate overall health score (0-100)
    health_score = 100

    # Factor 1: Initiative progress (40 points)
    if plan.initiatives:
        completed = sum(1 for i in plan.initiatives if i.status == "completed")
        initiative_score = (completed / len(plan.initiatives)) * 40
        health_score -= (40 - initiative_score)

    # Factor 2: KPI performance (30 points)
    if plan.kpis:
        on_target = sum(1 for k in plan.kpis if k.current_value and k.target_value and k.current_value >= k.target_value)
        kpi_score = (on_target / len(plan.kpis)) * 30
        health_score -= (30 - kpi_score)

    # Factor 3: Risk management (20 points)
    if plan.risks:
        critical_risks = sum(1 for r in plan.risks if r.risk_level == "critical")
        risk_penalty = min(critical_risks * 5, 20)  # -5 points per critical risk, max -20
        health_score -= risk_penalty

    # Factor 4: Budget adherence (10 points)
    if plan.budgets:
        over_budget = sum(1 for b in plan.budgets if b.spent_amount > b.total_budget)
        budget_penalty = min(over_budget * 5, 10)
        health_score -= budget_penalty

    health_score = max(0, min(100, health_score))  # Clamp to 0-100

    return {
        "plan_id": plan.id,
        "plan_name": plan.title,
        "health_score": round(health_score, 1),
        "health_status": "Excellent" if health_score >= 90 else "Good" if health_score >= 70 else "Fair" if health_score >= 50 else "Poor",
        "initiatives": {
            "total": len(plan.initiatives),
            "completed": sum(1 for i in plan.initiatives if i.status == "completed"),
            "in_progress": sum(1 for i in plan.initiatives if i.status == "in_progress"),
            "at_risk": sum(1 for i in plan.initiatives if i.status == "on_hold")
        },
        "kpis": {
            "total": len(plan.kpis),
            "on_target": sum(1 for k in plan.kpis if k.current_value and k.target_value and k.current_value >= k.target_value),
            "below_target": sum(1 for k in plan.kpis if k.current_value and k.target_value and k.current_value < k.target_value)
        },
        "budgets": {
            "total": len(plan.budgets),
            "total_budget": sum(float(b.total_budget) for b in plan.budgets),
            "total_spent": sum(float(b.spent_amount) for b in plan.budgets),
            "total_available": sum(float(b.available_amount) for b in plan.budgets)
        },
        "risks": {
            "total": len(plan.risks),
            "critical": sum(1 for r in plan.risks if r.risk_level == "critical"),
            "high": sum(1 for r in plan.risks if r.risk_level == "high"),
            "medium": sum(1 for r in plan.risks if r.risk_level == "medium"),
            "low": sum(1 for r in plan.risks if r.risk_level == "low")
        },
        "goals": {
            "total": len(plan.goals),
            "completed": sum(1 for g in plan.goals if g.status == "completed"),
            "on_track": sum(1 for g in plan.goals if g.status == "on_track"),
            "at_risk": sum(1 for g in plan.goals if g.status == "at_risk")
        }
    }
