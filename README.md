# 企業HR勞動法規查詢AI

> RAG-Based Legal Information System for Taiwan Labor Law

以 RAG（Retrieval-Augmented Generation）技術為核心，結合全國法規資料庫與勞工法教授著作，提供企業 HR 人員自然語言勞工法規查詢服務。

---

## 線上展示
🌐 **完整功能影片 Demo**：<https://youtu.be/kly8Ly7tg-U?si=CtSKJ5VSNMb3YXeX>
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
│  📜  法條庫          │  ├─────────────────────────────────────────────┤  │
│  📚  書籍庫          │  │  雇主可以單方面調降薪資嗎？                  │  │
│                      │  └─────────────────────────────────────────────┘  │
│                      ├───────────────────────────────────────────────────┤
│  [ 清除對話紀錄 ]    │  請輸入勞工法規問題...                    [ ➤ ]  │
└──────────────────────┴───────────────────────────────────────────────────┘
```

---

## 功能特色

- **自然語言提問**：直接用中文問，不需要輸入關鍵字
- **範疇守門（Guardrail）**：過濾非勞工法問題，避免亂答與 API 浪費
- **智慧路由（Router）**：自動判斷 A／B 型，選擇最適合的檢索策略
- **信心門檻**：A 型若無高度相關法條，回覆「無明確規定」而非硬掰（避免幻覺）
- **即時流程進度**：SSE 串流，側欄逐步顯示每個關卡的真實狀態與耗時
- **來源可追溯**：每個回答附上引用的法條條號（📜）或書籍章節（📚）
- **本地免費 Embedding**：bge-m3 本地執行，無需付費嵌入 API（生成採 Claude API）
- **體驗細節**：回答以 Markdown 渲染；對話以 localStorage 保存，重新整理不消失

---

## RAG 架構說明

### 查詢流程

每次查詢依序經過 Guardrail → Router → 檢索 →（A 型）信心門檻 → LLM 生成，
並以 SSE 即時串流每一步進度到前端側欄。

```mermaid
flowchart TD
    Q["使用者問題"] --> G{"Guardrail（check_scope · LLM）<br/>是否屬台灣勞工法範疇？"}
    G -->|否| OOS["超出服務範疇<br/>(out_of_scope)"]
    G -->|是| R{"Router（route · LLM）<br/>A 型 or B 型？"}
    R -->|"A 直接查詢"| EA["Embedding (bge-m3) ＋ 檢索<br/>法條庫（280 條）→ Top-5"]
    R -->|"B 爭議解釋"| EB["Embedding (bge-m3) ＋ 檢索<br/>書籍庫（5 本）Top-5 ＋ 法條庫 Top-2"]
    EA --> C{"信心門檻<br/>cosine 距離 ≤ 0.5？"}
    C -->|否| NL["無明確規定<br/>(no_law)"]
    C -->|是| GEN["LLM 生成<br/>Claude Opus 4.8"]
    EB --> GEN
    GEN --> ANS["白話回答 ＋ 來源（📜 法條／📚 書籍）"]
```

### 系統架構

```mermaid
flowchart LR
    U["瀏覽器・單頁前端<br/>即時進度 · Markdown · localStorage"]
    subgraph C["Docker 容器（Flask + Gunicorn gthread）"]
        S["server.py<br/>/api/query (SSE)"] --> E["RAG Engine"]
        E --> GR["guardrail.py"]
        E --> RT["router.py"]
        E --> EMB["bge-m3<br/>本地嵌入"]
        E --> DB[("ChromaDB<br/>法條庫 280 條 ＋ 書籍庫 5 本")]
    end
    U <-->|"HTTP / SSE"| S
    E -->|"Anthropic API"| LLM["Claude Opus 4.8"]
