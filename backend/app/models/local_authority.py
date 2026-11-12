# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base
from ..core.enum_helpers import EnumColumn


class LocalAuthorityType(StrEnum):
    name_personal = "name_personal"
    name_corporate = "name_corporate"
    name_meeting = "name_meeting"
    name_jurisdiction = "name_jurisdiction"
    subject_topic = "subject_topic"
    subject_geographic = "subject_geographic"
    subject_temporal = "subject_temporal"
    subject_genre = "subject_genre"
    title_uniform = "title_uniform"
    title_series = "title_series"
    other = "other"


class LocalAuthorityStatus(StrEnum):
    provisional = "provisional"  # awaiting cataloger review
    active = "active"
    deprecated = "deprecated"    # superseded by use_instead


class LocalAuthority(Base):
    __tablename__ = "bibframe_local_authorities"

    id = Column(Integer, primary_key=True, index=True)

    library_system_id = Column(
        Integer,
        ForeignKey("library_systems.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    authority_type = EnumColumn(LocalAuthorityType, nullable=False, index=True)
    status = EnumColumn(LocalAuthorityStatus, nullable=False, index=True)

    label = Column(String(500), nullable=False)
    label_normalized = Column(String(500), nullable=False, index=True)

    scope_note = Column(Text, nullable=True)
    source_notes = Column(Text, nullable=True)

    variants = Column(JSONB, nullable=True)
    related_authorities = Column(JSONB, nullable=True)
    external_links = Column(JSONB, nullable=True)

    use_instead_id = Column(
        Integer,
        ForeignKey("bibframe_local_authorities.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    use_instead = relationship("LocalAuthority", remote_side=[id])

    __table_args__ = (
        UniqueConstraint(
            "library_system_id",
            "authority_type",
            "label_normalized",
            name="uq_local_authority_heading",
        ),
        Index("ix_local_authority_label_normalized", "label_normalized"),
    )

    def __repr__(self) -> str:
        return f"<LocalAuthority(id={self.id}, type={self.authority_type}, label={self.label!r})>"
