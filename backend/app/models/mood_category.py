# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.database import Base
from app.models.mixins import TimestampMixin


class MoodCategory(Base, TimestampMixin):
    __tablename__ = "mood_categories"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(120), nullable=False)
    slug = Column(String(60), nullable=False, unique=True, index=True)
    icon = Column(String(60), nullable=False)
    tags = Column(ARRAY(Text()), nullable=False, server_default="{}")
    keywords = Column(ARRAY(Text()), nullable=False, server_default="{}")
    display_order = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")
