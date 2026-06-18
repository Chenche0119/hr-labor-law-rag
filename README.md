# 企業HR勞動法規查詢AI

> RAG-Based Legal Information System for Taiwan Labor Law

以 RAG（Retrieval-Augmented Generation）技術為核心，結合全國法規資料庫與勞工法教授著作，提供企業 HR 人員自然語言勞工法規查詢服務。

---

## 線上展示

### **網站預覽**：[https://ai.kleee.uk](https://ai.kleee.uk)

> 線上版本部署於 Google Cloud Run，使用 Secret Manager 管理 `GROQ_API_KEY`，避免將 API Key 寫入程式碼或提交到 GitHub。
> 由於 Cloud Run 設定為 `min-instances=0` 以降低閒置成本，服務休眠後的第一次開啟或第一次對話可能需要較長載入時間，等待模型與向量資料庫初始化後即可正常使用。

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
- **低成本架構**：使用 Groq API + sentence-transformers 本地 Embedding，Cloud Run 可用 `min-instances=0` 控制閒置成本

---

## RAG 架構說明

![系統架構流程圖](static/architecture.png)

> [點此開啟互動版架構圖](https://viewer.diagrams.net/?url=https://raw.githubusercontent.com/Chenche0119/hr-labor-law-rag/main/static/architecture.drawio)

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
| LLM | Groq API（llama-3.3-70b-versatile） | 速度快，適合即時問答 |
| Embedding | sentence-transformers（本地） | **免費**，支援中文多語言 |
| 向量資料庫 | ChromaDB | 本地持久化儲存 |
| Embedding 模型 | paraphrase-multilingual-MiniLM-L12-v2 | 多語言，約 500MB |
| 容器化 | Docker | 封裝 Python 環境與應用程式 |
| 雲端部署 | Google Cloud Run | Serverless 容器部署，自動擴縮 |

---

## 資料來源

### 法條庫（280 條）

從[全國法規資料庫](https://law.moj.gov.tw)自動下載：

| 法規名稱 | 條數 |
|---------|------|
| 勞動基準法 | 86 條 |
| 勞工退休金條例 | 58 條 |
| 性別平等工作法 | 45 條 |
| 勞工保險條例 | 91 條 |

### 書籍庫（需自行準備）

將勞工法教授著作（`.docx` 或 `.pdf` 格式）放入 `data/books/` 目錄，執行 `process_books.py` 後自動切割入庫。

---

## 快速開始

### 前置需求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)（建議）、conda 或 pip
- [Groq API Key](https://console.groq.com)（免費註冊）

### 安裝步驟

**1. 取得專案**

```bash
git clone https://github.com/Chenche0119/hr-labor-law-rag.git
cd hr-labor-law-rag
```

**2. 建立虛擬環境並安裝依賴**

使用 `uv`：

```bash
uv venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

或使用 `conda`：

```bash
conda env create -f environment.yml
conda activate hr-labor-law-rag
```

> 首次執行時 sentence-transformers 會自動下載模型（約 500MB），需要網路連線。

**3. 設定 API Key**

前往 [console.groq.com](https://console.groq.com) 免費註冊並取得 API Key，然後：

```bash
cp .env.example .env
# 用任意編輯器開啟 .env，填入你的 Key：
# GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

**4. 下載法條並建立向量索引**

```bash
# 下載 4 部勞工法規（約 10 秒）
python scripts/download_laws.py

# 建立 ChromaDB 向量索引（首次約 1~2 分鐘）
python scripts/build_index.py
```

**5. 啟動系統**

```bash
python server.py
```

開啟瀏覽器前往 **http://localhost:5001**


---

## 書籍資料建置（選用）

若有勞工法教授著作（.docx 或 .pdf），可加入書籍庫以提升 B 型問題的回答品質：

```bash
# 1. 將書籍檔案放入 data/books/ 目錄
cp your_book.docx data/books/

# 2. 處理並切割成 chunk
python scripts/process_books.py

# 3. 重新建立向量索引
python scripts/build_index.py
```

---

## 專案結構

```
hr-labor-law-rag/
├── server.py                  # Flask 後端（/api/query、/api/health）
├── app.py                     # Streamlit 版本（備用）
├── requirements.txt
├── environment.yml            # conda 環境設定
├── Dockerfile                 # Cloud Run 容器設定
├── .dockerignore
├── .gcloudignore
├── .env.example               # API Key 範本
├── static/
│   └── index.html             # 單頁 HTML 前端
├── src/
│   └── rag_engine.py          # 核心 RAG 引擎
│                              #   Guardrail → Router → 檢索 → LLM
├── scripts/
│   ├── download_laws.py       # 爬取全國法規資料庫
│   ├── process_books.py       # 處理書籍 Word/PDF
│   └── build_index.py         # 建立 ChromaDB 向量索引
├── eval/
│   └── evaluation.py          # 評估腳本
├── data/
│   ├── laws/                  # 法條 JSON（自動產生）
│   └── books/                 # 書籍原始檔（手動放入）
└── chroma_db/                 # ChromaDB 向量資料庫（自動產生）
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
python eval/evaluation.py
```

評估內容：

| 評估項目 | 題數 | 指標 |
|---------|------|------|
| Guardrail 攔截準確率 | 10 題（範疇外） | 正確攔截數 / 10 |
| Guardrail 放行準確率 | 25 題（範疇內） | 正確放行數 / 25 |
| Router A 型準確率 | 10 題 | 正確分類數 / 10 |
| Router B 型準確率 | 10 題 | 正確分類數 / 10 |

結果輸出至 `eval/eval_results.json`。

---

## 組員分工

| 姓名 | 職責 |
|------|------|
| 林仰恩 | 書籍庫資料清洗、向量化與實務場景整合測試 |
| 陳姿吟 | RAG 系統核心開發、API 串接、環境部署與向量資料庫建立 |
| 許文晴 | 專案報告撰寫與系統邏輯整合 |
| 林昀蓁 | 專案報告撰寫與系統邏輯整合 |
| 吳秉彥 | GCP 託管網站、雲端部署與專案報告撰寫 |

---

## 注意事項

- 本系統提供法規資訊查詢，**不構成正式法律意見**。
- 法條內容來源為全國法規資料庫，以最新公布版本為準。
- `data/laws/`、`chroma_db/`、`.env` 不納入版本控制。
