"""ORM modeli sistema Korisnickog centra (demo)."""
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

EMBED_DIM = 1024


class OrgUnit(Base):
    __tablename__ = "org_units"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # operater, supervizor, admin
    org_unit_id: Mapped[int | None] = mapped_column(ForeignKey("org_units.id"))
    password_hash: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    org_unit: Mapped[OrgUnit | None] = relationship()


class Codebook(Base):
    """Opsti sifarnici (kategorije, prioriteti, tipovi provere...)."""

    __tablename__ = "codebooks"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    code: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(String(200))
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB)
    label: Mapped[str] = mapped_column(String(200), default="")


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    customer_type: Mapped[str] = mapped_column(String(20), default="fizicko")  # fizicko, pravno
    company: Mapped[str] = mapped_column(String(200), default="")
    pib: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(200), default="", index=True)
    phone: Mapped[str] = mapped_column(String(40), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source: Mapped[str] = mapped_column(String(40), default="evidencija")  # evidencija, automatski
    merged_into_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="customer", cascade="all, delete-orphan")


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    plate: Mapped[str] = mapped_column(String(20), index=True)
    category: Mapped[str] = mapped_column(String(10), default="I")
    tag_number: Mapped[str] = mapped_column(String(30), default="", index=True)
    account_balance: Mapped[float] = mapped_column(Float, default=0)  # demo, izmisljeno
    customer: Mapped[Customer] = relationship(back_populates="vehicles")


class PhoneContact(Base):
    __tablename__ = "phone_contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), index=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"))
    direction: Mapped[str] = mapped_column(String(10), default="dolazni")
    phone: Mapped[str] = mapped_column(String(40), default="")
    staff_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    topic: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(Text, default="")


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(30), unique=True)
    subject: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="novo", index=True)
    channel: Mapped[str] = mapped_column(String(20), default="email")
    category: Mapped[str] = mapped_column(String(60), default="")
    priority: Mapped[str] = mapped_column(String(20), default="normalan")
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), index=True)
    org_unit_id: Mapped[int | None] = mapped_column(ForeignKey("org_units.id"), index=True)
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    language: Mapped[str] = mapped_column(String(10), default="sr")
    script: Mapped[str] = mapped_column(String(10), default="latin")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    needs_billing_check: Mapped[bool] = mapped_column(Boolean, default=False)
    billing_check: Mapped[dict] = mapped_column(JSONB, default=dict)
    ai_status: Mapped[str] = mapped_column(String(20), default="pending")
    routing_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_historical: Mapped[bool] = mapped_column(Boolean, default=False)

    customer: Mapped[Customer | None] = relationship()
    org_unit: Mapped[OrgUnit | None] = relationship()
    assigned_to: Mapped[User | None] = relationship()
    emails: Mapped[list["Email"]] = relationship(back_populates="case", order_by="Email.received_at")
    events: Mapped[list["CaseEvent"]] = relationship(back_populates="case", order_by="CaseEvent.at")


class Email(Base):
    __tablename__ = "emails"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), index=True)
    direction: Mapped[str] = mapped_column(String(5), default="in")  # in, out
    message_id: Mapped[str] = mapped_column(String(300), default="", index=True)
    in_reply_to: Mapped[str] = mapped_column(String(300), default="")
    from_addr: Mapped[str] = mapped_column(String(200), default="")
    from_name: Mapped[str] = mapped_column(String(200), default="")
    to_addr: Mapped[str] = mapped_column(String(200), default="")
    subject: Mapped[str] = mapped_column(String(500), default="")
    body_text: Mapped[str] = mapped_column(Text, default="")
    body_clean: Mapped[str] = mapped_column(Text, default="")
    headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    attachments: Mapped[list] = mapped_column(JSONB, default=list)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    folder: Mapped[str] = mapped_column(String(20), default="prijem")  # prijem, spam, tehnicka, obradjeno
    filter_reason: Mapped[str] = mapped_column(String(300), default="")
    language: Mapped[str] = mapped_column(String(10), default="")
    script: Mapped[str] = mapped_column(String(10), default="")
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    case: Mapped[Case | None] = relationship(back_populates="emails")


