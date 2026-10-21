"""Podešavanja aplikacije, čitaju se iz promenljivih okruženja."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://demo:demo@localhost:5432/kcdemo"
    secret_key: str = "demo-tajni-kljuc-promeniti"

    # AI rezim: "live" koristi pravi LLM (vLLM ili Ollama), "mock" koristi
    # deterministicka pravila (za testiranje bez GPU-a i kao rezerva).
    ai_mode: str = "live"
    llm_base_url: str = "http://llm:8000/v1"
    llm_api_key: str = "demo"
    llm_model: str = "gemma-4"
    # "auto" prepoznaje Ollama po adresi, moze se zadati i "ollama" ili "vllm"
    llm_backend: str = "auto"
    llm_timeout: float = 180.0
    llm_max_tokens: int = 1200
    # Ako LLM nije dostupan, automatski predji na mock da demo ne stane.
    ai_fallback_to_mock: bool = True

    embed_url: str = "http://embed:80"
    rerank_url: str = "http://rerank:80"
    imagegen_url: str = "http://imagegen:8000"

    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    mail_from: str = "Korisnicki centar (demo) <kontakt@demo-kc.rs>"
    mail_domain: str = "demo-kc.rs"

    # Javni URL demoa (koristi se za simulaciju Instagram image_url)
    public_base_url: str = "http://localhost:8080"
    media_dir: str = "/data/media"

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = ""
    # URL Langfuse UI-ja za linkove iz aplikacije (moze se razlikovati od internog hosta)
    langfuse_ui_url: str = ""

    seed_on_start: bool = True
    worker_poll_seconds: float = 2.0
    # Koliko dugo radnik ceka da LLM postane dostupan (npr. dok se model preuzima) pre rezervnog rezima
    llm_wait_seconds: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
