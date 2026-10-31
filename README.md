# Guida al funzionamento: Micoflora toscana (RAG con LangGraph)

Progetto che stima la probabilità di crescita dei funghi nei boschi della Toscana in un periodo dato, combinando RAG ibrido, dati meteo e un LLM orchestrati con LangGraph.

## 1. Architettura generale

```
React (nginx) ──/api──▶ FastAPI ──▶ LangGraph ──▶ ChromaDB (vettoriale)
     ▲                                  │         BM25 (lessicale)
     └────── SSE (eventi dei nodi) ◀────┤         Open-Meteo (tool)
                                        └───────▶ Groq (LLM)
```

All'avvio il seeder legge i JSON in `backend/data/` e popola ChromaDB, poi parte uvicorn.

## 2. Il grafo LangGraph

```
parse_input
    │
route_query ──(arco condizionale)──┐
    │                              │
    ├─▶ semantic_search ──┐        │   ← fan-out parallelo
    ├─▶ literal_search  ──┤        │     (se la query è ibrida)
    │                     ▼
    │               merge_rerank          ← fan-in + RRF
    │                     │
    │               resolve_zone
    │                     │
    │               fetch_weather         ← tool @tool
    │                     │
    │              compute_features       ← codice deterministico
    │                     │
    │         ┌─▶ estimate_growth (LLM)
    │         │           │
    │         └── validate_output         ← ciclo di retry (max 2)
    │                     │
    └────────────▶ build_response
```

## 3. Cosa insegna ogni nodo

| Nodo | Concetto |
|---|---|
| `parse_input` | Validazione Pydantic come primo nodo |
| `route_query` + `dispatch` | **Conditional edge**: sceglie 1 o 2 rami |
| `semantic_search` / `literal_search` | Nodi paralleli che scrivono su chiavi diverse dello **state** |
| `merge_rerank` | **Fan-in** + Reciprocal Rank Fusion |
| `fetch_weather` | Tool LangChain richiamato dentro un nodo |
| `compute_features` | Logica deterministica accanto all'LLM |
| `estimate_growth` ⇄ `validate_output` | **Loop di retry** con validazione strutturata |
| `build_response` | Validazione finale dell'output |

## 4. Tecniche di RAG avanzato

- **Hybrid search**: ricerca semantica (embedding in Chroma) più ricerca letterale (BM25). Il semantico trova i concetti simili, il BM25 i termini esatti come i nomi latini dei funghi.
- **Routing della query**: un nodo decide se serve solo uno dei due retriever o entrambi.
- **Reciprocal Rank Fusion (RRF)**: unisce le due classifiche sommando `1/(k + posizione)` per ogni documento, senza dover normalizzare punteggi di scala diversa.
- **Metadati nei documenti**: campi come `forest_types`, `latin_names` e `verified` permettono filtri e tracciabilità delle fonti.

## 5. Come nasce la stima

1. **Baseline deterministica** (`services/features.py`): stagionalità del bosco × pioggia dei 15 giorni precedenti × temperature, con penalità per gelo e caldo.
2. **LLM (Groq)**: legge indicatori e documenti recuperati e può correggere la baseline di al massimo ±20 punti.
3. **Validazione**: se l'output non è valido si riprova fino a 2 volte, poi si ripiega sulla baseline. Senza chiave Groq si usa direttamente la baseline.

Pattern utile: l'LLM non decide da solo, corregge entro limiti un risultato deterministico, e c'è sempre un fallback.

## 6. Meteo (Open-Meteo)

- **Passato**: archivio.
- **Fino a +15 giorni**: previsioni.
- **Oltre**: climatologia, cioè la media degli stessi giorni dei 3 anni precedenti.

## 7. Streaming verso il frontend

`graph.astream(stream_mode=["custom","updates"])` fa passare gli eventi. Il decoratore `@traced` in `nodes.py` emette `node_start` e `node_end`, che arrivano al browser via SSE. La navbar mostra così in tempo reale quale nodo è attivo.

## 8. Ordine di lettura consigliato

1. `backend/app/graph/`: prima lo **state** e la definizione del grafo, per vedere come sono collegati nodi e archi.
2. `nodes.py`: `route_query`/`dispatch` per il conditional edge, poi `merge_rerank`.
3. `services/features.py`: la parte deterministica.
4. Il ciclo `estimate_growth` ⇄ `validate_output`.