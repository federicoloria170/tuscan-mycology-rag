export interface Zone {
  id: string; name: string; lat: number; lon: number; radius_km: number;
  altitude_min: number; altitude_max: number; forests: Record<string, number>; description: string;
}
export interface GraphNodeMeta { id: string; label: string; description: string; stage: number }
export type SearchMode = "semantic" | "literal" | "hybrid";
export interface NodeStatus { state: "idle" | "running" | "done" | "error"; ms?: number; summary?: string | null }

export interface Hit {
  id: string; title: string; category: string; snippet: string; score: number;
  source: "semantic" | "bm25" | "both"; reference: string; verified: boolean;
}
export interface Reference { title: string; reference: string; verified: boolean }
export interface WeatherDay {
  date: string; tmax: number | null; tmin: number | null; rain: number;
  source: "archivio" | "previsione" | "climatologia"; in_period: boolean;
}
export interface Weather { days: WeatherDay[]; sources: string[]; note: string | null; error: string | null }
export interface Features {
  weather_available: boolean; rain_prev_15d: number | null; rain_period: number | null; rain_days: number | null;
  tmean_period: number | null; tmin_period: number | null; tmax_period: number | null;
  frost_days: number | null; hot_days: number | null; seasonal_index: number;
  score_rain: number; score_temp: number; stress_factor: number; baseline_percent: number;
}
export interface Growth {
  percentage: number; confidence: "low" | "medium" | "high"; rationale: string;
  key_factors: string[]; method: "llm" | "deterministic";
}
export interface SearchResponse {
  query: string; mode: SearchMode; mode_reason: string; zone: Zone; start_date: string; end_date: string;
  hits: Hit[]; references: Reference[]; forest_breakdown: { type: string; label: string; weight: number }[];
  weather: Weather; features: Features; growth: Growth; disclaimers: string[];
}
export interface SearchRequest { query: string; zone_id: string; start_date: string; end_date: string }

export type StreamEvent =
  | { event: "node_start"; node: string }
  | { event: "node_end"; node: string; ms: number; summary?: string | null; data?: { mode: SearchMode; reason: string } | null }
  | { event: "node_error"; node: string; message: string }
  | { event: "result"; data: SearchResponse }
  | { event: "error"; message: string };
