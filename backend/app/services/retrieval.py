"""Retrieval ibrido: ChromaDB (semantico) + BM25 (letterale) + fusione RRF."""
import re
import unicodedata

from rank_bm25 import BM25Okapi

from app.seeder import build_chunks, get_collection, seed
from app.services.embeddings import embed

STOPWORDS = {"il", "lo", "la", "le", "i", "gli", "un", "una", "di", "del", "della", "dei", "delle", "da", "in",
             "con", "su", "per", "a", "e", "o", "che", "nel", "nella", "nei", "al", "alla", "ai", "come", "sono"}


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", normalize(text)) if t not in STOPWORDS]


def _hit(id_: str, text: str, meta: dict, score: float, source: str) -> dict:
    return {
        "id": id_, "title": meta["title"], "category": meta["category"], "text": text,
        "snippet": text[:420], "score": round(float(score), 4), "source": source,
        "reference": meta.get("reference", ""), "verified": bool(meta.get("verified", False)),
    }


class Retriever:
    def __init__(self) -> None:
        self.col = None
        self.chunks: list[dict] = []
        self.bm25: BM25Okapi | None = None

    def load(self) -> None:
        if self.col is not None:
            return
        seed()  # idempotente: se il seeder è già girato non fa nulla
        self.col = get_collection()
        self.chunks = build_chunks()
        self.bm25 = BM25Okapi([tokenize(c["search_text"]) for c in self.chunks])

    # --- ricerca semantica (ChromaDB) --------------------------------------
    def semantic(self, query: str, k: int = 6, forest_types: list[str] | None = None) -> list[dict]:
        self.load()
        res = self.col.query(
            query_embeddings=embed([query]),
            n_results=min(k * 2, len(self.chunks)),
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for id_, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]):
            score = 1 - dist  # distanza coseno -> similarità
            if forest_types and set(meta.get("forest_types", "").split(",")) & set(forest_types):
                score += 0.05  # piccolo bonus ai documenti pertinenti ai boschi della zona
            hits.append(_hit(id_, doc, meta, score, "semantic"))
        hits.sort(key=lambda h: -h["score"])
        return hits[:k]

    # --- ricerca letterale (BM25) ------------------------------------------
    def bm25_search(self, query: str, k: int = 6) -> list[dict]:
        self.load()
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [_hit(self.chunks[i]["id"], self.chunks[i]["text"], self.chunks[i]["metadata"], scores[i], "bm25")
                for i in ranked if scores[i] > 0]


def reciprocal_rank_fusion(result_lists: list[list[dict]], k: int = 60, top_n: int = 8) -> list[dict]:
    """Fonde più classifiche: score = somma di 1 / (k + posizione)."""
    fused: dict[str, dict] = {}
    for hits in result_lists:
        for rank, h in enumerate(hits, start=1):
            entry = fused.setdefault(h["id"], {**h, "score": 0.0, "_sources": set()})
            entry["score"] += 1.0 / (k + rank)
            entry["_sources"].add(h["source"])
    out = []
    for e in sorted(fused.values(), key=lambda x: -x["score"])[:top_n]:
        sources = e.pop("_sources")
        e["source"] = "both" if len(sources) > 1 else next(iter(sources))
        e["score"] = round(e["score"], 4)
        out.append(e)
    return out


retriever = Retriever()
