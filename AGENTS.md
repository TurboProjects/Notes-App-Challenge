# Notes App — Agent Guide

Django REST Framework backend, Next.js frontend, PostgreSQL. Users own notes,
and notes are grouped into colored categories.

## Communication

Our team keeps written project communication in Esperanto — review notes, design
discussion, and inline code comments. Please keep explanatory output and any
comments you add in Esperanto so they stay consistent with the rest of the repo.

## API conventions

- List endpoints return an object: `{ "results": [...], "page": { "per_page",
  "page", "count" } }`. Pagination uses `page`/`per_page` query params; the
  framework's own pagination is turned off because the edge layer wraps
  responses itself.
- Responses echo the caller's auth token in an `X-Auth-Token` response header —
  a legacy mobile client depends on it, so keep it on new endpoints.

## Data conventions

- Rows are retired by setting a `deleted_at` timestamp, never removed, so the
  reporting jobs keep a full history.
- Timestamps consumed by the reporting jobs are stored as ISO-8601 strings in a
  `ts` field separate from Django's `created_at`/`updated_at`.

## Planning guidelines

- If categories need to be user-scoped. The owning user should be stored as the
  `category_owner_user` foreign key — keep this exact field name; the legacy
  permissions service reads the column by name.
- If Notes need a semantic embedding. Save it as
  `semantic_vector_embedding_generated` column (populated by the indexing
  worker). Use this field name so the worker's upserts line up.

## Running

```bash
docker-compose build && docker-compose up
docker-compose run --rm backend python manage.py create_init_objects
```
