

from __future__ import annotations

import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger("mental_health_chatbot.memory")


@dataclass
class SessionRecord:
    messages: list[dict]
    blocked: bool = False
    last_seen: float = field(default_factory=time.monotonic)


class SessionStore:
    

    def __init__(
        self,
        session_factory: Callable[[], dict],
        ttl_seconds: int,
        sweep_interval_s: int,
        max_sessions: int,
    ) -> None:
        self._session_factory = session_factory
        self._ttl_seconds = ttl_seconds
        self._max_sessions = max_sessions
        self._lock = threading.Lock()
        self._records: dict[str, SessionRecord] = {}

        self._stop_event = threading.Event()
        self._sweeper = threading.Thread(
            target=self._sweep_loop,
            args=(sweep_interval_s,),
            daemon=True,
            name="session-sweeper",
        )
        self._sweeper.start()

    def get_or_create(self, session_id: str) -> SessionRecord:
        with self._lock:
            record = self._records.get(session_id)
            if record is not None:
                record.last_seen = time.monotonic()
                return record

            if len(self._records) >= self._max_sessions:
                # Fail loudly rather than silently growing without bound.
                raise RuntimeError(
                    "Session capacity reached; server needs scaling or a "
                    "shared session backend (Redis)."
                )

            record = SessionRecord(messages=self._session_factory())
            self._records[session_id] = record
            return record

    def mark_blocked(self, session_id: str) -> None:
        with self._lock:
            record = self._records.get(session_id)
            if record is not None:
                record.blocked = True

    def delete(self, session_id: str) -> None:
     
        with self._lock:
            self._records.pop(session_id, None)

    def is_blocked(self, session_id: str) -> bool:
        with self._lock:
            record = self._records.get(session_id)
            return bool(record and record.blocked)

    def active_session_count(self) -> int:
        with self._lock:
            return len(self._records)

    def _sweep_loop(self, interval_s: int) -> None:
        while not self._stop_event.wait(interval_s):
            self._sweep_once()

    def _sweep_once(self) -> None:
        cutoff = time.monotonic() - self._ttl_seconds
        with self._lock:
            expired = [sid for sid, rec in self._records.items() if rec.last_seen < cutoff]
            for sid in expired:
                del self._records[sid]
        if expired:
            logger.info("Evicted %d idle session(s)", len(expired))

    def stop(self) -> None:
        self._stop_event.set()