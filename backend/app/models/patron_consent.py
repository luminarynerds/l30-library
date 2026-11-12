# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class PatronConsent(Base):

    __tablename__ = "patron_consents"

    # BigInteger so prod (Postgres) gets BIGSERIAL room to grow; the
    # SQLite variant falls back to INTEGER so test DBs autoincrement
    # correctly. Without ``with_variant`` SQLite treats BIGINT as a
    # non-rowid type and ``INSERT`` violates NOT NULL on ``id``.
    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        index=True,
        autoincrement=True,
    )
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Kept as plain VARCHAR rather than an Enum so adding a new consent
    # kind ships in one PR (no migration). Validated at the schema layer.
    consent_type = Column(String(64), nullable=False, index=True)
    granted = Column(Boolean, nullable=False)
    recorded_by_staff_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    recorded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    patron = relationship("User", foreign_keys=[patron_id])
    recorded_by = relationship("User", foreign_keys=[recorded_by_staff_id])

    __table_args__ = (
        Index("ix_patron_consents_patron_id", "patron_id"),
        Index("ix_patron_consents_consent_type", "consent_type"),
        # NOTE: the active-row uniqueness is enforced by a partial unique
        # index (``uq_patron_consents_active``) declared in the alembic
        # migration; SQLAlchemy can't express partial unique constraints
        # in a portable way, so it lives in DDL only.
    )
