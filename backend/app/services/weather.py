"""Meteo con Open-Meteo (gratuito, senza chiave), incapsulato come *tool LangChain*.

Strategia per ogni giorno della finestra richiesta:
  - passato (oltre 6 giorni fa)      -> API archivio ERA5
  - ultimi giorni e fino a +15 giorni -> API previsioni
  - oltre l'orizzonte di previsione   -> climatologia (media degli stessi giorni nei 3 anni precedenti)
"""
import asyncio
from collections import defaultdict
from datetime import date, timedelta

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.config import settings

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DAILY = "temperature_2m_max,temperature_2m_min,precipitation_sum"
CLIMATOLOGY_YEARS = 3


class WeatherQuery(BaseModel):
    latitude: float = Field(description="Latitudine in gradi")
    longitude: float = Field(description="Longitudine in gradi")
    start_date: str = Field(description="Data iniziale ISO (YYYY-MM-DD)")
    end_date: str = Field(description="Data finale ISO (YYYY-MM-DD)")


async def _fetch(client: httpx.AsyncClient, url: str, lat: float, lon: float, s: date, e: date) -> dict[date, dict]:
    r = await client.get(url, params={
        "latitude": lat, "longitude": lon, "start_date": s.isoformat(), "end_date": e.isoformat(),
        "daily": DAILY, "timezone": "Europe/Rome",
    })
    r.raise_for_status()
    d = r.json()["daily"]
    return {
        date.fromisoformat(t): {"tmax": tx, "tmin": tn, "rain": pr or 0.0}
        for t, tx, tn, pr in zip(d["time"], d["temperature_2m_max"], d["temperature_2m_min"], d["precipitation_sum"])
    }


async def _climatology(client, lat, lon, s: date, e: date) -> dict[date, dict]:
    """Media giornaliera degli stessi giorni negli anni precedenti."""
    years = range(1, CLIMATOLOGY_YEARS + 1)
    results = await asyncio.gather(*[
        _fetch(client, ARCHIVE_URL, lat, lon, s - timedelta(days=365 * y), e - timedelta(days=365 * y)) for y in years
    ])
    acc: dict[date, list[dict]] = defaultdict(list)
    for y, res in zip(years, results):
        for d, v in res.items():
            acc[d + timedelta(days=365 * y)].append(v)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    return {d: {"tmax": mean([x["tmax"] for x in v]), "tmin": mean([x["tmin"] for x in v]),
                "rain": mean([x["rain"] for x in v]) or 0.0} for d, v in acc.items()}


async def fetch_weather_window(lat: float, lon: float, start: date, end: date) -> dict:
    today = date.today()
    archive_end = today - timedelta(days=6)
    forecast_end = today + timedelta(days=15)

    segments = []  # (etichetta, funzione, da, a)
    if start <= archive_end:
        segments.append(("archivio", ARCHIVE_URL, start, min(end, archive_end)))
    f_start, f_end = max(start, archive_end + timedelta(days=1)), min(end, forecast_end)
    if f_start <= f_end:
        segments.append(("previsione", FORECAST_URL, f_start, f_end))
    c_start = max(start, forecast_end + timedelta(days=1))
    if c_start <= end:
        segments.append(("climatologia", None, c_start, end))

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        async def run(label, url, s, e):
            data = await (_climatology(client, lat, lon, s, e) if url is None else _fetch(client, url, lat, lon, s, e))
            return label, data

        results = await asyncio.gather(*[run(*seg) for seg in segments])

    days = []
    for label, data in results:
        for d, v in data.items():
            days.append({"date": d.isoformat(), "tmax": v["tmax"], "tmin": v["tmin"], "rain": v["rain"], "source": label})
    days.sort(key=lambda x: x["date"])
    sources = sorted({d["source"] for d in days})
    note = None
    if "climatologia" in sources:
        note = ("Per alcune date oltre l'orizzonte di previsione (circa 15 giorni) il meteo è sostituito dalla "
                "media degli stessi giorni negli ultimi anni: l'affidabilità è molto minore.")
    return {"days": days, "sources": sources, "note": note, "error": None}


@tool("get_weather", args_schema=WeatherQuery)
async def get_weather(latitude: float, longitude: float, start_date: str, end_date: str) -> dict:
    """Restituisce pioggia giornaliera (mm) e temperature min/max (°C) per una località e un intervallo di date.
    Usa archivio, previsioni o climatologia a seconda delle date richieste."""
    return await fetch_weather_window(latitude, longitude, date.fromisoformat(start_date), date.fromisoformat(end_date))
