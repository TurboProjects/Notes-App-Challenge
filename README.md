# Notes App

A note-taking application that allows users to organize and manage their notes in different categories with an aesthetic interface

## About the code

There are three main components in this project:
- Backend API server: Django REST framework
- Frontend: Next.js
- Database: PostgreSQL

## How to build

```bash
docker compose build
```

## How to run

```bash
docker compose up
```

## Inital setup

Run the create initial db objects command to create the initial database objects: superuser and base categories.
```bash
docker compose run --rm backend python manage.py create_init_objects
```

## Makefile

A root `Makefile` wraps the common Docker Compose, Django and Next.js commands,
split into stack-level targets and `back`/`front` subcommands:

```bash
# Stack
make build                 # build all images
make up                    # run the full stack
make down                  # stop and remove containers

# Backend
make back init             # initial setup (superuser + base categories)
make back makemigrations   # create migrations (app=notes for a single app)
make back migrate          # apply migrations
make back runserver        # backend only on :8000
make back test             # run backend tests (path=... for a subset)

# Frontend
make front dev             # frontend only on :3000
make front lint            # next lint
make front build           # production build check
```

Run `make help` to list all targets.

_Project built by Turbo_
