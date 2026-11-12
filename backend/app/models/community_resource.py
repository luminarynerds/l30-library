# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY

from ..core.database import Base
from .mixins import TimestampMixin


class CommunityResourceLink(Base, TimestampMixin):

    __tablename__ = "community_resource_links"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    category_label = Column(String(100), nullable=False)
    page_contexts = Column(ARRAY(String(50)), nullable=False)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    icon_hint = Column(String(50), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=False)
    source = Column(String(20), nullable=False, default="manual")
