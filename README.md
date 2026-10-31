# Micoflora toscana: progetto RAG con LangGraph

Sito per stimare la probabilità di crescita dei funghi nei boschi della Toscana in un periodo dato.
Progetto pensato anche per **imparare LangGraph**: i nodi sono commentati e visibili in tempo reale nella navbar.

## Avvio rapido

```bash
cp .env.example .env        # inserisci GROQ_API_KEY (senza chiave l'app funziona con la sola stima deterministica)
docker compose up --build
```

- App: http://localhost:8080
- API / Swagger: http://localhost:8000/docs

Il primo build scarica il modello di embedding (~120 MB) dentro l'immagine; l'avvio successivo è rapido.

## Architettura

```
React (nginx :80) ──/api──▶ FastAPI ──▶ LangGraph ──▶ ChromaDB (volume) + BM25 + Open-Meteo + Groq
```

Il container backend esegue **prima** `python -m app.seeder` (popola ChromaDB dai JSON in `backend/data/`)
e **poi** avvia uvicorn, quindi i dati sono disponibili da subito.

## Il grafo (backend/app/graph)

```
parse_input → route_query ─┬→ semantic_search ─┐
                           ├→ literal_search ──┼→ merge_rerank → resolve_zone → fetch_weather
                           └→ (ibrida: entrambi in parallelo)                       │
   build_response ← validate_output ⇄ estimate_growth ← compute_features ←──────────┘
```

| Nodo | Cosa insegna |
|---|---|
| `parse_input` | validazione con Pydantic come primo nodo |
| `route_query` + `dispatch` | **arco condizionale** che sceglie uno o due rami (fan-out parallelo) |
| `semantic_search` / `literal_search` | nodi paralleli che scrivono in chiavi diverse dello stato |
| `merge_rerank` | **fan-in** e Reciprocal Rank Fusion |
| `fetch_weather` | uso di un **tool LangChain** (`@tool`) dentro un nodo |
| `compute_features` | codice deterministico accanto all'LLM |
| `estimate_growth` ⇄ `validate_output` | **ciclo di retry** con validazione Pydantic |
| `build_response` | validazione finale dell'intero output |

Lo streaming usa `graph.astream(stream_mode=["custom","updates"])`: il decoratore `@traced` in `nodes.py`
emette gli eventi `node_start` / `node_end` che il frontend riceve via SSE.

## Come funziona la stima

1. **Baseline deterministica** (`services/features.py`): stagionalità del bosco × pioggia dei 15 giorni precedenti × temperature, con penalità per gelo e caldo.
2. **LLM (Groq)** interpreta indicatori e documenti RAG e può correggere la baseline di al massimo 20 punti.
3. Se l'output non è valido si riprova (max 2 volte), poi si usa la baseline. Se la chiave Groq manca si usa subito la baseline.

È un'euristica indicativa, **non un modello scientifico validato**.

## Meteo (Open-Meteo)

Passato → archivio; ultimi giorni fino a +15 giorni → previsioni; oltre → climatologia (media degli stessi giorni nei 3 anni precedenti), segnalata nell'interfaccia.

## Aggiungere conoscenza

Modifica o aggiungi documenti nei JSON di `backend/data/` (campi: `id`, `category`, `title`, `text`, `forest_types`, `latin_names`, `reference`, `verified`) e riavvia il backend: il seeder rileva le modifiche e reindicizza.
Per i riferimenti bibliografici: quelli inclusi sono **da verificare** sulle fonti originali prima di citarli; imposta `"verified": true` quando li hai controllati.

## Sviluppo senza Docker

```bash
cd backend && pip install -r requirements.txt && cp ../.env.example .env && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev      # http://localhost:5173 (proxy /api → :8000)
```

## Limiti noti

- Le zone sono cerchi indicativi (centro + raggio), non confini amministrativi.
- Stagionalità e soglie di pioggia/temperatura sono valori di partenza da calibrare.
- Non identifica funghi; la raccolta richiede il tesserino regionale e il controllo di un micologo.
