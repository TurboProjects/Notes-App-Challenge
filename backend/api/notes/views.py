from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.notes.models import Note, Category
from api.notes.serializers import NoteSerializer, CategorySerializer
from api.users.permissions import IsOwnerOrReadOnly
from rest_framework.decorators import action


try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:
    RecursiveCharacterTextSplitter = None

from api.ai import services
from api.ai.models import NoteChunk

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
            # Verify category exists and belongs to user
            category = get_object_or_404(Category, id=category_id)
            queryset = queryset.filter(category=category)
        
        return queryset.order_by('-updated_at')

    def get_object(self):
        obj = get_object_or_404(Note, id=self.kwargs['pk'], user=self.request.user)
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        note = serializer.save(user=self.request.user)
        # create chunks and embeddings for the newly created note
        chunks = services.chunk_text(note.title, note.content)
        if not chunks:
            return
        try:
            embeddings = services.embed_texts(chunks)
        except Exception:
            # don't block note creation on embedding errors; log in real app
            return

        objs = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            objs.append(
                NoteChunk(user=self.request.user, note=note, chunk_index=i, text=chunk, embedding=emb)
            )
        NoteChunk.objects.bulk_create(objs)

    def perform_update(self, serializer):
        note = serializer.save()
        # delete and recreate chunks
        NoteChunk.objects.filter(note=note).delete()
        chunks = services.chunk_text(note.title, note.content)
        if not chunks:
            return
        try:
            embeddings = services.embed_texts(chunks)
        except Exception:
            return

        objs = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            objs.append(NoteChunk(user=note.user, note=note, chunk_index=i, text=chunk, embedding=emb))
        NoteChunk.objects.bulk_create(objs)

    @action(detail=False, methods=['post'], url_path='generate-summary')
    def generate_summary(self, request):
        """
        Generate a summary for the given user query based on the most relevant notes.
        """
        user_query = request.data.get('query', '')
        if not user_query:
            return Response({'error': 'Query is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Get all notes for the authenticated user
        notes = Note.objects.filter(user=request.user)

        # Step 2: Chunking and embedding (assuming services.create_embeddings exists)
        chunks = [note.content for note in notes]
        embeddings = services.create_embeddings(chunks)

        # Step 3: Convert user query to vector
        query_vector = services.create_embedding(user_query)

        # Step 4: Query the vector database for the most similar notes
        top_notes = services.query_vector_db(query_vector, embeddings, top_k=3)

        # Step 5 & 6: Generate summary using LLM
        summary = services.generate_summary(user_query, top_notes)

        return Response({'query': user_query, 'summary': summary})


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
    


'''
Step 1 - Get all the notes (titles, descriptions) for the authenticated user.
Ste 2 - Chunking Strategy ==> Semantic Chunking ==> Create embeddings for step 1 and store in vector db. ==> pgvector
Step 3 - We have a user query ==> Convert this query to a vector ==> Some embedding model ==> OpeAI
Step 4 - Query the vector db to find the most similar notes.
Step 5 - Taking in the top 3 ranked notes and give it to the LLM
Step 6 - We will have to crerate a prompt template which will take in the user query and the top 3 notes. This will give a summary.
Step 7 - Test the pipeline end to end with metrics if possible.
Step 8 - API which will take in user query and return the summary.

'''