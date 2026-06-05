from typing import Any
from typing import override

from django.conf import settings
from django.db import connection

from api.notes.domain.ports import EventOutbox
from api.notes.models import OutboxEvent


class DjangoEventOutbox(EventOutbox):
    """Transactional outbox writer.

    The OutboxEvent INSERT joins the caller's transaction (ATOMIC_REQUESTS on
    the request path; explicit transaction in commands). The NOTIFY is issued
    in the same transaction: Postgres queues it and delivers it to listeners
    only at COMMIT, so the relay never wakes for work that rolled back.
    """

    @override
    def emit(
        self,
        *,
        topic: str,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> None:
        OutboxEvent.objects.create(
            topic=topic,
            correlation_id=correlation_id,
            payload=payload,
        )
        with connection.cursor() as cursor:
            cursor.execute(f'NOTIFY "{settings.OUTBOX_NOTIFY_CHANNEL}"')
