# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import enum
from enum import Enum, StrEnum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum, JSON
from sqlalchemy.orm import relationship

from ..core.database import Base


class PodOrderStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PRINTING = "printing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PodTitleConfig(Base):
    __tablename__ = "pod_title_configs"

    id = Column(Integer, primary_key=True, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("indie_authors.id", ondelete="CASCADE"), nullable=False, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    list_price_cents = Column(Integer, nullable=False)
    cost_price_cents = Column(Integer, nullable=True)
    binding_type = Column(String(30), default="paperback", nullable=False)
    interior_type = Column(String(20), default="bw", nullable=False)
    trim_size = Column(String(20), default="6x9", nullable=False)
    paper_type = Column(String(20), default="cream", nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    lulu_printable_id = Column(String(100), nullable=True)
    cover_file_url = Column(String(500), nullable=True)
    page_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))



class PodOrder(Base):
    __tablename__ = "pod_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    pod_config_id = Column(Integer, ForeignKey("pod_title_configs.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(PodOrderStatus, values_callable=lambda x: [m.value for m in x]), default=PodOrderStatus.PENDING, nullable=False, index=True)
    list_price_cents = Column(Integer, nullable=False)
    print_cost_cents = Column(Integer, nullable=True)
    shipping_cost_cents = Column(Integer, nullable=True)
    author_royalty_cents = Column(Integer, nullable=True)
    library_share_cents = Column(Integer, nullable=True)
    lulu_order_id = Column(String(100), nullable=True)
    tracking_number = Column(String(200), nullable=True)
    tracking_url = Column(String(500), nullable=True)
    shipping_address = Column(JSON, nullable=False)
    stripe_payment_intent_id = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    shipped_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="pod_orders")
    pod_config = relationship("PodTitleConfig")
