# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class PatronTrainingOptOut(Base):

    __tablename__ = "patron_training_opt_outs"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    opted_out_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    opted_in_at = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=True)
    requested_via = Column(String(20), nullable=False, default="web")  # web, staff, api

    @property
    def is_opted_out(self) -> bool:
        if self.opted_in_at is None:
            return True
        return self.opted_out_at > self.opted_in_at
