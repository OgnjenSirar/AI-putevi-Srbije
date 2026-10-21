"""Administracija: nalozi i uloge, organizacione jedinice, sifarnici, podesavanja, status sistema i demo alati."""
import io
import random
import smtplib
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai import llm
from ..ai.retrieval import embeddings_available, reranker_available
from ..config import get_settings
from ..db import SessionLocal, get_db
from ..models import AuditLog, Codebook, Email, Job, OrgUnit, Setting, User
from ..security import current_user, hash_password, password_problem, require_role
from ..seed.emails import POOL
from ..social.service import imagegen_status

router = APIRouter(prefix="/api/admin", tags=["administracija"])
settings = get_settings()


@router.get("/status")
def status(db: Session = Depends(get_db), user: User = Depends(current_user)):
    def ping(url: str) -> bool:
        try:
            return httpx.get(url, timeout=2).status_code < 500
        except Exception:
            return False

    smtp_ok = False
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=2):
            smtp_ok = True
    except Exception:
        pass
    jobs = dict(db.execute(select(Job.status, func.count()).group_by(Job.status)).all())
    return {
        "ai_mode": settings.ai_mode, "effective_mode": llm.effective_mode(), "llm_model": settings.llm_model,
        "services": {
            "llm": llm.llm_healthy(force=True), "embed": embeddings_available(), "rerank": reranker_available(),
            "imagegen": imagegen_status().get("status") == "ok", "imagegen_detail": imagegen_status(),
            "langfuse": bool(settings.langfuse_host and settings.langfuse_public_key and settings.langfuse_secret_key) and ping(settings.langfuse_host.rstrip("/") + "/api/public/health"),
            "smtp": smtp_ok,
        },
        "jobs": jobs, "langfuse_ui": settings.langfuse_ui_url, "mailpit_ui": "/mailpit/",
    }


# ------------------------------------------------------------------ nalozi

class UserIn(BaseModel):
    username: str
    full_name: str
    role: str
    org_unit_id: int | None = None
    active: bool = True
    password: str = ""


