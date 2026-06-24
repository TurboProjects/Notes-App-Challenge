"""PgAnswerDeltaPublisher: streaming answer deltas over Postgres NOTIFY.

Implements the AnswerDeltaPublisher port. Deltas are ephemeral UX,
best-effort by contract: a lost delta only degrades streaming; the durable
answer always arrives via the terminal `status` event.

Two mechanics matter here:
- **Autocommit connection**: NOTIFY fires at transaction commit, so deltas
  must ride a dedicated autocommit connection (the PgListener pattern) or
  they would all arrive at once when the worker's save-transaction commits.
- **Coalescing (~100ms)**: the LLM emits dozens of deltas per second;
  throttled flushes (plus a trailing debounce flush for the tail) keep NOTIFY
  churn and client re-renders sane. Payloads stay far below NOTIFY's ~8KB cap.
"""

import asyncio
import json
import logging

import psycopg
from django.conf import settings

from api.notes.domain.ports import AnswerDeltaPublisher
from api.notes.infrastructure.messaging.listener import _dsn

logger = logging.getLogger(__name__)

COALESCE_SECONDS = 0.1


class _SharedNotifyConnection:
    """One lazily-opened autocommit NOTIFY connection per worker process."""

    def __init__(self) -> None:
        self._conn: psycopg.AsyncConnection | None = None
        self._lock = asyncio.Lock()

    async def notify(self, channel: str, payload: str) -> None:
        async with self._lock:
            if self._conn is None or self._conn.closed:
                self._conn = await psycopg.AsyncConnection.connect(
                    _dsn(),
                    autocommit=True,
                )
            try:
                await self._conn.execute(
                    "SELECT pg_notify(%s, %s)",
                    (channel, payload),
                )
            except psycopg.Error:
                # Drop the broken connection; the next flush reconnects.
                conn, self._conn = self._conn, None
                await conn.close()
                raise


_notify_connection = _SharedNotifyConnection()
"""Module-level singleton: one NOTIFY connection per process by construction."""


class PgAnswerDeltaPublisher(AnswerDeltaPublisher):
    """Coalesces a single question's delta stream (one instance per message:
    the container builds a fresh use case per consumed event)."""

    def __init__(self, *, coalesce_seconds: float = COALESCE_SECONDS) -> None:
        self._coalesce_seconds = coalesce_seconds
        self._lock = asyncio.Lock()
        self._question_id: int | None = None
        self._pending_text = ""
        self._pending_seq = 0
        self._last_flush = 0.0
        self._trailing: asyncio.Task | None = None

    async def apublish(self, *, question_id: int, seq: int, text: str) -> None:
        async with self._lock:
            self._question_id = question_id
            self._pending_text += text
            self._pending_seq = seq
            if self._trailing is not None:
                self._trailing.cancel()
                self._trailing = None
            loop = asyncio.get_running_loop()
            if loop.time() - self._last_flush >= self._coalesce_seconds:
                await self._flush_locked()
            else:
                # Debounced trailing flush so the stream's tail is delivered
                # even if no further delta re-opens the throttle gate.
                self._trailing = asyncio.create_task(self._trailing_flush())

    async def _trailing_flush(self) -> None:
        await asyncio.sleep(self._coalesce_seconds)
        async with self._lock:
            await self._flush_locked()

    async def _flush_locked(self) -> None:
        if not self._pending_text or self._question_id is None:
            return
        payload = json.dumps(
            {
                "kind": "delta",
                "question_id": self._question_id,
                "seq": self._pending_seq,
                "text": self._pending_text,
            },
        )
        try:
            await _notify_connection.notify(settings.QUESTION_EVENTS_CHANNEL, payload)
        except psycopg.Error:
            # Best-effort by contract: keep the buffer and retry on the next
            # flush; the terminal `status` event remains the durable path.
            logger.exception("delta NOTIFY failed; keeping buffer for retry")
            return
        self._pending_text = ""
        self._last_flush = asyncio.get_running_loop().time()
