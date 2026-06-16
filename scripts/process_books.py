"""Process labor-law books (Word / PDF) into paragraph chunks as JSON."""
import json
import re
import sys
from pathlib import Path

import pdfplumber
from docx import Document

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import BOOKS_DIR, CHUNK_SIZE, OVERLAP

OUTPUT_FILE = BOOKS_DIR / "processed_books.json"


def chunk_text(text: str, source_meta: dict) -> list[dict]:
    """Split long text by CHUNK_SIZE while keeping metadata."""
    text = text.strip()
    if len(text) <= CHUNK_SIZE:
        return [{"content": text, **source_meta}]

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        # Try to break on a sentence boundary
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

        # Heading detection (Heading style, or short bold text)
        is_heading = para.style.name.startswith("Heading") or (
            len(text) < 30 and any(r.bold for r in para.runs if r.text.strip())
        )

        if is_heading:
            if buffer:
                meta = {
                    "book": book_name,
                    "section": current_section,
                    "source": f"《{book_name}》{current_section}",
                }
                chunks.extend(chunk_text(buffer, meta))
                buffer = ""
            current_section = text
        else:
            buffer += text + "\n"

    if buffer:
        meta = {
            "book": book_name,
            "section": current_section,
            "source": f"《{book_name}》{current_section}",
        }
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

    # Split on blank lines (two or more newlines = paragraph break)
    paragraphs = re.split(r"\n{2,}", full_text)
    buffer = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        buffer += para + "\n"
        if len(buffer) >= CHUNK_SIZE:
            meta = {
                "book": book_name,
                "section": "",
                "source": f"《{book_name}》",
            }
            chunks.extend(chunk_text(buffer, meta))
            buffer = ""

    if buffer:
        meta = {"book": book_name, "section": "", "source": f"《{book_name}》"}
        chunks.extend(chunk_text(buffer, meta))

    print(f"[OK] {book_name} (pdf): {len(chunks)} chunks")
    return chunks


def main():
    all_chunks = []

    for f in BOOKS_DIR.iterdir():
        if f.suffix.lower() == ".docx":
            all_chunks.extend(process_docx(f))
        elif f.suffix.lower() == ".pdf":
            all_chunks.extend(process_pdf(f))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fp:
        json.dump(all_chunks, fp, ensure_ascii=False, indent=2)

    print(f"\nDone: {len(all_chunks)} book chunks -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
