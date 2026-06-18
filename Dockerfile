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

# Bake the embedding model into the image. Only config.py (the model name)
# is copied here, so editing application code never invalidates this layer.
# The HF cache mount persists the download across builds, so even if the
# layer is invalidated the model is fetched from the network at most once.
COPY src/config.py ./src/config.py
COPY scripts/preload_model.py ./scripts/preload_model.py
RUN --mount=type=cache,target=/opt/hf-cache \
    HF_HOME=/opt/hf-cache uv run --no-project python scripts/preload_model.py \
 && mkdir -p /app/.cache/huggingface \
 && cp -a /opt/hf-cache/. /app/.cache/huggingface/

# Copy the rest of the project and install it
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

EXPOSE 5001

ENTRYPOINT ["bash", "docker-entrypoint.sh"]
