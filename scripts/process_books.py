"""
處理勞工法書籍（Word / PDF），切割成段落 chunk 並輸出 JSON
"""
import json
import re
from pathlib import Path

import pdfplumber
from docx import Document

BOOKS_INPUT_DIR = Path(__file__).parent.parent / "data" / "books"
OUTPUT_FILE = BOOKS_INPUT_DIR / "processed_books.json"

CHUNK_SIZE = 400   # 每個 chunk 目標字元數
OVERLAP = 50       # 段落間重疊字元數


def chunk_text(text: str, source_meta: dict) -> list[dict]:
    """將長文本按 CHUNK_SIZE 切割，保留 metadata"""
    text = text.strip()
    if len(text) <= CHUNK_SIZE:
        return [{"content": text, **source_meta}]

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        # 嘗試在句子邊界切割
        if end < len(text):
            for sep in ["。", "；", "\n"]:
                pos = text.rfind(sep, start, end)
                if pos > start + CHUNK_SIZE // 2:
                    end = pos + 1
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"content": chunk, **source_meta})
        start = end - OVERLAP
    return chunks


def process_docx(file_path: Path) -> list[dict]:
    doc = Document(file_path)
    book_name = file_path.stem
    chunks = []
    current_section = ""
    buffer = ""

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # 判斷是否為章節標題（粗體或短文字）
        is_heading = (
            para.style.name.startswith("Heading")
            or (len(text) < 30 and any(r.bold for r in para.runs if r.text.strip()))
        )

        if is_heading:
            if buffer:
                meta = {"book": book_name, "section": current_section, "source": f"《{book_name}》{current_section}"}
                chunks.extend(chunk_text(buffer, meta))
                buffer = ""
            current_section = text
        else:
            buffer += text + "\n"

    if buffer:
        meta = {"book": book_name, "section": current_section, "source": f"《{book_name}》{current_section}"}
        chunks.extend(chunk_text(buffer, meta))

    print(f"[OK] {book_name} (docx): {len(chunks)} chunks")
    return chunks


def process_pdf(file_path: Path) -> list[dict]:
    book_name = file_path.stem
    chunks = []

    with pdfplumber.open(file_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"

    # 按段落切割（兩個以上換行為段落分隔）
    paragraphs = re.split(r"\n{2,}", full_text)
    buffer = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        buffer += para + "\n"
        if len(buffer) >= CHUNK_SIZE:
            meta = {"book": book_name, "section": "", "source": f"《{book_name}》"}
            chunks.extend(chunk_text(buffer, meta))
            buffer = ""

    if buffer:
        meta = {"book": book_name, "section": "", "source": f"《{book_name}》"}
        chunks.extend(chunk_text(buffer, meta))

    print(f"[OK] {book_name} (pdf): {len(chunks)} chunks")
    return chunks


def main():
    all_chunks = []

    for f in BOOKS_INPUT_DIR.iterdir():
        if f.suffix.lower() == ".docx":
            all_chunks.extend(process_docx(f))
        elif f.suffix.lower() == ".pdf":
            all_chunks.extend(process_pdf(f))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fp:
        json.dump(all_chunks, fp, ensure_ascii=False, indent=2)

    print(f"\n完成！共 {len(all_chunks)} 個書籍 chunks，儲存至 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
