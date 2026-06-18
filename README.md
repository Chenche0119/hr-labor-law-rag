# 企業HR勞動法規查詢AI

> RAG-Based Legal Information System for Taiwan Labor Law

以 RAG（Retrieval-Augmented Generation）技術為核心，結合全國法規資料庫與勞工法教授著作，提供企業 HR 人員自然語言勞工法規查詢服務。

---

## 線上展示

🌐 **GCP 雲端 Demo**：<https://ai.kleee.uk>

> 線上版部署於 Google Cloud Run（為降低成本採較小 embedding 模型、`min-instances=0`），
> 休眠後首次開啟需稍候初始化，僅供快速試玩。
> **完整版（bge-m3 檢索 + Claude Opus 4.8 + 書籍庫）以下方本地 Docker 版為準。**
> GCP 部署細節由團隊另行補充。

---

## 系統畫面

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ⚖️  企業HR勞動法規查詢AI   RAG-Based Legal Information System   [系統資訊]  │
├──────────────────────┬───────────────────────────────────────────────────┤
│                      │                                                   │
│  查詢流程            │        您好，我是 HR 勞動法規查詢 AI              │
│  ────────────        │  請用自然語言提問，我將從法條庫與學術              │
│  1  Guardrail        │  著作中為您查詢準確的勞工法規資訊。               │
│  2  Router           │                                                   │
│  3  檢索             │  ┌─────────────────────────────────────────────┐  │
│  4  信心門檻         │  │  特休假幾天？計算方式是什麼？                │  │
│  5  LLM 生成         │  ├─────────────────────────────────────────────┤  │
│                      │  │  加班費如何計算？                            │  │
│  資料來源            │  ├─────────────────────────────────────────────┤  │
│  ────────────        │  │  承攬跟僱傭關係怎麼區分？                    │  │
│  🔵  法條庫          │  ├─────────────────────────────────────────────┤  │
│  📚  書籍庫          │  │  雇主可以單方面調降薪資嗎？                  │  │
│                      │  └─────────────────────────────────────────────┘  │
│                      ├───────────────────────────────────────────────────┤
│  [ 清除對話紀錄 ]    │  請輸入勞工法規問題...                    [ ➤ ]  │
└──────────────────────┴───────────────────────────────────────────────────┘
```

---

## 功能特色

- **自然語言提問**：直接用中文問，不需要輸入關鍵字
- **雙層保護機制**：Guardrail 過濾範疇外問題，避免 API 浪費
- **智慧路由**：自動判斷問題類型，選擇最適合的檢索策略
- **來源可追溯**：每個回答都附上引用的法條條號或書籍章節
- **本地免費 Embedding**：sentence-transformers 本地執行，無需付費 API（LLM 採 Claude API，需付費）

---

## RAG 架構說明

### 問題類型說明

| 類型 | 定義 | 範例 | 檢索策略 |
|------|------|------|---------|
| A 直接查詢型 | 問特定法條、數字、明確規定 | 「特休幾天？」「加班費怎麼算？」 | 只查法條庫，套用信心門檻 |
| B 爭議解釋型 | 問模糊地帶、實務見解、身份界定 | 「承攬與僱傭如何區分？」 | 書籍庫 Top-5 + 法條庫 Top-2 |

---

## 技術選用

| 模組 | 技術 | 說明 |
|------|------|------|
| 前端 | 原生 HTML / CSS / JavaScript | 單頁應用，無需框架 |
| 後端 | Flask 3.0 | 輕量 Python Web 框架 |
| LLM | Claude API（Opus 4.8） | 品質最佳，需 API Key |
| Embedding | sentence-transformers（本地） | **免費**，支援中文多語言 |
| 向量資料庫 | ChromaDB | 本地持久化儲存 |
| Embedding 模型 | BAAI/bge-m3 | 多語言檢索 SOTA，支援 8192 tokens，約 2.3GB |

---

## 資料來源

### 法條庫

從[全國法規資料庫](https://law.moj.gov.tw)自動下載以下四部法規：

- 勞動基準法
- 勞工退休金條例
- 性別平等工作法
- 勞工保險條例

### 書籍庫（需自行準備）

將勞工法教授著作（`.docx` 或 `.pdf` 格式）放入 `data/books/` 目錄，執行 `process_books.py` 後自動切割入庫。

---

## 快速開始

### 方式一：Docker 一鍵啟動（推薦）

前後端與向量資料庫打包在單一容器，首次啟動會**自動下載法條並建立索引**。

前置需求：[Docker](https://docs.docker.com/get-docker/) 與 Docker Compose、[Anthropic API Key](https://console.anthropic.com)。

```bash
# 1. 設定 API Key
cp .env.example .env
# 編輯 .env 填入 ANTHROPIC_API_KEY

