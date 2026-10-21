"""Predmeti i radni tok: lista, detalj, preuzimanje, prosledjivanje, odgovor, zatvaranje, AI predlozi."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..ai.pipeline import add_event
from ..ai.validator import edit_metrics
from ..db import get_db
from ..models import AISuggestion, Case, Customer, Email, Job, OrgUnit, PhoneContact, User
from ..security import current_user
from ..services import catalog as cat
from ..services.mail import send_reply
from ..services.serializers import case_row, contact_dict, customer_dict, email_dict, event_dict, suggestion_dict

router = APIRouter(prefix="/api", tags=["predmeti"])


def _now():
    return datetime.now(timezone.utc)


def _get_case(db: Session, case_id: int) -> Case:
    c = db.get(Case, case_id)
    if not c:
        raise HTTPException(404, "Predmet ne postoji")
    return c


def _latest_suggestion(db: Session, case_id: int) -> AISuggestion | None:
    return db.scalar(select(AISuggestion).where(AISuggestion.case_id == case_id).order_by(AISuggestion.id.desc()).limit(1))


@router.get("/cases")
def list_cases(status: str = "otvoreni", unit: str = "", priority: str = "", q: str = "", mine: bool = False,
               sla: str = "", category: str = "", limit: int = 200, db: Session = Depends(get_db),
               user: User = Depends(current_user)):
    qry = select(Case).options(selectinload(Case.org_unit), selectinload(Case.customer), selectinload(Case.assigned_to))
    if status == "otvoreni":
        qry = qry.where(Case.status.in_(["novo", "u_obradi", "ceka_proveru"]))
    elif status and status != "svi":
        qry = qry.where(Case.status == status)
    if unit:
        qry = qry.join(OrgUnit, Case.org_unit_id == OrgUnit.id).where(OrgUnit.code == unit)
    if priority:
        qry = qry.where(Case.priority == priority)
    if category:
        qry = qry.where(Case.category == category)
    if mine:
        qry = qry.where(Case.assigned_to_id == user.id)
    if sla == "prekoracen":
        qry = qry.where(Case.due_at < _now(), Case.status.in_(["novo", "u_obradi", "ceka_proveru"]))
    elif sla == "uskoro":
        qry = qry.where(Case.due_at >= _now(), Case.due_at < _now() + timedelta(hours=24),
                        Case.status.in_(["novo", "u_obradi", "ceka_proveru"]))
    if q:
        like = f"%{q}%"
        qry = qry.outerjoin(Customer, Case.customer_id == Customer.id).where(
            or_(Case.number.ilike(like), Case.subject.ilike(like), Customer.full_name.ilike(like), Customer.email.ilike(like)))
    prio_rank = case({"hitan": 0, "visok": 1, "normalan": 2, "nizak": 3}, value=Case.priority, else_=4)
    qry = qry.order_by(prio_rank, Case.due_at.asc().nulls_last()).limit(limit)
    cases = db.scalars(qry).unique().all()
    labels = {c["code"]: c["label"] for c in cat.categories(db)}
    last_in = {}
    if cases:
        ids = [c.id for c in cases]
        for e in db.scalars(select(Email).where(Email.case_id.in_(ids), Email.direction == "in").order_by(Email.received_at)).all():
            last_in[e.case_id] = e
    open_filter = Case.status.in_(["novo", "u_obradi", "ceka_proveru"])
    counts = {
        "otvoreni": db.scalar(select(func.count()).select_from(Case).where(open_filter)),
        "novo": db.scalar(select(func.count()).select_from(Case).where(Case.status == "novo")),
        "moji": db.scalar(select(func.count()).select_from(Case).where(open_filter, Case.assigned_to_id == user.id)),
        "prekoraceni": db.scalar(select(func.count()).select_from(Case).where(open_filter, Case.due_at < _now())),
        "uskoro": db.scalar(select(func.count()).select_from(Case).where(open_filter, Case.due_at >= _now(), Case.due_at < _now() + timedelta(hours=24))),
        "ai_u_obradi": db.scalar(select(func.count()).select_from(Case).where(Case.ai_status.in_(["pending", "processing"]))),
        "na_cekanju_mejlovi": db.scalar(select(func.count()).select_from(Job).where(Job.type == "process_email", Job.status.in_(["queued", "running"]))),
    }
    return {"items": [case_row(c, labels, last_in.get(c.id)) for c in cases], "counts": counts}


@router.get("/cases/{case_id}")
def case_detail(case_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _get_case(db, case_id)
    labels = {x["code"]: x["label"] for x in cat.categories(db)}
    units = {u.id: {"id": u.id, "code": u.code, "name": u.name} for u in db.scalars(select(OrgUnit)).all()}
    sug = _latest_suggestion(db, c.id)
    staff = {u.id: u.full_name for u in db.scalars(select(User)).all()}
    contacts, other_cases = [], []
    if c.customer_id:
        contacts = [contact_dict(p, staff) for p in db.scalars(select(PhoneContact).where(PhoneContact.customer_id == c.customer_id).order_by(PhoneContact.started_at.desc())).all()]
        others = db.scalars(select(Case).where(Case.customer_id == c.customer_id, Case.id != c.id).order_by(Case.created_at.desc()).limit(10)).all()
        other_cases = [{"id": o.id, "number": o.number, "subject": o.subject, "status": o.status, "created_at": o.created_at,
                        "category_label": labels.get(o.category, o.category)} for o in others]
    row = case_row(c, labels)
    return {
        **row,
        "billing_check": c.billing_check, "first_response_at": c.first_response_at, "closed_at": c.closed_at,
        "customer_full": customer_dict(c.customer) if c.customer else None,
        "emails": [email_dict(e) for e in c.emails],
        "events": [event_dict(e) for e in c.events],
        "suggestion": suggestion_dict(sug, user.full_name, units) if sug else None,
        "suggestion_count": db.scalar(select(func.count()).select_from(AISuggestion).where(AISuggestion.case_id == c.id)),
        "phone_contacts": contacts, "other_cases": other_cases,
    }


class AssignIn(BaseModel):
    user_id: int | None = None


@router.post("/cases/{case_id}/assign")
def assign(case_id: int, body: AssignIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _get_case(db, case_id)
    target = db.get(User, body.user_id) if body.user_id else user
    c.assigned_to_id = target.id
    if c.status == "novo":
        c.status = "u_obradi"
    add_event(db, c, "preuzet" if target.id == user.id else "dodeljen",
              "Predmet preuzet u rad." if target.id == user.id else f"Predmet dodeljen: {target.full_name}.", actor=user.full_name)
    db.commit()
    return {"ok": True}


class RoutingIn(BaseModel):
    org_unit_id: int
    priority: str
    category: str | None = None


def _finalize_routing(db: Session, c: Case, user: User) -> None:
    sug = _latest_suggestion(db, c.id)
    if sug and sug.accepted_unit is None:
        sug.final_unit_id = c.org_unit_id
        sug.final_priority = c.priority
        sug.accepted_unit = sug.suggested_unit_id == c.org_unit_id
        sug.accepted_priority = sug.suggested_priority == c.priority
        sug.operator_id = user.id


@router.post("/cases/{case_id}/routing")
def set_routing(case_id: int, body: RoutingIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _get_case(db, case_id)
    prev = (c.org_unit_id, c.priority, c.category)
    unit = db.get(OrgUnit, body.org_unit_id)
    if not unit:
        raise HTTPException(400, "Nepoznata jedinica")
    c.org_unit_id = unit.id
    c.priority = body.priority
    if body.category:
        c.category = body.category
    prios = cat.priorities(db)
    cmap = cat.category_map(db)
    if (prev[1] != c.priority or prev[2] != c.category) and c.created_at:
        days = min(cmap.get(c.category, {}).get("due_days", 8), prios.get(c.priority, {}).get("due_days", 8))
        c.due_at = c.created_at + timedelta(days=days)
    c.routing_confirmed = True
    changed = prev[0] != c.org_unit_id or prev[1] != c.priority or prev[2] != c.category
    _finalize_routing(db, c, user)
    add_event(db, c, "raspored", (f"Raspored izmenjen: jedinica {unit.code}, prioritet {c.priority}." if changed
                                  else f"AI predlog potvrđen: jedinica {unit.code}, prioritet {c.priority}."),
              actor=user.full_name, data={"promenjeno": changed})
    db.commit()
    return {"ok": True}


class ForwardIn(BaseModel):
    org_unit_id: int
    note: str = ""


@router.post("/cases/{case_id}/forward")
def forward(case_id: int, body: ForwardIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _get_case(db, case_id)
    unit = db.get(OrgUnit, body.org_unit_id)
    if not unit:
        raise HTTPException(400, "Nepoznata jedinica")
    c.org_unit_id = unit.id
    c.assigned_to_id = None
    c.status = "novo"
    c.routing_confirmed = True
    _finalize_routing(db, c, user)
    add_event(db, c, "prosledjen", f"Predmet prosleđen jedinici {unit.code} ({unit.name})." + (f" Napomena: {body.note}" if body.note else ""),
              actor=user.full_name)
    db.commit()
    return {"ok": True}


class NoteIn(BaseModel):
    text: str


@router.post("/cases/{case_id}/note")
def add_note(case_id: int, body: NoteIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _get_case(db, case_id)
    add_event(db, c, "interna_napomena", body.text, actor=user.full_name)
    db.commit()
    return {"ok": True}


class BillingIn(BaseModel):
    result: str
    waiting: bool = False


@router.post("/cases/{case_id}/billing-check")
def billing_check(case_id: int, body: BillingIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _get_case(db, case_id)
    bc = dict(c.billing_check or {})
    if body.waiting:
        bc["status"] = "zatrazena"
        c.status = "ceka_proveru"
        add_event(db, c, "provera", f"Zatražena provera u naplatnom sistemu. {body.result}", actor=user.full_name)
    else:
        bc["status"] = "obavljena"
        bc["rezultat"] = body.result
        bc["proverio"] = user.full_name
        bc["vreme"] = _now().isoformat()
        if c.status == "ceka_proveru":
            c.status = "u_obradi"
        add_event(db, c, "provera", f"Provera u naplatnom sistemu obavljena: {body.result}", actor=user.full_name)
    c.billing_check = bc
    db.commit()
    return {"ok": True}


class StatusIn(BaseModel):
    status: str
    note: str = ""


@router.post("/cases/{case_id}/status")
def set_status(case_id: int, body: StatusIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _get_case(db, case_id)
    c.status = body.status
    if body.status == "zatvoreno":
        c.closed_at = _now()
        _finalize_routing(db, c, user)
    add_event(db, c, "zatvoren" if body.status == "zatvoreno" else "status",
              ("Predmet zatvoren." if body.status == "zatvoreno" else f"Status promenjen: {body.status}.") + (f" {body.note}" if body.note else ""),
              actor=user.full_name)
    db.commit()
    return {"ok": True}


class ReplyIn(BaseModel):
    text: str
    suggestion_id: int | None = None
    close: bool = True


@router.post("/cases/{case_id}/reply")
def reply(case_id: int, body: ReplyIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _get_case(db, case_id)
    if not body.text.strip():
        raise HTTPException(400, "Odgovor je prazan")
    inbound = [e for e in c.emails if e.direction == "in"]
    last = inbound[-1] if inbound else None
    to_addr = last.from_addr if last else (c.customer.email if c.customer else "")
    to_name = last.from_name if last else (c.customer.full_name if c.customer else "")
    if not to_addr:
        raise HTTPException(400, "Nepoznata adresa primaoca")
    base_subject = (last.subject if last else c.subject) or c.subject
    base_subject = base_subject.removeprefix("Re: ").removeprefix("RE: ")
    if f"[{c.number}]" not in base_subject:
        base_subject = f"[{c.number}] {base_subject}"
    subject = f"Re: {base_subject}"
    refs = [e.message_id for e in c.emails if e.message_id]
    msg_id, ok, err = send_reply(to_addr, to_name, subject, body.text, last.message_id if last else "", refs[:-1])
    db.add(Email(case_id=c.id, direction="out", message_id=msg_id, in_reply_to=last.message_id if last else "",
                 from_addr="kontakt@demo-kc.rs", from_name="Korisnički centar", to_addr=to_addr, subject=subject,
                 body_text=body.text, folder="obradjeno", processed=True, sent_by_id=user.id))
    sug = db.get(AISuggestion, body.suggestion_id) if body.suggestion_id else _latest_suggestion(db, c.id)
    metrics = None
    if sug and sug.finalized_at is None:
        thresholds = cat.setting(db, "edit_thresholds", {}) or {}
        suggested = (sug.draft_rendered or "").replace("{{operater.ime}}", user.full_name)
        ratio, cls = edit_metrics(suggested, body.text, thresholds)
        sug.final_text = body.text
        sug.edit_ratio = ratio
        sug.edit_class = cls
        sug.finalized_at = _now()
        sug.operator_id = user.id
        if sug.accepted_unit is None:
            sug.final_unit_id = c.org_unit_id
            sug.final_priority = c.priority
            sug.accepted_unit = sug.suggested_unit_id == c.org_unit_id
            sug.accepted_priority = sug.suggested_priority == c.priority
        metrics = {"edit_ratio": ratio, "edit_class": cls}
    if not c.first_response_at:
        c.first_response_at = _now()
    if not c.assigned_to_id:
        c.assigned_to_id = user.id
    c.status = "zatvoreno" if body.close else "odgovoreno"
    if body.close:
        c.closed_at = _now()
    labels = {"bez_izmena": "bez izmena", "manje_izmene": "uz manje izmene", "vece_izmene": "uz veće izmene",
              "napisan_iznova": "napisan iznova"}
    txt = "Odgovor poslat korisniku" + (f" (AI predlog korišćen {labels.get(metrics['edit_class'], '')})" if metrics else "") + "."
    if not ok:
        txt += f" Upozorenje: SMTP server nije dostupan ({err[:80]}), poruka je sačuvana u sistemu."
    add_event(db, c, "odgovor_poslat", txt, actor=user.full_name, data={"message_id": msg_id, **(metrics or {})})
    if body.close:
        add_event(db, c, "zatvoren", "Predmet zatvoren.", actor=user.full_name)
    db.commit()
    return {"ok": True, "sent": ok, "metrics": metrics}


@router.post("/cases/{case_id}/reanalyze")
def reanalyze(case_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _get_case(db, case_id)
    c.ai_status = "pending"
    db.add(Job(type="analyze_case", payload={"case_id": c.id}))
    add_event(db, c, "ai_ponovo", "Zatražena nova AI analiza.", actor=user.full_name)
    db.commit()
    return {"ok": True}


class PhoneCaseIn(BaseModel):
    customer_id: int | None = None
    phone: str = ""
    topic: str
    note: str = ""
    duration_sec: int = 0
    open_case: bool = False
    org_unit_id: int | None = None
    priority: str = "normalan"


@router.post("/phone-contacts")
def log_phone(body: PhoneCaseIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    pc = PhoneContact(customer_id=body.customer_id, phone=body.phone, topic=body.topic, note=body.note,
                      duration_sec=body.duration_sec, staff_id=user.id, direction="dolazni")
    db.add(pc)
    db.flush()
    case_id = None
    if body.open_case:
        unit = db.get(OrgUnit, body.org_unit_id) if body.org_unit_id else db.scalar(select(OrgUnit).where(OrgUnit.code == "KC"))
        c = Case(subject=body.topic, channel="telefon", status="u_obradi", priority=body.priority, customer_id=body.customer_id,
                 org_unit_id=unit.id, assigned_to_id=user.id, number="tmp", ai_status="skipped", routing_confirmed=True,
                 category="opste_informacije", due_at=_now() + timedelta(days=8))
        db.add(c)
        db.flush()
        c.number = f"KC-{_now().year}-{c.id:06d}"
        pc.case_id = c.id
        add_event(db, c, "kreiran", f"Predmet otvoren iz telefonskog poziva. {body.note}", actor=user.full_name)
        case_id = c.id
    db.commit()
    return {"ok": True, "case_id": case_id, "contact_id": pc.id}


# ------------------------------------------------------------------ posta (odvojena)

@router.get("/mail")
def list_mail(folder: str = "spam", db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(Email).where(Email.folder == folder, Email.direction == "in").order_by(Email.received_at.desc()).limit(200)).all()
    pending = db.scalars(select(Email).where(Email.processed.is_(False), Email.direction == "in").order_by(Email.received_at)).all() if folder == "prijem" else []
    return {"items": [email_dict(e) for e in (pending if folder == "prijem" else rows)]}


@router.post("/mail/{email_id}/restore")
def restore_mail(email_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    e = db.get(Email, email_id)
    if not e:
        raise HTTPException(404, "Mejl ne postoji")
    e.processed = False
    e.folder = "prijem"
    e.filter_reason = f"Vraćeno u prijem ({user.full_name})"
    db.add(Job(type="process_email", payload={"email_id": e.id, "force_regular": True}))
    db.commit()
    return {"ok": True}
