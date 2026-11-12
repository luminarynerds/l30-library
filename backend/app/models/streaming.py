# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from decimal import Decimal
from enum import StrEnum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class StreamingService(PyEnum):
    PALACE = "palace"
    KANOPY = "kanopy"
    HOOPLA = "hoopla"


class StreamingContentType(PyEnum):
    MOVIE = "movie"
    TV_SERIES = "tv_series"
    TV_EPISODE = "tv_episode"
    AUDIOBOOK = "audiobook"
    EBOOK = "ebook"
    MUSIC_ALBUM = "music_album"
    COMIC = "comic"
    DOCUMENTARY = "documentary"


class StreamingCheckoutStatus(PyEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    RETURNED = "returned"


class StreamingServiceConfig(Base):
    __tablename__ = "streaming_service_configs"

    id = Column(Integer, primary_key=True, index=True)
    service = Column(Enum(StreamingService, values_callable=lambda x: [m.value for m in x]), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    api_base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=True)  # Encrypted in production
    api_secret = Column(String(500), nullable=True)  # Encrypted in production
    library_id = Column(String(100), nullable=True)  # Library's ID with the service

    # Cost tracking
    cost_per_checkout = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    # Deep link templates
    app_deep_link_template = Column(String(500), nullable=True)  # e.g., "palace://title/{content_id}"
    web_deep_link_template = Column(String(500), nullable=True)  # e.g., "https://thepalaceproject.org/title/{content_id}"

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    budgets = relationship("StreamingBudget", back_populates="service_config")
    checkouts = relationship("StreamingCheckout", back_populates="service_config")
    catalog_items = relationship("StreamingCatalogItem", back_populates="service_config")


class StreamingBudget(Base):
    __tablename__ = "streaming_budgets"

    id = Column(Integer, primary_key=True, index=True)
    service_config_id = Column(Integer, ForeignKey("streaming_service_configs.id", ondelete="CASCADE"), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_month = Column(Integer, nullable=True)  # NULL means annual budget

    # Budget amounts
    allocated_amount = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    spent_amount = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    # Checkout limits
    max_checkouts = Column(Integer, nullable=True)  # NULL means unlimited
    current_checkouts = Column(Integer, nullable=False, default=0)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    service_config = relationship("StreamingServiceConfig", back_populates="budgets")

    __table_args__ = (
        UniqueConstraint("service_config_id", "fiscal_year", "fiscal_month", name="uq_streaming_budget_period"),
        Index("ix_streaming_budgets_service_year", "service_config_id", "fiscal_year"),
    )

    @property
    def remaining_amount(self) -> Decimal:
        return self.allocated_amount - self.spent_amount

    @property
    def remaining_checkouts(self) -> int | None:
        if self.max_checkouts is None:
            return None
        return max(0, self.max_checkouts - self.current_checkouts)


class PatronStreamingLimit(Base):
    __tablename__ = "patron_streaming_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_config_id = Column(Integer, ForeignKey("streaming_service_configs.id", ondelete="CASCADE"), nullable=False)

    # Monthly limits
    monthly_limit = Column(Integer, nullable=False, default=5)  # Default: 5 checkouts per month
    current_month_checkouts = Column(Integer, nullable=False, default=0)
    limit_reset_date = Column(DateTime, nullable=False)  # When the monthly limit resets

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="streaming_limits")
    service_config = relationship("StreamingServiceConfig")

    __table_args__ = (
        UniqueConstraint("user_id", "service_config_id", name="uq_patron_streaming_limit"),
        Index("ix_patron_streaming_limits_user", "user_id"),
        Index("ix_patron_streaming_limits_reset", "limit_reset_date"),
    )

    @property
    def remaining_checkouts(self) -> int:
        return max(0, self.monthly_limit - self.current_month_checkouts)


class StreamingCatalogItem(Base):
    __tablename__ = "streaming_catalog_items"

    id = Column(Integer, primary_key=True, index=True)
    service_config_id = Column(Integer, ForeignKey("streaming_service_configs.id", ondelete="CASCADE"), nullable=False)

    # External identifiers
    external_id = Column(String(100), nullable=False)  # ID in the streaming service

    # Content metadata
    title = Column(String(500), nullable=False)
    author = Column(String(500), nullable=True)  # Author/Director/Artist
    description = Column(Text, nullable=True)
    content_type = Column(Enum(StreamingContentType, values_callable=lambda x: [m.value for m in x]), nullable=False)

    # Additional metadata
    isbn = Column(String(20), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    release_year = Column(Integer, nullable=True)
    genres = Column(Text, nullable=True)  # JSON array as string
    cover_url = Column(String(1000), nullable=True)
    rating = Column(String(20), nullable=True)  # MPAA rating, etc.

    # Availability
    is_available = Column(Boolean, default=True, nullable=False)
    available_until = Column(DateTime, nullable=True)  # NULL means always available

    # Linking to local catalog
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)

    # Cache management
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    service_config = relationship("StreamingServiceConfig", back_populates="catalog_items")
    catalog_item = relationship("CatalogItem", backref="streaming_items")
    checkouts = relationship("StreamingCheckout", back_populates="streaming_item")

    __table_args__ = (
        UniqueConstraint("service_config_id", "external_id", name="uq_streaming_catalog_item"),
        Index("ix_streaming_catalog_items_title", "title"),
        Index("ix_streaming_catalog_items_isbn", "isbn"),
        Index("ix_streaming_catalog_items_type", "content_type"),
        Index("ix_streaming_catalog_items_catalog", "catalog_item_id"),
    )


class StreamingCheckout(Base):
    __tablename__ = "streaming_checkouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    service_config_id = Column(Integer, ForeignKey("streaming_service_configs.id", ondelete="CASCADE"), nullable=False)
    streaming_item_id = Column(Integer, ForeignKey("streaming_catalog_items.id", ondelete="SET NULL"), nullable=True)

    # External reference
    external_checkout_id = Column(String(100), nullable=True)  # ID from the streaming service

    # Checkout details
    status = Column(Enum(StreamingCheckoutStatus, values_callable=lambda x: [m.value for m in x]), default=StreamingCheckoutStatus.ACTIVE, nullable=False)
    checked_out_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)  # When the streaming access expires
    returned_at = Column(DateTime, nullable=True)

    # Cost tracking
    cost = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    # Denormalized for reporting (preserved even if streaming_item is deleted)
    item_title = Column(String(500), nullable=True)
    item_content_type = Column(Enum(StreamingContentType, values_callable=lambda x: [m.value for m in x]), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="streaming_checkouts")
    service_config = relationship("StreamingServiceConfig", back_populates="checkouts")
    streaming_item = relationship("StreamingCatalogItem", back_populates="checkouts")

    __table_args__ = (
        Index("ix_streaming_checkouts_user_status", "user_id", "status"),
        Index("ix_streaming_checkouts_service", "service_config_id", "checked_out_at"),
        Index("ix_streaming_checkouts_expires", "expires_at", "status"),
    )


