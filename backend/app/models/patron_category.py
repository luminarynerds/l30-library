# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, Column, Integer, String

from app.core.database import Base
from app.models.mixins import TimestampMixin


class PatronCategory(Base, TimestampMixin):

    __tablename__ = "patron_categories"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    label = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
