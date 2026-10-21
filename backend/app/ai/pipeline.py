"""Obrada jednog dolaznog mejla: priprema, filter, otvaranje predmeta, AI analiza, uparivanje
korisnika, pretraga znanja, predlog odgovora sa promenljivama i validacija."""
import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AISuggestion, Case, CaseEvent, Customer, Email
from ..seed.catalog import SIGNATURE
from ..services import catalog as cat
from ..services.customers import match_customer
from . import llm, mock, prompts
from .retrieval import search_templates
from .text_utils import clean_email_body, detect_script, extract_entities, guess_language, normalize
from .validator import finalize_text, render, validate

log = logging.getLogger("pipeline")
settings = get_settings()

THREAT_RE = re.compile(r"(videcete sta ce biti|doci cu licno|ubic|zapalic|polomicu|upozoravam vas posledn|pozvacu ljude)")
SAFETY_RE = re.compile(r"(neko ce stradati|pre nego sto neko strada|opasno po zivot|nesrec|povreden)")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _email_text(email: Email) -> str:
    att = ""
    for a in email.attachments or []:
        if a.get("text"):
            att += f"\n\n[Prilog: {a.get('name')}]\n{a['text']}"
    return (email.body_clean or email.body_text) + att


# ---------------------------------------------------------------- filter

def rule_filter(email: Email) -> tuple[str | None, str, int]:
    """Vraca (klasa ili None ako nije jasno, razlog, spam skor)."""
    h = {k.lower(): str(v).lower() for k, v in (email.headers or {}).items()}
    frm = email.from_addr.lower()
    subj = normalize(email.subject)
    if h.get("auto-submitted", "no") != "no" or "x-autoreply" in h:
        return "tehnicka", "Automatski generisana poruka (zaglavlje Auto-Submitted)", 0
    if frm.startswith(("mailer-daemon", "postmaster")) or "delivery status notification" in subj or subj.startswith("undeliverable"):
        return "tehnicka", "Obaveštenje o neisporučenoj pošti", 0
    if "list-unsubscribe" in h or h.get("precedence") in ("bulk", "list"):
        return "tehnicka", "Bilten ili masovna pošta (List-Unsubscribe)", 0
    t = normalize(email.subject + " " + email.body_text)
    score = 0
    score += len(re.findall(r"https?://", t)) >= 2
    score += "!!!" in email.subject + email.body_text
    score += sum(1 for w in ["garant", "lottery", "winner", "bitcoin", "crypto", "prize", "kliknite ovde", "300%"] if w in t)
    score += sum(1 for w in ["ponuda", "besplatn", "akcij", "cenovnik u prilogu", "saradnj"] if w in t)
    if score >= 3:
        return "spam", "Više pokazatelja neželjene pošte", score
    if score == 0:
        return "regularno", "", 0
    return None, "", score


def run_filter(db: Session, email: Email) -> tuple[str, str, str]:
    klasa, razlog, _ = rule_filter(email)
    if klasa:
        return klasa, razlog, "pravila"
    msgs = [{"role": "system", "content": prompts.FILTER_SYSTEM},
            {"role": "user", "content": f"Od: {email.from_name} <{email.from_addr}>\nNaslov: {email.subject}\n<mejl>\n{email.body_text[:3000]}\n</mejl>"}]
    out, meta = llm.chat_json("filter", msgs, prompts.FILTER_SCHEMA,
                              lambda: mock.filter_mock(email.subject, email.body_text, email.from_addr), max_tokens=150)
    return out.get("klasa", "regularno"), out.get("razlog", ""), "AI" if meta["mode"] == "live" else "pravila (rezervni rezim)"


# ---------------------------------------------------------------- predmet

def _thread_case(db: Session, email: Email) -> Case | None:
    if email.in_reply_to:
        orig = db.scalar(select(Email).where(Email.message_id == email.in_reply_to))
        if orig and orig.case_id:
            return db.get(Case, orig.case_id)
    m = re.search(r"\[(KC-\d{4}-\d{6})\]", email.subject)
    if m:
        return db.scalar(select(Case).where(Case.number == m.group(1)))
    return None


def new_case_number(db: Session, case: Case) -> str:
    year = (case.created_at or now_utc()).year
    return f"KC-{year}-{case.id:06d}"


def add_event(db: Session, case: Case, type_: str, text: str, actor: str = "sistem", data: dict | None = None,
              at: datetime | None = None) -> None:
    ev = CaseEvent(case_id=case.id, type=type_, text=text, actor=actor, data=data or {})
    if at:
        ev.at = at
    db.add(ev)


