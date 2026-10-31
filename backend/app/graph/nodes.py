"""I nodi del grafo. Ogni nodo è una funzione: (stato) -> aggiornamenti parziali dello stato.

Il decoratore @traced emette eventi 'custom' (node_start / node_end) che il backend
inoltra al frontend via SSE: è così che la navbar mostra i nodi in esecuzione.
Un nodo può restituire la chiave speciale '_meta' = {"summary": ..., "data": ...}
che viene tolta dallo stato e inviata solo come evento.
"""
import asyncio
import functools
import json
import re
import time
import logging

from datetime import date, timedelta

from langgraph.config import get_stream_writer
from pydantic import ValidationError

from app.config import settings
from app.graph.state import GraphState
from app.schemas import (Features, ForestShare, GrowthEstimate, Hit, Reference, SearchRequest, SearchResponse,
                         Weather, ZoneInfo)
from app.services.features import PREV_DAYS, compute_features as compute_features_service
from app.services.llm import LLMUnavailable, build_messages, call_groq
from app.services.retrieval import reciprocal_rank_fusion, retriever
from app.services.routing import classify_query
from app.services.weather import get_weather
from app.zones import FOREST_LABELS, find_zone_in_text, get_zone

MAX_DEVIATION = 25  # punti di scarto massimo ammesso tra LLM e baseline

DISCLAIMERS = [
    "Stima indicativa basata su regole semplici, dati meteo e documenti: non è un modello scientifico validato.",
    "L'app non serve a identificare funghi commestibili: fai sempre controllare la raccolta da un micologo (ispettorato micologico ASL).",
    "In Toscana la raccolta richiede il tesserino regionale e il rispetto di limiti e divieti: verifica la normativa vigente.",
    "I riferimenti bibliografici nella base di conoscenza sono marcati 'da verificare' finché non li controlli sulle fonti originali.",
]

logger = logging.getLogger("uvicorn.error")


def traced(name: str):
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(state: GraphState):
            write = get_stream_writer()
            write({"event": "node_start", "node": name})
            t0 = time.perf_counter()
            try:
                out = await fn(state)
            except Exception as exc:
                write({"event": "node_error", "node": name, "message": str(exc)})
                raise
            meta = out.pop("_meta", {})
            write({"event": "node_end", "node": name, "ms": round((time.perf_counter() - t0) * 1000),
                   "summary": meta.get("summary"), "data": meta.get("data")})
            return out
        return wrapper
    return decorator


# 1) Validazione dell'input ---------------------------------------------------
@traced("parse_input")
async def parse_input(state: GraphState):
    raw = dict(state["request"])
    if not raw.get("zone_id"):
        zone = find_zone_in_text(raw.get("query", ""))
        if zone:
            raw["zone_id"] = zone["id"]
    req = SearchRequest.model_validate(raw)  # Pydantic: errori chiari se l'input è sbagliato
    if not get_zone(req.zone_id):
        raise ValueError("Zona non riconosciuta: selezionala sulla mappa o dal menu.")
    return {"request": req.model_dump(mode="json"), "attempts": 0,
            "_meta": {"summary": f"{req.zone_id}, {req.start_date} → {req.end_date}"}}


# 2) Router: semantica, letterale o ibrida ------------------------------------
@traced("route_query")
async def route_query(state: GraphState):
    mode, reason, terms = classify_query(state["request"]["query"])
    return {"mode": mode, "mode_reason": reason, "latin_terms": terms,
            "_meta": {"summary": mode, "data": {"mode": mode, "reason": reason}}}


def dispatch(state: GraphState) -> list[str]:
    """Arco condizionale: restituisce i nodi da eseguire. Due nomi = esecuzione in parallelo."""
    return {"semantic": ["semantic_search"], "literal": ["literal_search"],
            "hybrid": ["semantic_search", "literal_search"]}[state["mode"]]


# 3) Ricerche -----------------------------------------------------------------
@traced("semantic_search")
async def semantic_search(state: GraphState):
    req, zone = state["request"], get_zone(state["request"]["zone_id"])
    query = f'{req["query"]}. Zona: {zone["name"]}'
    hits = await asyncio.to_thread(retriever.semantic, query, 6, list(zone["forests"]))
    return {"semantic_hits": hits, "_meta": {"summary": f"{len(hits)} passaggi (ChromaDB)"}}


@traced("literal_search")
async def literal_search(state: GraphState):
    query = state["request"]["query"] + " " + " ".join(state.get("latin_terms", []))
    hits = await asyncio.to_thread(retriever.bm25_search, query, 6)
    return {"literal_hits": hits, "_meta": {"summary": f"{len(hits)} passaggi (BM25)"}}


@traced("merge_rerank")
async def merge_rerank(state: GraphState):
    lists = [state.get("semantic_hits", []), state.get("literal_hits", [])]
    hits = reciprocal_rank_fusion([l for l in lists if l])
    return {"hits": hits, "_meta": {"summary": f"{len(hits)} risultati dopo RRF"}}


# 4) Zona e meteo -------------------------------------------------------------
@traced("resolve_zone")
async def resolve_zone(state: GraphState):
    zone = get_zone(state["request"]["zone_id"])
    return {"zone": zone, "_meta": {"summary": f'{zone["name"]} ({zone["altitude_min"]}-{zone["altitude_max"]} m)'}}


