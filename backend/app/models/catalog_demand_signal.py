# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class DemandSignalType(StrEnum):
    FAILED_SEARCH = "failed_search"
    ILL_REQUEST = "ill_request"
    PEAK_HOLD_DEPTH = "peak_hold_depth"
    AGENT_UNFOUND = "agent_unfound"


class DemandSignalResolution(StrEnum):
    ACQUIRED = "acquired"
    ILL = "ill"
    NO_ACTION = "no_action"


class CatalogDemandSignal(Base):
    __tablename__ = "catalog_demand_signals"

    id = Column(Integer, primary_key=True, index=True)
    # Stored as the underlying pg enum value (lowercase per L30
    # convention); ``String(32)`` keeps the model SQLite-compatible.
    signal_type = Column(String(32), nullable=False, index=True)
    normalized_title = Column(String(500), nullable=True)
    normalized_isbn = Column(String(20), nullable=True)
    normalized_subject = Column(String(255), nullable=True)
    query_text = Column(Text, nullable=True)
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recorded_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution = Column(String(32), nullable=True)
    # Column name 'metadata' is reserved at the SQLAlchemy ORM level
    # (``Base.metadata``); we pin the DB column name explicitly while
    # the Python attribute is renamed.
    metadata_ = Column("metadata", JSON, nullable=False, server_default="{}")

    patron = relationship("User", lazy="raise")

    __table_args__ = (
        Index(
            "ix_demand_signals_type_recorded",
            "signal_type",
            "recorded_at",
        ),
    )
