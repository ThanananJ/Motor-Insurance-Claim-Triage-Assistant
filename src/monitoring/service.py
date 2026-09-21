"""Fail-open monitoring facade: observability must never stop claim triage."""

from __future__ import annotations

import logging
from uuid import uuid4

from .models import EventType, MonitoringEvent
from .repository import MonitoringRepository

LOGGER = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self, repository: MonitoringRepository | None = None) -> None:
        self.repository = repository or MonitoringRepository()

    @staticmethod
    def new_request_id() -> str:
        return str(uuid4())

    def record(self, event_type: EventType, request_id: str, **fields) -> bool:
        try:
            return self.repository.insert(MonitoringEvent(event_type=event_type, request_id=request_id, **fields))
        except Exception as exc:
            LOGGER.warning("Monitoring write failed (%s); claim workflow continues", type(exc).__name__)
            return False
