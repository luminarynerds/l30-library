# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from pydantic import BaseModel

from ._base import StrictInputSchema
from typing import List, Optional
from datetime import datetime


class BookClubListItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    genre: Optional[str] = None
    meeting_frequency: Optional[str] = None
    member_count: int = 0
    max_members: Optional[int] = None
    # Capacity signals (waitlist feature). current_member_count mirrors
    # member_count today but is named distinctly per the spec contract.
    current_member_count: int = 0
    waitlist_count: int = 0
    is_full: bool = False
    current_book_title: Optional[str] = None
    current_book_author: Optional[str] = None
    is_member: bool = False
    next_meeting_date: Optional[datetime] = None


class BookClubDetail(BookClubListItem):
    created_at: datetime | None = None
    # None = caller not on the waitlist (or anonymous); 1-based FIFO
    # position otherwise. Omitted from list items (expensive at scale).
    patron_waitlist_position: Optional[int] = None
    # None = roster hidden (anonymous caller). [] = visible but empty.
    members: Optional[List["BookClubMemberInfo"]] = None
    upcoming_meetings: List["BookClubMeetingInfo"] = []


class BookClubMemberInfo(BaseModel):
    id: int
    user_id: int
    display_name: str
    joined_at: datetime
    role: str = "member"


class BookClubMeetingInfo(BaseModel):
    id: int
    title: Optional[str] = None
    scheduled_at: datetime
    location: Optional[str] = None
    is_virtual: bool = False
    discussion_count: int = 0


class DiscussionThread(BaseModel):
    id: int
    meeting_id: int
    user_id: int
    author_name: str
    title: str
    content: str
    created_at: datetime | None = None
    is_pinned: bool = False
    reply_count: int = 0


class DiscussionReply(BaseModel):
    id: int
    discussion_id: int
    user_id: int
    author_name: str
    content: str
    created_at: datetime | None = None
class ChatMessage(BaseModel):
    id: int
    meeting_id: int
    user_id: int
    author_name: str
    content: str
    created_at: datetime | None = None
class CreateDiscussionRequest(StrictInputSchema):
    title: str
    content: str


class CreateReplyRequest(StrictInputSchema):
    content: str


class BookClubListResponse(BaseModel):
    clubs: List[BookClubListItem] = []
    total: int = 0
    page: int = 1
    per_page: int = 20


class DiscussionSearchHit(BaseModel):

    id: int
    meeting_id: int
    meeting_title: Optional[str] = None
    meeting_scheduled_at: datetime
    meeting_is_archived: bool = False
    snippet: str = ""
    author_display_name: str = ""
    created_at: datetime
    rank: float = 0.0


class DiscussionSearchResponse(BaseModel):

    hits: List[DiscussionSearchHit] = []
    total: int = 0
    q: str = ""
    include_archived: bool = False


class MeetingArchiveResponse(BaseModel):

    id: int
    book_club_id: int
    title: str
    is_archived: bool
    meeting_date: datetime
