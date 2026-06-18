"""評估 Guardrail 與 Router 兩個 LLM 分類器的嚴謹指標。

題組為 held-out（不與 src/guardrail.py 的 few-shot 範例重複），標籤對齊現行
prompt 定義：
- Guardrail：in-scope = 任何台灣勞工法主題（應放行）；
  out-scope = 非勞工法（應攔截）。
- Router：A = 直接查詢特定法條/數字/明確規定；B = 爭議/實務/身份界定。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.guardrail import check_scope
from src.rag_engine import RAGEngine
from src.router import route

engine = RAGEngine()

TEST_CASES = {
    # Router 正樣本：明確 A（直接查特定數字/法條）
    "router_a": [
        "勞工每日正常工作時間上限是幾小時？",
        "勞工繼續工作滿一年，可以有幾天特別休假？",
        "資遣費的計算基準為何？",
        "雇主每月應為勞工提繳退休金的比例是多少？",
        "女性勞工分娩前後的產假有幾週？",
        "勞工每七天至少應有幾日休息？",
        "延長工時連同正常工時，每日合計上限為幾小時？",
        "雇主資遣勞工，依年資最長須於幾日前預告？",
        "未滿十六歲之童工，每日工作時間上限為幾小時？",
        "育嬰留職停薪最長可申請至子女滿幾歲？",
    ],
    # Router 正樣本：明確 B（爭議解釋/身份界定）
    "router_b": [
        "承攬與僱傭關係如何區分？",
        "派遣勞工與要派單位之間的雇主責任如何認定？",
        "離職後競業禁止條款在什麼情況下會無效？",
        "雇主調動勞工職務是否合法，判斷標準為何？",
        "試用期內解僱勞工是否需要預告及給付資遣費？",
        "外籍家庭看護工是否適用勞動基準法？",
        "接案的自由工作者有沒有勞動法上的保護？",
        "雇主以「不能勝任工作」為由解僱的認定標準為何？",
        "勞工集體於同一天請特別休假以表達抗議，雇主可否視為曠職？",
        "雇主單方面調降勞工薪資是否合法？",
    ],
    # Guardrail in-scope 邊界（屬勞工法、易被誤判為非勞工法，應放行）
    "in_scope_boundary": [
        "醫師因長時間值班導致中風，能否認定為職業災害？",
        "Uber 司機與平台之間算不算勞動關係？",
        "雇主要求簽訂最低服務年限，約定的違約金過高是否有效？",
        "遭遇職場性騷擾時，依性別平等工作法雇主負有哪些義務？",
        "雇主進行大量解僱前，必須踐行什麼程序？",
        "企業併購時，原有勞工的勞動契約應如何處理？",
        "雇主可否拒絕與工會進行團體協商？",
        "員工因公出差途中發生車禍，是否屬於職業災害？",
    ],
    # Guardrail out-scope 明確（非勞工法，應攔截）
    "out_scope_clear": [
        "明天台北會不會下雨？",
        "幫我用 Python 寫一個氣泡排序。",
        "現在適合買比特幣嗎？",
        "酒後駕車的刑事責任是什麼？",
        "我國憲法保障哪些基本人權？",
        "食品標示不實會被如何處罰？",
        "申請中華民國護照需要哪些文件？",
        "推薦幾部最近好看的電影。",
    ],
    # Guardrail out-scope 邊界（與工作/公司相鄰但非勞工法，應攔截）
    "out_scope_boundary": [
        "公司的營業稅稅率是多少？",
        "上市公司的獨立董事如何選任？",
        "申請發明專利的流程是什麼？",
        "公司辦理現金增資的程序為何？",
        "公司向銀行貸款的利率有沒有法定上限？",
        "公司尾牙摸彩的中獎獎品需要繳稅嗎？",
    ],
}


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1


def run_guardrail_eval() -> dict:
    print("=" * 60)
    print("Guardrail 評估（in-scope 應放行 / out-scope 應攔截）")
    print("=" * 60)

    groups = {
        "in_clear": (TEST_CASES["router_a"] + TEST_CASES["router_b"], True),
        "in_boundary": (TEST_CASES["in_scope_boundary"], True),
        "out_clear": (TEST_CASES["out_scope_clear"], False),
        "out_boundary": (TEST_CASES["out_scope_boundary"], False),
    }

    tp = fn = tn = fp = 0
    false_neg: list[str] = []
    false_pos: list[str] = []
    subgroup: dict[str, dict] = {}

    for grp, (qs, in_scope) in groups.items():
        correct = 0
        print(f"\n[{grp}（{'應放行' if in_scope else '應攔截'}）]")
        for q in qs:
            passed = check_scope(engine._llm, q)
            ok = passed == in_scope
            correct += int(ok)
            if in_scope:
                if passed:
                    tp += 1
                else:
                    fn += 1
                    false_neg.append(q)
            else:
                if not passed:
                    tn += 1
                else:
                    fp += 1
                    false_pos.append(q)
            mark = "✓" if ok else ("✗ 誤擋" if in_scope else "✗ 誤放")
            print(f"  {mark} {q}")
        subgroup[grp] = {"correct": correct, "total": len(qs)}

    p, r, f1 = _prf(tp, fp, fn)
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    total = tp + fp + fn + tn
    acc = (tp + tn) / total if total else 0.0

    print("\n混淆矩陣（正類別 = in-scope）:")
    print(f"  in-scope : 放行 TP={tp:<3} 誤擋 FN={fn}")
    print(f"  out-scope: 誤放 FP={fp:<3} 攔截 TN={tn}")
    print("\n指標:")
    print(f"  Precision = {p:.3f}")
    print(f"  Recall（放行率/Sensitivity） = {r:.3f}")
    print(f"  Specificity（攔截率） = {spec:.3f}")
    print(f"  F1 = {f1:.3f}    Accuracy = {acc:.3f}")
    print("  子組準確率:")
    for grp, v in subgroup.items():
        print(f"    {grp}: {v['correct']}/{v['total']}")
    if false_neg:
        print(f"  誤擋（false-negative）: {false_neg}")
    if false_pos:
        print(f"  誤放（false-positive）: {false_pos}")

    return {
        "confusion": {"TP": tp, "FN": fn, "FP": fp, "TN": tn},
        "precision": round(p, 3),
        "recall": round(r, 3),
        "specificity": round(spec, 3),
        "f1": round(f1, 3),
        "accuracy": round(acc, 3),
        "subgroup": subgroup,
        "false_negative": false_neg,
        "false_positive": false_pos,
    }


def run_router_eval() -> dict:
    print("\n" + "=" * 60)
    print("Router 評估（A = 直接查詢 / B = 爭議解釋）")
    print("=" * 60)

    cm = {"AA": 0, "AB": 0, "BA": 0, "BB": 0}
    misclassified: list[dict] = []

    for truth, key in (("A", "router_a"), ("B", "router_b")):
        print(f"\n[{truth} 型]")
        for q in TEST_CASES[key]:
            pred = route(engine._llm, q)
            cm[truth + pred] += 1
            ok = pred == truth
            if not ok:
                misclassified.append({"q": q, "truth": truth, "pred": pred})
            print(f"  {'✓' if ok else '✗'} [truth={truth} pred={pred}] {q}")

    aa, ab, ba, bb = cm["AA"], cm["AB"], cm["BA"], cm["BB"]
    total = aa + ab + ba + bb
    acc = (aa + bb) / total if total else 0.0
    a_p, a_r, a_f1 = _prf(aa, ba, ab)
    b_p, b_r, b_f1 = _prf(bb, ab, ba)
    macro_f1 = (a_f1 + b_f1) / 2

    print("\n混淆矩陣（列 = 真實, 欄 = 預測）:")
    print("          pred A   pred B")
    print(f"  真 A    {aa:>6}   {ab:>6}")
    print(f"  真 B    {ba:>6}   {bb:>6}")
    print("\n指標:")
    print(f"  Accuracy = {acc:.3f}    Macro-F1 = {macro_f1:.3f}")
    print(f"  A: P={a_p:.3f} R={a_r:.3f} F1={a_f1:.3f}")
    print(f"  B: P={b_p:.3f} R={b_r:.3f} F1={b_f1:.3f}")
    if misclassified:
        print(f"  誤分類: {misclassified}")

    return {
        "confusion": {"A_A": aa, "A_B": ab, "B_A": ba, "B_B": bb},
        "accuracy": round(acc, 3),
        "macro_f1": round(macro_f1, 3),
        "A": {"precision": round(a_p, 3), "recall": round(a_r, 3),
              "f1": round(a_f1, 3)},
        "B": {"precision": round(b_p, 3), "recall": round(b_r, 3),
              "f1": round(b_f1, 3)},
        "misclassified": misclassified,
    }


def main() -> None:
    guardrail = run_guardrail_eval()
    router = run_router_eval()

    out_file = Path(__file__).parent / "eval_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(
            {"guardrail": guardrail, "router": router},
            f, ensure_ascii=False, indent=2,
        )
    print(f"\n評估結果已儲存至 {out_file}")


if __name__ == "__main__":
    main()
