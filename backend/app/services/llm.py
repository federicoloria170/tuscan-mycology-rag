"""Chiamata a Groq (via langchain-groq) per interpretare indicatori + documenti RAG."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings

SYSTEM = """Sei un assistente esperto di micologia toscana. Ricevi: indicatori meteo calcolati, informazioni sul
bosco e brani di documenti recuperati da una base di conoscenza. Devi stimare la probabilità di crescita di funghi
epigei spontanei nella zona e nel periodo indicati.

Regole:
- Ti viene dato un punteggio 'baseline' calcolato con regole deterministiche: puoi correggerlo di al massimo 20 punti,
  e solo se i documenti o i dati lo giustificano.
- Usa solo i dati forniti; non inventare citazioni o misure.
- Se i dati meteo sono assenti o sono climatologia, abbassa la confidenza.
- Rispondi in italiano con UN SOLO oggetto JSON, senza testo aggiuntivo, con questo schema:
{"percentage": <intero 0-100>, "confidence": "low"|"medium"|"high",
 "rationale": "<2-4 frasi che spiegano la stima>", "key_factors": ["<max 5 fattori brevi>"]}"""


class LLMUnavailable(Exception):
    """Chiave Groq non configurata."""


def build_messages(zone: dict, req: dict, features: dict, weather_note: str | None,
                   hits: list[dict], prev_error: str | None) -> list:
    docs = "\n".join(f'- [{h["title"]}] {h["text"][:450]}' for h in hits[:5]) or "(nessun documento)"
    payload = {
        "zona": zone["name"], "boschi": zone["forests"],
        "quota_m": [zone["altitude_min"], zone["altitude_max"]],
        "periodo": [req["start_date"], req["end_date"]],
        "richiesta_utente": req["query"], "indicatori": features, "nota_meteo": weather_note,
    }
    user = f"DATI:\n{json.dumps(payload, ensure_ascii=False)}\n\nDOCUMENTI:\n{docs}\n"
    if prev_error:
        user += f"\nLa risposta precedente non era valida ({prev_error}). Correggila e rispondi solo con il JSON."
    return [SystemMessage(content=SYSTEM), HumanMessage(content=user)]


async def call_groq(messages: list) -> str:
    if not settings.groq_api_key:
        raise LLMUnavailable("GROQ_API_KEY non configurata")
    from langchain_groq import ChatGroq

    llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key,
                   temperature=0.2, max_tokens=3000)
    try:
        # prima provo con la modalità JSON forzata (se il modello la supporta)
        result = await llm.bind(response_format={"type": "json_object"}).ainvoke(messages)
    except Exception as exc:
        if "BadRequest" not in type(exc).__name__:
            raise
        # il modello rifiuta quel parametro: riprovo senza, il prompt chiede già solo JSON
        result = await llm.ainvoke(messages)
    return result.content