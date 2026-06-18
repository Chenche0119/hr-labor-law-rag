"""Central configuration: all tunable parameters live here (no hardcoding)."""
import os
from pathlib import Path

# Project root (this file is at <root>/src/config.py)
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
LAWS_DIR = DATA_DIR / "laws"
BOOKS_DIR = DATA_DIR / "books"
CHROMA_DIR = ROOT_DIR / "chroma_db"

# LLM (Anthropic Claude)
LLM_MODEL = "claude-opus-4-8"
CLASSIFY_MAX_TOKENS = 16  # guardrail / router only emit YES-NO or A-B
ANSWER_MAX_TOKENS = 8192  # must cover adaptive thinking + the visible answer

# Embedding (local sentence-transformers, multilingual)
EMBED_MODEL_NAME = "BAAI/bge-m3"

# Retrieval confidence threshold (cosine distance; smaller is more relevant).
# Calibrated for bge-m3: relevant queries score <=0.42, irrelevant ~0.58.
CONFIDENCE_THRESHOLD = 0.5

# Vector index building
BATCH_SIZE = 128

# Book chunking
CHUNK_SIZE = 400  # target characters per chunk
OVERLAP = 50  # overlapping characters between chunks

# Law crawler
TARGET_LAWS = [
    {"name": "勞動基準法", "pcode": "N0030001"},
    {"name": "勞工退休金條例", "pcode": "N0030020"},
    {"name": "性別平等工作法", "pcode": "N0030014"},
    {"name": "勞工保險條例", "pcode": "N0050001"},
]
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# Web server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5001"))

# Gunicorn (production WSGI, used in Docker). One worker keeps a single copy
# of the embedding model in memory; threads handle concurrency for the
# I/O-bound LLM calls. Timeout covers long answer generation.
GUNICORN_WORKERS = int(os.getenv("GUNICORN_WORKERS", "1"))
GUNICORN_THREADS = int(os.getenv("GUNICORN_THREADS", "4"))
GUNICORN_TIMEOUT = int(os.getenv("GUNICORN_TIMEOUT", "120"))
