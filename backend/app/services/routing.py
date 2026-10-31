"""Classificazione della query: semantica, letterale o ibrida (regole deterministiche)."""
import re
from functools import lru_cache

from app.seeder import load_documents
from app.services.retrieval import STOPWORDS, normalize

# Radici di parole che indicano una domanda sulle *condizioni* di crescita.
CONDITION_STEMS = (
    "piogg", "piove", "umid", "temperatur", "cald", "fredd", "gelo", "gelat", "siccit", "cresc", "condizion",
    "period", "stagion", "quando", "dove", "clim", "meteo", "terren", "suol", "altitud", "esposiz", "bosc",
    "faggeta", "castagnet", "quercet", "abetin", "lecce", "pinet", "favor", "fruttific", "nascit", "produz",
    "micorriz", "rugiad", "nebbi", "autunn", "estat", "primavera", "inverno",
)
ABBREV = re.compile(r"\b[A-Z]\.\s?[a-z]{3,}\b")  # es. "B. edulis"


@lru_cache(maxsize=1)
def _latin_vocab() -> tuple[set[str], set[str]]:
    full: set[str] = set()
    for d in load_documents():
        full.update(normalize(n) for n in d.get("latin_names", []))
    genera = {n.split()[0] for n in full if len(n.split()) >= 2}
    return full, genera


def classify_query(query: str) -> tuple[str, str, list[str]]:
    """Restituisce (modo, motivazione, termini_latini)."""
    full, genera = _latin_vocab()
    q = normalize(query)

    terms = [n for n in full if n in q]
    terms += [g for g in genera if re.search(rf"\b{g}\b", q) and not any(g in t for t in terms)]
    terms += [m.group(0) for m in ABBREV.finditer(query)]

    remaining = q
    for t in terms:
        remaining = remaining.replace(normalize(t), " ")
    tokens = [t for t in re.findall(r"\w+", remaining) if t not in STOPWORDS]
    has_condition = any(t.startswith(CONDITION_STEMS) for t in tokens)
    long_text = len(tokens) >= 3

    if terms and (has_condition or long_text):
        return "hybrid", f"Nome latino ({', '.join(terms[:3])}) più una domanda sulle condizioni di crescita.", terms
    if terms:
        return "literal", f"Rilevato nome scientifico: {', '.join(terms[:3])}. Uso la ricerca letterale (BM25).", terms
    if not has_condition and len(tokens) <= 2:
        return "literal", "Termine breve e specifico: cerco la corrispondenza esatta (BM25).", []
    return "semantic", "Domanda descrittiva sulle condizioni di crescita: uso la ricerca semantica (ChromaDB).", []
