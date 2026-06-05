FROM docker.io/python:3.12-slim-bookworm

ARG BUILD_ENVIRONMENT=local
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  BUILD_ENV=${BUILD_ENVIRONMENT} \
  UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  PATH="/app/.venv/bin:$PATH"

# uv binary, pinned to a minor version
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /usr/local/bin/

WORKDIR ${APP_HOME}

# Translations dependencies only — psycopg[binary] ships its own libpq,
# so build-essential/libpq-dev are no longer needed.
RUN apt-get update && apt-get install --no-install-recommends -y \
  gettext \
  && rm -rf /var/lib/apt/lists/*

# Dependency files first so the uv sync layer caches across code changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
  if [ "${BUILD_ENVIRONMENT}" = "production" ]; then \
  uv sync --frozen --no-dev; \
  else \
  uv sync --frozen; \
  fi

COPY ./compose/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint && chmod +x /entrypoint

COPY ./compose/start /start
RUN sed -i 's/\r$//g' /start && chmod +x /start

# copy application code to WORKDIR
COPY . ${APP_HOME}

ENTRYPOINT ["/entrypoint"]
