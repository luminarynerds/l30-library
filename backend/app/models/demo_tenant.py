# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
import enum
from enum import StrEnum
from datetime import datetime, timedelta

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class LibrarySize(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class DemoTenant(Base):
    __tablename__ = "demo_tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    library_name = Column(String(200), nullable=False)
    admin_name = Column(String(200), nullable=False)
    admin_email = Column(String(255), nullable=False, unique=True)
    library_size = Column(String(10), nullable=False, default="small")
    feature_flags = Column(JSON, nullable=False, default=dict)
    branding = Column(JSON, nullable=False, default=dict)
    demo_token = Column(String(100), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    last_login_at = Column(DateTime, nullable=True)
    seeded_features = Column(JSON, nullable=False, default=list)