def process_email(db: Session, email_id: int, force_regular: bool = False) -> dict:
    email = db.get(Email, email_id)
    if not email:
        return {"status": "nema mejla"}
    if email.processed:
        return {"status": "vec obradjen"}
    email.body_clean = clean_email_body(email.body_text)
    email.script = detect_script(email.body_text)
    email.language = guess_language(email.body_text)

    klasa, razlog, metod = ("regularno", "", "ručno") if force_regular else run_filter(db, email)
    if klasa != "regularno":
        email.folder = "spam" if klasa == "spam" else "tehnicka"
        email.filter_reason = f"{razlog} ({metod})"
        email.processed = True
        db.commit()
        return {"status": "odvojeno", "folder": email.folder}

    case = _thread_case(db, email)
    if case:
        email.case_id = case.id
        email.folder = "obradjeno"
        reopened = case.status in ("zatvoreno", "odgovoreno")
        case.status = "u_obradi" if case.assigned_to_id else "novo"
        if reopened or (case.due_at and case.due_at < now_utc()):
            prio_days = cat.priorities(db).get(case.priority, {}).get("due_days", 8)
            case.due_at = now_utc() + timedelta(days=prio_days)
            case.closed_at = None
        add_event(db, case, "nova_poruka", "Stigla je nova poruka korisnika u postojećoj prepisci." + (" Predmet je ponovo otvoren." if reopened else ""),
                  data={"email_id": email.id})
        db.flush()
    else:
        case = Case(subject=email.subject[:500], channel="email", status="novo", created_at=email.received_at,
                    language=email.language, script=email.script, number=f"tmp-{email.id}")
        db.add(case)
        db.flush()
        case.number = new_case_number(db, case)
        email.case_id = case.id
        email.folder = "obradjeno"
        add_event(db, case, "kreiran", f"Predmet otvoren automatski po prijemu mejla od {email.from_name or email.from_addr}.",
                  at=email.received_at, data={"email_id": email.id})
    email.processed = True
    db.commit()
    analyze_case(db, case.id, email.id)
    return {"status": "predmet", "case_id": case.id}


def analyze_case(db: Session, case_id: int, email_id: int | None = None, actor: str = "AI") -> AISuggestion | None:
    case = db.get(Case, case_id)
    if not case:
        return None
    emails_in = [e for e in case.emails if e.direction == "in"]
    email = db.get(Email, email_id) if email_id else (emails_in[-1] if emails_in else None)
    if not email:
        return None
    case.ai_status = "processing"
    db.commit()
    try:
        sug = _analyze(db, case, email)
        case.ai_status = "done"
        db.commit()
        return sug
    except Exception as e:  # pragma: no cover
        log.exception("AI obrada nije uspela za predmet %s", case_id)
        db.rollback()
        case = db.get(Case, case_id)
        case.ai_status = "failed"
        add_event(db, case, "ai_greska", f"AI obrada nije uspela: {e}", actor="AI")
        db.commit()
        return None