@router.get("/users")
def users(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [{"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role, "org_unit_id": u.org_unit_id,
             "active": u.active} for u in db.scalars(select(User).order_by(User.id)).all()]


@router.post("/users")
def create_user(body: UserIn, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    if db.scalar(select(User).where(User.username == body.username.strip().lower())):
        raise HTTPException(400, "Korisničko ime je zauzeto")
    if problem := password_problem(body.password):
        raise HTTPException(400, problem)
    u = User(username=body.username.strip().lower(), full_name=body.full_name, role=body.role, org_unit_id=body.org_unit_id,
             active=body.active, password_hash=hash_password(body.password))
    db.add(u)
    db.add(AuditLog(actor=user.full_name, entity="nalog", entity_id=body.username, action="kreiranje", summary=f"Novi nalog {body.full_name} ({body.role})"))
    db.commit()
    return {"id": u.id}


@router.put("/users/{uid}")
def update_user(uid: int, body: UserIn, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "Nalog ne postoji")
    diff = {k: {"pre": getattr(u, k), "posle": getattr(body, k)} for k in ("full_name", "role", "org_unit_id", "active") if getattr(u, k) != getattr(body, k)}
    u.full_name, u.role, u.org_unit_id, u.active = body.full_name, body.role, body.org_unit_id, body.active
    if body.password:
        if problem := password_problem(body.password):
            raise HTTPException(400, problem)
        u.password_hash = hash_password(body.password)
    if diff:
        db.add(AuditLog(actor=user.full_name, entity="nalog", entity_id=u.username, action="izmena", summary=f"Izmena naloga {u.full_name}", diff=diff))
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ jedinice i sifarnici

class UnitIn(BaseModel):
    code: str
    name: str
    description: str = ""
    email: str = ""
    active: bool = True


@router.get("/units")
def units(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [{"id": u.id, "code": u.code, "name": u.name, "description": u.description, "email": u.email, "active": u.active}
            for u in db.scalars(select(OrgUnit).order_by(OrgUnit.id)).all()]


@router.post("/units")
def create_unit(body: UnitIn, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    u = OrgUnit(**body.model_dump())
    db.add(u)
    db.add(AuditLog(actor=user.full_name, entity="jedinica", entity_id=body.code, action="kreiranje", summary=f"Nova jedinica {body.name}"))
    db.commit()
    return {"id": u.id}


@router.put("/units/{uid}")
def update_unit(uid: int, body: UnitIn, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    u = db.get(OrgUnit, uid)
    for k, v in body.model_dump().items():
        setattr(u, k, v)
    db.add(AuditLog(actor=user.full_name, entity="jedinica", entity_id=u.code, action="izmena", summary=f"Izmena jedinice {u.name}"))
    db.commit()
    return {"ok": True}


@router.get("/codebooks")
def codebooks(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(Codebook).order_by(Codebook.kind, Codebook.sort)).all()
    out: dict[str, list] = {}
    for r in rows:
        out.setdefault(r.kind, []).append({"id": r.id, "code": r.code, "label": r.label, "data": r.data, "active": r.active})
    return out


class CodebookIn(BaseModel):
    label: str
    data: dict = {}
    active: bool = True


@router.put("/codebooks/{cid}")
def update_codebook(cid: int, body: CodebookIn, db: Session = Depends(get_db), user: User = Depends(require_role("admin", "supervizor"))):
    r = db.get(Codebook, cid)
    if not r:
        raise HTTPException(404, "Stavka ne postoji")
    diff = {"pre": {"label": r.label, "data": r.data}, "posle": body.model_dump()}
    r.label, r.data, r.active = body.label, {**r.data, **body.data}, body.active
    db.add(AuditLog(actor=user.full_name, entity="sifarnik", entity_id=f"{r.kind}:{r.code}", action="izmena", summary=f"Izmena šifarnika {r.kind}: {r.label}", diff=diff))
    db.commit()
    return {"ok": True}


@router.get("/settings")
def get_settings_(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [{"key": s.key, "label": s.label, "value": s.value} for s in db.scalars(select(Setting).order_by(Setting.key)).all()]


class SettingIn(BaseModel):
    value: dict


@router.put("/settings/{key}")
def put_setting(key: str, body: SettingIn, db: Session = Depends(get_db), user: User = Depends(require_role("admin", "supervizor"))):
    s = db.get(Setting, key)
    if not s:
        raise HTTPException(404, "Podešavanje ne postoji")
    db.add(AuditLog(actor=user.full_name, entity="podesavanje", entity_id=key, action="izmena", summary=f"Izmena podešavanja {s.label}",
                    diff={"pre": s.value, "posle": body.value}))
    s.value = body.value
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ demo alati

def _extract_attachment(name: str, ctype: str, data: bytes) -> dict:
    text = ""
    if name.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader

            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)[:5000]
        except Exception as e:
            text = f"[PDF nije moguće pročitati: {e}]"
    elif name.lower().endswith((".txt", ".csv")):
        text = data.decode("utf-8", "ignore")[:5000]
    elif ctype.startswith("image/"):
        text = f"[slika {name}, {len(data) // 1024} KB]"
    return {"name": name, "type": ctype, "size": len(data), "text": text}


@router.post("/simulate/inbound")
async def simulate_inbound(from_name: str = Form(...), from_addr: str = Form(...), subject: str = Form(...),
                           body: str = Form(...), file: UploadFile | None = File(None),
                           db: Session = Depends(get_db), user: User = Depends(current_user)):
    atts = []
    if file is not None and file.filename:
        atts.append(_extract_attachment(file.filename, file.content_type or "", await file.read()))
    e = Email(direction="in", message_id=f"<{uuid.uuid4().hex}@{from_addr.split('@')[-1]}>", from_addr=from_addr.strip(),
              from_name=from_name.strip(), to_addr="kontakt@demo-kc.rs", subject=subject.strip(), body_text=body,
              attachments=atts, received_at=datetime.now(timezone.utc), folder="prijem")
    db.add(e)
    db.flush()
    db.add(Job(type="process_email", payload={"email_id": e.id}))
    db.commit()
    return {"ok": True, "email_id": e.id}


class WaveIn(BaseModel):
    count: int = 3


@router.post("/simulate/wave")
def simulate_wave(body: WaveIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    picks = random.sample(POOL, k=min(max(1, body.count), len(POOL)))
    ids = []
    for p in picks:
        e = Email(direction="in", message_id=f"<{uuid.uuid4().hex}@{p['from_addr'].split('@')[-1]}>", from_addr=p["from_addr"],
                  from_name=p["from_name"], to_addr="kontakt@demo-kc.rs", subject=p["subject"], body_text=p["body"],
                  received_at=datetime.now(timezone.utc), folder="prijem")
        db.add(e)
        db.flush()
        db.add(Job(type="process_email", payload={"email_id": e.id}))
        ids.append(e.id)
    db.commit()
    return {"ok": True, "email_ids": ids}


@router.post("/reset")
def reset_demo(user: User = Depends(require_role("admin", "supervizor"))):
    from ..seed.seed import reset_database, seed_all

    import shutil
    from pathlib import Path

    from ..seed.social_examples import seed_social_examples

    reset_database()
    for sub in ("social", "backgrounds", "public"):
        shutil.rmtree(Path(settings.media_dir) / sub, ignore_errors=True)
    with SessionLocal() as db:
        res = seed_all(db)
    seed_social_examples()
    return {"ok": True, **res}
