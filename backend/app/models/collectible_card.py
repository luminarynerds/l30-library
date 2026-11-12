# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Text, Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum, StrEnum

from ..core.database import Base


class CardEdition(StrEnum):
    STANDARD = "standard"
    LIMITED = "limited"
    SIGNED = "signed"
    FOUNDERS = "founders"


class CollectibleCard(Base):
    __tablename__ = "collectible_cards"

    id = Column(Integer, primary_key=True, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("digital_access_orders.id", ondelete="SET NULL"), nullable=True)
    serial_number = Column(String(50), unique=True, nullable=False, index=True)
    edition = Column(SQLEnum(CardEdition, name="card_edition", values_callable=lambda x: [e.value for e in x]), default=CardEdition.STANDARD, nullable=False)
    is_signed = Column(Boolean, default=False, nullable=False)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    print_count = Column(Integer, default=0, nullable=False)
    cached_title = Column(String(500), nullable=False)
    cached_author_name = Column(String(255), nullable=False)
    cached_cover_url = Column(String(500), nullable=True)
    qr_url = Column(String(500), nullable=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", backref="collectible_cards")
