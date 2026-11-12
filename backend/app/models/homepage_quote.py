# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, Column, Index, Integer, String, Text

from app.core.database import Base
from app.models.mixins import TimestampMixin


class HomepageQuote(Base, TimestampMixin):

    __tablename__ = "homepage_quotes"

    id = Column(Integer, primary_key=True, index=True)
    locale = Column(String(8), nullable=False, index=True)
    quote_text = Column(Text, nullable=False)
    attribution = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    display_order = Column(Integer, nullable=False, default=0, server_default="0")

    __table_args__ = (
        Index(
            "ix_homepage_quotes_locale_active_order",
            "locale",
            "is_active",
            "display_order",
        ),
    )

    def __repr__(self) -> str:
        return f"<HomepageQuote id={self.id} locale={self.locale}>"
