# Notes App — development commands (everything runs through Docker Compose)
#
# Usage:
#   make <stack-cmd>          e.g. make up, make build
#   make back <cmd>           e.g. make back test path=api/notes/test/test_views.py
#   make front <cmd>          e.g. make front lint
#
# One subcommand per invocation (make back test front lint is NOT supported).

COMPOSE ?= docker compose
RUN_BACKEND = $(COMPOSE) run --rm backend
RUN_FRONTEND = $(COMPOSE) run --rm frontend

# Optional args: make back test path=...   make back makemigrations app=...
path ?=
app ?=

.DEFAULT_GOAL := help

# When the first goal is "back" or "front", treat the remaining goals as a
# subcommand: declare them as no-ops and re-invoke make on back-<cmd>/front-<cmd>.
ifneq (,$(filter back front,$(firstword $(MAKECMDGOALS))))
  SUBCMD := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(SUBCMD):;@:)
endif

.PHONY: help build up down logs back front \
	back-runserver back-makemigrations back-migrate back-shell back-init \
	back-test back-lint back-mypy back-sync back-help \
	front-dev front-lint front-build front-shell front-install front-help

# ==== Stack =================================================================

help: ## Show this help
	@echo "Stack:"
	@grep -E '^(help|build|up|down|logs|back|front):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo "Backend (make back <cmd>):"
	@grep -E '^back-[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | sed 's/^back-/back /' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo "Frontend (make front <cmd>):"
	@grep -E '^front-[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | sed 's/^front-/front /' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

build: ## Build all docker images
	$(COMPOSE) build

up: ## Start the full stack (backend :8000, frontend :3000, postgres)
	# --renew-anon-volumes: refresh the /app/.venv anonymous volume from the
	# image after a rebuild with new dependencies (otherwise it goes stale).
	$(COMPOSE) up --renew-anon-volumes

down: ## Stop and remove containers
	$(COMPOSE) down

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

back: ## Backend commands: make back <cmd> (see make back help)
	@$(MAKE) --no-print-directory $(if $(SUBCMD),back-$(SUBCMD),back-help)

front: ## Frontend commands: make front <cmd> (see make front help)
	@$(MAKE) --no-print-directory $(if $(SUBCMD),front-$(SUBCMD),front-help)

# ==== Backend ===============================================================

back-help: ## List backend subcommands
	@echo "Backend (make back <cmd>):"
	@grep -E '^back-[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | sed 's/^back-/back /' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

back-runserver: ## Start the backend only (runs migrate + uvicorn ASGI on :8000)
	$(COMPOSE) up --renew-anon-volumes backend

back-makemigrations: ## Create new migrations (optionally: make back makemigrations app=notes)
	$(RUN_BACKEND) python manage.py makemigrations $(app)

back-migrate: ## Apply database migrations
	$(RUN_BACKEND) python manage.py migrate

back-shell: ## Open a Django shell
	$(RUN_BACKEND) python manage.py shell

back-init: ## Create initial db objects (superuser + base categories)
	$(RUN_BACKEND) python manage.py create_init_objects

back-test: ## Run backend tests (optionally: make back test path=api/notes/test/test_views.py)
	$(RUN_BACKEND) pytest $(path)

back-lint: ## Run ruff over the backend
	$(RUN_BACKEND) ruff check .

back-mypy: ## Run mypy over the backend
	$(RUN_BACKEND) mypy api

back-sync: ## Create/update the local backend venv with uv (for IDE tooling)
	cd backend && uv sync

# ==== Frontend ==============================================================

front-help: ## List frontend subcommands
	@echo "Frontend (make front <cmd>):"
	@grep -E '^front-[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | sed 's/^front-/front /' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

front-dev: ## Start the frontend only (next dev on :3000)
	$(COMPOSE) up frontend

front-lint: ## Run next lint
	$(RUN_FRONTEND) npm run lint

front-build: ## Run a production build check (next build)
	# The image sets NODE_ENV=development (for next dev); next build needs
	# production or it mixes dev/prod runtimes and prerendering fails.
	$(COMPOSE) run --rm -e NODE_ENV=production frontend npm run build

front-shell: ## Open a shell in the frontend container (alpine: sh)
	$(RUN_FRONTEND) sh

front-install: ## Rebuild the frontend image after changing package.json
	# node_modules lives in the image (mounted as an anonymous volume),
	# so new dependencies require rebuilding the image.
	$(COMPOSE) build frontend
