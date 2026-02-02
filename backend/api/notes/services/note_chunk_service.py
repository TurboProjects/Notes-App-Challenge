import hashlib

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 400


class NoteChunkService:

    @staticmethod
    def generate_chunks(content):
        if not content:
            return []
        
        step = CHUNK_SIZE - CHUNK_OVERLAP
        chunks = []
        position = 0
        chunk_index = 0
        
        while position < len(content):
            chunk_text = content[position:position + CHUNK_SIZE]
            if chunk_text.strip():
                content_hash = hashlib.sha256(chunk_text.encode()).hexdigest()
                chunks.append((chunk_index, chunk_text, content_hash))
                chunk_index += 1
            position += step
        
        return chunks