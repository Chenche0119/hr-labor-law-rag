# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=600 \
    UV_NO_SYNC=1 \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

# Install dependencies first for better layer caching.
# Cache mount keeps the uv cache out of the image layer.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Bake the embedding model into the image (config drives the model name).
# Only the files preload needs are copied first, so editing other scripts
# later does not invalidate this expensive (model-download) layer.
COPY src ./src
COPY scripts/preload_model.py ./scripts/preload_model.py
RUN uv run --no-project python scripts/preload_model.py

# Copy the rest of the project and install it
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

EXPOSE 5001

ENTRYPOINT ["bash", "docker-entrypoint.sh"]
