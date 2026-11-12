# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import SoftDeleteMixin, TimestampMixin


class EntityType(StrEnum):
    CHECKOUT = "checkout"
    HOLD = "hold"
    FINE = "fine"
    CATALOG_ITEM = "catalog_item"
    ITEM_COPY = "item_copy"
    USER = "user"
    READING_LIST = "reading_list"
    LEARNING_PATH = "learning_path"
    ROOM_RESERVATION = "room_reservation"
    EQUIPMENT_CHECKOUT = "equipment_checkout"
    EVENT = "event"
    SETTINGS = "settings"


class ChangeType(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    MERGE = "merge"


class VersionHistory(Base, TimestampMixin):
    __tablename__ = "version_history"

    id = Column(Integer, primary_key=True, index=True)

    # Entity identification
    entity_type = Column(SQLEnum(EntityType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)

    # Change tracking
    change_type = Column(SQLEnum(ChangeType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    version_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.

    # Who made the change and context
    changed_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # What changed
    # Store full entity state for point-in-time restoration
    entity_state = Column(JSON, nullable=True)  # Complete entity snapshot

    # Field-level changes (only what changed)
    # Format: {"field_name": {"old": value, "new": value, "type": "string|int|bool|datetime"}}
    changes = Column(JSON, nullable=True)

    # Soft delete tracking
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    deletion_reason = Column(String(500), nullable=True)

    # Additional context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    change_reason = Column(String(500), nullable=True)  # Why was this changed?

    # Timestamps

    # Relationships
    changed_by = relationship(
        "User",
        foreign_keys=[changed_by_user_id],
        backref="version_history_created"
    )
    deleted_by = relationship(
        "User",
        foreign_keys=[deleted_by_user_id],
        backref="version_history_deleted"
    )

    def __repr__(self) -> str:
        return (
            f"<VersionHistory(id={self.id}, entity_type={self.entity_type}, "
            f"entity_id={self.entity_id}, version={self.version_number}, "
            f"change_type={self.change_type})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type.value if self.entity_type else None,
            "entity_id": self.entity_id,
            "change_type": self.change_type.value if self.change_type else None,
            "version_number": self.version_number,
            "changed_by_user_id": self.changed_by_user_id,
            "entity_state": self.entity_state,
            "changes": self.changes,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "deletion_reason": self.deletion_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
