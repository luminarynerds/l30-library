# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from ..core.database import Base


class Z3950Source(Base):
    __tablename__ = "z3950_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=210)
    database_name = Column(String(100), nullable=False)
    syntax = Column(String(20), default="USMARC")
    encoding = Column(String(20), default="UTF-8")
    sru_url = Column(String(500), nullable=True)
    requires_auth = Column(Boolean, default=False)
    username = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=True)
    is_enabled = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_test_success = Column(Boolean, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
