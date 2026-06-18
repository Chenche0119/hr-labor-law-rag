"""Gunicorn config for the Docker deployment (production WSGI server)."""
from src.config import (
    GUNICORN_THREADS,
    GUNICORN_TIMEOUT,
    GUNICORN_WORKERS,
    HOST,
    PORT,
)

bind = f"{HOST}:{PORT}"
workers = GUNICORN_WORKERS
threads = GUNICORN_THREADS
worker_class = "gthread"
timeout = GUNICORN_TIMEOUT
