"""Flask backend: wraps the RAG engine in an HTTP API for the frontend."""
import json
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory

from src.config import HOST, PORT

load_dotenv(Path(__file__).parent / ".env")

app = Flask(__name__, static_folder="static")

TYPE_LABELS = {
    "A": "直接查詢型（法條庫）",
    "B": "爭議解釋型（書籍庫＋法條庫）",
    "out_of_scope": "超出服務範疇",
    "no_law": "現行法規無明確規定",
}

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


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _serialize_result(ev: dict) -> dict:
    return {
        "step": "result",
        "answer": ev["answer"],
        "query_type": ev["query_type"],
        "query_type_label": TYPE_LABELS.get(
            ev["query_type"], ev["query_type"]
        ),
        "guardrail_passed": ev.get("guardrail_passed", True),
        "chunks": [
            {
                "source": c.source,
                "content": c.content[:300],
                "distance": round(c.distance, 4),
                "collection": c.collection,
            }
            for c in ev.get("chunks", [])
        ],
    }


@app.route("/api/query", methods=["POST"])
def query():
    data = request.get_json()
    question = (data or {}).get("question", "").strip()
    if not question:
        return jsonify({"error": "問題不能為空"}), 400

    def stream():
        try:
            for ev in get_engine().query_stream(question):
                if ev["step"] == "result":
                    yield _sse(_serialize_result(ev))
                else:
                    yield _sse(ev)
        except Exception as e:
            yield _sse({"step": "error", "error": f"系統錯誤：{e}"})

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print(f"\n🔗 open http://localhost:{PORT}\n")
    app.run(debug=False, host=HOST, port=PORT)
