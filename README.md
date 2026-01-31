# Notes App

A note-taking application that allows users to organize and manage their notes in different categories, with an aesthetic interface and **AI-powered question-answering** over your notes (RAG).

## About the code

There are four main components:

- **Backend API**: Django + Django REST Framework (auth, users, categories, notes, and AI query).
- **Frontend**: Next.js (notes UI, categories, and the AI question modal).
- **Database**: PostgreSQL with **pgvector** for storing note embeddings.
- **AI / RAG**: Chunked notes → embeddings (sentence-transformers or fallback) → vector search → LLM summarization (OpenAI when configured).

---

## AI feature: what it is and how to use it

### What it does

The app can answer questions over **your notes** using a simple RAG (Retrieval-Augmented Generation) flow:

1. **Indexing**: When you create or edit a note, the backend chunks the text and stores embeddings in PostgreSQL (pgvector). You can also backfill existing notes with a management command.
2. **Query**: You ask a question (e.g. "What are my pending todos?" or "Summarize my notes"). The app embeds the question, finds the most relevant note chunks by vector similarity, and sends them to an LLM to produce a short, natural-language answer.
3. **Where to use it**:
   - **In the app**: On the Notes page, use the cactus icon to open the question modal. Type your question and send; the answer appears below.
   - **Via API**: `POST /api/v1/ai/query/` with a JSON body `{ "query": "Your question here", "top_k": 5 }` and header `Authorization: Token <your-auth-token>`.

### How to set it up

1. **Environment**: In the backend, set your OpenAI key (and optional model) so the app can call the LLM. For Docker, add to `backend/.envs/.local/.django` (or your env file):
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   OPENAI_MODEL=gpt-4o-mini   # optional; default is gpt-3.5-turbo
   ```
   If `OPENAI_API_KEY` is not set, the API still works but returns concatenated chunks instead of an LLM summary.

2. **Backfill embeddings** (for notes that already exist): Run once, or after adding many notes:
   ```bash
   docker compose exec backend python manage.py backfill_note_chunks
   ```
   New notes get chunks and embeddings automatically on create/update.

3. **Run the stack**: Start backend and frontend (e.g. `docker compose up`). Log in, create or open notes, then use the cactus modal or the API to ask questions.

### API reference (AI)

| Method | Endpoint              | Auth   | Body (JSON)                    | Response (200)        |
|--------|------------------------|--------|--------------------------------|------------------------|
| POST   | `/api/v1/ai/query/`    | Token  | `{ "query": "...", "top_k": 5 }` | `{ "answer": "...", "sources": [...] }` |

---

## How to build

```bash
docker-compose build
```

## How to run

```bash
docker-compose up
```

## Initial setup

Run the create-initial-db-objects command to create the superuser and base categories:

```bash
docker compose run --rm backend python manage.py create_init_objects
```

(Optional) Backfill note chunks for the AI feature:

```bash
docker compose exec backend python manage.py backfill_note_chunks
```

---

_Project built by Turbo_
