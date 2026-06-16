#!/usr/bin/env bash
set -e

echo "=== HR 勞動法規 RAG 系統安裝設定 ==="

# uv handles the virtualenv and dependencies via pyproject.toml
if ! command -v uv &> /dev/null; then
    echo "[ERROR] 請先安裝 uv：https://docs.astral.sh/uv/"
    exit 1
fi

echo "[1/3] 安裝 Python 依賴..."
uv sync

echo "[2/3] 複製環境變數範本..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  已建立 .env，請填入 ANTHROPIC_API_KEY"
else
    echo "  .env 已存在，跳過"
fi

echo "[3/3] 確認目錄結構..."
mkdir -p data/laws data/books chroma_db

echo ""
echo "=== 安裝完成 ==="
echo ""
echo "接下來的步驟："
echo "  1. 編輯 .env 填入 ANTHROPIC_API_KEY"
echo "  2. 下載法條：uv run python scripts/download_laws.py"
echo "  3. 放入書籍檔案至 data/books/ 後執行：uv run python scripts/process_books.py"
echo "  4. 建立向量索引：uv run python scripts/build_index.py"
echo "  5. 啟動系統：uv run python server.py"
