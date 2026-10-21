"""Punjenje baze izmisljenim podacima za demo. Pokrece se pri startu ako je baza prazna,
ili iz administracije ("Resetuj demo")."""
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..ai.text_utils import clean_email_body, detect_script
from ..ai.validator import edit_metrics, render
from ..db import Base, engine
from ..models import (
    AICall, AISuggestion, AuditLog, Case, CaseEvent, Codebook, Customer, Email, Job, KBTemplate,
    KBTemplateVersion, KBVariable, KBVariableVersion, OrgUnit, PhoneContact, Setting, User, Vehicle,
)
from ..security import hash_password
from . import catalog, emails, people

log = logging.getLogger("seed")
UTC = timezone.utc


def is_seeded(db: Session) -> bool:
    return db.scalar(select(User).limit(1)) is not None


def reset_database() -> None:
    from ..db import init_db

    with engine.begin() as conn:
        for t in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f'DROP TABLE IF EXISTS "{t.name}" CASCADE'))
    init_db()


def seed_all(db: Session, process_inbox: bool = True) -> dict:
    rnd = random.Random(42)
    now = datetime.now(UTC)

    # ------------------------------------------------ jedinice, nalozi, sifarnici
    units = {}
    for code, name, desc, mail in catalog.ORG_UNITS:
        u = OrgUnit(code=code, name=name, description=desc, email=mail)
        db.add(u)
        units[code] = u
    db.flush()
    users = {}
    for username, name, role, unit in catalog.USERS:
        u = User(username=username, full_name=name, role=role, org_unit_id=units[unit].id if unit else None,
                 password_hash=hash_password("demo"))
        db.add(u)
        users[username] = u
    for i, (code, label, data) in enumerate(catalog.PRIORITIES):
        db.add(Codebook(kind="prioritet", code=code, label=label, data=data, sort=i))
    for i, (code, label, unit, prio, due, check, kws) in enumerate(catalog.CATEGORIES):
        db.add(Codebook(kind="kategorija", code=code, label=label, sort=i,
                        data={"unit": unit, "priority": prio, "due_days": due, "needs_check": check, "keywords": kws}))
    for i, (code, label) in enumerate(catalog.BILLING_CHECK_TYPES):
        db.add(Codebook(kind="provera", code=code, label=label, sort=i))
    for i, (code, label) in enumerate([("novo", "Novo"), ("u_obradi", "U obradi"), ("ceka_proveru", "Čeka proveru"),
                                       ("odgovoreno", "Odgovoreno"), ("zatvoreno", "Zatvoreno")]):
        db.add(Codebook(kind="status", code=code, label=label, sort=i))
    for key, (value, label) in catalog.SETTINGS.items():
        db.add(Setting(key=key, value=value, label=label))

    # ------------------------------------------------ znanje sluzbe
    for key, label, value, group, owner in catalog.VARIABLES + catalog.EXTRA_VARIABLES:
        verified = now - timedelta(days=rnd.randint(3, 120))
        v = KBVariable(key=key, label=label, value=value, group=group, owner=owner, verified_at=verified,
                       updated_at=verified)
        db.add(v)
        db.flush()
        db.add(KBVariableVersion(variable_id=v.id, version=1, value=value, changed_by="Početni unos", changed_at=verified,
                                 change_note="Početna vrednost"))
    # jedna promenljiva sa istorijom izmena (demonstracija verzionisanja)
    v = db.scalar(select(KBVariable).where(KBVariable.key == "cena.tag_depozit"))
    old_at = now - timedelta(days=200)
    db.add(KBVariableVersion(variable_id=v.id, version=0, value="1.200 dinara", changed_by="Jasmina Ristić",
                             changed_at=old_at, change_note="Vrednost iz prethodnog cenovnika"))
    for code, title, category, unit, tags, body in catalog.TEMPLATES:
        changed = now - timedelta(days=rnd.randint(10, 300))
        t = KBTemplate(code=code, title=title, category=category, org_unit_id=units[unit].id, body=body, tags=tags,
                       version=1, updated_by="Jasmina Ristić", updated_at=changed)
        db.add(t)
        db.flush()
        db.add(KBTemplateVersion(template_id=t.id, version=1, title=title, body=body, changed_by="Jasmina Ristić",
                                 changed_at=changed, change_note="Početna verzija"))
    db.flush()

    # ------------------------------------------------ korisnici
    cust = {}
    for key, name, typ, company, pib, mail, phone, city, addr, vehicles in people.CUSTOMERS:
        c = Customer(full_name=name, customer_type=typ, company=company, pib=pib, email=mail, phone=phone, city=city,
                     address=addr, created_at=now - timedelta(days=rnd.randint(30, 900)))
        for plate, catg, tag, bal in vehicles:
            c.vehicles.append(Vehicle(plate=plate, category=catg, tag_number=tag, account_balance=bal))
        db.add(c)
        cust[key] = c
    db.flush()
    for ckey, direction, topic, note, dur, days, staff in people.PHONE_CONTACTS:
        c = cust.get(ckey) if ckey else None
        db.add(PhoneContact(customer_id=c.id if c else None, direction=direction, topic=topic, note=note,
                            duration_sec=dur, phone=c.phone if c else "+381 64 000 0000", staff_id=users[staff].id,
                            started_at=now - timedelta(days=days, hours=rnd.randint(0, 8))))
    db.flush()

    # ------------------------------------------------ istorijski (zatvoreni) predmeti
    hist = _seed_history(db, rnd, now, units, users, cust)

    # ------------------------------------------------ nova dolazna posta
    inbox_ids = []
    for e in emails.INBOX + emails.FILTERED:
        em = Email(direction="in", message_id=f"<{uuid.uuid4().hex}@{e['from_addr'].split('@')[-1]}>",
                   from_addr=e["from_addr"], from_name=e["from_name"], to_addr="kontakt@demo-kc.rs",
                   subject=e["subject"], body_text=e["body"], headers=e.get("headers", {}),
                   attachments=e.get("attachments", []), received_at=now - timedelta(hours=e["hours_ago"]),
                   folder="prijem")
        db.add(em)
        db.flush()
        inbox_ids.append((em.received_at, em.id))
    # odgovor korisnika u postojecoj prepisci
    if hist.get("goran_msg_id"):
        em = Email(direction="in", message_id=f"<{uuid.uuid4().hex}@example.rs>", in_reply_to=hist["goran_msg_id"],
                   from_addr="goran.simic@example.rs", from_name="Goran Simić", to_addr="kontakt@demo-kc.rs",
                   subject=f"Re: [{hist['goran_number']}] Kategorija vozila za kombi",
                   body_text=("Poštovani,\n\nhvala na odgovoru, ali problem i dalje postoji. Juče (20.10.) mi je na stanici "
                              "Pojate ponovo naplaćena kategorija II za kombi KV 212-MN, iako ste napisali da je ispravljeno.\n\n"
                              "Goran Simić\n\n> Poštovani Goran Simić,\n> kategorija vozila određuje se prema broju osovina..."),
                   received_at=now - timedelta(hours=17), folder="prijem")
        db.add(em)
        db.flush()
        inbox_ids.append((em.received_at, em.id))
    db.commit()
    if process_inbox:
        for _, eid in sorted(inbox_ids):
            db.add(Job(type="process_email", payload={"email_id": eid}))
        db.add(Job(type="index_kb", payload={"all": True}))
        db.commit()
    db.add(AuditLog(actor="sistem", entity="demo", action="seed", summary="Baza napunjena izmišljenim podacima za demo"))
    db.commit()
    return {"inbox": len(inbox_ids), "istorija": hist["count"]}


