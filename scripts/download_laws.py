"""Crawl labor-law articles from the national law database (law.moj.gov.tw)."""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import HTTP_HEADERS, LAWS_DIR, TARGET_LAWS

LAWS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_html(pcode: str) -> str:
    url = f"https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={pcode}"
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_articles(html: str, law_name: str) -> list[dict]:
    """Parse article numbers and bodies from the HTML."""
    articles = []

    # Strip script/style
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.S)

    # Primary: match the data-no attribute (newer layout)
    data_no_matches = re.findall(
        r'data-no="([^"]+)"[^>]*>.*?<div[^>]*class="[^"]*law-article[^"]*"[^>]*>(.*?)</div>',
        html,
        re.S,
    )
    if data_no_matches:
        for art_no, content in data_no_matches:
            content = re.sub(r"<[^>]+>", "", content).strip()
            content = re.sub(r"\s+", " ", content)
            if content:
                articles.append(
                    {
                        "law_name": law_name,
                        "article_no": art_no.strip(),
                        "content": content,
                        "source": f"{law_name}第{art_no.strip()}條",
                    }
                )
        return articles

    # Fallback: strip tags and match "第X條" paragraphs
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", "", text)

    pattern = r"第\s*(\d+(?:-\d+)?)\s*條\s*((?:[^\n第]|\n(?!\s*第))+)"
    for m in re.finditer(pattern, text):
        art_no = m.group(1).strip()
        content = m.group(2).strip()
        content = re.sub(r"\s+", " ", content)
        if len(content) > 5:
            articles.append(
                {
                    "law_name": law_name,
                    "article_no": art_no,
                    "content": f"第{art_no}條 {content}",
                    "source": f"{law_name}第{art_no}條",
                }
            )

    return articles


def main():
    all_articles = []

    for law in TARGET_LAWS:
        print(f"downloading {law['name']}...")
        try:
            html = fetch_html(law["pcode"])
            articles = parse_articles(html, law["name"])

            if not articles:
                print("  [WARN] no articles parsed; layout may have changed")
            else:
                all_articles.extend(articles)
                out_file = LAWS_DIR / f"{law['name']}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(articles, f, ensure_ascii=False, indent=2)
                print(f"  [OK] {len(articles)} articles -> {out_file.name}")

        except Exception as e:
            print(f"  [ERROR] {e}")

        time.sleep(1)  # avoid hammering the server

    if all_articles:
        summary_file = LAWS_DIR / "all_laws.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        print(f"\nDone: {len(all_articles)} articles -> {summary_file}")
    else:
        print("\n[ERROR] no articles downloaded")


if __name__ == "__main__":
    main()
