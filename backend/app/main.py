"""Glavna FastAPI aplikacija Korisnickog centra (demo)."""
import logging
import shutil
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import SessionLocal, init_db
from .routers import admin, auth, cases, customers, knowledge, reports, social
from .seed.social_examples import seed_social_examples

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")
settings = get_settings()

app = FastAPI(title="Korisnički centar (demo)", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for r in (auth.router, cases.router, customers.router, knowledge.router, social.router, reports.router, admin.router):
    app.include_router(r)

Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def public_config():
    return {"ai_mode": settings.ai_mode, "langfuse_ui": settings.langfuse_ui_url, "mailpit_ui": "/mailpit/",
            "llm_model": settings.llm_model}


@app.on_event("startup")
def startup():
    init_db()
    if settings.seed_on_start:
        from .seed.seed import is_seeded, seed_all

        with SessionLocal() as db:
            if not is_seeded(db):
                log.info("Baza je prazna, punim izmišljenim podacima...")
                for sub in ("social", "backgrounds", "public"):
                    shutil.rmtree(Path(settings.media_dir) / sub, ignore_errors=True)
                log.info("Rezultat: %s", seed_all(db))
    threading.Thread(target=seed_social_examples, daemon=True).start()