def _template_for(db: Session, category: str) -> KBTemplate | None:
    return db.scalar(select(KBTemplate).where(KBTemplate.category == category).order_by(KBTemplate.code))


def _mutate(text_: str, cls: str, rnd: random.Random) -> str:
    if cls == "bez_izmena":
        return text_
    if cls == "manje_izmene":
        extra = rnd.choice([
            "\n\nIzvinjavamo se zbog neprijatnosti.",
            "\n\nU međuvremenu stojimo Vam na raspolaganju za sva pitanja.",
            "\n\nProverili smo i potvrđujemo da je stanje ispravljeno.",
        ])
        return text_.replace("zahvaljujemo na prijavi", "hvala Vam na prijavi").replace("Poštovani/a", "Poštovani") + extra
    if cls == "vece_izmene":
        lines = text_.split("\n\n")
        keep = lines[:2] + lines[3:] if len(lines) > 4 else lines
        return "\n\n".join(keep).replace("Napominjemo", "Takođe napominjemo") + "\n\nProverom je utvrđeno da je transakcija ispravno evidentirana, a iznos je vraćen na Vaš račun."
    return ("Poštovani,\n\nnakon razgovora sa kolegama iz nadležne službe, obaveštavamo Vas da je Vaš zahtev rešen "
            "i da su sva sredstva vraćena. Hvala na strpljenju.\n\nS poštovanjem,\nKorisnički centar")


