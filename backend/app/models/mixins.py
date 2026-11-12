# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime, Integer, ForeignKey, Boolean, String, event, func
from sqlalchemy.orm import declared_attr, relationship


class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, "before_update", cls._touch_updated_at, propagate=True)

    @staticmethod
    def _touch_updated_at(mapper, connection, target):
        target.updated_at = datetime.now(timezone.utc)


class AuditMixin:
    @declared_attr
    def created_by_id(cls):
        return Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    @declared_attr
    def created_by(cls):
        return relationship("User", foreign_keys=[cls.created_by_id])


class SoftDeleteMixin:

    @declared_attr
    def is_deleted(cls):
        return Column(Boolean, default=False, index=True)

    @declared_attr
    def deleted_at(cls):
        return Column(DateTime(timezone=True), nullable=True)

    @declared_attr
    def deleted_by_user_id(cls):
        return Column(
            Integer,
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True
        )

    @declared_attr
    def deletion_reason(cls):
        return Column(String(500), nullable=True)

    def soft_delete(self, user_id: Optional[int] = None, reason: Optional[str] = None) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by_user_id = user_id
        self.deletion_reason = reason

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by_user_id = None
        self.deletion_reason = None

    def is_soft_deleted(self) -> bool:
        return self.is_deleted is True
