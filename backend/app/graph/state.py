"""Lo STATO è la memoria condivisa del grafo: ogni nodo legge da qui e restituisce solo gli aggiornamenti."""
from typing import TypedDict


class GraphState(TypedDict, total=False):
    request: dict            # SearchRequest serializzato
    mode: str                # semantic | literal | hybrid
    mode_reason: str
    latin_terms: list[str]
    semantic_hits: list[dict]
    literal_hits: list[dict]
    hits: list[dict]         # risultato della fusione
    zone: dict
    weather: dict
    features: dict
    llm_raw: str | None      # risposta grezza dell'LLM
    attempts: int            # tentativi LLM già fatti
    validation_error: str | None
    growth: dict | None
    response: dict
