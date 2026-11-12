# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, Text, DateTime, CheckConstraint, JSON
from sqlalchemy.sql import func

from ..core.database import Base


class LibraryBranding(Base):
    __tablename__ = "library_branding"
    __table_args__ = (
        CheckConstraint("id = 1", name="singleton_branding"),
    )

    id = Column(Integer, primary_key=True, default=1)
    library_name = Column(String(255), nullable=False, default="My Library")
    library_short_name = Column(String(50), default="")
    domain = Column(String(255), default="")
    contact_email = Column(String(255), default="")
    privacy_email = Column(String(255), default="")
    indie_email = Column(String(255), default="")
    giving_email = Column(String(255), default="")
    phone = Column(String(50), default="")
    address_line1 = Column(String(255), default="")
    address_line2 = Column(String(255), default="")
    primary_color = Column(String(7), default="#E89B44")
    accent_color = Column(String(7), default="#8B5E5E")
    secondary_color = Column(String(7), default="")
    surface_color = Column(String(7), default="")
    ink_color = Column(String(7), default="")
    card_prefix = Column(String(10), default="LIB")
    logo_url = Column(String(500), default="")
    hero_image_url = Column(String(500), default="")
    display_font = Column(String(120), default="")
    body_font = Column(String(120), default="")
    nav_style = Column(String(30), default="default")
    hero_title = Column(String(500), default="")
    hero_subtitle = Column(String(500), default="You belong here.")
    tagline = Column(String(255), default="")
    # Structured donate-page content (tiers, impact areas, monthly, ways-to-give,
    # intro, testimonials, tax note). Null/empty => donate page hides configurable
    # sections. See DonatePage.tsx DonateConfig for the shape.
    donate_config = Column(JSON, nullable=True)
    # About page "Our Story" timeline: {"timeline": [{"year","title","description"}]}
    # Null -> the frontend keeps its stock i18n timeline.
    about_story = Column(JSON, nullable=True)
    # Sensory / ND access info shown on the public homepage. All three are
    # optional -- NULL hides the field entirely (no empty placeholders shown).
    quiet_hours = Column(Text, nullable=True)
    sensory_friendly_times = Column(Text, nullable=True)
    low_stim_seating = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
