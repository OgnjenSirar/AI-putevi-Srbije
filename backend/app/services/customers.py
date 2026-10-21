"""Uparivanje obracanja sa korisnicima i predlozi za objedinjavanje zapisa.
U produkciji se predlaze Splink (probabilisticko povezivanje), ovde je pojednostavljena tezinska ocena."""
import re
from itertools import combinations

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.text_utils import normalize, normalize_plate
from ..models import AuditLog, Case, Customer, PhoneContact, Vehicle


def _digits(phone: str) -> str:
    d = re.sub(r"\D", "", phone or "")
    return d[-8:] if len(d) >= 8 else d


def match_customer(db: Session, email: str, name: str, plates: list[str], tags: list[str]) -> tuple[Customer | None, str]:
    email = (email or "").lower().strip()
    if email:
        c = db.scalar(select(Customer).where(Customer.email == email, Customer.merged_into_id.is_(None)))
        if c:
            return c, "mejl adresa"
    for t in tags:
        v = db.scalar(select(Vehicle).where(Vehicle.tag_number == t))
        if v and v.customer and v.customer.merged_into_id is None:
            return v.customer, f"broj TAG-a {t}"
    for p in plates:
        np_ = normalize_plate(p)
        for v in db.scalars(select(Vehicle)).all():
            if normalize_plate(v.plate) == np_ and v.customer and v.customer.merged_into_id is None:
                return v.customer, f"registarska oznaka {p}"
    return None, ""


def pair_score(a: Customer, b: Customer) -> tuple[float, list[str]]:
    reasons = []
    score = 0.0
    na, nb = normalize(a.company or a.full_name), normalize(b.company or b.full_name)
    name_sim = fuzz.token_sort_ratio(na, nb) / 100
    if name_sim >= 0.85:
        score += 0.4 * name_sim
        reasons.append(f"slično ime ({int(name_sim * 100)}%)")
    if a.email and b.email and a.email.lower() == b.email.lower():
        score += 0.5
        reasons.append("ista mejl adresa")
    da, db_ = _digits(a.phone), _digits(b.phone)
    if da and da == db_:
        score += 0.35
        reasons.append("isti telefon")
    pa = {normalize_plate(v.plate) for v in a.vehicles}
    pb = {normalize_plate(v.plate) for v in b.vehicles}
    if pa & pb:
        score += 0.35
        reasons.append("ista registarska oznaka")
    ta = {v.tag_number for v in a.vehicles if v.tag_number}
    tb = {v.tag_number for v in b.vehicles if v.tag_number}
    if ta & tb:
        score += 0.5
        reasons.append("isti TAG")
    if a.city and b.city and normalize(a.city) == normalize(b.city):
        score += 0.05
    return min(score, 1.0), reasons


def duplicate_suggestions(db: Session, threshold: float = 0.6) -> list[dict]:
    customers = db.scalars(select(Customer).where(Customer.merged_into_id.is_(None))).all()
    out = []
    for a, b in combinations(customers, 2):
        if normalize(a.full_name)[:1] != normalize(b.full_name)[:1] and not (a.phone and _digits(a.phone) == _digits(b.phone)):
            continue
        s, reasons = pair_score(a, b)
        if s >= threshold and len(reasons) >= 2:
            # glavni zapis: onaj sa vise vozila / starijim datumom
            primary, dup = (a, b) if (len(a.vehicles), -a.id) >= (len(b.vehicles), -b.id) else (b, a)
            out.append({"primary_id": primary.id, "duplicate_id": dup.id, "score": round(s, 2), "reasons": reasons,
                        "primary_name": primary.full_name, "duplicate_name": dup.full_name})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


def merge(db: Session, primary_id: int, duplicate_id: int, actor: str) -> Customer:
    primary = db.get(Customer, primary_id)
    dup = db.get(Customer, duplicate_id)
    if not primary or not dup or primary.id == dup.id:
        raise ValueError("Neispravni zapisi za spajanje")
    moved = {"vozila": 0, "predmeti": 0, "pozivi": 0}
    existing_plates = {normalize_plate(v.plate) for v in primary.vehicles}
    for v in list(dup.vehicles):
        if normalize_plate(v.plate) in existing_plates and not v.tag_number:
            db.delete(v)
            continue
        v.customer_id = primary.id
        moved["vozila"] += 1
    for c in db.scalars(select(Case).where(Case.customer_id == dup.id)).all():
        c.customer_id = primary.id
        moved["predmeti"] += 1
    for p in db.scalars(select(PhoneContact).where(PhoneContact.customer_id == dup.id)).all():
        p.customer_id = primary.id
        moved["pozivi"] += 1
    if not primary.phone and dup.phone:
        primary.phone = dup.phone
    alt_emails = [e for e in [dup.email] if e and e != primary.email]
    if alt_emails:
        primary.note = (primary.note + "\n" if primary.note else "") + "Dodatni mejl: " + ", ".join(alt_emails)
    dup.merged_into_id = primary.id
    db.add(AuditLog(actor=actor, entity="korisnik", entity_id=str(primary.id), action="spajanje",
                    summary=f"Zapis #{dup.id} ({dup.full_name}) pripojen zapisu #{primary.id} ({primary.full_name})",
                    diff={"premesteno": moved, "duplikat": dup.id}))
    db.commit()
    return primary
