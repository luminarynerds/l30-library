# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class BanType(StrEnum):
    CHALLENGED = "challenged"
    RESTRICTED = "restricted"
    BANNED = "banned"
    PENDING = "pending"


class BanSource(StrEnum):
    PEN_AMERICA = "pen_america"
    ALA = "ala"
    STAFF_ENTRY = "staff_entry"
    NEWS = "news"


class BanReport(TimestampMixin, Base):

    __tablename__ = "ban_reports"

    id = Column(Integer, primary_key=True, index=True)
    isbn = Column(String(20), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    author = Column(String(500), nullable=False)
    state = Column(String(2), nullable=True, index=True)
    county = Column(String(200), nullable=True)
    district = Column(String(500), nullable=True)
    institution = Column(String(500), nullable=True)
    ban_type = Column(
        SQLEnum(BanType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=BanType.CHALLENGED,
    )
    reason = Column(Text, nullable=True)
    reason_category = Column(String(100), nullable=True)
    source = Column(SQLEnum(BanSource, values_callable=lambda x: [e.value for e in x]), nullable=False)
    source_url = Column(String(1000), nullable=True)
    date_reported = Column(Date, nullable=True)
    date_enacted = Column(Date, nullable=True)
    catalog_match_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    matched_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    catalog_match = relationship("CatalogItem", back_populates=None)
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates=None)
    alerts = relationship(
        "BanAlertNotification",
        back_populates="ban_report",
        cascade="all, delete-orphan",
    )


class BanAlertNotification(TimestampMixin, Base):

    __tablename__ = "ban_alert_notifications"

    id = Column(Integer, primary_key=True, index=True)
    ban_report_id = Column(
        Integer,
        ForeignKey("ban_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seen_at = Column(DateTime(timezone=True), nullable=True)
    emailed_at = Column(DateTime(timezone=True), nullable=True)

    ban_report = relationship("BanReport", back_populates="alerts")
    user = relationship("User", back_populates=None)


class AdvocacyLetterTemplate(TimestampMixin, Base):

    __tablename__ = "advocacy_letter_templates"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    subject_line = Column(String(500), nullable=False)
    body_template = Column(Text, nullable=False)
    target_level = Column(String(20), nullable=False, default="any")
    is_active = Column(Boolean, nullable=False, default=True)


class BanTrackerSubscription(TimestampMixin, Base):

    __tablename__ = "ban_tracker_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 'any' | 'state' | 'catalog'. 'catalog' means "only when a ban
    # report has a catalog_match_id" — see digest worker (phase 3).
    scope = Column(String(32), nullable=False)
    # Required when scope='state'; enforced at the Pydantic layer so
    # the user sees a 422 with a useful message instead of a generic
    # CHECK violation.
    state_filter = Column(String(2), nullable=True)
    # Optional narrowing within any scope.
    ban_type_filter = Column(String(32), nullable=True)
    frequency = Column(String(16), nullable=False, default="weekly")
    is_active = Column(Boolean, nullable=False, default=True)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    unsubscribe_token = Column(String(64), nullable=False, unique=True, index=True)

    user = relationship("User", foreign_keys=[user_id], back_populates=None)
