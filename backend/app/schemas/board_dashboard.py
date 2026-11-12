# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Literal

from pydantic import BaseModel


class AttentionItem(BaseModel):
    id: str
    urgency: Literal["overdue", "upcoming", "routine"]
    title: str
    description: str
    deadline: str | None = None
    action_label: str
    action_url: str


class AttentionItemsResponse(BaseModel):
    items: list[AttentionItem] = []


class StatusEntry(BaseModel):
    label: str
    value: str
    warning: bool = False


class StatusArea(BaseModel):
    title: str
    icon: str
    entries: list[StatusEntry] = []


class BoardStatusResponse(BaseModel):
    areas: list[StatusArea] = []


class BoardActivityItem(BaseModel):
    id: int
    icon: str
    description: str
    timestamp: str


class BoardActivityResponse(BaseModel):
    items: list[BoardActivityItem] = []


class SignOffItem(BaseModel):
    id: str
    title: str
    description: str
    action_label: str
    action_url: str


class SignOffQueueResponse(BaseModel):
    items: list[SignOffItem] = []


class ChecklistItem(BaseModel):
    label: str
    done: bool = False


class NextMeetingResponse(BaseModel):
    date: str
    time: str
    location: str
    is_chairing: bool = False
    relative_time: str | None = None
    checklist: list[ChecklistItem] = []


class UpcomingItem(BaseModel):
    date: str
    title: str
    note: str


class UpcomingResponse(BaseModel):
    items: list[UpcomingItem] = []
