# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .mixins import TimestampMixin


class SavedSearch(Base, TimestampMixin):

    __tablename__ = "saved_searches"

    # UUID PK keeps the URL/id space distinct from integer-keyed resources
    # (patrons cannot infer or enumerate other users' searches).
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        default=uuid.uuid4,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # NOTE on multi-tenancy: the L30 catalog is currently single-library
    # (CatalogItem has no library_id FK), so tenant scoping is enforced by
    # the user-id check alone. ``library_system_id`` is kept here as an
    # optional column so it lights up correctly the day the catalog grows
    # a tenant FK; until then it stays NULL and the API never reads it.
    library_system_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filters_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}", default=dict
    )
    sort_by: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    view_mode: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    notify_on_new: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    notify_in_app: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", default=True
    )
    notify_email: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )

    last_notified_item_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # `user` relationship kept passive; routes load SavedSearch from the
    # patron's own session and never serialize the user object.
    user = relationship("User", lazy="select")

    __table_args__ = (
        Index(
            "ix_saved_searches_user_created",
            "user_id",
            "created_at",
        ),
        # Partial index keeps the notifier's nightly scan cheap as the table
        # grows: only rows actually opted in to alerts get walked.
        Index(
            "ix_saved_searches_notify_on_new",
            "notify_on_new",
            postgresql_where="notify_on_new = true",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<SavedSearch id={self.id} user_id={self.user_id} "
            f"name={self.name!r} notify_on_new={self.notify_on_new}>"
        )
