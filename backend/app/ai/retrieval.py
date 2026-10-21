"""Hibridna pretraga znanja sluzbe: full-text (PostgreSQL) + vektorska (BGE-M3 preko TEI) + reranker."""
import logging
import re
import time

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import KBTemplate
from .text_utils import normalize

log = logging.getLogger("retrieval")
settings = get_settings()
_svc_health: dict[str, tuple[float, bool]] = {}


def _service_ok(url: str) -> bool:
    now = time.time()
    t, ok = _svc_health.get(url, (0.0, False))
    if now - t < 30:
        return ok
    try:
        ok = httpx.get(url.rstrip("/") + "/health", timeout=2).status_code == 200
    except Exception:
        ok = False
    _svc_health[url] = (now, ok)
    return ok


def embeddings_available() -> bool:
    return _service_ok(settings.embed_url)


def reranker_available() -> bool:
    return _service_ok(settings.rerank_url)


def embed(texts: list[str]) -> list[list[float]] | None:
    if not texts or not embeddings_available():
        return None
    try:
        r = httpx.post(settings.embed_url.rstrip("/") + "/embed", json={"inputs": texts, "truncate": True}, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("Embedding nije uspeo: %s", e)
        _svc_health[settings.embed_url] = (time.time(), False)
        return None


def rerank(query: str, docs: list[str]) -> list[float] | None:
    if not docs or not reranker_available():
        return None
    try:
        r = httpx.post(settings.rerank_url.rstrip("/") + "/rerank",
                       json={"query": query, "texts": docs, "truncate": True}, timeout=60)
        r.raise_for_status()
        scores = [0.0] * len(docs)
        for item in r.json():
            scores[item["index"]] = float(item["score"])
        return scores
    except Exception as e:
        log.warning("Rerank nije uspeo: %s", e)
        _svc_health[settings.rerank_url] = (time.time(), False)
        return None


def template_doc(t: KBTemplate) -> str:
    return f"{t.title}. Kategorija: {t.category}. Oznake: {', '.join(t.tags or [])}.\n{t.body}"


def index_templates(db: Session, only_missing: bool = True) -> int:
    q = select(KBTemplate).where(KBTemplate.active.is_(True))
    if only_missing:
        q = q.where(KBTemplate.embedding.is_(None))
    items = db.scalars(q).all()
    if not items:
        return 0
    vecs = embed([template_doc(t) for t in items])
    if vecs is None:
        return 0
    for t, v in zip(items, vecs):
        t.embedding = v
    db.commit()
    return len(items)


def search_templates(db: Session, query: str, category_hint: str | None = None, k: int = 4) -> list[dict]:
    """Vraca listu {template, score, metode} sortiranu po relevantnosti."""
    templates = db.scalars(select(KBTemplate).where(KBTemplate.active.is_(True))).all()
    by_id = {t.id: t for t in templates}
    ranks: dict[int, dict] = {}

    # 1) full-text: normalizovan tekst bez dijakritika (radi i za osisanu latinicu i cirilicu)
    nq = normalize(query)
    words = set(re.findall(r"[a-z0-9]{4,}", nq))
    words |= {w.replace("dj", "d") for w in words if "dj" in w}  # unaccent pretvara đ u d
    words = sorted(words)[:60]
    if words:
        tsq = " | ".join(words)
        rows = db.execute(text("""
            SELECT id, ts_rank(to_tsvector('simple', unaccent(lower(title || ' ' || body || ' ' || category))),
                               to_tsquery('simple', :q)) AS r
            FROM kb_templates WHERE active ORDER BY r DESC LIMIT 10
        """), {"q": tsq}).all()
        for pos, (tid, r) in enumerate(rows):
            if r and r > 0:
                ranks.setdefault(tid, {"rrf": 0.0, "metode": []})
                ranks[tid]["rrf"] += 1.0 / (60 + pos)
                ranks[tid]["metode"].append("tekst")

    # 2) vektorska pretraga
    vec = embed([query[:4000]])
    if vec:
        rows = db.execute(text("""
            SELECT id, 1 - (embedding <=> CAST(:v AS vector)) AS sim FROM kb_templates
            WHERE active AND embedding IS NOT NULL ORDER BY embedding <=> CAST(:v AS vector) LIMIT 10
        """), {"v": str(vec[0])}).all()
        for pos, (tid, sim) in enumerate(rows):
            ranks.setdefault(tid, {"rrf": 0.0, "metode": []})
            ranks[tid]["rrf"] += 1.0 / (60 + pos)
            ranks[tid]["metode"].append("vektor")

    # 3) blagi podsticaj za sablone iz predlozene kategorije
    if category_hint:
        for t in templates:
            if t.category == category_hint:
                ranks.setdefault(t.id, {"rrf": 0.0, "metode": []})
                ranks[t.id]["rrf"] += 0.02
                ranks[t.id]["metode"].append("kategorija")

    candidates = sorted(ranks.items(), key=lambda x: x[1]["rrf"], reverse=True)[:8]
    if not candidates:
        return []
    # 4) reranker (cross-encoder) ako je dostupan
    scores = rerank(query[:2000], [template_doc(by_id[tid]) for tid, _ in candidates])
    results = []
    for i, (tid, info) in enumerate(candidates):
        score = scores[i] if scores else info["rrf"] * 30
        metode = list(dict.fromkeys(info["metode"] + (["reranker"] if scores else [])))
        results.append({"template": by_id[tid], "score": round(float(score), 4), "metode": metode})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]
