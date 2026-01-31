from django.conf import settings
from django.db import models
from pgvector.django import VectorField
from api.notes.models import Note

class NoteChunk(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=768)

    class Meta:
        unique_together = ("note", "chunk_index")
