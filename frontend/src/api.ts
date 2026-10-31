import type { GraphNodeMeta, SearchRequest, StreamEvent, Zone } from "./types";

export async function fetchZones(): Promise<Zone[]> {
  const r = await fetch("/api/zones");
  if (!r.ok) throw new Error("Impossibile caricare le zone");
  return r.json();
}

export async function fetchGraph(): Promise<GraphNodeMeta[]> {
  const r = await fetch("/api/graph");
  if (!r.ok) throw new Error("Impossibile caricare il grafo");
  return (await r.json()).nodes;
}

/** POST + lettura dello stream SSE (EventSource non supporta POST, quindi uso fetch). */
export async function streamSearch(req: SearchRequest, onEvent: (e: StreamEvent) => void, signal: AbortSignal) {
  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok || !res.body) {
    let msg = `Errore ${res.status}`;
    try {
      const body = await res.json();
      const d = body.detail;
      msg = Array.isArray(d) ? d.map((x: { msg: string }) => x.msg.replace("Value error, ", "")).join("; ") : d ?? msg;
    } catch { /* corpo non JSON */ }
    throw new Error(msg);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const line = block.split("\n").find((l) => l.startsWith("data:"));
      if (line) onEvent(JSON.parse(line.slice(5).trim()));
    }
  }
}
