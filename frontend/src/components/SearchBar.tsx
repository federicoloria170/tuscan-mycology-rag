import type { SearchMode, Zone } from "../types";

interface Props {
  query: string; setQuery: (v: string) => void;
  start: string; setStart: (v: string) => void;
  end: string; setEnd: (v: string) => void;
  zones: Zone[]; zoneId: string; setZoneId: (v: string) => void;
  onSubmit: () => void; loading: boolean;
  mode: { mode: SearchMode; reason: string } | null;
}

const MODE_LABEL: Record<SearchMode, string> = {
  semantic: "Ricerca semantica", literal: "Ricerca letterale", hybrid: "Ricerca ibrida",
};
const EXAMPLES = [
  "Boletus edulis",
  "umidità e temperature favorevoli ai porcini in faggeta",
  "Amanita caesarea quando cresce nei querceti dopo la pioggia",
];

export default function SearchBar(p: Props) {
  return (
    <div className="searchbar">
      <form className="search-row" onSubmit={(e) => { e.preventDefault(); if (p.query.trim().length > 1) p.onSubmit(); }}>
        <label className="field grow">
          <span>Cosa cerchi</span>
          <input type="search" value={p.query} onChange={(e) => p.setQuery(e.target.value)}
            placeholder="Un nome latino (Boletus edulis) o una domanda sulle condizioni di crescita" />
        </label>
        <label className="field">
          <span>Zona</span>
          <select value={p.zoneId} onChange={(e) => p.setZoneId(e.target.value)}>
            {p.zones.map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Dal</span>
          <input type="date" value={p.start} onChange={(e) => p.setStart(e.target.value)} />
        </label>
        <label className="field">
          <span>Al</span>
          <input type="date" value={p.end} min={p.start} onChange={(e) => p.setEnd(e.target.value)} />
        </label>
        <button className="go" type="submit" disabled={p.loading || p.query.trim().length < 2}>
          {p.loading ? "Analisi in corso" : "Stima la crescita"}
        </button>
      </form>
      <div className="search-hints">
        {p.mode ? (
          <span className={`badge mode-${p.mode.mode}`} title={p.mode.reason}>{MODE_LABEL[p.mode.mode]}</span>
        ) : null}
        <span className="mode-reason">
          {p.mode ? p.mode.reason : (
            <>Prova: {EXAMPLES.map((ex) => (
              <button key={ex} type="button" className="chip" onClick={() => p.setQuery(ex)}>{ex}</button>
            ))}</>
          )}
        </span>
      </div>
    </div>
  );
}