# 2. 建置並啟動（首次會建置 image 並自動灌入法條資料）
docker compose up --build
```

開啟瀏覽器前往 **http://localhost:5001**。

- 向量資料庫（`chroma_db/`）與資料（`data/`）以 volume 持久化，重啟不需重建索引。
- 嵌入模型（BAAI/bge-m3）已預先打包進 image，首次啟動無需等待下載。
- image 採 **CPU-only PyTorch**（移除整套 CUDA），體積約 9GB（原 CUDA 版約 18GB）；如需 GPU 推論需自行調整 torch 來源。
- 啟動時以 `HF_HUB_OFFLINE=1` 從打包好的快取載入模型，避免網路不穩時卡住。
- 加入書籍庫：將檔案放入 `data/books/` 後，於容器內執行
  `docker compose exec app uv run python scripts/process_books.py && docker compose exec app uv run python scripts/build_index.py`。

---

### 方式二：本機 uv 安裝

#### 前置需求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [Anthropic API Key](https://console.anthropic.com)

#### 安裝步驟

**1. 取得專案**

```bash
git clone https://github.com/Chenche0119/hr-labor-law-rag.git
cd hr-labor-law-rag
```

**2. 安裝依賴**

```bash
uv sync
```

> 首次執行時 sentence-transformers 會自動下載 bge-m3 模型（約 2.3GB），需要網路連線。

**3. 設定 API Key**

前往 [console.anthropic.com](https://console.anthropic.com) 取得 API Key，然後：

```bash
cp .env.example .env
# 用任意編輯器開啟 .env，填入你的 Key：
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
```

**4. 下載法條並建立向量索引**

```bash
# 下載 4 部勞工法規（約 10 秒）
uv run python scripts/download_laws.py

# 建立 ChromaDB 向量索引（首次約 1~2 分鐘）
uv run python scripts/build_index.py
```

**5. 啟動系統**

```bash
uv run python server.py
```

開啟瀏覽器前往 **http://localhost:5001**

---

## 書籍資料建置（選用）

加入勞工法教授著作（.docx / .pdf）可提升 B 型（爭議解釋）問題的回答品質。
檔名會作為來源標籤（顯示為《檔名》），請取有意義的書名。docx 能偵測章節標題、
metadata 較完整，有 docx 版優先用 docx。

**Docker（推薦）**

```bash
# 1. 將書籍檔案放入 data/books/（會自動掛載進容器）
mkdir -p data/books
cp 你的書籍.pdf data/books/

# 2. 切割成 chunk（不需模型）
docker compose exec app uv run python scripts/process_books.py

# 3. 建立書籍向量索引（用 bge-m3；已索引的法條會自動略過）
docker compose exec app uv run python scripts/build_index.py

# 4. 重啟讓服務載入新的書籍庫
docker compose restart app
```

**本機 uv**

```bash
mkdir -p data/books && cp 你的書籍.docx data/books/
uv run python scripts/process_books.py
uv run python scripts/build_index.py
```

---

## 專案結構

```
hr-labor-law-rag/
├── server.py                  # Flask 後端（/api/query、/api/health）
├── pyproject.toml             # 依賴與 ruff 設定（uv 管理）
├── .env.example               # API Key 範本
├── Dockerfile                 # 單容器映像（含預載嵌入模型）
├── docker-compose.yml         # 一鍵啟動編排（含 volume 持久化）
├── docker-entrypoint.sh       # 首次啟動自動下載法條並建索引
├── static/
│   └── index.html             # 單頁 HTML 前端
├── src/
│   ├── config.py              # 集中參數設定
│   └── rag_engine.py          # 核心 RAG 引擎
│                              #   Guardrail → Router → 檢索 → LLM
├── scripts/
│   ├── download_laws.py       # 爬取全國法規資料庫
│   ├── process_books.py       # 處理書籍 Word/PDF
│   ├── preload_model.py       # 建置時預載嵌入模型
│   └── build_index.py         # 建立 ChromaDB 向量索引
├── eval/
│   └── evaluation.py          # 評估腳本
└── data/
    ├── laws/                  # 法條 JSON（自動產生）
    └── books/                 # 書籍原始檔（手動放入）
```

---

## API 說明

### `POST /api/query`

```json
// Request
{ "question": "特休假幾天？" }

// Response
{
  "answer": "結論：特休假天數根據...",
  "query_type": "A",
  "query_type_label": "直接查詢型（法條庫）",
  "guardrail_passed": true,
  "chunks": [
    {
      "source": "勞動基準法第38條",
      "content": "第38條 勞工在同一雇主...",
      "distance": 0.3947,
      "collection": "laws"
    }
  ]
}
```

### `GET /api/health`

```json
{ "status": "ok" }
```

---

## 執行評估

```bash
uv run python eval/evaluation.py
```

評估內容：

| 評估項目 | 題數 | 指標 |
|---------|------|------|
| Guardrail 攔截準確率 | 10 題（範疇外） | 正確攔截數 / 10 |
| Guardrail 放行準確率 | 25 題（範疇內） | 正確放行數 / 25 |
| Router A 型準確率 | 10 題 | 正確分類數 / 10 |
| Router B 型準確率 | 10 題 | 正確分類數 / 10 |
| Guardrail 邊界放行 | 10 題（職災、醫護/機師工時、平台工作者、競業/調職等邊界但屬勞工法） | 正確放行數 / 10 |
| Guardrail 邊界攔截 | 6 題（稅務、公司治理、智財等邊界但非勞工法） | 正確攔截數 / 6 |

結果輸出至 `eval/eval_results.json`。

---

## 組員分工

| 姓名 | 職責 |
|------|------|
| 林仰恩 | |
| 陳姿吟 | |
| 許文晴 | |
| 林昀蓁 | |
| 吳秉彥 | |

---

## 注意事項

- 本系統提供法規資訊查詢，**不構成正式法律意見**。
- 法條內容來源為全國法規資料庫，以最新公布版本為準。
- `data/laws/`、`chroma_db/`、`.env` 不納入版本控制。
