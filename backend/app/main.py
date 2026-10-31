"""API FastAPI: espone zone, struttura del grafo e la ricerca in streaming (SSE)."""
import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.graph.builder import NODE_META, graph
from app.schemas import SearchRequest, ZoneInfo
from app.services.retrieval import retriever
from app.zones import ZONES


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(retriever.load)  # carica Chroma, costruisce BM25, scalda gli embedding
    yield


app = FastAPI(title="Tuscan Mycology RAG", lifespan=lifespan)


@app.get("/api/health")
async def health():
    return {"status": "ok", "chunks": len(retriever.chunks)}


@app.get("/api/zones")
async def zones() -> list[ZoneInfo]:
    return [ZoneInfo(**z) for z in ZONES]


@app.get("/api/graph")
async def graph_meta():
    return {"nodes": NODE_META}


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


@app.post("/api/search")
async def search(req: SearchRequest):
    async def stream():
        try:
            # stream_mode "custom": eventi emessi dai nodi; "updates": aggiornamenti di stato per nodo
            async for mode, chunk in graph.astream({"request": req.model_dump(mode="json")},
                                                   stream_mode=["custom", "updates"]):
                if mode == "custom":
                    yield sse(chunk)
                elif mode == "updates" and "build_response" in chunk:
                    yield sse({"event": "result", "data": chunk["build_response"]["response"]})
        except Exception as exc:
            yield sse({"event": "error", "message": str(exc)})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
