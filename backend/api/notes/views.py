from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from api.notes.infrastructure.container import build_request_note_indexing_use_case
from api.notes.models import Category
from api.notes.models import Note
from api.notes.serializers import CategorySerializer
from api.notes.serializers import NoteSerializer
from api.users.permissions import IsOwnerOrReadOnly


class NoteViewSet(viewsets.ModelViewSet):
    """Notes owned by the authenticated user; filter with ?category_id=."""

    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        queryset = Note.objects.filter(user=self.request.user)

        category_id = self.request.query_params.get("category_id", None)
        if category_id is not None:
            # 404 on an unknown category before filtering.
            category = get_object_or_404(Category, id=category_id)
            queryset = queryset.filter(category=category)

        return queryset.order_by("-updated_at")

    def get_object(self):
        obj = get_object_or_404(Note, id=self.kwargs["pk"], user=self.request.user)
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        # Re-index trigger lives in the application layer, not the ORM model:
        # hash + debounce + outbox emit run in this request transaction.
        note = serializer.save(user=self.request.user)
        build_request_note_indexing_use_case().execute(note_id=note.id)

    def perform_update(self, serializer):
        note = serializer.save()
        build_request_note_indexing_use_case().execute(note_id=note.id)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Category.objects.all()
