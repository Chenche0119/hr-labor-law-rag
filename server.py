"""Flask backend: wraps the RAG engine in an HTTP API for the frontend."""
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from src.config import PORT

load_dotenv(Path(__file__).parent / ".env")

app = Flask(__name__, static_folder="static")

# Lazy-load the RAG engine (avoid needing an API key at startup)
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        from src.rag_engine import RAGEngine

        _engine = RAGEngine()
    return _engine


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/query", methods=["POST"])
def query():
    data = request.get_json()
    question = (data or {}).get("question", "").strip()
    if not question:
        return jsonify({"error": "問題不能為空"}), 400

    try:
        result = get_engine().query(question)
    except Exception as e:
        return jsonify({"error": f"系統錯誤：{e}"}), 500

    type_labels = {
        "A": "直接查詢型（法條庫）",
        "B": "爭議解釋型（書籍庫＋法條庫）",
        "out_of_scope": "超出服務範疇",
        "no_law": "現行法規無明確規定",
    }

    return jsonify(
        {
            "answer": result.answer,
            "query_type": result.query_type,
            "query_type_label": type_labels.get(
                result.query_type, result.query_type
            ),
            "guardrail_passed": result.guardrail_passed,
            "chunks": [
                {
                    "source": c.source,
                    "content": c.content[:300],
                    "distance": round(c.distance, 4),
                    "collection": c.collection,
                }
                for c in result.chunks
            ],
        }
    )


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print(f"\n🔗 open http://localhost:{PORT}\n")
    app.run(debug=False, port=PORT)
