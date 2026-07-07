from typing import List

from django.db.models.expressions import RawSQL
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from api.ai import services
from django.conf import settings
from api.ai.models import NoteChunk


class QueryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        query = request.data.get("query")
        top_k = int(request.data.get("top_k", 5))
        if not query:
            return Response({"detail": "Missing `query`"}, status=status.HTTP_400_BAD_REQUEST)

        emb = services.embed_texts([query])
        if not emb:
            return Response({"detail": "Failed to embed query"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        vector = emb[0]
        # pgvector accepts vector literals like: [0.1,0.2,...]
        vector_str = "[" + ",".join(map(str, vector)) + "]"

        # find top-k similar chunks for this user
        qs = (
            NoteChunk.objects.filter(user=request.user)
            .annotate(distance=RawSQL("embedding <-> %s::vector", (vector_str,)))
            .order_by("distance")[:top_k]
        )

        sources = []
        contexts: List[dict] = []
        for c in qs:
            sources.append({"note_id": c.note_id, "chunk_index": c.chunk_index, "text": c.text, "distance": float(c.distance)})
            contexts.append({"note_id": c.note_id, "chunk_index": c.chunk_index, "text": c.text})

        # Use LLM to synthesize an answer when configured, otherwise join.
        llm_result = services.llm_summarize(query, contexts)
        if isinstance(llm_result, dict) and "answer" in llm_result:
            return Response({"answer": llm_result.get("answer"), "sources": llm_result.get("sources", sources)})

        # Fallback
        return Response({"answer": str(llm_result), "sources": sources})
from django.shortcuts import render

# Create your views here.