class StreamingUsageStats(Base):
    __tablename__ = "streaming_usage_stats"

    id = Column(Integer, primary_key=True, index=True)
    service_config_id = Column(Integer, ForeignKey("streaming_service_configs.id", ondelete="CASCADE"), nullable=False)

    # Time period
    stat_date = Column(DateTime, nullable=False)  # Date of statistics

    # Checkout metrics
    total_checkouts = Column(Integer, nullable=False, default=0)
    unique_patrons = Column(Integer, nullable=False, default=0)

    # Cost metrics
    total_cost = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    # Content type breakdown (JSON as string)
    checkouts_by_type = Column(Text, nullable=True)

    # Top content (JSON as string - list of {item_id, title, checkouts})
    top_items = Column(Text, nullable=True)

    # Relationships
    service_config = relationship("StreamingServiceConfig")

    __table_args__ = (
        UniqueConstraint("service_config_id", "stat_date", name="uq_streaming_usage_stats_period"),
        Index("ix_streaming_usage_stats_date", "stat_date"),
    )


class DefaultPatronStreamingLimit(Base):
    __tablename__ = "default_patron_streaming_limits"

    id = Column(Integer, primary_key=True, index=True)
    service_config_id = Column(Integer, ForeignKey("streaming_service_configs.id", ondelete="CASCADE"), nullable=False)
    user_role = Column(String(50), nullable=False)  # e.g., "PATRON", "STAFF", "CHILD"
    monthly_limit = Column(Integer, nullable=False, default=5)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    service_config = relationship("StreamingServiceConfig")

    __table_args__ = (
        UniqueConstraint("service_config_id", "user_role", name="uq_default_streaming_limit_role"),
    )
