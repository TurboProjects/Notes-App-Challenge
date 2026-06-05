"""PgListener: the shared LISTEN primitive (design D2 / ADR-0001).

Used by two consumers with different roles:
- the outbox relay (wake-up signal over `outbox_channel`)
- the SSE broadcaster (result notifications over `question_events`)

LISTEN is a *subscription*: it needs a continuously-held, autocommit
connection (notifications arriving while disconnected are lost — that is why
both users pair it with a durable fallback: the relay's slow poll, the SSE
snapshot query on connect).
"""

import contextlib
import logging

import psycopg
from django.conf import settings

logger = logging.getLogger(__name__)


def _dsn() -> str:
    db = settings.DATABASES["default"]
    return (
        f"host={db['HOST']} port={db['PORT']} dbname={db['NAME']} "
        f"user={db['USER']} password={db['PASSWORD']}"
    )


class PgListener:
    """Holds one dedicated autocommit connection LISTENing on a channel and
    yields notification payloads; `timeout` bounds the wait so callers can
    interleave fallback work (e.g. the relay's slow poll)."""

    def __init__(self, channel: str):
        self._channel = channel
        self._conn: psycopg.AsyncConnection | None = None

    async def __aenter__(self):
        self._conn = await psycopg.AsyncConnection.connect(_dsn(), autocommit=True)
        await self._conn.execute(f'LISTEN "{self._channel}"')
        logger.info("listening on channel %s", self._channel)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._conn is not None:
            with contextlib.suppress(Exception):
                await self._conn.close()
        self._conn = None

    async def wait(self, *, wait_seconds: float) -> list[str]:
        """Block until a notification arrives or `wait_seconds` elapse;
        returns the payloads received (empty on timeout — callers use that
        as their fallback tick)."""
        assert self._conn is not None, "PgListener used outside its context"
        return [
            notify.payload
            async for notify in self._conn.notifies(
                timeout=wait_seconds,
                stop_after=1,
            )
        ]
