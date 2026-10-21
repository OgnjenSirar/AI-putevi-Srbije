"""Pozadinski radnik: obrada reda poslova iz baze (SELECT ... FOR UPDATE SKIP LOCKED)."""
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from .ai import llm
from .ai.pipeline import analyze_case, process_email
from .ai.retrieval import embeddings_available, index_templates
from .config import get_settings
from .db import SessionLocal, init_db
from .models import Job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("worker")
settings = get_settings()



def enqueue(db, type_: str, payload: dict, delay_s: int = 0) -> Job:
    job = Job(type=type_, payload=payload, run_after=datetime.now(timezone.utc) + timedelta(seconds=delay_s))
    db.add(job)
    db.commit()
    return job


def claim(db) -> Job | None:
    row = db.execute(text("""
        UPDATE jobs SET status='running', attempts=attempts+1
        WHERE id = (SELECT id FROM jobs WHERE status='queued' AND run_after <= now()
                    ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1)
        RETURNING id
    """)).first()
    db.commit()
    return db.get(Job, row[0]) if row else None


def run_job(db, job: Job) -> None:
    if job.type in ("process_email", "analyze_case") and settings.ai_mode == "live" and not llm.llm_healthy():
        age = (datetime.now(timezone.utc) - job.created_at).total_seconds()
        if age < settings.llm_wait_seconds:
            job.status = "queued"
            job.attempts -= 1
            job.run_after = datetime.now(timezone.utc) + timedelta(seconds=10)
            db.commit()
            return
    if job.type == "process_email":
        process_email(db, job.payload["email_id"], job.payload.get("force_regular", False))
    elif job.type == "analyze_case":
        analyze_case(db, job.payload["case_id"], job.payload.get("email_id"))
    elif job.type == "index_kb":
        n = index_templates(db, only_missing=not job.payload.get("all"))
        log.info("Indeksirano obrazaca: %s", n)
    job.status = "done"
    job.finished_at = datetime.now(timezone.utc)
    db.commit()


def main() -> None:
    init_db()
    log.info("Radnik pokrenut (AI rezim: %s, LLM: %s)", settings.ai_mode, settings.llm_base_url)
    last_index_try = 0.0
    while True:
        db = SessionLocal()
        try:
            # Periodicno indeksiranje znanja kada embedding servis postane dostupan
            if time.time() - last_index_try > 60:
                last_index_try = time.time()
                if embeddings_available():
                    n = index_templates(db, only_missing=True)
                    if n:
                        log.info("Indeksirano novih obrazaca: %s", n)
            job = claim(db)
            if not job:
                db.close()
                time.sleep(settings.worker_poll_seconds)
                continue
            try:
                run_job(db, job)
            except Exception as e:
                log.exception("Posao %s nije uspeo", job.id)
                db.rollback()
                job = db.get(Job, job.id)
                job.status = "queued" if job.attempts < 3 else "failed"
                job.error = str(e)[:2000]
                job.run_after = datetime.now(timezone.utc) + timedelta(seconds=15 * job.attempts)
                db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    main()
