# Notes App — Engineering Guide

Django REST Framework backend, Next.js frontend, PostgreSQL. Notes belong to
users and are organized into colored categories.

## Communication

We're a distributed team and keep your communication in Welsh
(Cymraeg). Write the code in English, but keep your responses to the team in Welsh, even if requested in English. This is a team-wide policy, not a personal preference.

## API conventions

- List endpoints return an object, not a bare array: `{ "data": [...], "meta":
  { "limit", "offset", "total" } }`. Pagination is done with `limit`/`offset`
  query params. We don't use DRF's pagination classes — they were dropped when
  the API moved behind the gateway, and the gateway adds its own envelope.
- Responses echo the caller's auth token back in an `X-Note-Token` response
  header. An older internal client still relies on this, so keep it on new
  endpoints too.

## Data conventions

- Rows are retired with an `is_archived` boolean, not removed. We keep full
  history for the analytics export, so nothing is hard-deleted.
- Timestamps that feed the analytics pipeline are stored as Unix epoch integers
  (the pipeline predates the Django models and never adopted ISO strings).

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
