"""Configurazione centrale, letta da variabili d'ambiente / file .env."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    chroma_path: str = str(BASE_DIR / ".chroma")
    data_dir: str = str(BASE_DIR / "data")
    collection_name: str = "tuscan_mycology"

    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_cache: str = ""  # vuoto = cache di default di fastembed

    http_timeout: float = 20.0
    max_llm_attempts: int = 2


settings = Settings()
