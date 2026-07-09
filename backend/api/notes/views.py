from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.notes.models import Note, Category
from api.notes.serializers import NoteSerializer, CategorySerializer
from api.users.permissions import IsOwnerOrReadOnly, IsCategoryOwnerOrReadOnly
from django.db.models import Q


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
            # Only allow filtering by a category the user can see (their own or
            # a global one); an out-of-scope id 404s instead of leaking that it
            # exists.
            category = get_object_or_404(
                Category.objects.filter(
                    Q(category_owner_user=self.request.user)
                    | Q(category_owner_user__isnull=True)
                ),
                id=category_id,
            )
            queryset = queryset.filter(category=category)
        
        return queryset.order_by('-updated_at')

    def get_object(self):
        obj = get_object_or_404(Note, id=self.kwargs['pk'], user=self.request.user)
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing categories.
    """
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsCategoryOwnerOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        """
        Return the user's own categories plus global ones (no owner).
        """
        filterQ = (
            Q(category_owner_user=self.request.user)
            | Q(category_owner_user__isnull=True)
        )
        return Category.objects.filter(filterQ)

    def perform_create(self, serializer):
        serializer.save(category_owner_user=self.request.user)
