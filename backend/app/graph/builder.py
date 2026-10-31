"""Assemblaggio del grafo: nodi + archi (fissi e condizionali)."""
from langgraph.graph import END, START, StateGraph

from app.graph import nodes as n
from app.graph.state import GraphState

# Metadati usati dal frontend per disegnare la navbar (stage = colonna; stessa colonna = parallelo)
NODE_META = [
    {"id": "parse_input", "label": "Parse input", "stage": 0, "description": "Valida richiesta, zona e date con Pydantic"},
    {"id": "route_query", "label": "Route query", "stage": 1, "description": "Decide: ricerca semantica, letterale o ibrida"},
    {"id": "semantic_search", "label": "Semantic search", "stage": 2, "description": "ChromaDB: condizioni di crescita"},
    {"id": "literal_search", "label": "Literal search", "stage": 2, "description": "BM25: nomi latini e termini esatti"},
    {"id": "merge_rerank", "label": "Merge + RRF", "stage": 3, "description": "Fonde le classifiche (Reciprocal Rank Fusion)"},
    {"id": "resolve_zone", "label": "Resolve zone", "stage": 4, "description": "Boschi, quota e coordinate della zona"},
    {"id": "fetch_weather", "label": "Fetch weather", "stage": 5, "description": "Tool LangChain su Open-Meteo"},
    {"id": "compute_features", "label": "Compute features", "stage": 6, "description": "Indicatori deterministici e baseline"},
    {"id": "estimate_growth", "label": "Estimate (Groq)", "stage": 7, "description": "L'LLM interpreta dati e documenti"},
    {"id": "validate_output", "label": "Validate", "stage": 8, "description": "Pydantic valida; se serve, retry"},
    {"id": "build_response", "label": "Build response", "stage": 9, "description": "Assembla la risposta finale"},
]


def build_graph():
    g = StateGraph(GraphState)
    for name in ["parse_input", "route_query", "semantic_search", "literal_search", "merge_rerank", "resolve_zone",
                 "fetch_weather", "compute_features", "estimate_growth", "validate_output", "build_response"]:
        g.add_node(name, getattr(n, name))

    g.add_edge(START, "parse_input")
    g.add_edge("parse_input", "route_query")
    # arco condizionale: uno o due nodi (fan-out parallelo nel caso ibrido)
    g.add_conditional_edges("route_query", n.dispatch, ["semantic_search", "literal_search"])
    g.add_edge("semantic_search", "merge_rerank")  # fan-in: merge_rerank parte quando i rami attivi hanno finito
    g.add_edge("literal_search", "merge_rerank")
    g.add_edge("merge_rerank", "resolve_zone")
    g.add_edge("resolve_zone", "fetch_weather")
    g.add_edge("fetch_weather", "compute_features")
    g.add_edge("compute_features", "estimate_growth")
    g.add_edge("estimate_growth", "validate_output")
    # ciclo di retry
    g.add_conditional_edges("validate_output", n.after_validate, {"retry": "estimate_growth", "done": "build_response"})
    g.add_edge("build_response", END)
    return g.compile()


graph = build_graph()
