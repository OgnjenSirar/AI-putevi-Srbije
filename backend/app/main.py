"""Glavna FastAPI aplikacija Korisnickog centra (demo)."""
import logging
import shutil
import threading
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import SessionLocal, init_db
from .models import User
from .security import current_user
from .routers import admin, auth, cases, customers, knowledge, reports, social
from .seed.social_examples import seed_social_examples

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")
settings = get_settings()

# Bez javne dokumentacije API-ja i bez CORS-a: aplikacija se koristi samo preko nginx-a, sa iste adrese
app = FastAPI(title="Korisnički centar (demo)", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None)
for r in (auth.router, cases.router, customers.router, knowledge.router, social.router, reports.router, admin.router):
    app.include_router(r)

Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def public_config(user: User = Depends(current_user)):
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
    with SessionLocal() as db:
        from .seed.seed import apply_managed_passwords

        n = apply_managed_passwords(db)
        if n:
            log.info("Azurirane lozinke naloga: %s", n)
    threading.Thread(target=seed_social_examples, daemon=True).start()
