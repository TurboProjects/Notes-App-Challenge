import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings.local')

import django
django.setup()

from celery import Celery
from api.notes.models import Note
from api.notes.services.note_embeddings_service import NoteEmbeddingsService

app = Celery('notes_app')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task
def process_note_embeddings(note_id):
    note = Note.objects.get(id=note_id)
    note.embedding_status = 'processing'
    note.save()
    
    try:
        service = NoteEmbeddingsService()
        result = service.process_note(note)
        return result
    except Exception as error:
        note.embedding_status = 'error'
        note.save()
        raise error