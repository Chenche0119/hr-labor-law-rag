"""
從全國法規資料庫網頁爬取勞工相關法規條文
"""
import json
import re
import time
import urllib.request
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "laws"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_LAWS = [
    {"name": "勞動基準法",     "pcode": "N0030001"},
    {"name": "勞工退休金條例", "pcode": "N0030020"},
    {"name": "性別平等工作法", "pcode": "N0030014"},
    {"name": "勞工保險條例",   "pcode": "N0050001"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def fetch_html(pcode: str) -> str:
    url = f"https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={pcode}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_articles(html: str, law_name: str) -> list[dict]:
    """從 HTML 解析條號與條文內容"""
    articles = []

    # 移除 script/style
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.S)

    # 找出條文區塊：全國法規資料庫的條文放在 <div class="law-article"> 或 <tr> 內
    # 先嘗試抓 data-no 屬性（新版）
    data_no_matches = re.findall(
        r'data-no="([^"]+)"[^>]*>.*?<div[^>]*class="[^"]*law-article[^"]*"[^>]*>(.*?)</div>',
        html, re.S
    )
    if data_no_matches:
        for art_no, content in data_no_matches:
            content = re.sub(r"<[^>]+>", "", content).strip()
            content = re.sub(r"\s+", " ", content)
            if content:
                articles.append({
                    "law_name": law_name,
                    "article_no": art_no.strip(),
                    "content": content,
                    "source": f"{law_name}第{art_no.strip()}條",
                })
        return articles

    # 備用：用正規表達式抓「第X條」後的文字段落
    # 去掉 HTML tags
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", "", text)

    # 找 第X條 或 第 X 條 格式
    pattern = r"第\s*(\d+(?:-\d+)?)\s*條\s*((?:[^\n第]|\n(?!\s*第))+)"
    for m in re.finditer(pattern, text):
        art_no = m.group(1).strip()
        content = m.group(2).strip()
        content = re.sub(r"\s+", " ", content)
        if len(content) > 5:
            articles.append({
                "law_name": law_name,
                "article_no": art_no,
                "content": f"第{art_no}條 {content}",
                "source": f"{law_name}第{art_no}條",
            })

    return articles


def main():
    all_articles = []

    for law in TARGET_LAWS:
        print(f"下載 {law['name']}...")
        try:
            html = fetch_html(law["pcode"])
            articles = parse_articles(html, law["name"])

            if not articles:
                print(f"  [WARN] 未解析到條文，可能頁面結構改變")
            else:
                all_articles.extend(articles)
                out_file = OUTPUT_DIR / f"{law['name']}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(articles, f, ensure_ascii=False, indent=2)
                print(f"  [OK] {len(articles)} 條 → {out_file.name}")

        except Exception as e:
            print(f"  [ERROR] {e}")

        time.sleep(1)  # 避免頻繁請求

    if all_articles:
        summary_file = OUTPUT_DIR / "all_laws.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        print(f"\n完成！共 {len(all_articles)} 條法條 → {summary_file}")
    else:
        print("\n[ERROR] 未能下載任何法條")


if __name__ == "__main__":
    main()
