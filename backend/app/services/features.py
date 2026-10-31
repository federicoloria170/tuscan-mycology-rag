"""Indicatori deterministici: rendono la stima riproducibile e guidano l'LLM.

La 'baseline' è un punteggio 0-95 costruito con regole semplici e trasparenti:

    baseline = 100 * stagionalità^0.6 * (0.6 * punteggio_pioggia + 0.4 * punteggio_temperatura) * stress

È un'euristica di partenza, NON un modello validato scientificamente.
"""
import json
from datetime import date, timedelta
from pathlib import Path

from app.config import settings

PREV_DAYS = 15


def _seasonality() -> dict[str, list[float]]:
    data = json.loads((Path(settings.data_dir) / "seasonality.json").read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def seasonal_index(forests: dict[str, float], start: date, end: date) -> float:
    table = _seasonality()
    total_w = sum(forests.values()) or 1.0
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    vals = [sum(table[f][d.month - 1] * w for f, w in forests.items() if f in table) / total_w for d in days]
    return sum(vals) / len(vals)


def rain_score(mm: float | None) -> float:
    if mm is None:
        return 0.5
    if mm < 10:
        return 0.05 + 0.015 * mm
    if mm < 40:
        return 0.2 + 0.5 * (mm - 10) / 30
    if mm < 70:
        return 0.7 + 0.3 * (mm - 40) / 30
    if mm <= 120:
        return 1.0
    return max(0.6, 1.0 - 0.4 * (mm - 120) / 80)


def temp_score(t: float | None) -> float:
    if t is None:
        return 0.5
    if 8 <= t <= 18:
        return 1.0
    if t < 8:
        return max(0.0, t / 8)
    return max(0.0, 1 - (t - 18) / 10)


def compute_features(zone: dict, start: date, end: date, days: list[dict]) -> dict:
    by_date = {date.fromisoformat(d["date"]): d for d in days}
    period = [d for dt, d in by_date.items() if start <= dt <= end]
    prev = [d for dt, d in by_date.items() if start - timedelta(days=PREV_DAYS) <= dt < start]

    tmax = [d["tmax"] for d in period if d["tmax"] is not None]
    tmin = [d["tmin"] for d in period if d["tmin"] is not None]
    rain_prev = round(sum(d["rain"] for d in prev), 1) if prev else None
    rain_period = round(sum(d["rain"] for d in period), 1) if period else None
    tmean = round((sum(tmax) / len(tmax) + sum(tmin) / len(tmin)) / 2, 1) if tmax and tmin else None
    frost_days = sum(1 for t in tmin if t < 0) if tmin else None
    hot_days = sum(1 for t in tmax if t >= 30) if tmax else None

    # pioggia "efficace": quella che precede il periodo pesa di più di quella interna al periodo
    if rain_prev is None and rain_period is None:
        rain_eff = None
    else:
        rain_eff = (rain_prev or 0) + 0.5 * min(rain_period or 0, 60)

    season = seasonal_index(zone["forests"], start, end)
    s_rain, s_temp = rain_score(rain_eff), temp_score(tmean)
    n = max(len(period), 1)
    stress = 1.0
    stress -= 0.5 * ((frost_days or 0) / n) + 0.4 * ((hot_days or 0) / n)
    stress = round(max(0.3, min(1.0, stress)), 2)

    baseline = 100 * (season ** 0.6) * (0.6 * s_rain + 0.4 * s_temp) * stress
    return {
        "weather_available": bool(period),
        "rain_prev_15d": rain_prev, "rain_period": rain_period,
        "rain_days": sum(1 for d in period if d["rain"] >= 1) if period else None,
        "tmean_period": tmean,
        "tmin_period": round(min(tmin), 1) if tmin else None,
        "tmax_period": round(max(tmax), 1) if tmax else None,
        "frost_days": frost_days, "hot_days": hot_days,
        "seasonal_index": round(season, 2), "score_rain": round(s_rain, 2), "score_temp": round(s_temp, 2),
        "stress_factor": stress, "baseline_percent": round(min(95.0, baseline), 1),
    }
