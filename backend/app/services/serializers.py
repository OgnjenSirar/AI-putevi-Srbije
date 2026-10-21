"""Pretvaranje modela u recnike za API."""
from datetime import datetime, timedelta, timezone

from ..models import AISuggestion, Case, CaseEvent, Customer, Email, PhoneContact


def _now():
    return datetime.now(timezone.utc)


def sla_state(case: Case) -> str:
    if case.status in ("zatvoreno", "odgovoreno") or not case.due_at:
        return "ok"
    if case.due_at < _now():
        return "prekoracen"
    if case.due_at < _now() + timedelta(hours=24):
        return "uskoro"
    return "ok"


def case_row(c: Case, cat_labels: dict, last_in: Email | None = None) -> dict:
    return {
        "id": c.id, "number": c.number, "subject": c.subject, "status": c.status, "priority": c.priority,
        "category": c.category, "category_label": cat_labels.get(c.category, c.category),
        "org_unit": {"id": c.org_unit.id, "code": c.org_unit.code, "name": c.org_unit.name} if c.org_unit else None,
        "customer": {"id": c.customer.id, "name": c.customer.full_name} if c.customer else None,
        "assigned_to": {"id": c.assigned_to.id, "name": c.assigned_to.full_name} if c.assigned_to else None,
        "due_at": c.due_at, "created_at": c.created_at, "sla": sla_state(c), "channel": c.channel,
        "needs_billing_check": c.needs_billing_check, "billing_status": (c.billing_check or {}).get("status"),
        "ai_status": c.ai_status, "language": c.language, "script": c.script, "routing_confirmed": c.routing_confirmed,
        "snippet": ((last_in.body_clean or last_in.body_text)[:160] if last_in else ""),
    }


def email_dict(e: Email) -> dict:
    return {"id": e.id, "direction": e.direction, "from_addr": e.from_addr, "from_name": e.from_name, "to_addr": e.to_addr,
            "subject": e.subject, "body": e.body_text, "body_clean": e.body_clean, "received_at": e.received_at,
            "attachments": e.attachments, "message_id": e.message_id, "in_reply_to": e.in_reply_to,
            "folder": e.folder, "filter_reason": e.filter_reason, "language": e.language, "script": e.script,
            "headers": e.headers}


def event_dict(ev: CaseEvent) -> dict:
    return {"id": ev.id, "at": ev.at, "actor": ev.actor, "type": ev.type, "text": ev.text, "data": ev.data}


def suggestion_dict(s: AISuggestion, operator_name: str, units_by_id: dict) -> dict:
    def fill(t: str) -> str:
        return (t or "").replace("{{operater.ime}}", operator_name).replace("{{оператер.име}}", operator_name)

    return {
        "id": s.id, "created_at": s.created_at, "model": s.model, "mode": s.mode, "prompt_version": s.prompt_version,
        "kb_version": s.kb_version, "category": s.category,
        "suggested_unit": units_by_id.get(s.suggested_unit_id), "suggested_priority": s.suggested_priority,
        "reasoning": s.reasoning, "confidence": s.confidence, "rule_overrides": s.rule_overrides, "entities": s.entities,
        "billing_check": s.billing_check, "draft_template": s.draft_template, "draft": fill(s.draft_rendered),
        "operator_note": s.operator_note, "sources": s.sources, "warnings": s.warnings,
        "finalized_at": s.finalized_at, "edit_class": s.edit_class, "edit_ratio": s.edit_ratio,
        "accepted_unit": s.accepted_unit, "accepted_priority": s.accepted_priority, "trace_id": s.trace_id,
    }


def customer_dict(c: Customer, full: bool = False) -> dict:
    d = {"id": c.id, "full_name": c.full_name, "customer_type": c.customer_type, "company": c.company, "pib": c.pib,
         "email": c.email, "phone": c.phone, "city": c.city, "address": c.address, "source": c.source,
         "created_at": c.created_at, "merged_into_id": c.merged_into_id, "note": c.note,
         "vehicles": [{"id": v.id, "plate": v.plate, "category": v.category, "tag_number": v.tag_number,
                       "account_balance": v.account_balance} for v in c.vehicles]}
    return d


def contact_dict(p: PhoneContact, staff_names: dict) -> dict:
    return {"id": p.id, "customer_id": p.customer_id, "case_id": p.case_id, "direction": p.direction, "phone": p.phone,
            "staff": staff_names.get(p.staff_id, ""), "started_at": p.started_at, "duration_sec": p.duration_sec,
            "topic": p.topic, "note": p.note}
