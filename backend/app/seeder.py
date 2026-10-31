"""Seeder: legge i JSON in data/, li divide in chunk e li carica in ChromaDB.

Si lancia con:  python -m app.seeder  [--force]
È idempotente: se i dati non sono cambiati non fa nulla.
"""
import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

DATA_FILES = ["forests.json", "species.json", "periods.json", "science.json", "expert_tips.json"]


@lru_cache(maxsize=1)
def load_documents() -> list[dict]:
    docs: list[dict] = []
    for name in DATA_FILES:
        docs.extend(json.loads((Path(settings.data_dir) / name).read_text(encoding="utf-8")))
    return docs


def chunk_text(text: str, max_chars: int = 650, overlap: int = 100) -> list[str]:
    """Divide per frasi, accorpando fino a max_chars; piccola sovrapposizione tra chunk."""
    sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
    chunks, current = [], ""
    for s in sentences:
        s = s if s.endswith(".") else s + "."
        if current and len(current) + len(s) + 1 > max_chars:
            chunks.append(current)
            current = current[-overlap:].split(" ", 1)[-1] + " " + s
        else:
            current = f"{current} {s}".strip()
    if current:
        chunks.append(current)
    return chunks or [text]


def build_chunks() -> list[dict]:
    chunks = []
    for doc in load_documents():
        for i, piece in enumerate(chunk_text(doc["text"])):
            text = f'{doc["title"]}. {piece}'
            chunks.append({
                "id": f'{doc["id"]}#{i}',
                "text": text,
                # testo per BM25: titolo + nomi latini + contenuto
                "search_text": f'{text} {" ".join(doc.get("latin_names", []))}',
                "metadata": {
                    "doc_id": doc["id"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "forest_types": ",".join(doc.get("forest_types", [])),
                    "latin_names": ",".join(doc.get("latin_names", [])),
                    "reference": doc.get("reference", ""),
                    "verified": bool(doc.get("verified", False)),
                },
            })
    return chunks


def _client():
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=settings.chroma_path,
                                     settings=ChromaSettings(anonymized_telemetry=False))


def get_collection():
    return _client().get_collection(settings.collection_name)


def _data_hash(chunks: list[dict]) -> str:
    h = hashlib.sha256(settings.embedding_model.encode())
    for c in chunks:
        h.update(c["id"].encode())
        h.update(c["text"].encode())
    return h.hexdigest()


def seed(force: bool = False) -> str:
    from app.services.embeddings import embed

    chunks = build_chunks()
    digest = _data_hash(chunks)
    hash_file = Path(settings.chroma_path) / ".seed_hash"
    client = _client()

    if not force:
        try:
            col = client.get_collection(settings.collection_name)
            if col.count() == len(chunks) and hash_file.exists() and hash_file.read_text() == digest:
                print(f"[seeder] collezione già aggiornata ({col.count()} chunk): nessuna azione")
                return "skipped"
        except Exception:
            pass

    try:
        client.delete_collection(settings.collection_name)
    except Exception:
        pass
    col = client.create_collection(settings.collection_name, metadata={"hnsw:space": "cosine"})

    for i in range(0, len(chunks), 32):
        batch = chunks[i:i + 32]
        col.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
            embeddings=embed([c["text"] for c in batch]),
        )
    hash_file.write_text(digest)
    print(f"[seeder] indicizzati {len(chunks)} chunk da {len(load_documents())} documenti")
    return "seeded"


if __name__ == "__main__":
    seed(force="--force" in sys.argv)
