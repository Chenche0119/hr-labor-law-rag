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
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Retrieval confidence threshold (cosine distance; smaller is more relevant)
CONFIDENCE_THRESHOLD = 0.6

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

# Flask server
PORT = int(os.getenv("PORT", "5001"))
