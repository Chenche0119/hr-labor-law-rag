"""Layer 2 Router: classify a question into type A or B."""
from collections.abc import Callable
from typing import Literal

from src.config import CLASSIFY_MAX_TOKENS

ROUTER_PROMPT = (
    "你是一個問題類型分類器。將問題分為：\n"
    "A = 直接查詢型：問特定法條、數字、明確規定"
    "（例：特休幾天、加班費怎麼算）\n"
    "B = 爭議解釋型：問模糊地帶、實務見解、身份界定"
    "（例：承攬與僱傭如何區分）\n"
    "只回答 A 或 B，不要其他文字。"
)


def route(llm: Callable[..., str], question: str) -> Literal["A", "B"]:
    """Return 'A' (direct lookup) or 'B' (interpretation; the safe default)."""
    answer = llm(ROUTER_PROMPT, question, max_tokens=CLASSIFY_MAX_TOKENS)
    return "A" if answer.strip().upper().startswith("A") else "B"
