"""Priprema objava: LLM pise tekst i popunjava polja sablona, pregledac (headless Chromium)
renderuje sliku iz HTML sablona, opciono AI pozadina (FLUX.2 klein), simulirana objava preko Meta Graph API."""
import base64
import logging
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from ..ai import llm, mock, prompts
from ..config import get_settings
from ..models import AuditLog, SocialPost
from .definitions import BY_CODE, FORMATS, TEMPLATES, social_schema, templates_prompt
from .icons import DEFAULT_ICON, ICONS

log = logging.getLogger("social")
settings = get_settings()
HERE = Path(__file__).parent
env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html"]))
GRAPH = "https://graph.facebook.com/v26.0"
DEMO_PAGE_ID = "100000000000001"
DEMO_IG_ID = "17840000000000001"


def media_root() -> Path:
    p = Path(settings.media_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def media_url(path: str) -> str:
    rel = os.path.relpath(path, media_root())
    return f"/media/{rel}"


# ---------------------------------------------------------------- render

def _html(post: SocialPost, fmt: str) -> str:
    tpl = BY_CODE[post.template_code]
    dims = FORMATS[fmt]
    icon_key = post.fields.get("ikonica") or DEFAULT_ICON.get(post.template_code)
    bg = Path(post.background).resolve().as_uri() if post.background and Path(post.background).exists() else ""
    return env.get_template("post.html").render(
        tpl=post.template_code, f=post.fields, w=dims["w"], h=dims["h"], fmt=fmt, accent=tpl["accent"],
        icon=ICONS.get(icon_key, ""), background=bg, ai_background=post.background_is_ai and bool(bg),
        font_dir=(HERE / "assets" / "fonts").resolve().as_uri(), chip=tpl["label"], lang="sr-Latn")


def render_post(post: SocialPost, formats: list[str] | None = None) -> tuple[dict, list[dict]]:
    """Renderuje JPEG za svaki format. Vraca (format->putanja, preliv polja)."""
    from playwright.sync_api import sync_playwright

    formats = formats or list(FORMATS)
    out_dir = media_root() / "social" / str(post.id)
    out_dir.mkdir(parents=True, exist_ok=True)
    version = uuid.uuid4().hex[:8]
    images, overflow = {}, []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--allow-file-access-from-files"])
        try:
            for fmt in formats:
                dims = FORMATS[fmt]
                page = browser.new_page(viewport={"width": dims["w"], "height": dims["h"]})
                html_path = out_dir / f"_{fmt}.html"
                html_path.write_text(_html(post, fmt), encoding="utf-8")
                page.goto(html_path.resolve().as_uri())
                page.wait_for_load_state("networkidle")
                page.evaluate("document.fonts.ready")
                over = page.evaluate("""() => [...document.querySelectorAll('.polje')]
                    .filter(e => {
                        const lh = parseFloat(getComputedStyle(e).lineHeight) || 40
                        return e.scrollHeight > e.clientHeight + lh * 0.45 || e.scrollWidth > e.clientWidth + 4
                    })
                    .map(e => e.dataset.key)""")
                for k in over:
                    overflow.append({"format": fmt, "polje": k})
                path = out_dir / f"{fmt}-{version}.jpg"
                page.screenshot(path=str(path), type="jpeg", quality=92)
                images[fmt] = str(path)
                page.close()
        finally:
            browser.close()
    # obrisi stare verzije
    for f in out_dir.glob("*.jpg"):
        if str(f) not in images.values():
            f.unlink(missing_ok=True)
    return images, overflow


def _shorten(field: dict, value: str) -> str:
    msgs = [{"role": "system", "content": prompts.SHORTEN_SYSTEM},
            {"role": "user", "content": f"Najviše znakova: {field['max'] - 4}\nPolje: {field['label']}\nTekst: {value}"}]
    out, _ = llm.chat_json("mreze_skracivanje", msgs, prompts.SHORTEN_SCHEMA,
                           lambda: {"tekst": value[: max(8, field["max"] - 6)].rsplit(" ", 1)[0]}, max_tokens=120)
    return (out.get("tekst") or value)[: field["max"]]


def render_with_fit(db: Session, post: SocialPost, max_rounds: int = 2) -> SocialPost:
    """Renderuje, a ako tekst ne staje u okvir, trazi od LLM-a da skrati to polje i ponovo renderuje."""
    tpl = BY_CODE[post.template_code]
    fields_by_key = {f["key"]: f for f in tpl["fields"]}
    history = []
    for rnd in range(max_rounds + 1):
        images, overflow = render_post(post)
        keys = sorted({o["polje"] for o in overflow})
        if not keys or rnd == max_rounds:
            break
        new_fields = dict(post.fields)
        for k in keys:
            if k in fields_by_key and new_fields.get(k):
                before = new_fields[k]
                new_fields[k] = _shorten(fields_by_key[k], before)
                history.append({"polje": k, "pre": before, "posle": new_fields[k]})
        post.fields = new_fields
    post.images = images
    post.render_warnings = ([{"tip": "skraceno", "poruka": f"Polje \"{h['polje']}\" je skraćeno jer nije stajalo u okvir.", **h} for h in history]
                            + [{"tip": "preliv", "poruka": f"Tekst u polju \"{o['polje']}\" i dalje ne staje ({o['format']})."} for o in overflow])
    db.commit()
    return post


# ---------------------------------------------------------------- AI tekst

def _clean_fields(code: str, fields: dict) -> dict:
    tpl = BY_CODE[code]
    out = {}
    for f in tpl["fields"]:
        v = (fields.get(f["key"]) or "").strip()
        if f["type"] == "choice":
            v = v if v in f["options"] else f["options"][0]
        out[f["key"]] = v
    return out


def draft_post(db: Session, brief: str, user_name: str) -> SocialPost:
    msgs = [{"role": "system", "content": prompts.SOCIAL_SYSTEM + "\n\nŠabloni:\n" + templates_prompt()},
            {"role": "user", "content": f"Opis objave od operatera:\n<opis>\n{brief}\n</opis>"}]
    out, meta = llm.chat_json("mreze_tekst", msgs, social_schema(), lambda: mock.social_mock(brief, TEMPLATES),
                              max_tokens=900, temperature=0.5)
    code = out.get("sablon") if out.get("sablon") in BY_CODE else "obavestenje"
    post = SocialPost(created_by=user_name, brief=brief, template_code=code, fields=_clean_fields(code, out.get("polja") or {}),
                      fb_text=out.get("tekst_facebook", ""), ig_text=out.get("tekst_instagram", ""),
                      alt_text=out.get("alt_tekst", ""), image_prompt=out.get("prompt_slike", ""),
                      ai_meta={"mode": meta.get("mode"), "model": meta.get("model")})
    db.add(post)
    db.commit()
    render_with_fit(db, post)
    return post


# ---------------------------------------------------------------- AI pozadina

def imagegen_status() -> dict:
    try:
        r = httpx.get(settings.imagegen_url.rstrip("/") + "/health", timeout=3)
        return r.json() if r.status_code == 200 else {"status": "nedostupan"}
    except Exception:
        return {"status": "nedostupan"}


def generate_background(db: Session, post: SocialPost, prompt: str | None = None) -> SocialPost:
    prompt = (prompt or post.image_prompt or "empty modern highway at dusk, realistic photo").strip()
    prompt += ", no text, no letters, no logos, no watermark"
    t0 = time.time()
    try:
        r = httpx.post(settings.imagegen_url.rstrip("/") + "/generate",
                       json={"prompt": prompt, "width": 768, "height": 960, "steps": 4, "seed": int(time.time()) % 100000},
                       timeout=300)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        llm.record_image_call(int((time.time() - t0) * 1000), ok=False, error=str(e))
        raise RuntimeError(f"Servis za generisanje slika nije dostupan: {e}") from e
    llm.record_image_call(int((time.time() - t0) * 1000))
    bg_dir = media_root() / "backgrounds"
    bg_dir.mkdir(exist_ok=True)
    path = bg_dir / f"{post.id}-{uuid.uuid4().hex[:6]}.png"
    path.write_bytes(base64.b64decode(data["image_b64"]))
    post.background = str(path)
    post.background_is_ai = True
    post.image_prompt = prompt
    post.ai_meta = {**(post.ai_meta or {}), "pozadina": {"model": data.get("model"), "trajanje_ms": data.get("ms")}}
    db.commit()
    return render_with_fit(db, post)


def set_upload_background(db: Session, post: SocialPost, content: bytes, filename: str) -> SocialPost:
    bg_dir = media_root() / "backgrounds"
    bg_dir.mkdir(exist_ok=True)
    ext = Path(filename).suffix.lower() or ".jpg"
    path = bg_dir / f"{post.id}-upload-{uuid.uuid4().hex[:6]}{ext}"
    path.write_bytes(content)
    post.background = str(path)
    post.background_is_ai = False
    db.commit()
    return render_with_fit(db, post)


# ---------------------------------------------------------------- simulirana objava

def publish_simulated(db: Session, post: SocialPost, actor: str) -> SocialPost:
    """Pravi tacno one pozive koje bi produkcija poslala Meta Graph API-ju, ali ih ne salje."""
    img = post.images.get("portret") or next(iter(post.images.values()))
    public_dir = media_root() / "public"
    public_dir.mkdir(exist_ok=True)
    pub_name = f"{uuid.uuid4().hex}.jpg"
    shutil.copy(img, public_dir / pub_name)
    public_url = f"{settings.public_base_url.rstrip('/')}/media/public/{pub_name}"
    token = "EAAG...(system user token iz sefa za tajne, skriven)"
    ts = datetime.now(timezone.utc)
    container = f"1789{int(ts.timestamp())}"
    media_id = f"1790{int(ts.timestamp())}"
    used = db.query(SocialPost).filter(SocialPost.status == "objavljeno").count()
    log_entries = [
        {"korak": "Facebook: objava fotografije sa tekstom", "metod": "POST", "url": f"{GRAPH}/{DEMO_PAGE_ID}/photos",
         "telo": {"source": f"@{Path(img).name} (multipart, JPEG)", "message": post.fb_text, "access_token": token},
         "odgovor": {"id": f"{int(ts.timestamp())}01", "post_id": f"{DEMO_PAGE_ID}_{int(ts.timestamp())}01"}},
        {"korak": "Instagram: provera dnevnog limita", "metod": "GET", "url": f"{GRAPH}/{DEMO_IG_ID}/content_publishing_limit",
         "telo": {"fields": "quota_usage,config", "access_token": token},
         "odgovor": {"data": [{"quota_usage": used, "config": {"quota_total": 100, "quota_duration": 86400}}]}},
        {"korak": "Instagram: kontejner sa slikom (Meta preuzima sliku sa javnog URL-a)", "metod": "POST",
         "url": f"{GRAPH}/{DEMO_IG_ID}/media",
         "telo": {"image_url": public_url, "caption": post.ig_text, "alt_text": post.alt_text, "access_token": token},
         "odgovor": {"id": container}},
        {"korak": "Instagram: status kontejnera", "metod": "GET", "url": f"{GRAPH}/{container}",
         "telo": {"fields": "status_code", "access_token": token}, "odgovor": {"status_code": "FINISHED", "id": container}},
        {"korak": "Instagram: objava", "metod": "POST", "url": f"{GRAPH}/{DEMO_IG_ID}/media_publish",
         "telo": {"creation_id": container, "access_token": token}, "odgovor": {"id": media_id}},
        {"korak": "Čišćenje", "metod": "-", "url": public_url,
         "telo": {}, "odgovor": {"napomena": "U produkciji se javni fajl briše odmah posle objave."}},
    ]
    post.publish_log = log_entries
    post.status = "objavljeno"
    post.published_at = ts
    db.add(AuditLog(actor=actor, entity="objava", entity_id=str(post.id), action="objava (simulacija)",
                    summary=f"Objava \"{post.fields.get('naslov', '')}\" na Facebook i Instagram (simulirano)"))
    db.commit()
    return post


def post_to_dict(post: SocialPost) -> dict:
    tpl = BY_CODE.get(post.template_code, {})
    return {
        "id": post.id, "created_at": post.created_at, "created_by": post.created_by, "brief": post.brief,
        "template_code": post.template_code, "template_label": tpl.get("label", ""), "fields": post.fields,
        "fb_text": post.fb_text, "ig_text": post.ig_text, "alt_text": post.alt_text, "image_prompt": post.image_prompt,
        "background": media_url(post.background) if post.background else "", "background_is_ai": post.background_is_ai,
        "images": {k: media_url(v) for k, v in (post.images or {}).items()}, "render_warnings": post.render_warnings,
        "status": post.status, "approved_by": post.approved_by, "approved_at": post.approved_at,
        "scheduled_at": post.scheduled_at, "published_at": post.published_at, "publish_log": post.publish_log,
        "ai_meta": post.ai_meta,
    }
