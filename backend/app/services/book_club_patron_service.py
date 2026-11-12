# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.book_club import (
    BookClub, BookClubMember, BookClubMeeting, BookClubRole, BookClubStatus,
    BookClubDiscussion, BookClubWaitlistEntry, DiscussionStatus,
)
from app.services import book_club_service
from app.models.user import User
from app.schemas.book_club_patron import (
    BookClubListItem,
    BookClubDetail,
    BookClubMemberInfo,
    BookClubMeetingInfo,
    DiscussionThread,
    DiscussionReply,
    ChatMessage,
    BookClubListResponse,
)


class BookClubPatronService:

    @staticmethod
    async def list_clubs(
        genre: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        user_id: Optional[int] = None,
        db: Optional[AsyncSession] = None,
    ) -> BookClubListResponse:
        if db is None:
            return BookClubListResponse(clubs=[], total=0, page=page, per_page=per_page)

        query = (
            select(BookClub)
            .where(
                and_(
                    BookClub.is_public == True,
                    BookClub.status == BookClubStatus.active,
                )
            )
            .options(joinedload(BookClub.members), joinedload(BookClub.meetings).joinedload(BookClubMeeting.catalog_item))
        )

        if search:
            safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(
                BookClub.name.ilike(f"%{safe_search}%")
                | BookClub.description.ilike(f"%{safe_search}%")
            )

        if genre:
            query = query.where(BookClub.genre == genre)

        # Count total before pagination
        count_query = select(func.count(BookClub.id)).where(
            and_(
                BookClub.is_public == True,
                BookClub.status == BookClubStatus.active,
            )
        )
        if search:
            count_query = count_query.where(
                BookClub.name.ilike(f"%{safe_search}%")
                | BookClub.description.ilike(f"%{safe_search}%")
            )
        if genre:
            count_query = count_query.where(BookClub.genre == genre)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * per_page
        query = query.order_by(BookClub.name).offset(offset).limit(per_page)

        result = await db.execute(query)
        clubs = result.unique().scalars().all()

        items = []
        for club in clubs:
            member_count = len(club.members) if club.members else 0
            is_member = False
            if user_id and club.members:
                is_member = any(m.user_id == user_id for m in club.members)

            # Find next upcoming meeting
            now = datetime.now(timezone.utc)
            all_meetings = [m for m in (club.meetings or []) if m.meeting_date]
            upcoming = [
                m for m in all_meetings
                if m.meeting_date > now
                and m.status in (DiscussionStatus.planned, DiscussionStatus.in_progress)
            ]
            upcoming.sort(key=lambda m: m.meeting_date)
            next_meeting = upcoming[0] if upcoming else None

            # Pick the meeting whose catalog_item represents the "currently reading" book:
            # prefer the next upcoming meeting with a linked catalog_item; otherwise fall back
            # to the most recent past meeting with a linked catalog_item. catalog_item is
            # eager-loaded via joinedload above to avoid MissingGreenlet on async access.
            current_book_meeting = None
            for m in upcoming:
                if m.catalog_item is not None:
                    current_book_meeting = m
                    break
            if current_book_meeting is None:
                past_with_book = [
                    m for m in all_meetings
                    if m.meeting_date <= now and m.catalog_item is not None
                ]
                past_with_book.sort(key=lambda m: m.meeting_date, reverse=True)
                current_book_meeting = past_with_book[0] if past_with_book else None

            current_book_title = (
                current_book_meeting.catalog_item.title
                if current_book_meeting and current_book_meeting.catalog_item
                else None
            )
            current_book_author = (
                current_book_meeting.catalog_item.author
                if current_book_meeting and current_book_meeting.catalog_item
                else None
            )

            waitlist_count = await book_club_service.get_waitlist_count(
                club.id, db
            )
            is_full = (
                club.max_members is not None
                and member_count >= club.max_members
            )

            items.append(BookClubListItem(
                id=club.id,
                name=club.name,
                description=club.description,
                genre=club.genre,
                meeting_frequency=club.meeting_frequency,
                member_count=member_count,
                max_members=club.max_members,
                current_member_count=member_count,
                waitlist_count=waitlist_count,
                is_full=is_full,
                current_book_title=current_book_title,
                current_book_author=current_book_author,
                is_member=is_member,
                next_meeting_date=next_meeting.meeting_date if next_meeting else None,
            ))

        return BookClubListResponse(clubs=items, total=total, page=page, per_page=per_page)

    @staticmethod
    async def list_genres(db: Optional[AsyncSession] = None) -> list[str]:
        if db is None:
            return []
        result = await db.execute(
            select(BookClub.genre)
            .where(
                and_(
                    BookClub.is_public == True,
                    BookClub.status == BookClubStatus.active,
                    BookClub.genre.isnot(None),
                )
            )
            .distinct()
        )
        rows = result.scalars().all()
        return sorted([g for g in rows if g])

    @staticmethod
    async def get_club_detail(club_id: int, user_id: Optional[int] = None, db: Optional[AsyncSession] = None) -> Optional[BookClubDetail]:
        if db is None:
            return None

        query = (
            select(BookClub)
            .where(BookClub.id == club_id)
            .options(
                joinedload(BookClub.members).joinedload(BookClubMember.user),
                joinedload(BookClub.meetings),
            )
        )
        result = await db.execute(query)
        club = result.unique().scalars().first()

        if not club:
            return None

        member_count = len(club.members) if club.members else 0
        is_member = user_id is not None and any(m.user_id == user_id for m in (club.members or []))

        # Anonymous callers don't see the roster; authenticated callers do.
        members: Optional[list[BookClubMemberInfo]] = None
        if user_id is not None:
            members = []
            for m in (club.members or []):
                display_name = "Member"
                if m.user:
                    display_name = f"{m.user.first_name or ''} {m.user.last_name or ''}".strip() or m.user.email
                members.append(BookClubMemberInfo(
                    id=m.id,
                    user_id=m.user_id,
                    display_name=display_name,
                    joined_at=m.joined_at,
                    role=m.role.value if m.role else "member",
                ))

        # Build upcoming meetings. Archived meetings are hidden from patron
        # views regardless of the book_club_history_enabled flag — they
        # belong on the staff History tab.
        now = datetime.now(timezone.utc)
        upcoming_meetings = []
        for mtg in (club.meetings or []):
            if getattr(mtg, "is_archived", False):
                continue
            if mtg.meeting_date and mtg.meeting_date > now and mtg.status != DiscussionStatus.cancelled:
                upcoming_meetings.append(BookClubMeetingInfo(
                    id=mtg.id,
                    title=mtg.title,
                    scheduled_at=mtg.meeting_date,
                    location=mtg.location,
                ))
        upcoming_meetings.sort(key=lambda m: m.scheduled_at)

        # Capacity signals. Scalar helpers — NEVER lazy relationship
        # access here (MissingGreenlet under async serialization).
        waitlist_count = await book_club_service.get_waitlist_count(
            club.id, db
        )
        is_full = (
            club.max_members is not None
            and member_count >= club.max_members
        )
        patron_waitlist_position = None
        if user_id is not None:
            patron_waitlist_position = (
                await book_club_service.get_patron_waitlist_position(
                    club.id, user_id, db
                )
            )

        return BookClubDetail(
            id=club.id,
            name=club.name,
            description=club.description,
            meeting_frequency=club.meeting_frequency,
            member_count=member_count,
            max_members=club.max_members,
            current_member_count=member_count,
            waitlist_count=waitlist_count,
            is_full=is_full,
            patron_waitlist_position=patron_waitlist_position,
            is_member=is_member,
            created_at=club.created_at,
            members=members,
            upcoming_meetings=upcoming_meetings[:10],
        )

    @staticmethod
    async def join_club(
        club_id: int, user_id: int, db: Optional[AsyncSession] = None
    ) -> dict:
        if db is None:
            return {"status": "not_found", "position": None}

        club = (
            await db.execute(
                select(BookClub).where(
                    and_(
                        BookClub.id == club_id,
                        BookClub.status == BookClubStatus.active,
                    )
                )
            )
        ).scalars().first()
        if not club:
            return {"status": "not_found", "position": None}

        # Already a confirmed member?
        existing_member = await db.scalar(
            select(func.count())
            .select_from(BookClubMember)
            .where(
                BookClubMember.book_club_id == club_id,
                BookClubMember.user_id == user_id,
            )
        )
        if existing_member:
            return {"status": "already_member", "position": None}

        # Capacity check via scalar COUNT (eager-loaded list is stale
        # under concurrency).
        if await book_club_service.is_club_full(club, db):
            return await BookClubPatronService.add_to_waitlist(
                club_id=club_id, user_id=user_id, db=db, _club=club
            )

        db.add(
            BookClubMember(
                book_club_id=club_id,
                user_id=user_id,
                role=BookClubRole.member,
            )
        )
        await db.commit()
        return {"status": "joined", "position": None}

    @staticmethod
    async def add_to_waitlist(
        club_id: int,
        user_id: int,
        db: Optional[AsyncSession] = None,
        _club: Optional[BookClub] = None,
    ) -> dict:
        if db is None:
            return {"status": "not_found", "position": None}

        club = _club
        if club is None:
            club = (
                await db.execute(
                    select(BookClub).where(
                        and_(
                            BookClub.id == club_id,
                            BookClub.status == BookClubStatus.active,
                        )
                    )
                )
            ).scalars().first()
        if not club:
            return {"status": "not_found", "position": None}

        if club.max_members is None:
            # Uncapped: nothing to wait for.
            return {"status": "uncapped", "position": None}

        already_member = await db.scalar(
            select(func.count())
            .select_from(BookClubMember)
            .where(
                BookClubMember.book_club_id == club_id,
                BookClubMember.user_id == user_id,
            )
        )
        if already_member:
            return {"status": "already_member", "position": None}

        existing = await db.scalar(
            select(BookClubWaitlistEntry).where(
                BookClubWaitlistEntry.book_club_id == club_id,
                BookClubWaitlistEntry.user_id == user_id,
            )
        )
        if existing is not None:
            position = await book_club_service.get_patron_waitlist_position(
                club_id, user_id, db
            )
            return {"status": "already_waitlisted", "position": position}

        db.add(
            BookClubWaitlistEntry(book_club_id=club_id, user_id=user_id)
        )
        await db.commit()
        position = await book_club_service.get_patron_waitlist_position(
            club_id, user_id, db
        )
        return {"status": "waitlisted", "position": position}

    @staticmethod
    async def leave_waitlist(
        club_id: int, user_id: int, db: Optional[AsyncSession] = None
    ) -> bool:
        if db is None:
            return False
        entry = await db.scalar(
            select(BookClubWaitlistEntry).where(
                BookClubWaitlistEntry.book_club_id == club_id,
                BookClubWaitlistEntry.user_id == user_id,
            )
        )
        if entry is None:
            return False
        await db.delete(entry)
        await db.commit()
        return True

    @staticmethod
    async def leave_club(club_id: int, user_id: int, db: Optional[AsyncSession] = None) -> bool:
        if db is None:
            return False

        result = await db.execute(
            select(BookClubMember).where(
                and_(
                    BookClubMember.book_club_id == club_id,
                    BookClubMember.user_id == user_id,
                )
            )
        )
        member = result.scalars().first()
        if not member:
            return False

        await db.delete(member)
        await db.flush()
        # A seat opened — promote the oldest waitlisted patron (if any)
        # in the SAME transaction so capacity stays consistent.
        await book_club_service.promote_next_from_waitlist(club_id, db)
        await db.commit()
        return True

    @staticmethod
    async def list_discussions(
        club_id: int, meeting_id: int, db: Optional[AsyncSession] = None
    ) -> List[DiscussionThread]:
        if db is None:
            return []

        # Verify the meeting belongs to this club AND isn't archived
        # before disclosing any threads.
        meeting_row = await db.execute(
            select(BookClubMeeting).where(
                and_(
                    BookClubMeeting.id == meeting_id,
                    BookClubMeeting.book_club_id == club_id,
                    BookClubMeeting.is_archived.is_(False),
                )
            )
        )
        if meeting_row.scalars().first() is None:
            return []

        # selectinload BookClubDiscussion.author to avoid MissingGreenlet
        # on Pydantic serialization of author_name below.
        result = await db.execute(
            select(BookClubDiscussion)
            .where(BookClubDiscussion.meeting_id == meeting_id)
            .options(selectinload(BookClubDiscussion.author))
            .order_by(
                BookClubDiscussion.is_pinned.desc(),
                BookClubDiscussion.created_at.asc(),
            )
        )
        rows = result.scalars().all()

        threads: List[DiscussionThread] = []
        for d in rows:
            threads.append(DiscussionThread(
                id=d.id,
                meeting_id=d.meeting_id,
                user_id=d.user_id or 0,
                author_name=d.author_display_name or "",
                title=d.title,
                content=d.body,
                created_at=d.created_at,
                is_pinned=d.is_pinned,
                reply_count=0,
            ))
        return threads

    @staticmethod
    async def create_discussion(
        club_id: int,
        meeting_id: int,
        user_id: int,
        title: str,
        content: str,
        db: Optional[AsyncSession] = None,
    ) -> DiscussionThread:
        if db is None:
            return DiscussionThread(
                id=0,
                meeting_id=meeting_id,
                user_id=user_id,
                author_name="",
                title=title,
                content=content,
                created_at=datetime.now(timezone.utc),
            )

        meeting_row = await db.execute(
            select(BookClubMeeting).where(
                and_(
                    BookClubMeeting.id == meeting_id,
                    BookClubMeeting.book_club_id == club_id,
                )
            )
        )
        meeting = meeting_row.scalars().first()
        if meeting is None or meeting.is_archived:
            return DiscussionThread(
                id=0,
                meeting_id=meeting_id,
                user_id=user_id,
                author_name="",
                title=title,
                content=content,
                created_at=datetime.now(timezone.utc),
            )

        author_display = ""
        if user_id:
            user_row = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_row.scalars().first()
            if user is not None:
                author_display = (
                    f"{user.first_name or ''} {user.last_name or ''}".strip()
                    or user.email
                    or ""
                )

        discussion = BookClubDiscussion(
            meeting_id=meeting_id,
            user_id=user_id,
            author_display_name=author_display,
            title=title,
            body=content,
        )
        db.add(discussion)
        await db.commit()
        await db.refresh(discussion)

        return DiscussionThread(
            id=discussion.id,
            meeting_id=discussion.meeting_id,
            user_id=discussion.user_id or 0,
            author_name=discussion.author_display_name or "",
            title=discussion.title,
            content=discussion.body,
            created_at=discussion.created_at,
            is_pinned=discussion.is_pinned,
            reply_count=0,
        )

    @staticmethod
    async def list_replies(
        discussion_id: int, db: Optional[AsyncSession] = None
    ) -> List[DiscussionReply]:
        return []

    @staticmethod
    async def create_reply(
        discussion_id: int,
        user_id: int,
        content: str,
        db: Optional[AsyncSession] = None,
    ) -> DiscussionReply:
        return DiscussionReply(
            id=0,
            discussion_id=discussion_id,
            user_id=user_id,
            author_name="",
            content=content,
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    async def list_chat_messages(
        meeting_id: int, limit: int = 50, db: Optional[AsyncSession] = None
    ) -> List[ChatMessage]:
        return []

    @staticmethod
    async def get_meetings_for_ics(
        club_id: int, db: AsyncSession
    ) -> Optional[tuple[BookClub, list[BookClubMeeting]]]:
        club_result = await db.execute(
            select(BookClub).where(BookClub.id == club_id)
        )
        club = club_result.scalars().first()
        if not club:
            return None

        now = datetime.now(timezone.utc)
        meetings_result = await db.execute(
            select(BookClubMeeting)
            .where(
                and_(
                    BookClubMeeting.book_club_id == club_id,
                    BookClubMeeting.meeting_date >= now,
                    BookClubMeeting.status != DiscussionStatus.cancelled,
                    BookClubMeeting.is_archived.is_(False),
                )
            )
            .order_by(BookClubMeeting.meeting_date)
        )
        meetings = list(meetings_result.scalars().all())
        return club, meetings
