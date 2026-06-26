from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.notes.models import Note, Category
from api.notes.serializers import AIAssistantRequestSerializer, NoteSerializer, CategorySerializer
from api.notes.services.note_embeddings_service import NoteEmbeddingsService
from api.users.permissions import IsOwnerOrReadOnly
from api.worker.celery import process_note_embeddings


class NoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing notes.

    list:
    Return a paginated list of notes that belong to the authenticated user.
    Optionally filter by category_id using query parameter.
    """
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        """
        Filter queryset to return only notes that belong to the authenticated user,
        optionally filtered by category_id, ordered by last updated.
        """
        queryset = Note.objects.filter(user=self.request.user)

        category_id = self.request.query_params.get('category_id', None)
        if category_id is not None:
            category = get_object_or_404(Category, id=category_id)
            queryset = queryset.filter(category=category)

        return queryset.order_by('-updated_at')

    def get_object(self):
        obj = get_object_or_404(Note, id=self.kwargs['pk'], user=self.request.user)
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        note = serializer.save(user=self.request.user)
        process_note_embeddings.delay(note.id)

    def perform_update(self, serializer):
        note = serializer.save()
        process_note_embeddings.delay(note.id)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing categories.
    """
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        """
        Filter queryset to return only user's categories.
        """
        return Category.objects.all()


class AIAssistantViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = AIAssistantRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = NoteEmbeddingsService()
        result = service.search_and_respond(
            query=serializer.validated_data['query'],
            user=request.user
        )

        return Response(result)