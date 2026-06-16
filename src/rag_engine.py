"""RAG Engine: Guardrail -> Router -> Retrieval -> LLM generation.

- Embedding: sentence-transformers (local, free)
- LLM: Anthropic Claude
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import anthropic
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from src.config import (
    ANSWER_MAX_TOKENS,
    CHROMA_DIR,
    CLASSIFY_MAX_TOKENS,
    CONFIDENCE_THRESHOLD,
    EMBED_MODEL_NAME,
    LLM_MODEL,
)

load_dotenv(Path(__file__).parent.parent / ".env")

_embed_model = None


def get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        print("[load] embedding model...")
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embed_model


@dataclass
class RetrievedChunk:
    content: str
    source: str
    distance: float
    collection: str


@dataclass
class RAGResult:
    answer: str
    query_type: Literal["A", "B", "out_of_scope", "no_law"]
    chunks: list[RetrievedChunk] = field(default_factory=list)
    guardrail_passed: bool = True


class RAGEngine:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.embed_model = get_embed_model()
        self.chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._laws_col = None
        self._books_col = None

    @property
    def laws_col(self):
        if self._laws_col is None:
            self._laws_col = self.chroma.get_or_create_collection(
                "laws", metadata={"hnsw:space": "cosine"}
            )
        return self._laws_col

    @property
    def books_col(self):
        if self._books_col is None:
            self._books_col = self.chroma.get_or_create_collection(
                "books", metadata={"hnsw:space": "cosine"}
            )
        return self._books_col

    def _embed(self, text: str) -> list[float]:
        return self.embed_model.encode(text).tolist()

    def _llm(
        self, system: str, user: str, *, max_tokens: int, thinking: bool = False
    ) -> str:
        kwargs = {}
        if thinking:
            kwargs["thinking"] = {"type": "adaptive"}
        resp = self.client.messages.create(
            model=LLM_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            **kwargs,
        )
        return "".join(b.text for b in resp.content if b.type == "text")

    # ------------------------------------------------------------------
    # Layer 1: Guardrail
    # ------------------------------------------------------------------
    def guardrail(self, question: str) -> bool:
        system = (
            "你是一個問題範疇判斷器。判斷使用者的問題是否屬於「台灣勞工法律」範疇，"
            "包含：勞動基準法、勞工退休金、性別平等工作法、勞工保險、勞動合同等相關主題。\n"
            "只回答 YES 或 NO，不要其他文字。\n"
            "YES = 屬於台灣勞工法範疇\n"
            "NO = 不屬於（如天氣、程式設計、所得稅、董事薪資等）"
        )
        answer = self._llm(system, question, max_tokens=CLASSIFY_MAX_TOKENS)
        return answer.strip().upper().startswith("Y")

    # ------------------------------------------------------------------
    # Layer 2: Router
    # ------------------------------------------------------------------
    def router(self, question: str) -> Literal["A", "B"]:
        system = (
            "你是一個問題類型分類器。將問題分為：\n"
            "A = 直接查詢型：問特定法條、數字、明確規定"
            "（例：特休幾天、加班費怎麼算）\n"
            "B = 爭議解釋型：問模糊地帶、實務見解、身份界定"
            "（例：承攬與僱傭如何區分）\n"
            "只回答 A 或 B，不要其他文字。"
        )
        answer = self._llm(system, question, max_tokens=CLASSIFY_MAX_TOKENS)
        return "A" if answer.strip().upper().startswith("A") else "B"

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def _query_col(
        self, col, embedding: list[float], n: int
    ) -> list[RetrievedChunk]:
        count = col.count()
        if count == 0:
            return []
        results = col.query(
            query_embeddings=[embedding], n_results=min(n, count)
        )
        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            dist = results["distances"][0][i]
            source = meta.get("source", meta.get("law_name", "未知來源"))
            col_name = "laws" if col == self.laws_col else "books"
            chunks.append(
                RetrievedChunk(
                    content=doc,
                    source=source,
                    distance=dist,
                    collection=col_name,
                )
            )
        return chunks

    def retrieve_type_a(self, embedding: list[float]) -> list[RetrievedChunk]:
        return self._query_col(self.laws_col, embedding, n=5)

    def retrieve_type_b(self, embedding: list[float]) -> list[RetrievedChunk]:
        books = self._query_col(self.books_col, embedding, n=5)
        laws = self._query_col(self.laws_col, embedding, n=2)
        return books + laws

    # ------------------------------------------------------------------
    # LLM generation
    # ------------------------------------------------------------------
    SYSTEM_PROMPT = (
        "你是一位專業的台灣勞動法規顧問，專門協助企業HR人員查詢與理解勞動相關法規。\n"
        "請根據以下提供的法條與參考資料回答問題。\n"
        "回答時請：\n"
        "1. 引用具體條文（如：勞基法第30條）\n"
        "2. 以白話文解說法條含義\n"
        "3. 若資料中找不到答案，請明確說明，不要憑空捏造\n"
        "回答格式：結論 → 法條依據 → 白話說明"
    )

    def generate_answer(
        self, question: str, chunks: list[RetrievedChunk]
    ) -> str:
        context = "\n\n".join(f"【{c.source}】\n{c.content}" for c in chunks)
        return self._llm(
            self.SYSTEM_PROMPT,
            f"參考資料：\n{context}\n\n使用者問題：{question}",
            max_tokens=ANSWER_MAX_TOKENS,
            thinking=True,
        )

    # ------------------------------------------------------------------
    # Main query entry point
    # ------------------------------------------------------------------
    def query(self, question: str) -> RAGResult:
        if not self.guardrail(question):
            return RAGResult(
                answer=(
                    "抱歉，本系統僅提供台灣勞工法律相關問題的查詢服務，"
                    "您的問題超出服務範疇。"
                ),
                query_type="out_of_scope",
                guardrail_passed=False,
            )

        q_type = self.router(question)
        embedding = self._embed(question)

        if q_type == "A":
            chunks = self.retrieve_type_a(embedding)
            if not chunks or chunks[0].distance > CONFIDENCE_THRESHOLD:
                return RAGResult(
                    answer=(
                        "根據現行法規資料庫，目前無明確的法條規定對應您的問題。"
                        "建議諮詢專業法律顧問或查閱勞動部最新公告。"
                    ),
                    query_type="no_law",
                    chunks=chunks,
                )
            chunks = [c for c in chunks if c.distance <= CONFIDENCE_THRESHOLD]
        else:
            chunks = self.retrieve_type_b(embedding)

        answer = self.generate_answer(question, chunks)
        return RAGResult(answer=answer, query_type=q_type, chunks=chunks)