class CaseEvent(Base):
    __tablename__ = "case_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor: Mapped[str] = mapped_column(String(200), default="sistem")
    type: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    case: Mapped[Case] = relationship(back_populates="events")


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    model: Mapped[str] = mapped_column(String(120), default="")
    mode: Mapped[str] = mapped_column(String(10), default="live")
    prompt_version: Mapped[str] = mapped_column(String(20), default="")
    kb_version: Mapped[str] = mapped_column(String(40), default="")
    category: Mapped[str] = mapped_column(String(60), default="")
    suggested_unit_id: Mapped[int | None] = mapped_column(ForeignKey("org_units.id"))
    suggested_priority: Mapped[str] = mapped_column(String(20), default="")
    reasoning: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0)
    rule_overrides: Mapped[list] = mapped_column(JSONB, default=list)
    entities: Mapped[dict] = mapped_column(JSONB, default=dict)
    billing_check: Mapped[dict] = mapped_column(JSONB, default=dict)
    draft_template: Mapped[str] = mapped_column(Text, default="")
    draft_rendered: Mapped[str] = mapped_column(Text, default="")
    operator_note: Mapped[str] = mapped_column(Text, default="")
    sources: Mapped[list] = mapped_column(JSONB, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    # Konacne vrednosti (popunjava se pri slanju odgovora / potvrdi rasporeda)
    final_unit_id: Mapped[int | None] = mapped_column(ForeignKey("org_units.id"))
    final_priority: Mapped[str] = mapped_column(String(20), default="")
    final_text: Mapped[str] = mapped_column(Text, default="")
    accepted_unit: Mapped[bool | None] = mapped_column(Boolean)
    accepted_priority: Mapped[bool | None] = mapped_column(Boolean)
    edit_ratio: Mapped[float | None] = mapped_column(Float)
    edit_class: Mapped[str] = mapped_column(String(30), default="")
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[str] = mapped_column(String(100), default="")


class AICall(Base):
    __tablename__ = "ai_calls"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    feature: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(120), default="")
    mode: Mapped[str] = mapped_column(String(10), default="live")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    case_id: Mapped[int | None] = mapped_column(Integer)
    org_unit_id: Mapped[int | None] = mapped_column(Integer)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str] = mapped_column(Text, default="")


class KBTemplate(Base):
    __tablename__ = "kb_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(60), default="")
    org_unit_id: Mapped[int | None] = mapped_column(ForeignKey("org_units.id"))
    body: Mapped[str] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_by: Mapped[str] = mapped_column(String(200), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    embedding = mapped_column(Vector(EMBED_DIM), nullable=True)


class KBTemplateVersion(Base):
    __tablename__ = "kb_template_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("kb_templates.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(String(200), default="")
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    change_note: Mapped[str] = mapped_column(String(500), default="")


class KBVariable(Base):
    __tablename__ = "kb_variables"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    label: Mapped[str] = mapped_column(String(300))
    value: Mapped[str] = mapped_column(Text)
    group: Mapped[str] = mapped_column(String(40), default="ostalo")
    owner: Mapped[str] = mapped_column(String(200), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KBVariableVersion(Base):
    __tablename__ = "kb_variable_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    variable_id: Mapped[int] = mapped_column(ForeignKey("kb_variables.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    value: Mapped[str] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(String(200), default="")
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    change_note: Mapped[str] = mapped_column(String(500), default="")


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str] = mapped_column(Text, default="")


class SocialPost(Base):
    __tablename__ = "social_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(200), default="")
    brief: Mapped[str] = mapped_column(Text, default="")
    template_code: Mapped[str] = mapped_column(String(60), default="")
    fields: Mapped[dict] = mapped_column(JSONB, default=dict)
    fb_text: Mapped[str] = mapped_column(Text, default="")
    ig_text: Mapped[str] = mapped_column(Text, default="")
    alt_text: Mapped[str] = mapped_column(Text, default="")
    image_prompt: Mapped[str] = mapped_column(Text, default="")
    background: Mapped[str] = mapped_column(String(300), default="")  # putanja do AI pozadine
    background_is_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    images: Mapped[dict] = mapped_column(JSONB, default=dict)  # format -> putanja
    render_warnings: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(20), default="nacrt")
    approved_by: Mapped[str] = mapped_column(String(200), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publish_log: Mapped[list] = mapped_column(JSONB, default=list)
    ai_meta: Mapped[dict] = mapped_column(JSONB, default=dict)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    actor: Mapped[str] = mapped_column(String(200), default="sistem")
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(60), default="")
    action: Mapped[str] = mapped_column(String(60))
    summary: Mapped[str] = mapped_column(Text, default="")
    diff: Mapped[dict] = mapped_column(JSONB, default=dict)
