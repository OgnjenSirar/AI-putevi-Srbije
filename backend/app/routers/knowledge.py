"""Znanje sluzbe: obrasci odgovora i promenljivi podaci, sa istorijom izmena."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.retrieval import embeddings_available, index_templates, search_templates
from ..ai.validator import PLACEHOLDER_RE, render
from ..db import get_db
from ..models import AuditLog, KBTemplate, KBTemplateVersion, KBVariable, KBVariableVersion, OrgUnit, User
from ..security import current_user
from ..services import catalog as cat

router = APIRouter(prefix="/api/knowledge", tags=["znanje"])


def _now():
    return datetime.now(timezone.utc)


def tpl_dict(t: KBTemplate, units: dict) -> dict:
    return {"id": t.id, "code": t.code, "title": t.title, "category": t.category, "org_unit": units.get(t.org_unit_id),
            "body": t.body, "tags": t.tags, "active": t.active, "version": t.version, "updated_by": t.updated_by,
            "updated_at": t.updated_at, "indexed": t.embedding is not None,
            "variables": sorted({m.group(1) for m in PLACEHOLDER_RE.finditer(t.body)})}


@router.get("/templates")
def list_templates(db: Session = Depends(get_db), user: User = Depends(current_user)):
    units = {u.id: {"id": u.id, "code": u.code, "name": u.name} for u in db.scalars(select(OrgUnit)).all()}
    return [tpl_dict(t, units) for t in db.scalars(select(KBTemplate).order_by(KBTemplate.code)).all()]


@router.get("/templates/{tid}")
def get_template(tid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = db.get(KBTemplate, tid)
    if not t:
        raise HTTPException(404, "Obrazac ne postoji")
    units = {u.id: {"id": u.id, "code": u.code, "name": u.name} for u in db.scalars(select(OrgUnit)).all()}
    versions = db.scalars(select(KBTemplateVersion).where(KBTemplateVersion.template_id == t.id).order_by(KBTemplateVersion.version.desc())).all()
    preview, used, unknown = render(t.body, cat.variables(db), {"korisnik.ime": "Petar Petrović", "predmet.broj": "KC-2026-000001"})
    return {**tpl_dict(t, units), "preview": preview, "unknown_variables": unknown,
            "versions": [{"version": v.version, "title": v.title, "body": v.body, "changed_by": v.changed_by,
                          "changed_at": v.changed_at, "change_note": v.change_note} for v in versions]}


class TemplateIn(BaseModel):
    code: str
    title: str
    category: str
    org_unit_id: int | None = None
    body: str
    tags: list[str] = []
    active: bool = True
    change_note: str = ""


@router.post("/templates")
def create_template(body: TemplateIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if db.scalar(select(KBTemplate).where(KBTemplate.code == body.code)):
        raise HTTPException(400, "Šifra obrasca već postoji")
    t = KBTemplate(code=body.code, title=body.title, category=body.category, org_unit_id=body.org_unit_id, body=body.body,
                   tags=body.tags, active=body.active, version=1, updated_by=user.full_name, updated_at=_now())
    db.add(t)
    db.flush()
    db.add(KBTemplateVersion(template_id=t.id, version=1, title=t.title, body=t.body, changed_by=user.full_name,
                             change_note=body.change_note or "Novi obrazac"))
    db.add(AuditLog(actor=user.full_name, entity="obrazac", entity_id=t.code, action="kreiranje", summary=f"Novi obrazac {t.code}"))
    db.commit()
    index_templates(db, only_missing=True)
    return {"id": t.id}


@router.put("/templates/{tid}")
def update_template(tid: int, body: TemplateIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = db.get(KBTemplate, tid)
    if not t:
        raise HTTPException(404, "Obrazac ne postoji")
    changed = (t.title, t.body, t.category, t.org_unit_id, t.active, t.tags) != (body.title, body.body, body.category, body.org_unit_id, body.active, body.tags)
    if not changed:
        return {"id": t.id, "version": t.version}
    t.title, t.body, t.category, t.org_unit_id, t.active, t.tags = body.title, body.body, body.category, body.org_unit_id, body.active, body.tags
    t.version += 1
    t.updated_by = user.full_name
    t.updated_at = _now()
    t.embedding = None
    db.add(KBTemplateVersion(template_id=t.id, version=t.version, title=t.title, body=t.body, changed_by=user.full_name,
                             change_note=body.change_note))
    db.add(AuditLog(actor=user.full_name, entity="obrazac", entity_id=t.code, action="izmena",
                    summary=f"Obrazac {t.code} izmenjen (verzija {t.version})", diff={"napomena": body.change_note}))
    db.commit()
    index_templates(db, only_missing=True)
    return {"id": t.id, "version": t.version}


@router.get("/variables")
def list_variables(db: Session = Depends(get_db), user: User = Depends(current_user)):
    usage = {}
    for t in db.scalars(select(KBTemplate)).all():
        for m in PLACEHOLDER_RE.finditer(t.body):
            if m.group(1).startswith("var."):
                usage.setdefault(m.group(1)[4:], []).append(t.code)
    out = []
    for v in cat.variables_full(db):
        versions = db.scalars(select(KBVariableVersion).where(KBVariableVersion.variable_id == v.id).order_by(KBVariableVersion.changed_at.desc())).all()
        age_days = (_now() - v.verified_at).days if v.verified_at else None
        out.append({"id": v.id, "key": v.key, "label": v.label, "value": v.value, "group": v.group, "owner": v.owner,
                    "version": v.version, "verified_at": v.verified_at, "updated_at": v.updated_at, "stale": (age_days or 0) > 90,
                    "used_in": sorted(set(usage.get(v.key, []))),
                    "history": [{"value": h.value, "changed_by": h.changed_by, "changed_at": h.changed_at, "change_note": h.change_note} for h in versions]})
    return out


class VariableIn(BaseModel):
    key: str
    label: str
    value: str
    group: str = "ostalo"
    owner: str = ""
    change_note: str = ""


@router.post("/variables")
def create_variable(body: VariableIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if db.scalar(select(KBVariable).where(KBVariable.key == body.key)):
        raise HTTPException(400, "Ključ već postoji")
    v = KBVariable(key=body.key, label=body.label, value=body.value, group=body.group, owner=body.owner, updated_at=_now(), verified_at=_now())
    db.add(v)
    db.flush()
    db.add(KBVariableVersion(variable_id=v.id, version=1, value=v.value, changed_by=user.full_name, change_note=body.change_note or "Nova promenljiva"))
    db.add(AuditLog(actor=user.full_name, entity="promenljiva", entity_id=v.key, action="kreiranje", summary=f"Nova promenljiva {v.key}"))
    db.commit()
    return {"id": v.id}


@router.put("/variables/{vid}")
def update_variable(vid: int, body: VariableIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    v = db.get(KBVariable, vid)
    if not v:
        raise HTTPException(404, "Promenljiva ne postoji")
    old = v.value
    v.label, v.group, v.owner = body.label, body.group, body.owner
    v.verified_at = _now()
    if body.value != old:
        v.value = body.value
        v.version += 1
        v.updated_at = _now()
        db.add(KBVariableVersion(variable_id=v.id, version=v.version, value=v.value, changed_by=user.full_name, change_note=body.change_note))
        db.add(AuditLog(actor=user.full_name, entity="promenljiva", entity_id=v.key, action="izmena",
                        summary=f"{v.key}: \"{old}\" → \"{v.value}\"", diff={"pre": old, "posle": v.value, "napomena": body.change_note}))
    db.commit()
    return {"id": v.id, "version": v.version}


class SearchIn(BaseModel):
    query: str


@router.post("/search")
def search(body: SearchIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    res = search_templates(db, body.query, k=5)
    return {"embeddings": embeddings_available(),
            "results": [{"code": r["template"].code, "title": r["template"].title, "score": r["score"], "metode": r["metode"]} for r in res]}


@router.post("/reindex")
def reindex(db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = index_templates(db, only_missing=False)
    return {"indexed": n, "embeddings": embeddings_available()}
