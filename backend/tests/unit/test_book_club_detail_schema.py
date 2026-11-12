"""Asserts BookClubDetail.members defaults to None (roster hidden)."""
from datetime import datetime, timezone

from app.schemas.book_club_patron import BookClubDetail, BookClubMemberInfo


def test_book_club_detail_members_defaults_to_none():
    """Anonymous detail responses MUST omit roster (members=None, not [])."""
    detail = BookClubDetail(
        id=1,
        name="Mystery Lovers",
        member_count=7,
        max_members=12,
        created_at=datetime.now(timezone.utc),
    )
    assert detail.members is None
    dumped = detail.model_dump()
    assert dumped["members"] is None


def test_book_club_detail_members_accepts_list():
    """Authenticated detail responses populate members as a list."""
    detail = BookClubDetail(
        id=1,
        name="Mystery Lovers",
        member_count=1,
        created_at=datetime.now(timezone.utc),
        members=[
            BookClubMemberInfo(
                id=1,
                user_id=42,
                display_name="J. Ruiz",
                joined_at=datetime.now(timezone.utc),
                role="admin",
            )
        ],
    )
    assert detail.members is not None
    assert len(detail.members) == 1
    assert detail.members[0].role == "admin"