@traced("fetch_weather")
async def fetch_weather(state: GraphState):
    req, zone = state["request"], state["zone"]
    start = date.fromisoformat(req["start_date"]) - timedelta(days=PREV_DAYS)  # includo i giorni precedenti
    try:
        weather = await get_weather.ainvoke({  # chiamata al tool LangChain
            "latitude": zone["lat"], "longitude": zone["lon"],
            "start_date": start.isoformat(), "end_date": req["end_date"]})
        summary = ", ".join(weather["sources"]) or "nessun dato"
    except Exception as exc:  # il grafo prosegue senza meteo, con confidenza ridotta
        weather = {"days": [], "sources": [], "note": None, "error": f"Meteo non disponibile: {exc}"}
        summary = "errore meteo (proseguo senza)"
    return {"weather": weather, "_meta": {"summary": summary}}


@traced("compute_features")
async def compute_features(state: GraphState):
    req = state["request"]
    feats = compute_features_service(state["zone"], date.fromisoformat(req["start_date"]),
                                     date.fromisoformat(req["end_date"]), state["weather"]["days"])
    return {"features": feats, "_meta": {"summary": f'baseline {feats["baseline_percent"]}%'}}


# 5) Stima con LLM + validazione + eventuale retry ---------------------------
@traced("estimate_growth")
async def estimate_growth(state: GraphState):
    attempts = state.get("attempts", 0) + 1
    messages = build_messages(state["zone"], state["request"], state["features"], state["weather"].get("note"),
                              state.get("hits", []), state.get("validation_error"))
    try:
        raw = await call_groq(messages)
        summary = f"tentativo {attempts}"
    except LLMUnavailable:
        raw, summary = None, "LLM non configurato"
    except Exception as exc:
        logger.exception("Chiamata Groq fallita")
        raw, summary = None, f"errore LLM: {type(exc).__name__}: {str(exc)[:150]}"
    return {"llm_raw": raw, "attempts": attempts, "_meta": {"summary": summary}}


def _fallback_growth(features: dict, reason: str) -> dict:
    conf = "low" if not features["weather_available"] else "medium"
    factors = [f'Stagionalità {features["seasonal_index"]:.2f}', f'Punteggio pioggia {features["score_rain"]:.2f}',
               f'Punteggio temperatura {features["score_temp"]:.2f}']
    return GrowthEstimate(
        percentage=round(features["baseline_percent"]), confidence=conf, method="deterministic",
        rationale=f"Stima calcolata solo con gli indicatori deterministici ({reason}). "
                  "Combina stagionalità del bosco, pioggia recente e temperature.",
        key_factors=factors).model_dump()


@traced("validate_output")
async def validate_output(state: GraphState):
    feats, raw = state["features"], state.get("llm_raw")
    if raw is None:  # LLM non disponibile: inutile riprovare
        return {"growth": _fallback_growth(feats, "LLM non disponibile"), "validation_error": None,
                "_meta": {"summary": "fallback deterministico"}}
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        growth = GrowthEstimate.model_validate_json(match.group(0) if match else raw)
        if abs(growth.percentage - feats["baseline_percent"]) > MAX_DEVIATION:
            raise ValueError(f'percentuale troppo distante dalla baseline ({feats["baseline_percent"]})')
        growth.method = "llm"
        return {"growth": growth.model_dump(), "validation_error": None, "_meta": {"summary": "output valido"}}
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        msg = str(exc).splitlines()[0][:200]
        if state.get("attempts", 0) >= settings.max_llm_attempts:
            return {"growth": _fallback_growth(feats, "output LLM non valido dopo i tentativi"),
                    "validation_error": None, "_meta": {"summary": "fallback dopo retry"}}
        return {"growth": None, "validation_error": msg, "_meta": {"summary": f"non valido, riprovo: {msg}"}}


def after_validate(state: GraphState) -> str:
    return "done" if state.get("growth") else "retry"


# 6) Risposta finale ----------------------------------------------------------
@traced("build_response")
async def build_response(state: GraphState):
    req, zone = state["request"], state["zone"]
    start, end = date.fromisoformat(req["start_date"]), date.fromisoformat(req["end_date"])
    weather = dict(state["weather"])
    weather["days"] = [{**d, "in_period": start <= date.fromisoformat(d["date"]) <= end} for d in weather["days"]]

    seen, refs = set(), []
    for h in state.get("hits", []):
        if h["reference"] and h["reference"] not in seen and h["category"] in ("scienza", "consiglio", "periodo"):
            seen.add(h["reference"])
            refs.append(Reference(title=h["title"], reference=h["reference"], verified=h["verified"]))

    response = SearchResponse(
        query=req["query"], mode=state["mode"], mode_reason=state["mode_reason"],
        zone=ZoneInfo(**zone), start_date=start, end_date=end,
        hits=[Hit(**h) for h in state.get("hits", [])], references=refs,
        forest_breakdown=[ForestShare(type=t, label=FOREST_LABELS.get(t, t), weight=w) for t, w in zone["forests"].items()],
        weather=Weather(**weather), features=Features(**state["features"]),
        growth=GrowthEstimate(**state["growth"]), disclaimers=DISCLAIMERS,
    )  # ultima validazione Pydantic dell'intero output
    return {"response": response.model_dump(mode="json"),
            "_meta": {"summary": f'{response.growth.percentage}% ({response.growth.method})'}}
