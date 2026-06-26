Feb - 02:

1. Models
    a. Add NoteChunk => content, note_id, embedding(1024 - chunks de 2000 +-400)
    b. EMBEDDING_STATUS => []

2. Arch
    a. Levantar un redis/RabbitMQ
    b. Celery
    c. 2 Queues (Chunk, Embedding)
    d. Base Cache

3. Endpoints
    a. /ai_assistant