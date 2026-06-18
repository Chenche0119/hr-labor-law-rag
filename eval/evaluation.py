"""
評估腳本：Guardrail / Router 功能驗證 + 對照實驗
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag_engine import RAGEngine

engine = RAGEngine()

# -------------------------------------------------------------------
# 評估題組（依計劃書設計）
# -------------------------------------------------------------------
TEST_CASES = {
    "type_a": [  # A 型：直接查詢型（預期通過 Guardrail、Router=A）
        "特休假幾天？",
        "加班費如何計算？",
        "試用期最長幾個月？",
        "勞工退休金雇主應提繳多少比例？",
        "產假幾天？",
        "育嬰留停可以請幾年？",
        "每週法定工時是幾小時？",
        "資遣費如何計算？",
        "勞工保險普通事故保險費率是多少？",
        "懷孕員工可以調職嗎？",
    ],
    "type_b": [  # B 型：爭議解釋型（預期通過 Guardrail、Router=B）
        "承攬跟僱傭怎麼區分？",
        "派遣工與正職員工的差異是什麼？",
        "打卡紀錄可以算加班的依據嗎？",
        "主管可以算加班費嗎？",
        "試用期解雇需要預告嗎？",
        "外籍勞工適用勞基法嗎？",
        "家事服務業雇主的責任範圍？",
        "自僱者有沒有勞動保護？",
        "兼職員工享有特休假嗎？",
        "雇主單方面降薪合法嗎？",
    ],
    "no_law": [  # 無明確法條的勞工法問題（預期通過 Guardrail、信心門檻攔截）
        "公司霸凌如何申訴？",
        "職場語言暴力的法律責任？",
        "遠距工作的相關法規？",
        "AI 取代人力時的資遣規定？",
        "平台經濟工作者（如外送員）的保護？",
    ],
    "out_of_scope": [  # 超出範疇（預期 Guardrail 攔截）
        "今天天氣如何？",
        "幫我寫一段 Python 程式",
        "公司所得稅怎麼申報？",
        "董事會薪酬有什麼規定？",
        "如何投資股票？",
        "台灣憲法第幾條保障言論自由？",
        "食品安全法規是什麼？",
        "交通違規罰鍰怎麼算？",
        "房東可以漲租金嗎？",
        "公司商標如何申請？",
    ],
    # 邊界測試（held-out：刻意不與 guardrail prompt 的 few-shot 範例重複）
    "boundary_in_scope": [  # 邊界但屬勞工法（預期放行）
        "醫師過勞死，雇主要負職業災害責任嗎？",
        "外送平台的外送員算不算勞工？",
        "飛航機師的休息時間有法律規範嗎？",
        "醫護人員適用勞基法的工時規定嗎？",
        "離職後競業禁止條款一定有效嗎？",
        "雇主可以單方面把員工調到外縣市嗎？",
        "最低服務年限約款合法嗎？",
        "職場性騷擾可以向公司申訴嗎？",
        "大量解僱勞工有特別的保護規定嗎？",
        "勞工可以組工會嗎？",
    ],
    "boundary_out_scope": [  # 邊界但非勞工法（預期攔截）
        "公司的營業稅申報期限是什麼時候？",
        "上市公司獨立董事的薪酬如何規範？",
        "公司商標要怎麼註冊？",
        "新創公司增資發行新股的程序？",
        "辦公室租約的押金可以退嗎？",
        "員工旅遊推薦哪些景點？",
    ],
}


def run_guardrail_router_eval():
    print("=" * 60)
    print("評估一：Guardrail 與 Router 功能驗證")
    print("=" * 60)

    results = {
        "guardrail_intercept": {
            "correct": 0,
            "total": len(TEST_CASES["out_of_scope"]),
        },
        "guardrail_pass": {
            "correct": 0,
            "total": (
                len(TEST_CASES["type_a"])
                + len(TEST_CASES["type_b"])
                + len(TEST_CASES["no_law"])
            ),
        },
        "router_a": {"correct": 0, "total": len(TEST_CASES["type_a"])},
        "router_b": {"correct": 0, "total": len(TEST_CASES["type_b"])},
    }

    # Guardrail 攔截準確率
    print("\n[Guardrail 攔截測試]")
    for q in TEST_CASES["out_of_scope"]:
        passed = engine.guardrail(q)
        correct = not passed
        results["guardrail_intercept"]["correct"] += int(correct)
        mark = "✓" if correct else "✗"
        print(f"  {mark} [{('攔截' if not passed else '未攔截')}] {q}")

    # Guardrail 放行準確率
    print("\n[Guardrail 放行測試]")
    in_scope = (
        TEST_CASES["type_a"] + TEST_CASES["type_b"] + TEST_CASES["no_law"]
    )
    for q in in_scope:
        passed = engine.guardrail(q)
        correct = passed
        results["guardrail_pass"]["correct"] += int(correct)
        mark = "✓" if correct else "✗"
        print(f"  {mark} [{('放行' if passed else '錯誤攔截')}] {q}")

    # Router 分類準確率
    print("\n[Router A 型測試]")
    for q in TEST_CASES["type_a"]:
        q_type = engine.router(q)
        correct = q_type == "A"
        results["router_a"]["correct"] += int(correct)
        mark = "✓" if correct else "✗"
        print(f"  {mark} [Router={q_type}] {q}")

    print("\n[Router B 型測試]")
    for q in TEST_CASES["type_b"]:
        q_type = engine.router(q)
        correct = q_type == "B"
        results["router_b"]["correct"] += int(correct)
        mark = "✓" if correct else "✗"
        print(f"  {mark} [Router={q_type}] {q}")

    print("\n" + "=" * 60)
    print("評估結果摘要：")
    for key, v in results.items():
        pct = v["correct"] / v["total"] * 100 if v["total"] > 0 else 0
        label = {
            "guardrail_intercept": "Guardrail 攔截準確率",
            "guardrail_pass": "Guardrail 放行準確率",
            "router_a": "Router A 型準確率",
            "router_b": "Router B 型準確率",
        }[key]
        print(f"  {label}: {v['correct']}/{v['total']} = {pct:.1f}%")

    return results


def run_boundary_eval():
    """邊界測試：量化 guardrail 在範疇邊界的對錯。"""
    print("\n" + "=" * 60)
    print("評估三：Guardrail 邊界測試")
    print("=" * 60)

    results = {
        "boundary_in_scope": {
            "correct": 0,
            "total": len(TEST_CASES["boundary_in_scope"]),
            "false_negative": [],
        },
        "boundary_out_scope": {
            "correct": 0,
            "total": len(TEST_CASES["boundary_out_scope"]),
            "false_positive": [],
        },
    }

    print("\n[邊界 - 應放行]")
    for q in TEST_CASES["boundary_in_scope"]:
        passed = engine.guardrail(q)
        results["boundary_in_scope"]["correct"] += int(passed)
        if not passed:
            results["boundary_in_scope"]["false_negative"].append(q)
        print(f"  {'✓' if passed else '✗ 誤擋'} {q}")

    print("\n[邊界 - 應攔截]")
    for q in TEST_CASES["boundary_out_scope"]:
        passed = engine.guardrail(q)
        results["boundary_out_scope"]["correct"] += int(not passed)
        if passed:
            results["boundary_out_scope"]["false_positive"].append(q)
        print(f"  {'✓' if not passed else '✗ 誤放'} {q}")

    print("\n邊界測試結果：")
    for key, v in results.items():
        pct = v["correct"] / v["total"] * 100 if v["total"] > 0 else 0
        print(f"  {key}: {v['correct']}/{v['total']} = {pct:.1f}%")

    return results


def run_comparison_experiment(
    questions: list[str], condition: str
) -> list[dict]:
    """執行對照實驗，回傳每題的答案與評分空間"""
    print(f"\n[對照實驗：{condition}]")
    records = []
    for q in questions:
        result = engine.query(q)
        records.append({
            "question": q,
            "answer": result.answer,
            "query_type": result.query_type,
            "sources": [c.source for c in result.chunks],
            "condition": condition,
            # 評分欄位（人工填寫）
            "correctness": None,
            "completeness": None,
            "hallucination": None,
            "source_citation": None,
        })
        print(f"  Q: {q[:40]}...")
        print(f"  A: {result.answer[:80]}...\n")

    return records


def main():
    # 評估一：功能驗證
    eval1_results = run_guardrail_router_eval()

    # 評估三：Guardrail 邊界測試
    boundary_results = run_boundary_eval()

    # 評估二：對照實驗（模型升級）
    print("\n" + "=" * 60)
    print("評估二：對照實驗（A型+B型 各10題）")
    comparison_qs = TEST_CASES["type_a"][:5] + TEST_CASES["type_b"][:5]
    records = run_comparison_experiment(
        comparison_qs, condition="Claude Opus 4.8"
    )

    # 輸出結果 JSON
    output = {
        "eval1_guardrail_router": eval1_results,
        "eval2_comparison": records,
        "eval3_boundary": boundary_results,
    }
    out_file = Path(__file__).parent / "eval_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n評估結果已儲存至 {out_file}")


if __name__ == "__main__":
    main()
