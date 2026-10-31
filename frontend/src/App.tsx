import { useCallback, useEffect, useRef, useState } from "react";
import { fetchGraph, fetchZones, streamSearch } from "./api";
import GraphNavbar from "./components/GraphNavbar";
import MapView from "./components/MapView";
import ResultPanel from "./components/ResultPanel";
import SearchBar from "./components/SearchBar";
import type { GraphNodeMeta, NodeStatus, SearchMode, SearchResponse, StreamEvent, Zone } from "./types";

const iso = (d: Date) => d.toISOString().slice(0, 10);
const addDays = (n: number) => { const d = new Date(); d.setDate(d.getDate() + n); return iso(d); };

export default function App() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [nodes, setNodes] = useState<GraphNodeMeta[]>([]);
  const [status, setStatus] = useState<Record<string, NodeStatus>>({});
  const [query, setQuery] = useState("");
  const [zoneId, setZoneId] = useState("casentino");
  const [start, setStart] = useState(addDays(0));
  const [end, setEnd] = useState(addDays(7));
  const [mode, setMode] = useState<{ mode: SearchMode; reason: string } | null>(null);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetchZones().then(setZones).catch((e) => setError(e.message));
    fetchGraph().then(setNodes).catch((e) => setError(e.message));
  }, []);

  const onEvent = useCallback((ev: StreamEvent) => {
    if (ev.event === "node_start") {
      setStatus((s) => ({ ...s, [ev.node]: { state: "running" } }));
    } else if (ev.event === "node_end") {
      setStatus((s) => ({ ...s, [ev.node]: { state: "done", ms: ev.ms, summary: ev.summary } }));
      if (ev.node === "route_query" && ev.data) setMode({ mode: ev.data.mode, reason: ev.data.reason });
    } else if (ev.event === "node_error") {
      setStatus((s) => ({ ...s, [ev.node]: { state: "error", summary: ev.message } }));
    } else if (ev.event === "result") {
      setResult(ev.data);
    } else if (ev.event === "error") {
      setError(ev.message);
    }
  }, []);

  const run = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true); setError(null); setResult(null); setMode(null); setStatus({});
    try {
      await streamSearch({ query, zone_id: zoneId, start_date: start, end_date: end }, onEvent, ctrl.signal);
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const selected = zones.find((z) => z.id === zoneId);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden>🍄</span>
          <div>
            <h1>Micoflora toscana</h1>
            <p>Dove e quando crescono i funghi nei boschi della Toscana</p>
          </div>
        </div>
        <SearchBar
          query={query} setQuery={setQuery} start={start} setStart={setStart} end={end} setEnd={setEnd}
          zones={zones} zoneId={zoneId} setZoneId={setZoneId} onSubmit={run} loading={loading} mode={mode}
        />
      </header>

      <GraphNavbar nodes={nodes} status={status} />

      <main className="main">
        <section className="map-wrap" aria-label="Mappa delle zone">
          <MapView zones={zones} selectedId={zoneId} onSelect={setZoneId} result={result} />
        </section>
        <aside className="panel" aria-live="polite">
          <ResultPanel result={result} loading={loading} error={error} zone={selected} />
        </aside>
      </main>
    </div>
  );
}
