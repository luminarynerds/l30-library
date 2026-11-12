# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base


class IndieAuthor(Base):
    __tablename__ = "indie_authors"

    id = Column(Integer, primary_key=True, index=True)
    pen_name = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    profile_image_url = Column(String(500), nullable=True)
