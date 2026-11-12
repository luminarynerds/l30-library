# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func

from ..core.database import Base
from ..core.encryption import EncryptedString


class LegalClinicNotify(Base):
    """One-time email opt-in for legal clinic scheduling notifications.

    Row is DELETED after the notification email is sent (notified_at is set
    and then the row is purged). Dedup via email_hash (blind index on HMAC
    of the normalised address) so duplicate submissions are idempotent.
    """
    __tablename__ = "legal_clinic_notify"

    id = Column(String(36), primary_key=True)
    _email = Column("email", EncryptedString(255), nullable=False)
    email_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notified_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, value):
        self._email = value
