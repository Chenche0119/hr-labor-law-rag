"""
建立 ChromaDB 向量資料庫（法條庫 + 書籍庫）
使用 OpenAI text-embedding-3-small 做 embedding
"""
import json
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

DATA_DIR = Path(__file__).parent.parent / "data"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


def get_embeddings(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [e.embedding for e in resp.data]


def index_collection(
    chroma_client: chromadb.Client,
    openai_client: OpenAI,
    collection_name: str,
    documents: list[dict],
    content_key: str = "content",
) -> chromadb.Collection:
    col = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    existing_ids = set(col.get()["ids"])
    new_docs = [d for i, d in enumerate(documents) if str(i) not in existing_ids]

    if not new_docs:
        print(f"[SKIP] {collection_name} 已是最新狀態（{len(documents)} 筆）")
        return col

    print(f"[BUILD] {collection_name}: 新增 {len(new_docs)} 筆...")

    for batch_start in range(0, len(new_docs), BATCH_SIZE):
        batch = new_docs[batch_start : batch_start + BATCH_SIZE]
        texts = [d[content_key] for d in batch]
        embeddings = get_embeddings(openai_client, texts)

        ids = [str(batch_start + i) for i in range(len(batch))]
        metadatas = [{k: v for k, v in d.items() if k != content_key} for d in batch]

        col.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        print(f"  {batch_start + len(batch)}/{len(new_docs)}")

    print(f"[OK] {collection_name}: 共 {col.count()} 筆")
    return col


def main():
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # 法條庫
    laws_file = DATA_DIR / "laws" / "all_laws.json"
    if laws_file.exists():
        with open(laws_file, encoding="utf-8") as f:
            laws = json.load(f)
        index_collection(chroma_client, openai_client, "laws", laws)
    else:
        print(f"[WARN] 找不到 {laws_file}，請先執行 scripts/download_laws.py")

    # 書籍庫
    books_file = DATA_DIR / "books" / "processed_books.json"
    if books_file.exists():
        with open(books_file, encoding="utf-8") as f:
            books = json.load(f)
        index_collection(chroma_client, openai_client, "books", books)
    else:
        print(f"[WARN] 找不到 {books_file}，請先執行 scripts/process_books.py")


if __name__ == "__main__":
    main()
