"""Pre-download the embedding model at Docker build time.

Baking the model into the image avoids a network wait (and failure risk)
during first-run index building.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from sentence_transformers import SentenceTransformer

from src.config import EMBED_MODEL_NAME

SentenceTransformer(EMBED_MODEL_NAME)
print(f"[preload] cached embedding model: {EMBED_MODEL_NAME}")
