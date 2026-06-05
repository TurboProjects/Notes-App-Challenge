from django.contrib import admin

from .models import Answer
from .models import Category
from .models import InboxEvent
from .models import Note
from .models import OutboxEvent
from .models import Question


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    list_filter = ()
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'indexed_at', 'created_at', 'updated_at')
    list_filter = ('category', 'created_at', 'updated_at')
    search_fields = ('title', 'content', 'user__email')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at', 'content_hash', 'indexed_at')
    raw_id_fields = ('user',)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Live ledger visibility (design D9 demo windows) — strictly read-only."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OutboxEvent)
class OutboxEventAdmin(ReadOnlyAdmin):
    list_display = ('id', 'topic', 'correlation_id', 'attempts', 'created_at', 'published_at')
    list_filter = ('topic', ('published_at', admin.EmptyFieldListFilter))
    search_fields = ('correlation_id', 'event_id')
    ordering = ('-id',)


@admin.register(InboxEvent)
class InboxEventAdmin(ReadOnlyAdmin):
    list_display = (
        'id', 'consumer', 'correlation_id', 'processing_status',
        'error_code', 'claimed_at', 'processed_at',
    )
    list_filter = ('consumer', 'processing_status')
    search_fields = ('correlation_id', 'event_id')
    ordering = ('-id',)


@admin.register(Question)
class QuestionAdmin(ReadOnlyAdmin):
    list_display = ('id', 'user', 'text', 'created_at')
    search_fields = ('text', 'user__email')
    ordering = ('-created_at',)


@admin.register(Answer)
class AnswerAdmin(ReadOnlyAdmin):
    list_display = ('id', 'question', 'created_at')
    ordering = ('-created_at',)
