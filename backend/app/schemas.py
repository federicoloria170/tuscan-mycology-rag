"""Modelli Pydantic: validano sia l'input dell'utente sia l'output finale."""
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SearchMode = Literal["semantic", "literal", "hybrid"]


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    zone_id: str | None = None
    start_date: date
    end_date: date

    @field_validator("query")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("La ricerca è troppo corta")
        return v

    @model_validator(mode="after")
    def _check_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("La data finale precede quella iniziale")
        if (self.end_date - self.start_date).days > 30:
            raise ValueError("Il periodo può durare al massimo 31 giorni")
        if self.start_date > date.today() + timedelta(days=400):
            raise ValueError("Data troppo lontana nel futuro")
        return self


class ZoneInfo(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    radius_km: float
    altitude_min: int
    altitude_max: int
    forests: dict[str, float]
    description: str


class ForestShare(BaseModel):
    type: str
    label: str
    weight: float


class Hit(BaseModel):
    id: str
    title: str
    category: str
    snippet: str
    score: float
    source: Literal["semantic", "bm25", "both"]
    reference: str = ""
    verified: bool = False


class Reference(BaseModel):
    title: str
    reference: str
    verified: bool


class WeatherDay(BaseModel):
    date: date
    tmax: float | None = None
    tmin: float | None = None
    rain: float = 0.0
    source: Literal["archivio", "previsione", "climatologia"]
    in_period: bool = False


class Weather(BaseModel):
    days: list[WeatherDay] = []
    sources: list[str] = []
    note: str | None = None
    error: str | None = None


class Features(BaseModel):
    weather_available: bool
    rain_prev_15d: float | None = None
    rain_period: float | None = None
    rain_days: int | None = None
    tmean_period: float | None = None
    tmin_period: float | None = None
    tmax_period: float | None = None
    frost_days: int | None = None
    hot_days: int | None = None
    seasonal_index: float
    score_rain: float
    score_temp: float
    stress_factor: float
    baseline_percent: float


class GrowthEstimate(BaseModel):
    percentage: int = Field(ge=0, le=100)
    confidence: Literal["low", "medium", "high"]
    rationale: str = Field(min_length=10, max_length=1200)
    key_factors: list[str] = Field(default_factory=list, max_length=6)
    method: Literal["llm", "deterministic"] = "llm"


class SearchResponse(BaseModel):
    query: str
    mode: SearchMode
    mode_reason: str
    zone: ZoneInfo
    start_date: date
    end_date: date
    hits: list[Hit]
    references: list[Reference]
    forest_breakdown: list[ForestShare]
    weather: Weather
    features: Features
    growth: GrowthEstimate
    disclaimers: list[str]
