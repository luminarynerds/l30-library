# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.mixins import TimestampMixin

from ..core.database import Base


class AuthorityTerm(Base, TimestampMixin):
    __tablename__ = "authority_terms"

    id = Column(Integer, primary_key=True)
    term = Column(String(500), nullable=False)
    normalized_term = Column(String(500), nullable=False)
    term_type = Column(String(40), nullable=False)
    scope_note = Column(Text, nullable=True)
    is_preferred = Column(Boolean, nullable=False, server_default="true", default=True)

    outgoing_relations = relationship(
        "AuthorityTermRelation",
        foreign_keys="AuthorityTermRelation.term_id",
        back_populates="term",
        cascade="all, delete-orphan",
    )
    incoming_relations = relationship(
        "AuthorityTermRelation",
        foreign_keys="AuthorityTermRelation.related_term_id",
        back_populates="related_term",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("term_type", "term", name="uq_authority_terms_type_term"),
        Index("ix_authority_terms_type_normalized", "term_type", "normalized_term"),
    )


class AuthorityTermRelation(Base):
    __tablename__ = "authority_term_relations"

    id = Column(Integer, primary_key=True)
    term_id = Column(Integer, ForeignKey("authority_terms.id", ondelete="CASCADE"), nullable=False)
    related_term_id = Column(Integer, ForeignKey("authority_terms.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(20), nullable=False)

    term = relationship(
        "AuthorityTerm", foreign_keys=[term_id], back_populates="outgoing_relations"
    )
    related_term = relationship(
        "AuthorityTerm", foreign_keys=[related_term_id], back_populates="incoming_relations"
    )

    __table_args__ = (
        CheckConstraint("term_id <> related_term_id", name="ck_authority_relation_no_self_loop"),
        UniqueConstraint(
            "term_id", "related_term_id", "relation_type",
            name="uq_authority_relations_edge",
        ),
        Index("ix_authority_relations_term_type", "term_id", "relation_type"),
        Index("ix_authority_relations_related_type", "related_term_id", "relation_type"),
    )


RELATION_TYPES = frozenset({"see_also", "broader", "narrower", "use_for"})
TERM_TYPES = frozenset({"subject", "author", "series", "genre", "geographic"})
