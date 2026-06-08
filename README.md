# 企業HR勞動法規查詢AI

RAG-Based Legal Information System，結合全國法規資料庫與勞工法教授著作，提供企業HR人員自然語言勞工法規查詢服務。

## 系統架構

```
使用者提問
  ↓
Guardrail（判斷是否屬台灣勞工法範疇）
  ↓（通過）
Router（A型：直接查詢 / B型：爭議解釋）
  ↓
ChromaDB 檢索（法條庫 + 書籍庫）
  ↓
信心門檻過濾（僅 A型）
  ↓
Claude Haiku 生成白話回答
  ↓
HTML 前端顯示（含來源標示）
```

## 快速開始

### 1. 安裝環境

需要 Python 3.11+，建議使用 [uv](https://docs.astral.sh/uv/)：

```bash
# 建立虛擬環境
uv venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安裝依賴
uv pip install -r requirements.txt
```

### 2. 設定 API 金鑰

```bash
cp .env.example .env
# 編輯 .env，填入以下兩個金鑰：
# OPENAI_API_KEY=...
# ANTHROPIC_API_KEY=...
```

### 3. 建立資料與向量索引

```bash
# 下載法條（勞基法、勞退條例、性平法、勞保條例）
python scripts/download_laws.py

# 放入書籍至 data/books/（.docx 或 .pdf）後處理
python scripts/process_books.py

# 建立 ChromaDB 向量索引
python scripts/build_index.py
```

### 4. 啟動系統

```bash
python server.py
# 開啟瀏覽器前往 http://localhost:5000
```

## 檔案結構

```
hr_rag/
├── server.py              # Flask 後端 API
├── app.py                 # Streamlit 版本（備用）
├── requirements.txt
├── .env.example
├── static/
│   └── index.html         # 單頁 HTML 前端
├── src/
│   └── rag_engine.py      # 核心 RAG 引擎
├── scripts/
│   ├── download_laws.py   # 下載全國法規資料庫
│   ├── process_books.py   # 處理書籍 Word/PDF
│   └── build_index.py     # 建立 ChromaDB 索引
├── eval/
│   └── evaluation.py      # 評估腳本
└── data/
    ├── laws/              # 法條 JSON（.gitignore 排除）
    └── books/             # 書籍原始檔（請自行放入）
```

## 技術選用

| 模組 | 技術 |
|------|------|
| 前端 | 原生 HTML / CSS / JavaScript |
| 後端 | Flask |
| LLM | Claude Haiku 4.5（Anthropic） |
| Embedding | text-embedding-3-small（OpenAI） |
| 向量資料庫 | ChromaDB |

## 評估

```bash
python eval/evaluation.py
```

執行 Guardrail / Router 功能驗證與對照實驗，結果輸出至 `eval/eval_results.json`。
