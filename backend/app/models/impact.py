# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship

from ..core.database import Base
from .mixins import TimestampMixin


# Enum value sets — keep in sync with ``schemas/impact.py`` and the
# CHECK constraints below.
DIRECTION_BETTER_VALUES = ("up", "down")
CADENCE_VALUES = ("monthly", "quarterly", "semi_annual", "annual")
GEOGRAPHIC_SCOPE_VALUES = (
    "census_tract",
    "school_district",
    "zip",
    "county",
    "service_area",
    "custom",
)
EVIDENCE_STRENGTH_VALUES = (
    "theoretical",
    "program_aligned",
    "outcome_correlated",
    "quasi_experimental",
    "experimental",
)


class OutcomeIndicator(Base, TimestampMixin):

    __tablename__ = "outcome_indicators"

    id = Column(Integer, primary_key=True, index=True)

    slug = Column(String(120), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    unit = Column(String(40), nullable=False)
    direction_better = Column(String(8), nullable=False)
    cadence = Column(String(16), nullable=False)
    geographic_scope_type = Column(String(24), nullable=False)

    primary_source = Column(String(255), nullable=True)
    source_url = Column(String(500), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    requires_board_approval = Column(Boolean, nullable=False, default=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    board_decision_link_id = Column(
        Integer,
        ForeignKey("board_decision_links.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    claims = relationship(
        "TheoryOfChangeClaim",
        back_populates="indicator",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "direction_better IN ('up', 'down')",
            name="ck_outcome_indicator_direction_better",
        ),
        CheckConstraint(
            "cadence IN ('monthly', 'quarterly', 'semi_annual', 'annual')",
            name="ck_outcome_indicator_cadence",
        ),
        CheckConstraint(
            "geographic_scope_type IN ('census_tract', 'school_district',"
            " 'zip', 'county', 'service_area', 'custom')",
            name="ck_outcome_indicator_geographic_scope_type",
        ),
        Index(
            "ix_outcome_indicators_active_scope",
            "is_active",
            "geographic_scope_type",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<OutcomeIndicator slug={self.slug!r} "
            f"approved={self.approved_at is not None}>"
        )


class TheoryOfChangeClaim(Base, TimestampMixin):

    __tablename__ = "theory_of_change_claims"

    id = Column(Integer, primary_key=True, index=True)

    outcome_indicator_id = Column(
        Integer,
        ForeignKey("outcome_indicators.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    contributing_program_id = Column(
        Integer, ForeignKey("programs.id", ondelete="SET NULL"), nullable=True
    )
    contributing_initiative_id = Column(
        Integer,
        ForeignKey("strategic_initiatives.id", ondelete="SET NULL"),
        nullable=True,
    )

    mechanism_short = Column(String(280), nullable=False)
    mechanism_detail = Column(Text, nullable=False)

    evidence_strength = Column(String(24), nullable=False, default="theoretical")
    evidence_citations = Column(Text, nullable=True)

    intended_dose = Column(String(255), nullable=True)
    expected_lag = Column(String(120), nullable=True)

    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    next_review_due = Column(Date, nullable=True)

    board_decision_link_id = Column(
        Integer,
        ForeignKey("board_decision_links.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active = Column(Boolean, nullable=False, default=True)
    retired_at = Column(DateTime(timezone=True), nullable=True)
    retired_reason = Column(Text, nullable=True)

    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    indicator = relationship("OutcomeIndicator", back_populates="claims")
    program = relationship("Program", foreign_keys=[contributing_program_id])
    initiative = relationship(
        "StrategicInitiative", foreign_keys=[contributing_initiative_id]
    )
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])

    __table_args__ = (
        CheckConstraint(
            "(contributing_program_id IS NULL) <> (contributing_initiative_id IS NULL)",
            name="ck_claim_program_xor_initiative",
        ),
        CheckConstraint(
            "evidence_strength IN ('theoretical', 'program_aligned',"
            " 'outcome_correlated', 'quasi_experimental', 'experimental')",
            name="ck_claim_evidence_strength",
        ),
        Index(
            "ix_theory_of_change_claims_indicator_active",
            "outcome_indicator_id",
            "is_active",
        ),
        Index(
            "ix_theory_of_change_claims_next_review",
            "next_review_due",
            postgresql_where=text("is_active = true"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TheoryOfChangeClaim id={self.id} "
            f"indicator={self.outcome_indicator_id} "
            f"evidence={self.evidence_strength}>"
        )
