# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func

from ..core.database import Base


class PageMetaTag(Base):

    __tablename__ = "page_meta_tags"

    id = Column(Integer, primary_key=True, index=True)
    page_path = Column(String(500), nullable=False, unique=True)
    page_name = Column(String(200), nullable=False)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    keywords = Column(String(500), nullable=True)
    og_title = Column(String(500), nullable=True)
    og_description = Column(Text, nullable=True)
    og_image = Column(String(500), nullable=True)
    twitter_card = Column(String(50), default="summary_large_image")
    canonical_url = Column(String(500), nullable=True)
    robots = Column(String(100), default="index, follow")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
