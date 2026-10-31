import type { SearchResponse, Zone } from "../types";
import { ForestChart, Gauge, WeatherChart } from "./Charts";

const CONF: Record<string, string> = { low: "bassa", medium: "media", high: "alta" };
const SRC: Record<string, string> = { semantic: "semantico", bm25: "letterale", both: "entrambi" };
const fmt = (v: number | null, unit = "") => (v === null ? "n.d." : `${v}${unit}`);

interface Props { result: SearchResponse | null; loading: boolean; error: string | null; zone?: Zone }

export default function ResultPanel({ result, loading, error, zone }: Props) {
  if (error) return <div className="notice error"><b>Qualcosa non ha funzionato.</b><p>{error}</p></div>;

  if (!result) {
    return (
      <div className="empty">
        <h2>{zone ? zone.name : "Scegli una zona"}</h2>
        {zone ? <p>{zone.description} Quota {zone.altitude_min}-{zone.altitude_max} m.</p> : null}
        <p>{loading ? "I nodi di LangGraph stanno lavorando: guarda la barra qui sopra."
          : "Scrivi una ricerca, scegli le date e premi «Stima la crescita». Clicca una zona sulla mappa per cambiarla."}</p>
      </div>
    );
  }

  const g = result.growth, f = result.features;
  return (
    <div className="result">
      <section className="verdict">
        <Gauge value={g.percentage} />
        <div>
          <h2>{result.zone.name}</h2>
          <p className="muted">{result.start_date} → {result.end_date}</p>
          <p>Confidenza <b>{CONF[g.confidence]}</b> · {g.method === "llm" ? "interpretata dall'LLM" : "solo indicatori deterministici"}</p>
        </div>
      </section>
      <p className="rationale">{g.rationale}</p>
      {g.key_factors.length ? <ul className="factors">{g.key_factors.map((k) => <li key={k}>{k}</li>)}</ul> : null}

      <section>
        <h3>Pioggia e temperature</h3>
        {result.weather.days.length ? <WeatherChart days={result.weather.days} /> : null}
        {result.weather.error ? <p className="notice warn">{result.weather.error}</p> : null}
        {result.weather.note ? <p className="notice warn">{result.weather.note}</p> : null}
        <dl className="stats">
          <div><dt>Pioggia 15 gg prima</dt><dd>{fmt(f.rain_prev_15d, " mm")}</dd></div>
          <div><dt>Pioggia nel periodo</dt><dd>{fmt(f.rain_period, " mm")}</dd></div>
          <div><dt>Temp. media</dt><dd>{fmt(f.tmean_period, " °C")}</dd></div>
          <div><dt>Giorni di gelo</dt><dd>{fmt(f.frost_days)}</dd></div>
          <div><dt>Stagionalità</dt><dd>{Math.round(f.seasonal_index * 100)}%</dd></div>
          <div><dt>Baseline regole</dt><dd>{Math.round(f.baseline_percent)}%</dd></div>
        </dl>
      </section>

      <section>
        <h3>Tipi di bosco</h3>
        <ForestChart data={result.forest_breakdown} />
      </section>

      <section>
        <h3>Passaggi recuperati</h3>
        <ul className="hits">
          {result.hits.map((h) => (
            <li key={h.id}>
              <div className="hit-head">
                <b>{h.title}</b>
                <span className={`badge src-${h.source}`}>{SRC[h.source]}</span>
              </div>
              <p>{h.snippet}</p>
            </li>
          ))}
        </ul>
      </section>

      {result.references.length ? (
        <section>
          <h3>Riferimenti</h3>
          <ul className="refs">
            {result.references.map((r) => (
              <li key={r.reference}>{r.reference}{!r.verified ? <span className="badge unverified">da verificare</span> : null}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <footer className="disclaimers">
        {result.disclaimers.map((d) => <p key={d}>{d}</p>)}
      </footer>
    </div>
  );
}
