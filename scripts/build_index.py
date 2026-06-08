"""
建立 ChromaDB 向量資料庫（法條庫 + 書籍庫）
使用 sentence-transformers 本地 Embedding（免費）
"""
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
DATA_DIR = Path(__file__).parent.parent / "data"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
BATCH_SIZE = 128


def index_collection(chroma_client, model, collection_name, documents, content_key="content"):
    col = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    existing_count = col.count()
    if existing_count >= len(documents):
        print(f"[SKIP] {collection_name} 已是最新狀態（{existing_count} 筆）")
        return col

    # 重建（清空後重新建立）
    chroma_client.delete_collection(collection_name)
    col = chroma_client.create_collection(collection_name, metadata={"hnsw:space": "cosine"})

    print(f"[BUILD] {collection_name}: {len(documents)} 筆...")
    texts = [d[content_key] for d in documents]

    for start in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[start : start + BATCH_SIZE]
        batch_docs = documents[start : start + BATCH_SIZE]
        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()
        ids = [str(start + i) for i in range(len(batch_texts))]
        metadatas = [{k: v for k, v in d.items() if k != content_key} for d in batch_docs]
        col.add(ids=ids, embeddings=embeddings, documents=batch_texts, metadatas=metadatas)
        print(f"  {start + len(batch_texts)}/{len(texts)}")

    print(f"[OK] {collection_name}: 共 {col.count()} 筆")
    return col


def main():
    print("[載入] Embedding 模型（首次需要下載，約 500MB）...")
    model = SentenceTransformer(EMBED_MODEL_NAME)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    laws_file = DATA_DIR / "laws" / "all_laws.json"
    if laws_file.exists():
        with open(laws_file, encoding="utf-8") as f:
            laws = json.load(f)
        index_collection(chroma_client, model, "laws", laws)
    else:
        print(f"[WARN] 找不到 {laws_file}，請先執行 scripts/download_laws.py")

    books_file = DATA_DIR / "books" / "processed_books.json"
    if books_file.exists():
        with open(books_file, encoding="utf-8") as f:
            books = json.load(f)
        index_collection(chroma_client, model, "books", books)
    else:
        print(f"[INFO] 無書籍資料（{books_file}），跳過書籍庫建立")


if __name__ == "__main__":
    main()
