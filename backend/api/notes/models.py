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
        if not self.name or not self.name.strip():
            raise ValidationError({"name": "Name cannot be empty or whitespace"})
        self.name = self.name.strip()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def note_count(self):
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
    # content_hash debounces re-embedding.
    content_hash = models.CharField(max_length=64, blank=True, default="")
    # indexed_at NULL (or chunks at an older embedding_version) marks pending work.
    indexed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class NoteChunk(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.IntegerField()
    text = models.TextField()
    content_hash = models.CharField(max_length=64)
    embedding = HalfVectorField(dimensions=1536)
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
    """
    Async-produced artifact. Its existence is the success state, and the
    OneToOne constraint doubles as the idempotency guard.
    """

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
    """A chunk the LLM actually cited (never the full top-k)."""

    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name="citations",
    )
    # Chunk is SET_NULL so citations survive re-chunking
    chunk = models.ForeignKey(
        NoteChunk,
        on_delete=models.SET_NULL,
        null=True,
        related_name="citations",
    )
    # note + snippet are denormalized fields so past answers stay auditable.
    note = models.ForeignKey(
        Note,
        on_delete=models.SET_NULL,
        null=True,
        related_name="citations",
    )
    snippet = models.TextField()
    # RRF score for fused winners. NULL for neighbor-expanded chunks.
    relevance_score = models.FloatField(null=True, blank=True)
    cited_order = models.IntegerField()

    class Meta:
        ordering = ["cited_order"]

    def __str__(self):
        return f"citation {self.cited_order} of answer {self.answer.id}"


class OutboxEvent(models.Model):
    """
    Transactional outbox (publish side).
    Written in the same transaction as the domain change it describes,
    the relay publishes with confirms and stamps published_at.
    No FKs into the domain: correlation by id.
    """

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
    """
    Idempotent-consumer ledger (consumer side). One row per (event, consumer)
    The unique constraint IS the claim, fan-out safe.
    """

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
    # TODO: This can be moved later to langfuse / langsmith via OTEL.
    # LLM telemetry (model, tokens): observability, not domain data.
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
