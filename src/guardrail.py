"""Layer 1 Guardrail: is the question within Taiwan labor-law scope?"""
from collections.abc import Callable

from src.config import CLASSIFY_MAX_TOKENS

GUARDRAIL_PROMPT = (
    "你是台灣勞工法範疇判斷器。判斷問題是否屬於「台灣勞動／勞工法律」範疇。\n"
    "只要與勞工的權利義務、勞動關係相關即為 YES，"
    "即使資料庫未必有對應法條。\n"
    "\n"
    "屬於範疇（YES）包含但不限於：\n"
    "- 勞動契約、從屬性與勞工身分認定（含醫護、飛航機師、外送平台、"
    "保險業務員等特殊工作者是否為勞工）\n"
    "- 工資、加班費；工時、休息、例假、輪班\n"
    "- 職業災害與過勞、雇主補償／賠償責任\n"
    "- 解僱、資遣、預告、最後手段性\n"
    "- 離職後競業禁止、最低服務年限、調職\n"
    "- 退休、勞工退休金；勞工保險、就業保險\n"
    "- 性別平等、職場性騷擾防治、育嬰留停、產假\n"
    "- 工會、團體協約、爭議行為（罷工）、大量解僱、職場霸凌申訴\n"
    "\n"
    "不屬於範疇（NO）：純稅務、公司治理（董事／委任經理人報酬）、"
    "智慧財產（商標／專利）、租賃、與勞動權義無關的純醫療或技術問題、一般常識。\n"
    "\n"
    "範例：\n"
    "Q：勞工因長期加班罹患心血管疾病，雇主要負職災補償責任嗎？ A：YES\n"
    "Q：保險業務員與公司是僱傭還是承攬關係？ A：YES\n"
    "Q：工會發起罷工需要經過什麼程序？ A：YES\n"
    "Q：公司今年要繳多少營利事業所得稅？ A：NO\n"
    "Q：公司董事的報酬由誰決定？ A：NO\n"
    "Q：辦公室租約到期房東可以漲租嗎？ A：NO\n"
    "\n"
    "只回答 YES 或 NO，不要其他文字。"
)


def check_scope(llm: Callable[..., str], question: str) -> bool:
    """Return True if the question is within Taiwan labor-law scope."""
    answer = llm(GUARDRAIL_PROMPT, question, max_tokens=CLASSIFY_MAX_TOKENS)
    return answer.strip().upper().startswith("Y")
