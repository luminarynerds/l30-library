# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class PrepAgendaItem(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    presenter: Optional[str] = None
    duration_minutes: Optional[int] = None
    order: int = 0
    attachments: List[str] = []


class PrepMotionItem(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    proposed_by: Optional[str] = None
    requires_vote: bool = True


class PrepActionItem(BaseModel):
    id: int
    description: str
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str = "open"
    from_meeting_date: Optional[datetime] = None


class PrepFinancialSnapshot(BaseModel):
    total_revenue_ytd: float = 0.0
    total_expenses_ytd: float = 0.0
    net_balance: float = 0.0
    budget_utilization_pct: float = 0.0
    key_line_items: List[dict] = []


class PrepComplianceItem(BaseModel):
    id: int
    area: str
    status: str  # 'compliant' | 'at_risk' | 'non_compliant'
    description: str
    due_date: Optional[datetime] = None


class PrepPreviousMinutes(BaseModel):
    meeting_id: int
    meeting_date: datetime
    summary: Optional[str] = None
    key_decisions: List[str] = []


class MeetingPrepPacket(BaseModel):
    meeting_id: int
    meeting_title: Optional[str] = None
    meeting_date: datetime
    location: Optional[str] = None
    agenda_items: List[PrepAgendaItem] = []
    pending_motions: List[PrepMotionItem] = []
    open_action_items: List[PrepActionItem] = []
    financial_snapshot: Optional[PrepFinancialSnapshot] = None
    compliance_items: List[PrepComplianceItem] = []
    previous_minutes: Optional[PrepPreviousMinutes] = None
    generated_at: datetime