def _analyze(db: Session, case: Case, email: Email) -> AISuggestion:
    cats = cat.categories(db)
    cmap = {c["code"]: c for c in cats}
    units = cat.units(db)
    ubc = cat.unit_by_code(db)
    checks = cat.check_types(db)
    prios = cat.priorities(db)
    text = _email_text(email)
    thread = ""
    if len([e for e in case.emails]) > 1:
        prev = [e for e in case.emails if e.id != email.id][-3:]
        thread = "\n\n".join(f"[{'korisnik' if e.direction == 'in' else 'služba'}, {e.received_at:%d.%m.%Y}]\n{(e.body_clean or e.body_text)[:800]}" for e in prev)

    # 1) Analiza
    user_msg = (f"Od: {email.from_name} <{email.from_addr}>\nNaslov: {email.subject}\n"
                + (f"Prethodna prepiska:\n<prepiska>\n{thread}\n</prepiska>\n" if thread else "")
                + f"<mejl>\n{text[:6000]}\n</mejl>")
    analysis, meta_a = llm.chat_json(
        "analiza",
        [{"role": "system", "content": prompts.analyze_system(cats, units, checks)}, {"role": "user", "content": user_msg}],
        prompts.analyze_schema([c["code"] for c in cats], [u["code"] for u in units], [c["code"] for c in checks]),
        lambda: mock.analyze_mock(email.subject, text, email.from_name, cats),
        case_id=case.id, max_tokens=900, trace_name=f"analiza {case.number}")

    category = analysis.get("kategorija") if analysis.get("kategorija") in cmap else "opste_informacije"
    unit_code = analysis.get("jedinica") if analysis.get("jedinica") in ubc else cmap[category]["unit"]
    priority = analysis.get("prioritet") if analysis.get("prioritet") in prios else cmap[category]["priority"]

    # 2) Pravila koja uvek vaze, nezavisno od modela
    overrides = []
    ntext = normalize(email.subject + " " + text)
    if analysis.get("ton") == "preteci" or THREAT_RE.search(ntext):
        if priority != "hitan":
            overrides.append({"pravilo": "pretnja", "poruka": "Prepoznata pretnja: prioritet podignut na hitan, obavestiti supervizora."})
        priority = "hitan"
    if SAFETY_RE.search(ntext) and priority in ("normalan", "nizak"):
        overrides.append({"pravilo": "bezbednost", "poruka": "Pominje se bezbednost na putu: prioritet podignut na visok."})
        priority = "visok"
    if category == "medijski_upit" and priority != "hitan":
        overrides.append({"pravilo": "mediji", "poruka": "Medijski upit: prioritet hitan i obaveštavanje Službe za odnose s javnošću."})
        priority = "hitan"
    if category == "pristup_informacijama":
        overrides.append({"pravilo": "zakonski_rok", "poruka": "Zahtev po Zakonu o slobodnom pristupu informacijama: zakonski rok 15 dana."})
        if priority in ("normalan", "nizak"):
            priority = "visok"

    # 3) Entiteti: spoj AI i regex izdvajanja (regex hvata ono sto model propusti)
    ent_ai = analysis.get("entiteti") or {}
    ent_rx = extract_entities(email.subject + "\n" + text)
    entities = {
        "ime": ent_ai.get("ime") or email.from_name,
        "tablice": sorted(set(ent_ai.get("tablice", []) + ent_rx["tablice"])),
        "tagovi": sorted(set(ent_ai.get("tagovi", []) + ent_rx["tagovi"])),
        "telefoni": sorted(set(ent_ai.get("telefoni", []) + ent_rx["telefoni"])),
        "datumi": sorted(set(ent_ai.get("datumi", []) + ent_rx["datumi"])),
        "iznosi": sorted(set(ent_ai.get("iznosi", []) + ent_rx["iznosi"])),
        "naplatne_stanice": sorted(set(ent_ai.get("naplatne_stanice", []) + ent_rx["naplatne_stanice"])),
    }

    # 4) Uparivanje sa korisnikom
    if not case.customer_id:
        cust, how = match_customer(db, email.from_addr, entities["ime"], entities["tablice"], entities["tagovi"])
        if not cust:
            cust = Customer(full_name=email.from_name or email.from_addr, email=email.from_addr.lower(),
                            phone=(entities["telefoni"][0] if entities["telefoni"] else ""), source="automatski",
                            note="Zapis kreiran automatski iz dolaznog mejla.")
            db.add(cust)
            db.flush()
            how = "novi zapis"
        case.customer_id = cust.id
        add_event(db, case, "korisnik", f"Obraćanje povezano sa korisnikom #{cust.id} ({cust.full_name}) prema: {how}.", actor="AI")

    # 5) Primena predloga na predmet (privremeno, dok operater ne potvrdi)
    unit = ubc[unit_code]
    billing = analysis.get("provera_naplatni_sistem") or {}
    if cmap[category]["needs_check"] and not billing.get("potrebna"):
        billing = {"potrebna": True, "tipovi": billing.get("tipovi") or [], "sta_proveriti": billing.get("sta_proveriti") or "Proveriti podatke o korisniku u naplatnom sistemu."}
    if not case.routing_confirmed:
        case.category = category
        case.org_unit_id = unit.id
        case.priority = priority
        due_days = min(cmap[category]["due_days"], prios.get(priority, {}).get("due_days", 8))
        case.due_at = (case.created_at or now_utc()) + timedelta(days=due_days)
    case.needs_billing_check = bool(billing.get("potrebna"))
    case.billing_check = {**billing, "status": case.billing_check.get("status", "otvorena") if case.billing_check else "otvorena"}
    case.language = analysis.get("jezik", case.language) if analysis.get("jezik") in ("sr", "en", "de") else case.language
    db.flush()

    # 6) Pretraga znanja i predlog odgovora
    query = f"{email.subject}\n{analysis.get('sazetak', '')}\n{text[:1500]}"
    found = search_templates(db, query, category_hint=category, k=4)
    variables = cat.variables(db)
    var_list = "\n".join(f"- {k}: {v}" for k, v in variables.items())
    tpl_text = "\n\n".join(f"[{r['template'].code}] {r['template'].title}\n{r['template'].body}" for r in found)
    cust = db.get(Customer, case.customer_id) if case.customer_id else None
    draft_user = (
        f"Broj predmeta: {case.number}\nIme korisnika: {cust.full_name if cust else email.from_name}\n"
        f"Jezik korisnika: {case.language}\nKategorija: {cmap[category]['label']}\n"
        f"Sažetak: {analysis.get('sazetak', '')}\n"
        f"Provera u naplatnom sistemu: {billing.get('sta_proveriti') if billing.get('potrebna') else 'nije potrebna'}\n"
        + (f"Dodatna pitanja u mejlu: {', '.join(cmap[c]['label'] for c in analysis.get('dodatne_kategorije', []) if c in cmap)}\n" if analysis.get("vise_pitanja") else "")
        + f"\nObrasci odgovora:\n{tpl_text or '(nema)'}\n\nPromenljive (ključ: vrednost):\n{var_list}\n\n"
        + (f"Prethodna prepiska:\n<prepiska>\n{thread}\n</prepiska>\n" if thread else "")
        + f"Mejl korisnika:\n<mejl>\n{text[:5000]}\n</mejl>"
    )
    draft, meta_d = llm.chat_json(
        "odgovor",
        [{"role": "system", "content": prompts.DRAFT_SYSTEM}, {"role": "user", "content": draft_user}],
        prompts.DRAFT_SCHEMA,
        lambda: mock.draft_mock([r["template"] for r in found], case.language),
        case_id=case.id, org_unit_id=unit.id, max_tokens=1100, trace_name=f"odgovor {case.number}")

    draft_template = (draft.get("odgovor") or "").strip()
    signature = SIGNATURE if case.language == "sr" else "\n\nKind regards,\n{{operater.ime}}\nCustomer Centre\n{{var.kontakt.call_centar}}"
    if case.language == "de":
        signature = "\n\nMit freundlichen Grüßen\n{{operater.ime}}\nKundenzentrum\n{{var.kontakt.call_centar}}"
    full_template = draft_template + signature
    context = {"korisnik.ime": cust.full_name if cust else (email.from_name or "korisniče"),
               "predmet.broj": case.number, "operater.ime": "{{operater.ime}}"}
    rendered, used_vars, unknown = render(full_template, variables, context)
    forbidden = (cat.setting(db, "forbidden_phrases", {}) or {}).get("value", [])
    allowed_extra = [case.number] + entities["tablice"] + entities["tagovi"] + entities["telefoni"] + entities["datumi"] + entities["iznosi"]
    warnings = validate(draft_template, email.subject + "\n" + text, allowed_extra, forbidden,
                        [u for u in unknown if u != "operater.ime"])
    if overrides:
        warnings = [{"nivo": "vazno", "tip": "pravilo", "poruka": o["poruka"]} for o in overrides] + warnings
    if meta_a.get("mode") == "mock":
        warnings.append({"nivo": "info", "tip": "rezim", "poruka": "Predlog je napravljen u rezervnom režimu (pravila), jer LLM nije bio dostupan."})
    rendered = finalize_text(rendered, case.script)

    used_codes = set(draft.get("korisceni_obrasci") or [])
    sources = [{"code": r["template"].code, "title": r["template"].title, "score": r["score"], "metode": r["metode"],
                "koriscen": r["template"].code in used_codes} for r in found]
    sug = AISuggestion(
        case_id=case.id, model=meta_d.get("model", ""), mode=meta_d.get("mode", "live"),
        prompt_version=prompts.PROMPT_VERSION, kb_version=cat.kb_version(db), category=category,
        suggested_unit_id=unit.id, suggested_priority=priority, reasoning=analysis.get("obrazlozenje", ""),
        confidence=float(analysis.get("pouzdanost") or 0), rule_overrides=overrides, entities=entities,
        billing_check=billing, draft_template=full_template, draft_rendered=rendered,
        operator_note=draft.get("napomena_za_operatera", ""), sources=sources, warnings=warnings,
        trace_id=meta_d.get("trace_id", ""),
    )
    db.add(sug)
    extra = ""
    if analysis.get("vise_pitanja"):
        extra = " Mejl sadrži više pitanja: " + ", ".join(cmap[c]["label"] for c in analysis.get("dodatne_kategorije", []) if c in cmap) + "."
    add_event(db, case, "ai_analiza",
              f"AI predlog: {cmap[category]['label']}, jedinica {unit.code}, prioritet {priority}"
              f" (pouzdanost {int(float(analysis.get('pouzdanost') or 0) * 100)}%).{extra}",
              actor="AI", data={"mode": meta_a.get("mode"), "sazetak": analysis.get("sazetak", ""),
                                "ton": analysis.get("ton"), "promenljive": used_vars})
    db.commit()
    return sug

