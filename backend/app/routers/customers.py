"""Evidencija korisnika: pregled, jedinstven prikaz obracanja, telefonski kontakti, objedinjavanje zapisa."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import AuditLog, Case, Customer, PhoneContact, User, Vehicle
from ..security import current_user
from ..services import catalog as cat
from ..services.customers import duplicate_suggestions, merge
from ..services.serializers import contact_dict, customer_dict

router = APIRouter(prefix="/api/customers", tags=["korisnici"])


@router.get("")
def list_customers(q: str = "", include_merged: bool = False, db: Session = Depends(get_db), user: User = Depends(current_user)):
    qry = select(Customer).options(selectinload(Customer.vehicles))
    if not include_merged:
        qry = qry.where(Customer.merged_into_id.is_(None))
    if q:
        like = f"%{q}%"
        qry = qry.outerjoin(Vehicle).where(or_(Customer.full_name.ilike(like), Customer.email.ilike(like), Customer.phone.ilike(like),
                                               Customer.company.ilike(like), Vehicle.plate.ilike(like), Vehicle.tag_number.ilike(like)))
    rows = db.scalars(qry.order_by(Customer.full_name).limit(300)).unique().all()
    counts = dict(db.execute(select(Case.customer_id, func.count()).group_by(Case.customer_id)).all())
    dup_ids = {d["duplicate_id"] for d in duplicate_suggestions(db)} | {d["primary_id"] for d in duplicate_suggestions(db)}
    return [{**customer_dict(c), "case_count": counts.get(c.id, 0), "possible_duplicate": c.id in dup_ids} for c in rows]


@router.get("/duplicates")
def duplicates(db: Session = Depends(get_db), user: User = Depends(current_user)):
    out = []
    for d in duplicate_suggestions(db):
        a, b = db.get(Customer, d["primary_id"]), db.get(Customer, d["duplicate_id"])
        out.append({**d, "primary": customer_dict(a), "duplicate": customer_dict(b)})
    return out


class MergeIn(BaseModel):
    primary_id: int
    duplicate_id: int


@router.post("/merge")
def do_merge(body: MergeIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        c = merge(db, body.primary_id, body.duplicate_id, user.full_name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return customer_dict(c)


@router.get("/{customer_id}")
def customer_detail(customer_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Customer, customer_id)
    if not c:
        raise HTTPException(404, "Korisnik ne postoji")
    labels = {x["code"]: x["label"] for x in cat.categories(db)}
    cases = db.scalars(select(Case).where(Case.customer_id == c.id).order_by(Case.created_at.desc())).all()
    staff = {u.id: u.full_name for u in db.scalars(select(User)).all()}
    contacts = db.scalars(select(PhoneContact).where(PhoneContact.customer_id == c.id).order_by(PhoneContact.started_at.desc())).all()
    merged = db.scalars(select(Customer).where(Customer.merged_into_id == c.id)).all()
    timeline = [{"type": "predmet", "at": x.created_at, "id": x.id, "number": x.number, "title": x.subject,
                 "status": x.status, "channel": x.channel, "category_label": labels.get(x.category, x.category)} for x in cases]
    timeline += [{"type": "poziv", "at": p.started_at, "id": p.id, "title": p.topic, "note": p.note, "staff": staff.get(p.staff_id, ""),
                  "duration_sec": p.duration_sec} for p in contacts]
    timeline.sort(key=lambda x: x["at"], reverse=True)
    return {**customer_dict(c), "timeline": timeline, "phone_contacts": [contact_dict(p, staff) for p in contacts],
            "merged_records": [{"id": m.id, "full_name": m.full_name, "email": m.email} for m in merged]}


class CustomerIn(BaseModel):
    full_name: str
    email: str = ""
    phone: str = ""
    city: str = ""
    address: str = ""
    note: str = ""


@router.put("/{customer_id}")
def update_customer(customer_id: int, body: CustomerIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Customer, customer_id)
    if not c:
        raise HTTPException(404, "Korisnik ne postoji")
    before = customer_dict(c)
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    diff = {k: {"pre": before[k], "posle": v} for k, v in body.model_dump().items() if before.get(k) != v}
    if diff:
        db.add(AuditLog(actor=user.full_name, entity="korisnik", entity_id=str(c.id), action="izmena",
                        summary=f"Izmena podataka korisnika {c.full_name}", diff=diff))
    db.commit()
    return customer_dict(c)


class ContactIn(BaseModel):
    topic: str
    note: str = ""
    duration_sec: int = 0
    direction: str = "dolazni"


@router.post("/{customer_id}/contacts")
def add_contact(customer_id: int, body: ContactIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Customer, customer_id)
    if not c:
        raise HTTPException(404, "Korisnik ne postoji")
    p = PhoneContact(customer_id=c.id, phone=c.phone, topic=body.topic, note=body.note, duration_sec=body.duration_sec,
                     direction=body.direction, staff_id=user.id)
    db.add(p)
    db.commit()
    return {"ok": True, "id": p.id}
