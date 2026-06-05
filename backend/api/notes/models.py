import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.db import models
from pgvector.django import HalfVectorField
from pgvector.django import HnswIndex

from api.notes.validators import validate_hex_color


class Category(models.Model):
    """
    Category model for organizing notes.
    """

    name = models.CharField(max_length=100)
    color = models.CharField(
        max_length=7,
        validators=[validate_hex_color],
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"

    def clean(self):
        """
        Ensure name is not empty or just whitespace
        """
        if not self.name or not self.name.strip():
            raise ValidationError({"name": "Name cannot be empty or whitespace"})
        self.name = self.name.strip()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def note_count(self):
        """
        Count the number of notes for the category
        """
        return self.notes.count()


class Note(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    title = models.CharField(max_length=200, default="Untitled Note")
    content = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notes",
    )
    # Indexing state (ADR-0002): content_hash debounces re-embedding;
    # indexed_at IS NULL (or an older embedding_version) marks pending work.
    content_hash = models.CharField(max_length=64, blank=True, default="")
    embedding_model = models.CharField(max_length=100, blank=True, default="")
    embedding_version = models.IntegerField(default=0)
    indexed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.email} - {self.title}"

    def save(self, *args, **kwargs):
        """Debounced re-index trigger (design D4): recompute content_hash on
        every save; emit note.embed.requested ONLY when it changed. The outbox
        insert joins the surrounding transaction (ATOMIC_REQUESTS on the
        request path), so the event commits or rolls back with the note."""
        # Lazy imports: the outbox adapter imports this module.
        from api.notes.domain.value_objects import sha256_of  # noqa: PLC0415
        from api.notes.infrastructure.messaging.outbox import (  # noqa: PLC0415
            DjangoEventOutbox,
        )

        new_hash = sha256_of(self.content or "")
        content_changed = new_hash != self.content_hash
        self.content_hash = new_hash
        super().save(*args, **kwargs)
        if content_changed:
            DjangoEventOutbox().emit(
                topic="note.embed.requested",
                correlation_id=str(self.id),
                payload={
                    "schema_version": 1,
                    "note_id": self.id,
                    "content_hash": new_hash,
                },
            )


class NoteChunk(models.Model):
    """The unit of retrieval and citation (design D3 / ADR-0002)."""

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.IntegerField()
    text = models.TextField()
    content_hash = models.CharField(max_length=64)
    # halfvec: half-precision — halves storage/index size at negligible recall
    # cost for 1536-dim normalized OpenAI embeddings.
    embedding = HalfVectorField(dimensions=1536)
    # Populated by the repository write path with SearchVector("text").
    content_tsv = SearchVectorField(null=True)
    embedding_model = models.CharField(max_length=100)
    embedding_version = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["note", "chunk_index"],
                name="notechunk_unique_note_index",
            ),
        ]
        indexes = [
            HnswIndex(
                name="notechunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["halfvec_cosine_ops"],
            ),
            GinIndex(fields=["content_tsv"], name="notechunk_tsv_gin"),
        ]

    def __str__(self):
        return f"chunk {self.chunk_index} of note {self.note.id}"


class Question(models.Model):
    """Immutable user input — the aggregate root. Carries NO processing
    state: the user-facing status is derived (Answer exists -> SUCCESS;
    rag-worker inbox FAILED -> FAILED; else PENDING). See ADR-0001."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.id}: {self.text[:50]}"


class Answer(models.Model):
    """The async-produced artifact. Its existence IS the success state; the
    OneToOne unique constraint doubles as the idempotency guard."""

    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        related_name="answer",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"answer to question {self.question.id}"


class Citation(models.Model):
    """A source the LLM actually cited (never the full top-k candidate set).

    chunk is SET_NULL so citations survive re-chunking; note + snippet are
    denormalized so past answers stay auditable forever."""

    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name="citations",
    )
    chunk = models.ForeignKey(
        NoteChunk,
        on_delete=models.SET_NULL,
        null=True,
        related_name="citations",
    )
    note = models.ForeignKey(
        Note,
        on_delete=models.SET_NULL,
        null=True,
        related_name="citations",
    )
    snippet = models.TextField()
    # RRF score for fused winners; NULL for neighbor-expanded chunks.
    relevance_score = models.FloatField(null=True, blank=True)
    cited_order = models.IntegerField()

    class Meta:
        ordering = ["cited_order"]

    def __str__(self):
        return f"citation {self.cited_order} of answer {self.answer_id}"


class OutboxEvent(models.Model):
    """Transactional outbox — publish side (ADR-0001). Written in the same
    transaction as the domain change it describes; the relay publishes to
    RabbitMQ with publisher confirms and stamps published_at after the ack.
    Deliberately no FKs into the domain (correlation by id)."""

    event_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    topic = models.CharField(max_length=100)
    correlation_id = models.CharField(max_length=64)
    payload = models.JSONField()
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            # Partial index: empty in steady state -> the relay's poll is O(pending).
            models.Index(
                fields=["id"],
                name="outbox_pending_idx",
                condition=models.Q(published_at__isnull=True),
            ),
            models.Index(
                fields=["topic", "correlation_id"],
                name="outbox_topic_corr_idx",
            ),
        ]

    def __str__(self):
        return f"{self.topic} ({self.event_id})"


class InboxEvent(models.Model):
    """Idempotent Consumer ledger — consume side (ADR-0001). One row per
    (event, consumer): the unique constraint IS the claim; fan-out safe."""

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    STATUS_CHOICES = [(SUCCEEDED, SUCCEEDED), (FAILED, FAILED)]

    event_id = models.UUIDField()
    consumer = models.CharField(max_length=100)
    correlation_id = models.CharField(max_length=64)
    # NULL while in-flight (claimed but not finished).
    processing_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        null=True,
        blank=True,
    )
    error_code = models.CharField(max_length=100, blank=True, default="")
    claimed_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    # LLM telemetry (model, tokens) — observability, not domain data.
    result_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event_id", "consumer"],
                name="inbox_unique_event_consumer",
            ),
        ]
        indexes = [
            models.Index(
                fields=["consumer", "correlation_id"],
                name="inbox_consumer_corr_idx",
            ),
        ]

    def __str__(self):
        return f"{self.consumer} <- {self.event_id} [{self.processing_status}]"