def _seed_history(db: Session, rnd: random.Random, now: datetime, units: dict, users: dict, cust: dict) -> dict:
    cats = {c[0]: c for c in catalog.CATEGORIES}
    weights = {"tag_neispravan": 14, "dopuna_racuna": 16, "tag_izdavanje": 10, "dupla_naplata": 7, "kategorija_vozila": 8,
               "povracaj_novca": 6, "raskid_ugovora": 5, "promena_podataka": 6, "cenovnik": 9, "stanje_puteva": 5,
               "ostecenje_vozila": 3, "prituzba_osoblje": 3, "pohvala": 3, "opste_informacije": 5, "fakture": 3,
               "interoperabilnost": 2, "naknadno_placanje": 3, "tag_zamena": 3, "guzve_naplata": 2, "prekrsaj": 2,
               "pristup_informacijama": 1, "medijski_upit": 1}
    codes = list(weights)
    w = [weights[c] for c in codes]
    variables = {v.key: v.value for v in db.scalars(select(KBVariable)).all()}
    unit_list = list(units.values())
    operator_by_unit = {u.org_unit_id: u for u in users.values() if u.role == "operater"}
    customers = [c for k, c in cust.items() if int(k[1:]) <= 30]
    prio_order = ["hitan", "visok", "normalan", "nizak"]
    edit_classes = ["bez_izmena"] * 46 + ["manje_izmene"] * 33 + ["vece_izmene"] * 14 + ["napisan_iznova"] * 7
    thresholds = dict(catalog.SETTINGS["edit_thresholds"][0])
    result = {"count": 0}
    n = 150
    for i in range(n):
        code = rnd.choices(codes, weights=w)[0]
        _, label, unit_code, prio, due_days, needs_check, _kw = cats[code]
        c = rnd.choice(customers)
        if i == n - 1:
            code, label, unit_code, prio, due_days, needs_check, _kw = cats["kategorija_vozila"]
            c = cust["c22"]
        created = now - timedelta(days=rnd.uniform(2.5, 62), hours=rnd.uniform(0, 10))
        created = created.replace(hour=rnd.randint(7, 19))
        unit = units[unit_code]
        case = Case(subject=label, channel=rnd.choices(["email", "email", "email", "telefon"])[0], category=code,
                    priority=prio, customer_id=c.id, org_unit_id=unit.id, status="zatvoreno", created_at=created,
                    due_at=created + timedelta(days=due_days), needs_billing_check=needs_check, ai_status="done",
                    routing_confirmed=True, is_historical=True, language="sr", script="latin", number=f"tmp-h{i}")
        db.add(case)
        db.flush()
        case.number = f"KC-{created.year}-{case.id:06d}"
        body = rnd.choice(emails.HISTORICAL_BODIES.get(code, ["Molim informaciju."]))
        plate = c.vehicles[0].plate if c.vehicles else ""
        em_in = Email(case_id=case.id, direction="in", message_id=f"<h{i}-{uuid.uuid4().hex[:8]}@example.rs>",
                      from_addr=c.email, from_name=c.full_name, to_addr="kontakt@demo-kc.rs", subject=label,
                      body_text=f"Poštovani,\n\n{body}" + (f" Vozilo {plate}." if plate else "") + f"\n\n{c.full_name}",
                      received_at=created, folder="obradjeno", processed=True, language="sr", script="latin")
        em_in.body_clean = clean_email_body(em_in.body_text)
        db.add(em_in)
        # AI predlog: vecinom tacan, ponekad pogresna jedinica ili prioritet
        sug_unit = unit if rnd.random() < 0.88 else rnd.choice([u for u in unit_list if u.id != unit.id])
        sug_prio = prio if rnd.random() < 0.84 else prio_order[min(3, max(0, prio_order.index(prio) + rnd.choice([-1, 1])))]
        tpl = _template_for(db, code)
        draft_t = (tpl.body if tpl else "Poštovani/a {{korisnik.ime}},\n\nzahvaljujemo na obraćanju.") + catalog.SIGNATURE
        operator = operator_by_unit.get(unit.id, users["ivana"])
        ctx = {"korisnik.ime": c.full_name, "predmet.broj": case.number, "operater.ime": operator.full_name}
        rendered, _, _ = render(draft_t, variables, ctx)
        rendered = rendered.replace("[PROVERA: ", "[PROVERA: ")
        ecls = rnd.choice(edit_classes)
        final = _mutate(rendered, ecls, rnd)
        if "[PROVERA" in final:
            final = final.replace("[PROVERA:", "Provereno:").replace("]", "")
        ratio, actual_cls = edit_metrics(rendered, final, thresholds)
        first_resp = created + timedelta(hours=rnd.uniform(1.0, 20 if prio in ("hitan", "visok") else 52))
        if rnd.random() < 0.08:
            first_resp = case.due_at + timedelta(hours=rnd.uniform(2, 40))
        first_resp = min(first_resp, now - timedelta(hours=rnd.uniform(2, 6)))
        if first_resp <= created:
            first_resp = created + timedelta(minutes=rnd.randint(20, 90))
        closed = min(first_resp + timedelta(hours=rnd.uniform(0.1, 30)), now - timedelta(minutes=rnd.randint(10, 90)))
        closed = max(closed, first_resp)
        case.first_response_at = first_resp
        case.closed_at = closed
        case.assigned_to_id = operator.id
        sug = AISuggestion(case_id=case.id, created_at=created + timedelta(seconds=rnd.randint(8, 40)), model="gemma-4",
                           mode="live", prompt_version="2026-10-01.1", kb_version="istorija", category=code,
                           suggested_unit_id=sug_unit.id, suggested_priority=sug_prio,
                           reasoning="Istorijski predlog (demo).", confidence=round(rnd.uniform(0.62, 0.97), 2),
                           draft_template=draft_t, draft_rendered=rendered, final_unit_id=unit.id, final_priority=prio,
                           final_text=final, accepted_unit=sug_unit.id == unit.id, accepted_priority=sug_prio == prio,
                           edit_ratio=ratio, edit_class=actual_cls, operator_id=operator.id, finalized_at=first_resp,
                           sources=[{"code": tpl.code, "title": tpl.title, "score": 0.8, "metode": ["tekst", "vektor"], "koriscen": True}] if tpl else [])
        db.add(sug)
        msg_id = f"<kc-{case.number}-{uuid.uuid4().hex[:6]}@demo-kc.rs>"
        db.add(Email(case_id=case.id, direction="out", message_id=msg_id, in_reply_to=em_in.message_id,
                     from_addr="kontakt@demo-kc.rs", from_name="Korisnički centar", to_addr=c.email,
                     subject=f"Re: [{case.number}] {label}", body_text=final, received_at=first_resp, folder="obradjeno",
                     processed=True, sent_by_id=operator.id))
        if i == n - 1:
            result["goran_msg_id"] = msg_id
            result["goran_number"] = case.number
            case.subject = "Kategorija vozila za kombi"
        for at, typ, actor, txt in [
            (created, "kreiran", "sistem", "Predmet otvoren automatski po prijemu mejla."),
            (created + timedelta(seconds=30), "ai_analiza", "AI", f"AI predlog: {label}, jedinica {sug_unit.code}, prioritet {sug_prio}."),
            (created + timedelta(minutes=rnd.randint(5, 240)), "preuzet", operator.full_name, "Predmet preuzet u rad."),
            (first_resp, "odgovor_poslat", operator.full_name, "Odgovor poslat korisniku."),
            (closed, "zatvoren", operator.full_name, "Predmet zatvoren."),
        ]:
            db.add(CaseEvent(case_id=case.id, at=at, actor=actor, type=typ, text=txt))
        # AI pozivi (tokeni i trajanje kao za Gemma 4 12B na L4)
        db.add(AICall(at=created + timedelta(seconds=10), feature="analiza", model="gemma-4", mode="live",
                      prompt_tokens=rnd.randint(1700, 2600), completion_tokens=rnd.randint(220, 420),
                      latency_ms=rnd.randint(3800, 8200), case_id=case.id, org_unit_id=unit.id))
        db.add(AICall(at=created + timedelta(seconds=25), feature="odgovor", model="gemma-4", mode="live",
                      prompt_tokens=rnd.randint(3400, 5200), completion_tokens=rnd.randint(280, 520),
                      latency_ms=rnd.randint(7000, 15000), case_id=case.id, org_unit_id=unit.id))
        result["count"] += 1
    # istorijska odvojena posta (spam i tehnicka)
    for j in range(28):
        folder = rnd.choice(["spam", "spam", "tehnicka"])
        at = now - timedelta(days=rnd.uniform(2.5, 60))
        db.add(Email(direction="in", message_id=f"<s{j}-{uuid.uuid4().hex[:8]}@spam.example>",
                     from_addr=f"promo{j}@ponude.example", from_name="Promo", subject="Specijalna ponuda" if folder == "spam" else "Automatski odgovor",
                     body_text="Ponuda...", received_at=at, folder=folder, processed=True,
                     filter_reason="Više pokazatelja neželjene pošte (pravila)" if folder == "spam" else "Automatski generisana poruka (pravila)"))
        if j % 3 == 0:
            db.add(AICall(at=at, feature="filter", model="gemma-4", mode="live", prompt_tokens=rnd.randint(300, 700),
                          completion_tokens=rnd.randint(20, 40), latency_ms=rnd.randint(500, 1400)))
    db.commit()
    return result


def detect_and_fill_scripts(db: Session) -> None:
    for e in db.scalars(select(Email).where(Email.script == "")).all():
        e.script = detect_script(e.body_text)
    db.commit()
