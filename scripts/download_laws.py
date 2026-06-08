"""
下載台灣全國法規資料庫的勞工相關法規 JSON
"""
import json
import requests
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "laws"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 全國法規資料庫 API（需要法規 PCode）
LAW_API = "https://law.moj.gov.tw/api/ch/law/all"
ARTICLE_API = "https://law.moj.gov.tw/api/ch/law/article/{pcode}"

TARGET_LAWS = [
    {"name": "勞動基準法", "pcode": "N0030001"},
    {"name": "勞工退休金條例", "pcode": "N0030020"},
    {"name": "性別平等工作法", "pcode": "N0030014"},
    {"name": "勞工保險條例", "pcode": "N0050001"},
]


def fetch_law_articles(pcode: str, law_name: str) -> list[dict]:
    url = ARTICLE_API.format(pcode=pcode)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[ERROR] 下載 {law_name} 失敗: {e}")
        return []

    articles = []
    # 全國法規 API 回傳格式：{"LawArticles": [{"ArticleNo": "1", "ArticleContent": "..."}]}
    raw_articles = data.get("LawArticles", data.get("articles", []))
    if isinstance(raw_articles, dict):
        raw_articles = raw_articles.get("LawArticle", [])

    for art in raw_articles:
        no = art.get("ArticleNo") or art.get("article_no", "")
        content = art.get("ArticleContent") or art.get("article_content", "")
        if no and content:
            articles.append({
                "law_name": law_name,
                "article_no": no,
                "content": content.strip(),
                "source": f"{law_name}第{no}條",
                "pcode": pcode,
            })

    print(f"[OK] {law_name}: {len(articles)} 條")
    return articles


def main():
    all_articles = []
    for law in TARGET_LAWS:
        articles = fetch_law_articles(law["pcode"], law["name"])
        all_articles.extend(articles)
        out_file = OUTPUT_DIR / f"{law['name']}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

    summary_file = OUTPUT_DIR / "all_laws.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    print(f"\n完成！共下載 {len(all_articles)} 條法條，儲存至 {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
