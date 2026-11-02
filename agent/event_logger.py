from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import requests


class EventLogger:
    def __init__(self, api_base_url: str, session_id: str, task_id: str):
        self.api_base_url = api_base_url.rstrip("/")
        self.session_id = session_id
        self.task_id = task_id
        self.events: list[dict[str, Any]] = []
        self.all_events: list[dict[str, Any]] = []
        self.errors = 0

    def record(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "task_id": self.task_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload or {},
        }
        self.events.append(event)
        self.all_events.append(event)
        return event

    def flush(self) -> None:
        if not self.events:
            return
        url = f"{self.api_base_url}/api/sessions/{self.session_id}/events"
        for offset in range(0, len(self.events), 500):
            batch = self.events[offset : offset + 500]
            response = requests.post(url, json={"events": batch}, timeout=15)
            response.raise_for_status()
            result = response.json()
            if result.get("accepted", 0) + result.get("duplicates", 0) != len(batch):
                raise RuntimeError("Event API did not acknowledge the full batch")
        self.events.clear()
