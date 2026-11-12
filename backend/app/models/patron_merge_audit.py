# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class PatronMergeAudit(Base, TimestampMixin):
    __tablename__ = "patron_merge_audits"

    id = Column(Integer, primary_key=True, index=True)

    # The patron account that was kept (merged into)
    primary_patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True
    )

    # The patron account that was deleted (merged from)
    # Stored as nullable since the user is deleted after merge
    secondary_patron_id = Column(Integer, nullable=False, index=True)

    # Staff member who performed the merge
    merged_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True
    )

    # Timestamp of the merge operation
    merged_at = Column(
        DateTime(timezone=True),
        index=True
    )

    # JSON containing details of what data was transferred
    # Structure: {
    #     "checkouts": [{"id": 1, "item_id": 2, ...}, ...],
    #     "holds": [{"id": 1, "item_id": 2, ...}, ...],
    #     "fines": [{"id": 1, "amount": "10.00", ...}, ...],
    #     "reading_lists": [{"id": 1, "name": "...", "items": [...], ...], ...],
    #     "favorites": [{"id": 1, "catalog_item_id": 2, ...}, ...]
    # }
    data_transferred = Column(JSON, nullable=True)

    # JSON snapshot of the secondary patron's data before deletion
    # Structure: {
    #     "user": {"id": 1, "email": "...", "first_name": "...", ...},
    #     "checkouts": [...],
    #     "holds": [...],
    #     "fines": [...],
    #     "reading_lists": [...],
    #     "favorites": [...],
    #     "notification_preferences": {...}
    # }
    data_archived = Column(JSON, nullable=True)

    # Summary counts for quick reference
    checkouts_transferred = Column(Integer, default=0, nullable=False)
    holds_transferred = Column(Integer, default=0, nullable=False)
    fines_transferred = Column(Integer, default=0, nullable=False)
    reading_lists_transferred = Column(Integer, default=0, nullable=False)
    favorites_transferred = Column(Integer, default=0, nullable=False)

    # Additional context/notes
    notes = Column(Text, nullable=True)

    # IP address and user agent for security tracking
    ip_address = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    primary_patron = relationship(
        "User",
        foreign_keys=[primary_patron_id],
        backref="merge_audits_as_primary"
    )
    merged_by = relationship(
        "User",
        foreign_keys=[merged_by_id],
        backref="patron_merges_performed"
    )

    def __repr__(self) -> str:
        return (
            f"<PatronMergeAudit(id={self.id}, "
            f"primary={self.primary_patron_id}, "
            f"secondary={self.secondary_patron_id}, "
            f"merged_at={self.merged_at})>"
        )

    @property
    def total_items_transferred(self) -> int:
        return (
            self.checkouts_transferred +
            self.holds_transferred +
            self.fines_transferred +
            self.reading_lists_transferred +
            self.favorites_transferred
        )
