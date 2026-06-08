"""
RAG Engine：Guardrail → Router → Retrieval → LLM 生成
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import anthropic
import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

EMBED_MODEL = "text-embedding-3-small"
LLM_MODEL = "claude-haiku-4-5-20251001"  # 開發期用 Haiku
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# 信心門檻（A 型問題用，ChromaDB cosine distance，越小越相關）
CONFIDENCE_THRESHOLD = 0.45


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
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._laws_col = None
        self._books_col = None

    @property
    def laws_col(self):
        if self._laws_col is None:
            self._laws_col = self.chroma.get_or_create_collection("laws", metadata={"hnsw:space": "cosine"})
        return self._laws_col

    @property
    def books_col(self):
        if self._books_col is None:
            self._books_col = self.chroma.get_or_create_collection("books", metadata={"hnsw:space": "cosine"})
        return self._books_col

    def _embed(self, text: str) -> list[float]:
        resp = self.openai.embeddings.create(model=EMBED_MODEL, input=[text])
        return resp.data[0].embedding

    def _llm(self, system: str, user: str) -> str:
        msg = self.claude.messages.create(
            model=LLM_MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text

    # ------------------------------------------------------------------
    # 第一層：Guardrail
    # ------------------------------------------------------------------
    def guardrail(self, question: str) -> bool:
        """回傳 True 表示問題在台灣勞工法範疇內"""
        system = (
            "你是一個問題範疇判斷器。判斷使用者的問題是否屬於「台灣勞工法律」範疇，"
            "包含：勞動基準法、勞工退休金、性別平等工作法、勞工保險、勞動合同等相關主題。\n"
            "只回答 YES 或 NO，不要其他文字。\n"
            "YES = 屬於台灣勞工法範疇\n"
            "NO = 不屬於（如天氣、程式設計、所得稅、董事薪資等）"
        )
        answer = self._llm(system, question).strip().upper()
        return answer.startswith("Y")

    # ------------------------------------------------------------------
    # 第二層：Router
    # ------------------------------------------------------------------
    def router(self, question: str) -> Literal["A", "B"]:
        """
        A = 直接查詢型（有明確法條依據的數字、規定）
        B = 爭議解釋型（模糊地帶、實務見解、身份界定）
        """
        system = (
            "你是一個問題類型分類器。將問題分為：\n"
            "A = 直接查詢型：問特定法條、數字、明確規定（例：特休幾天、加班費怎麼算）\n"
            "B = 爭議解釋型：問模糊地帶、實務見解、身份界定（例：承攬與僱傭如何區分）\n"
            "只回答 A 或 B，不要其他文字。"
        )
        answer = self._llm(system, question).strip().upper()
        return "A" if answer.startswith("A") else "B"

    # ------------------------------------------------------------------
    # 檢索
    # ------------------------------------------------------------------
    def _query_collection(self, col, embedding: list[float], n: int) -> list[RetrievedChunk]:
        results = col.query(query_embeddings=[embedding], n_results=min(n, col.count() or 1))
        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            dist = results["distances"][0][i]
            source = meta.get("source", meta.get("law_name", "未知來源"))
            collection_name = "laws" if col == self.laws_col else "books"
            chunks.append(RetrievedChunk(content=doc, source=source, distance=dist, collection=collection_name))
        return chunks

    def retrieve_type_a(self, embedding: list[float]) -> list[RetrievedChunk]:
        """A 型：只查法條庫 Top-5"""
        return self._query_collection(self.laws_col, embedding, n=5)

    def retrieve_type_b(self, embedding: list[float]) -> list[RetrievedChunk]:
        """B 型：書籍庫 Top-5 + 法條庫 Top-2"""
        book_chunks = self._query_collection(self.books_col, embedding, n=5)
        law_chunks = self._query_collection(self.laws_col, embedding, n=2)
        return book_chunks + law_chunks

    # ------------------------------------------------------------------
    # LLM 生成
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

    def generate_answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        context = "\n\n".join(
            f"【{c.source}】\n{c.content}" for c in chunks
        )
        user_prompt = f"參考資料：\n{context}\n\n使用者問題：{question}"
        return self._llm(self.SYSTEM_PROMPT, user_prompt)

    # ------------------------------------------------------------------
    # 主要查詢入口
    # ------------------------------------------------------------------
    def query(self, question: str) -> RAGResult:
        # Guardrail
        if not self.guardrail(question):
            return RAGResult(
                answer="抱歉，本系統僅提供台灣勞工法律相關問題的查詢服務，您的問題超出服務範疇。",
                query_type="out_of_scope",
                guardrail_passed=False,
            )

        # Router
        q_type = self.router(question)
        embedding = self._embed(question)

        if q_type == "A":
            chunks = self.retrieve_type_a(embedding)
            # 信心門檻：最相關的 chunk 距離若超過閾值，視為無明確法條
            if not chunks or chunks[0].distance > CONFIDENCE_THRESHOLD:
                return RAGResult(
                    answer="根據現行法規資料庫，目前無明確的法條規定對應您的問題。建議諮詢專業法律顧問或查閱勞動部最新公告。",
                    query_type="no_law",
                    chunks=chunks,
                )
            # 只保留通過門檻的 chunks
            chunks = [c for c in chunks if c.distance <= CONFIDENCE_THRESHOLD]
        else:
            chunks = self.retrieve_type_b(embedding)

        answer = self.generate_answer(question, chunks)
        return RAGResult(answer=answer, query_type=q_type, chunks=chunks)
