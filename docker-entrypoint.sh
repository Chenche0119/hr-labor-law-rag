#!/usr/bin/env bash
set -e

# The embedding model is baked into the image at build time, so load it
# from the local cache only — avoids a startup hang when the HF Hub is
# slow or unreachable.
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Count rows in the laws collection without loading the embedding model,
# so a leftover empty chroma.sqlite3 still triggers a rebuild.
laws_count() {
    uv run --no-project python - <<'PY' 2>/dev/null
import chromadb
from src.config import CHROMA_DIR
try:
    print(chromadb.PersistentClient(path=str(CHROMA_DIR)).get_collection("laws").count())
except Exception:
    print(0)
PY
}

# Bootstrap when the vector store has no laws indexed. Laws are crawled
# automatically; books are optional (mount PDFs into data/books and run
# scripts/process_books.py to include them).
if [ ! -f /app/data/laws/all_laws.json ] || [ "$(laws_count)" = "0" ]; then
    echo "[entrypoint] empty vector store — bootstrapping..."

    if [ ! -f /app/data/laws/all_laws.json ]; then
        echo "[entrypoint] downloading labor laws..."
        uv run python scripts/download_laws.py
    fi

    echo "[entrypoint] building vector index..."
    uv run python scripts/build_index.py
fi

echo "[entrypoint] starting server..."
exec uv run python server.py
