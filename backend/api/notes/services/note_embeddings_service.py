from pgvector.django import CosineDistance
from api.notes.models import Note, NoteChunk
from api.notes.services.openai_embeddings_service import OpenAIService
from api.notes.services.note_chunk_service import NoteChunkService


class NoteEmbeddingsService:
    def __init__(self):
        self.openai = OpenAIService()

    def process_note(self, note):
        new_chunks = NoteChunkService.generate_chunks(note.content)
        
        if not new_chunks:
            note.chunks.all().delete()
            note.embedding_status = 'completed'
            note.save()
            return {'created': 0, 'unchanged': 0, 'deleted': 0}
        
        existing_by_hash = {chunk.content_hash: chunk for chunk in note.chunks.all()}
        existing_hashes = set(existing_by_hash.keys())
        new_hashes = {content_hash for _, _, content_hash in new_chunks}
        
        unchanged_hashes = existing_hashes & new_hashes
        hashes_to_delete = existing_hashes - new_hashes
        chunks_to_create = [
            (index, text, content_hash) 
            for index, text, content_hash in new_chunks 
            if content_hash not in existing_hashes
        ]
        
        if hashes_to_delete:
            NoteChunk.objects.filter(note=note, content_hash__in=hashes_to_delete).delete()
        
        for index, _, content_hash in new_chunks:
            if content_hash in unchanged_hashes:
                existing_chunk = existing_by_hash[content_hash]
                if existing_chunk.chunk_index != index:
                    existing_chunk.chunk_index = index
                    existing_chunk.save(update_fields=['chunk_index'])
        
        if chunks_to_create:
            texts = [text for _, text, _ in chunks_to_create]
            embeddings = self.openai.get_embeddings(texts)
            
            for (index, text, content_hash), embedding in zip(chunks_to_create, embeddings):
                NoteChunk.objects.create(
                    note=note,
                    chunk_index=index,
                    content=text,
                    content_hash=content_hash,
                    embedding=embedding
                )
        
        note.embedding_status = 'completed'
        note.save()
        
        return {
            'created': len(chunks_to_create), 
            'unchanged': len(unchanged_hashes), 
            'deleted': len(hashes_to_delete)
        }

    def search_and_respond(self, query, user, limit=5):
        query_embedding = self.openai.get_embedding(query)
        
        similar_chunks = NoteChunk.objects.filter(
            note__user=user
        ).order_by(CosineDistance('embedding', query_embedding))[:limit]
        
        seen_note_ids = set()
        context = []
        
        for chunk in similar_chunks:
            if chunk.note_id not in seen_note_ids:
                seen_note_ids.add(chunk.note_id)
                context.append({
                    'note_id': chunk.note_id,
                    'note_title': chunk.note.title,
                    'content': chunk.content,
                })
        
        if not context:
            return {'response': 'No relevant notes found.', 'references': []}
        
        ai_response = self.openai.ask(query, context)
        
        referenced_ids = [ref.note_id for ref in ai_response.references]
        valid_note_ids = set(
            Note.objects.filter(user=user, id__in=referenced_ids).values_list('id', flat=True)
        )
        
        validated_references = [
            {'note_id': ref.note_id, 'note_title': ref.note_title}
            for ref in ai_response.references 
            if ref.note_id in valid_note_ids
        ]
        
        return {'response': ai_response.response, 'references': validated_references}