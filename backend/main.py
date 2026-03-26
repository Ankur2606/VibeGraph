"""
main.py — FastAPI application for the O2C Graph Intelligence System.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from data_loader import get_con
from graph_builder import build_graph
from guardrails import is_on_topic, REJECTION_MESSAGE
from query_engine import answer_query

app = FastAPI(title="O2C Graph Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pre-load data on startup
@app.on_event("startup")
async def startup_event():
    print("[main] Loading data into DuckDB...")
    get_con()
    print("[main] Data loaded. Server ready.")


# ── Cache the graph in memory (compute once) ─────────────────────────────────
_graph_cache: dict | None = None


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/graph")
async def get_graph():
    global _graph_cache
    if _graph_cache is None:
        _graph_cache = build_graph()
    return _graph_cache


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
async def chat(req: ChatRequest):
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Guardrail check
    if not is_on_topic(message):
        return {
            "answer": REJECTION_MESSAGE,
            "code": "",
            "code_type": "none",
        }

    try:
        result = answer_query(message)
        return result
    except ValueError as e:
        # GROQ_API_KEY not configured
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
