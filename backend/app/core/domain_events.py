# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class EventMetadata:

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = None
    causation_id: str | None = None
    actor_id: str | None = None
    source_context: str | None = None


@dataclass(frozen=True)
class DomainEvent:

    metadata: EventMetadata = field(default_factory=EventMetadata)

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    @property
    def event_id(self) -> str:
        return self.metadata.event_id

    @property
    def timestamp(self) -> datetime:
        return self.metadata.timestamp

    @property
    def aggregate_type(self) -> str:
        return "Unknown"

    @property
    def aggregate_id(self) -> str:
        return ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"event_type": self.event_type}
        for k, v in self.__dict__.items():
            if k == "metadata":
                result["metadata"] = {
                    "event_id": self.metadata.event_id,
                    "timestamp": self.metadata.timestamp.isoformat(),
                    "correlation_id": self.metadata.correlation_id,
                    "causation_id": self.metadata.causation_id,
                    "actor_id": self.metadata.actor_id,
                    "source_context": self.metadata.source_context,
                }
            elif isinstance(v, datetime):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result
