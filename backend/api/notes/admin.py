from django.contrib import admin

from .models import Answer
from .models import Category
from .models import Citation
from .models import InboxEvent
from .models import Note
from .models import NoteChunk
from .models import OutboxEvent
from .models import Question


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "color")
    list_filter = ()
    search_fields = ("name",)
    ordering = ("name",)


class NoteChunkInline(admin.TabularInline):
    model = NoteChunk
    extra = 0
    can_delete = False
    show_change_link = True
    ordering = ("chunk_index",)
    fields = ("chunk_index", "text", "content_hash", "embedding_version", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "category",
        "indexed_at",
        "created_at",
        "updated_at",
    )
    list_filter = ("category", "created_at", "updated_at")
    search_fields = ("title", "content", "user__email")
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at", "content_hash", "indexed_at")
    raw_id_fields = ("user",)
    inlines = (NoteChunkInline,)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NoteChunk)
class NoteChunkAdmin(ReadOnlyAdmin):
    list_display = (
        "id",
        "note",
        "chunk_index",
        "embedding_model",
        "embedding_version",
        "created_at",
    )
    list_filter = ("embedding_version", "embedding_model")
    search_fields = ("text", "note__title")
    ordering = ("note", "chunk_index")
    raw_id_fields = ("note",)
    fields = (
        "note",
        "chunk_index",
        "content_hash",
        "embedding_model",
        "embedding_version",
        "created_at",
        "embedding",
        "content_tsv",
    )


@admin.register(OutboxEvent)
class OutboxEventAdmin(ReadOnlyAdmin):
    list_display = (
        "id",
        "topic",
        "correlation_id",
        "attempts",
        "created_at",
        "published_at",
    )
    list_filter = ("topic", ("published_at", admin.EmptyFieldListFilter))
    search_fields = ("correlation_id", "event_id")
    ordering = ("-id",)


@admin.register(InboxEvent)
class InboxEventAdmin(ReadOnlyAdmin):
    list_display = (
        "id",
        "consumer",
        "correlation_id",
        "processing_status",
        "error_code",
        "claimed_at",
        "processed_at",
    )
    list_filter = ("consumer", "processing_status")
    search_fields = ("correlation_id", "event_id")
    ordering = ("-id",)


@admin.register(Question)
class QuestionAdmin(ReadOnlyAdmin):
    list_display = ("id", "user", "text", "created_at")
    search_fields = ("text", "user__email")
    ordering = ("-created_at",)


class CitationInline(admin.TabularInline):
    model = Citation
    extra = 0
    can_delete = False
    show_change_link = True
    ordering = ("cited_order",)
    fields = ("cited_order", "note", "chunk", "relevance_score", "snippet")
    readonly_fields = fields
    raw_id_fields = ("note", "chunk")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Answer)
class AnswerAdmin(ReadOnlyAdmin):
    list_display = ("id", "question", "created_at")
    ordering = ("-created_at",)
    inlines = (CitationInline,)


@admin.register(Citation)
class CitationAdmin(ReadOnlyAdmin):
    list_display = (
        "id",
        "answer",
        "cited_order",
        "note",
        "chunk",
        "relevance_score",
    )
    list_filter = (("relevance_score", admin.EmptyFieldListFilter),)
    search_fields = ("snippet", "note__title")
    ordering = ("-answer", "cited_order")
    raw_id_fields = ("answer", "note", "chunk")
