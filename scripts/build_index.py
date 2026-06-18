"""Build the ChromaDB vector store (laws + books).

Uses local sentence-transformers embeddings (free).
"""
import json
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import BATCH_SIZE, CHROMA_DIR, DATA_DIR, EMBED_MODEL_NAME

CHROMA_DIR.mkdir(parents=True, exist_ok=True)


def index_collection(
    chroma_client, model, collection_name, documents, content_key="content"
):
    col = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    existing_count = col.count()
    if existing_count >= len(documents):
        print(
            f"[SKIP] {collection_name} already up to date "
            f"({existing_count} items)"
        )
        return col

    # Rebuild (drop then recreate)
    chroma_client.delete_collection(collection_name)
    col = chroma_client.create_collection(
        collection_name, metadata={"hnsw:space": "cosine"}
    )

    print(f"[BUILD] {collection_name}: {len(documents)} items...")
    texts = [d[content_key] for d in documents]

    for start in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[start : start + BATCH_SIZE]
        batch_docs = documents[start : start + BATCH_SIZE]
        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()
        ids = [str(start + i) for i in range(len(batch_texts))]
        metadatas = [
            {k: v for k, v in d.items() if k != content_key} for d in batch_docs
        ]
        col.add(
            ids=ids,
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=metadatas,
        )
        print(f"  {start + len(batch_texts)}/{len(texts)}")

    print(f"[OK] {collection_name}: {col.count()} items total")
    return col


def main():
    print("[load] embedding model...")
    model = SentenceTransformer(EMBED_MODEL_NAME)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    laws_file = DATA_DIR / "laws" / "all_laws.json"
    if laws_file.exists():
        with open(laws_file, encoding="utf-8") as f:
            laws = json.load(f)
        index_collection(chroma_client, model, "laws", laws)
    else:
        print(
            f"[WARN] {laws_file} not found; "
            "run scripts/download_laws.py first"
        )

    books_file = DATA_DIR / "books" / "processed_books.json"
    if books_file.exists():
        with open(books_file, encoding="utf-8") as f:
            books = json.load(f)
        index_collection(chroma_client, model, "books", books)
    else:
        print(f"[INFO] no book data ({books_file}); skipping books collection")


if __name__ == "__main__":
    main()
