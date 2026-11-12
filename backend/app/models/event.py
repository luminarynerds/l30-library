# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base


class Event(Base, TimestampMixin):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "min_age IS NULL OR max_age IS NULL OR min_age <= max_age",
            name="ck_events_age_range_valid",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)

    location = Column(String(255), nullable=True)
    is_virtual = Column(Boolean, default=False)
    virtual_link = Column(String(500), nullable=True)

    audience = Column(
        String(100), nullable=True
    )  # e.g., "All ages", "Adults", "Children"
    category = Column(
        String(100), nullable=True
    )  # e.g., "Book Club", "Story Time", "Workshop"

    # Language the program is conducted in, as an ISO 639-1 code ("es", "zh").
    # NULL = unspecified (most events; historically English-default). Distinct
    # from the ASL accessibility flag — this is the spoken program language.
    event_language = Column(String(20), nullable=True, index=True)

    # Tags for granular filtering (e.g., "crafts", "stem", "music", "outdoor")
    tags = Column(ARRAY(String(50)), nullable=True, default=list)

    max_attendees = Column(Integer, nullable=True)
    registration_required = Column(Boolean, default=False)

    # Actual attendance recorded after the event. Nullable on purpose:
    # NULL means "staff hasn't entered a number yet"; 0 means "nobody came".
    # Mirrors Program.actual_attendance for the events path used in PLS/IMLS
    # reporting (see usage_statistics_service.generate_program_statistics).
    attended_count = Column(Integer, nullable=True, default=None)

    image_url = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=True)

    # Featured events support - displayed prominently at the top
    is_featured = Column(Boolean, default=False, index=True)

    # Series/recurring events grouping
    # Events with the same series_id are grouped together (e.g., "Summer Reading Week 1, 2, 3")
    series_id = Column(String(100), nullable=True, index=True)
    series_name = Column(String(255), nullable=True)  # Display name for the series

    # Social sharing metrics
    share_count = Column(Integer, default=0, nullable=False)

    # Event type — "standard" for regular events, "ama" for Author AMA sessions
    event_type = Column(String(50), nullable=False, default="standard", index=True)

    # MetisLib AMA session reference (only when event_type == "ama")
    metislib_ama_session_id = Column(Integer, nullable=True)

    # Indie author link (engagement platform)
    indie_author_id = Column(Integer, ForeignKey("indie_authors.id", ondelete="SET NULL"), nullable=True, index=True)
    indie_author = relationship("IndieAuthor", foreign_keys=[indie_author_id])

    # Branch hosting this event. SET NULL on branch delete so historical
    # events survive a branch closure without cascading deletion.
    branch_id = Column(
        Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Accessibility flags — surfaced on the public event detail page so
    # patrons can see what's already provided without contacting staff.
    wheelchair_accessible = Column(Boolean, default=False, nullable=False, server_default="false")
    asl_provided = Column(Boolean, default=False, nullable=False, server_default="false")
    captioning_provided = Column(Boolean, default=False, nullable=False, server_default="false")
    assistive_listening = Column(Boolean, default=False, nullable=False, server_default="false")
    sensory_friendly = Column(Boolean, default=False, nullable=False, server_default="false")
    large_print_available = Column(Boolean, default=False, nullable=False, server_default="false")
    accessibility_notes = Column(Text, nullable=True)

    # ------------------------------------------------------------------
    # Recurrence, presenters, partner orgs, photo-release, age range
    # ------------------------------------------------------------------

    # RFC 5545 RRULE string (e.g., "FREQ=WEEKLY;BYDAY=TU;UNTIL=20260815T120000Z").
    # When set, GET endpoints (deferred to a follow-up PR) will expand virtual
    # instances within a requested window using app.services.event_recurrence.
    recurrence_rule = Column(Text, nullable=True)

    # Self-FK for one-off override instances of a recurring series. Cascade so
    # deleting the parent removes orphaned overrides.
    parent_event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    parent = relationship(
        "Event",
        remote_side="Event.id",
        back_populates="overrides",
        foreign_keys=[parent_event_id],
    )
    overrides = relationship(
        "Event",
        back_populates="parent",
        foreign_keys=[parent_event_id],
        cascade="all, delete-orphan",
    )

    # Inline presenters array: [{name, bio?, fee?, program_partner_id?}].
    # Kept as JSONB to avoid a separate join table for a low-cardinality list.
    presenters = Column(JSONB, nullable=True)

    # Primary program partner for the event. SET NULL on delete so the
    # event survives a partner soft/hard delete without cascading.
    program_partner_id = Column(
        Integer,
        ForeignKey("event_program_partners.id", ondelete="SET NULL"),
        nullable=True,
    )
    program_partner = relationship(
        "EventProgramPartner",
        back_populates="events",
        foreign_keys=[program_partner_id],
    )

    # Photo-release: when True, patrons are prompted to consent on registration.
    photos_will_be_taken = Column(
        Boolean, default=False, nullable=False, server_default="false"
    )

    # Age-range targeting (inclusive). DB-level CHECK enforces min <= max.
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)

    # If True, attending patrons must be accompanied by a caregiver (typically
    # used in conjunction with min_age for young-children events).
    caregiver_required = Column(
        Boolean, default=False, nullable=False, server_default="false"
    )

    # ------------------------------------------------------------------
    # Structured sensory descriptors
    # ------------------------------------------------------------------
    # Let sensory-sensitive patrons pre-assess an event without having to
    # email staff. NULL means "staff have not specified it". The string
    # columns are validated against a fixed lowercase vocabulary by the
    # Pydantic input schemas — not the DB — so a historical bad row never
    # 500s the list endpoint.
    lighting = Column(String(20), nullable=True)  # dim | moderate | bright
    noise_level = Column(String(20), nullable=True)  # quiet | moderate | lively
    crowd_size = Column(String(20), nullable=True)  # small | medium | large
    quiet_space_available = Column(
        Boolean, default=False, nullable=False, server_default="false"
    )
