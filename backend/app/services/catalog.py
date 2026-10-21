"""Citanje sifarnika i znanja iz baze u oblik pogodan za AI i pravila."""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Codebook, KBTemplate, KBVariable, OrgUnit, Setting


def categories(db: Session) -> list[dict]:
    rows = db.scalars(select(Codebook).where(Codebook.kind == "kategorija", Codebook.active.is_(True)).order_by(Codebook.sort)).all()
    return [{"code": r.code, "label": r.label, "unit": r.data.get("unit"), "priority": r.data.get("priority"),
             "due_days": r.data.get("due_days", 8), "needs_check": r.data.get("needs_check", False),
             "keywords": r.data.get("keywords", [])} for r in rows]


def category_map(db: Session) -> dict[str, dict]:
    return {c["code"]: c for c in categories(db)}


def units(db: Session) -> list[dict]:
    rows = db.scalars(select(OrgUnit).where(OrgUnit.active.is_(True)).order_by(OrgUnit.id)).all()
    return [{"id": u.id, "code": u.code, "name": u.name, "description": u.description} for u in rows]


def unit_by_code(db: Session) -> dict[str, OrgUnit]:
    return {u.code: u for u in db.scalars(select(OrgUnit)).all()}


def check_types(db: Session) -> list[dict]:
    rows = db.scalars(select(Codebook).where(Codebook.kind == "provera").order_by(Codebook.sort)).all()
    return [{"code": r.code, "label": r.label} for r in rows]


def priorities(db: Session) -> dict[str, dict]:
    rows = db.scalars(select(Codebook).where(Codebook.kind == "prioritet").order_by(Codebook.sort)).all()
    return {r.code: {"label": r.label, **r.data} for r in rows}


def variables(db: Session) -> dict[str, str]:
    return {v.key: v.value for v in db.scalars(select(KBVariable)).all()}


def variables_full(db: Session) -> list[KBVariable]:
    return db.scalars(select(KBVariable).order_by(KBVariable.group, KBVariable.key)).all()


def kb_version(db: Session) -> str:
    """Kratak potpis verzije znanja: najnovija izmena obrazaca i promenljivih."""
    t = db.scalar(select(func.max(KBTemplate.updated_at)))
    v = db.scalar(select(func.max(KBVariable.updated_at)))
    latest = max([x for x in (t, v) if x] or [datetime.now(timezone.utc)])
    return latest.strftime("%Y%m%d-%H%M%S")


def setting(db: Session, key: str, default=None):
    s = db.get(Setting, key)
    return s.value if s else default
