# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.mixins import TimestampMixin

from ..core.database import Base


class EventProgramPartner(Base, TimestampMixin):
    __tablename__ = "event_program_partners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    # Lowercase snake-cased slug derived from name on create. Stable identifier
    # for URL slugs / external integrations.
    slug = Column(String(200), nullable=False, unique=True)
    website = Column(String(500), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    # Soft-delete flag. DELETE endpoint flips this to False unless force=true.
    is_active = Column(Boolean, default=True, nullable=False, server_default="true", index=True)

    # Back-pop from Event.program_partner (declared on Event side).
    events = relationship("Event", back_populates="program_partner")