```

### 問題類型說明

| 類型 | 定義 | 範例 | 檢索策略 |
|------|------|------|---------|
| A 直接查詢型 | 問特定法條、數字、明確規定 | 「特休幾天？」「加班費怎麼算？」 | 只查法條庫，套用信心門檻 |
| B 爭議解釋型 | 問模糊地帶、實務見解、身份界定 | 「承攬與僱傭如何區分？」 | 書籍庫 Top-5 + 法條庫 Top-2 |

---

## 技術選用

| 模組 | 技術 | 說明 |
|------|------|------|
| 前端 | 原生 HTML / CSS / JavaScript | 單頁應用；SSE 即時進度、marked.js 渲染 Markdown、localStorage 保存對話 |
| 後端 | Flask 3.0 + Gunicorn | 輕量 Web 框架；Docker 以 Gunicorn（gthread）提供生產級服務 |
| API 串流 | Server-Sent Events | `/api/query` 逐步串流管線進度與最終結果 |
| LLM | Claude API（Opus 4.8） | Guardrail／Router／生成皆用；需 API Key |
| Embedding | sentence-transformers + BAAI/bge-m3 | **本地免費**，多語言檢索 SOTA，1024 維、支援 8192 tokens（約 2.3GB） |
| 向量資料庫 | ChromaDB | 本地持久化（cosine）；法條庫 + 書籍庫兩個 collection |
| 容器化 | Docker + Compose | 單容器一鍵啟動；CPU-only PyTorch、預載模型、首次自動建索引 |

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
├── server.py                  # Flask 後端（/api/query SSE、/api/health）
├── gunicorn.conf.py           # Gunicorn 設定（gthread，讀 config）
├── pyproject.toml             # 依賴與 ruff 設定（uv 管理）
├── .env.example               # API Key 範本
├── Dockerfile                 # 單容器映像（CPU torch、預載並快取嵌入模型）
├── docker-compose.yml         # 一鍵啟動編排（含 volume 持久化）
├── docker-entrypoint.sh       # 首次啟動自動下載法條並建索引（離線載模型）
├── .dockerignore
├── static/
│   ├── index.html             # 單頁前端（即時進度、Markdown、對話保存）
│   └── marked.min.js          # Markdown 渲染（本地打包）
├── src/
│   ├── config.py              # 集中參數設定
│   ├── guardrail.py           # 第 1 層：範疇守門（check_scope）
│   ├── router.py              # 第 2 層：問題路由（route，A／B）
│   └── rag_engine.py          # 核心引擎：檢索 → 信心門檻 → LLM 生成
├── scripts/
│   ├── download_laws.py       # 爬取全國法規資料庫
│   ├── process_books.py       # 處理書籍 Word/PDF → chunk
│   ├── preload_model.py       # 建置時預載嵌入模型
│   └── build_index.py         # 建立 ChromaDB 向量索引
├── eval/
│   └── evaluation.py          # 評估腳本（Guardrail/Router + 邊界測試）
└── data/
    ├── laws/                  # 法條 JSON（自動產生）
    └── books/                 # 書籍原始檔（手動放入，不納版控）
```

---

## API 說明

### `POST /api/query`

以 **SSE（`text/event-stream`）逐步串流**管線進度，前端據此即時更新「查詢流程」側欄。

```
// Request
{ "question": "特休假幾天？" }

// Response：text/event-stream，每行 data: {event}
data: {"step":"guardrail","status":"running"}
data: {"step":"guardrail","status":"done","passed":true}
data: {"step":"router","status":"done","query_type":"A"}
data: {"step":"retrieve","status":"done","count":5,"scope":"laws"}
data: {"step":"confidence","status":"done","result":"pass"}
data: {"step":"generate","status":"running"}
data: {"step":"result","answer":"...","query_type":"A","query_type_label":"直接查詢型（法條庫）","guardrail_passed":true,"chunks":[{"source":"勞動基準法第38條","content":"...","distance":0.3947,"collection":"laws"}]}
```

事件類型：`guardrail` / `router` / `retrieve` / `confidence` / `generate`（含
`status: running|done|skipped`），最後一筆為 `result`（完整答案與來源），錯誤為
`{"step":"error","error":...}`。

### `GET /api/health`

```json
{ "status": "ok" }
```

---

## 執行評估

針對 Guardrail 與 Router 兩個 LLM 分類器，以**混淆矩陣 + Precision/Recall/F1**
量化。題組為 **held-out**（不與 Guardrail prompt 的 few-shot 範例重複），標籤對齊
現行 prompt 定義。

```bash
docker compose exec app uv run python eval/evaluation.py   # 或本機 uv run
```

### Guardrail（二元分類：in-scope 應放行 / out-scope 應攔截）

題組 42 題：in-scope 28（明確 20 ＋ 邊界 8）、out-scope 14（明確 8 ＋ 邊界 6）。
邊界題如職災過勞、醫護/機師工時、平台工作者、競業/調職（in）；稅務、公司治理、
智財、現金增資（out）。

| 指標 | 說明 | 結果 |
|------|------|:---:|
| Precision | 放行者中真屬勞工法的比例 | 1.000 |
| Recall（放行率） | in-scope 被正確放行的比例 | 1.000 |
| Specificity（攔截率） | out-scope 被正確攔截的比例 | 1.000 |
| F1 / Accuracy | — | 1.000 / 1.000 |

混淆矩陣：TP=28、FN=0、FP=0、TN=14（誤擋、誤放皆 0）。

### Router（A 直接查詢 / B 爭議解釋）

題組 20 題（A 10、B 10，皆語意明確、不取模稜兩可者）。

| 指標 | 結果 |
|------|:---:|
| Accuracy | 1.000 |
| Macro-F1 | 1.000 |
| A：P / R / F1 | 1.000 / 1.000 / 1.000 |
| B：P / R / F1 | 1.000 / 1.000 / 1.000 |

完整混淆矩陣、各題判定與 false-negative/positive 清單輸出至 `eval/eval_results.json`。

---

## 組員分工

| 姓名 | 職責 |
|------|------|
| 林仰恩 | 書籍庫資料清洗、向量化與實務場景整合測試 |
| 陳姿吟 | RAG 系統核心開發、API 串接、環境部署與向量資料庫建置 |
| 許文晴 | 專案報告撰寫與系統邏輯整合 |
| 林昀蓁 | 專案報告撰寫與系統邏輯整合 |
| 吳秉彥 | GCP 託管網站、部署測試與專案報告整合 |

---

## 注意事項

- 本系統提供法規資訊查詢，**不構成正式法律意見**。
- 法條內容來源為全國法規資料庫，以最新公布版本為準。
- `data/laws/`、`chroma_db/`、`.env` 不納入版本控制。
