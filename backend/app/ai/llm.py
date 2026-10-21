"""Klijent ka LLM-u (OpenAI-kompatibilan API: vLLM ili Ollama), sa merenjem tokena,
Langfuse tragovima i automatskim prelaskom na rezervni (mock) rezim."""
import json
import logging
import re
import time
from typing import Any, Callable

import httpx

from ..config import get_settings
from ..db import session_scope
from ..models import AICall

log = logging.getLogger("llm")
settings = get_settings()

_client = None
_langfuse_enabled = False
_health_cache: dict[str, Any] = {"t": 0.0, "ok": False}


def _get_client():
    global _client, _langfuse_enabled
    if _client is not None:
        return _client
    kwargs = dict(base_url=settings.llm_base_url, api_key=settings.llm_api_key, timeout=settings.llm_timeout)
    if settings.langfuse_public_key and settings.langfuse_secret_key and settings.langfuse_host:
        try:
            from langfuse.openai import OpenAI  # type: ignore

            _client = OpenAI(**kwargs)
            _langfuse_enabled = True
            log.info("LLM klijent sa Langfuse tragovima")
            return _client
        except Exception as e:  # pragma: no cover
            log.warning("Langfuse nije dostupan (%s), nastavljam bez tragova", e)
    from openai import OpenAI

    _client = OpenAI(**kwargs)
    return _client


def llm_healthy(force: bool = False) -> bool:
    if settings.ai_mode == "mock":
        return False
    now = time.time()
    if not force and now - _health_cache["t"] < 15:
        return _health_cache["ok"]
    ok = False
    try:
        r = httpx.get(settings.llm_base_url.rstrip("/") + "/models", timeout=3)
        if r.status_code == 200:
            ids = [m.get("id", "") for m in (r.json().get("data") or [])]
            # Server radi, ali model mora biti ucitan ili preuzet (Ollama: "ollama pull")
            ok = any(i == settings.llm_model or i.split(":")[0] == settings.llm_model for i in ids)
    except Exception:
        ok = False
    _health_cache.update(t=now, ok=ok)
    return ok


def _is_ollama() -> bool:
    if settings.llm_backend in ("ollama", "vllm"):
        return settings.llm_backend == "ollama"
    u = settings.llm_base_url.lower()
    return "ollama" in u or ":11434" in u


def effective_mode() -> str:
    if settings.ai_mode == "mock":
        return "mock"
    if llm_healthy():
        return "live"
    return "mock" if settings.ai_fallback_to_mock else "live"


def _record(feature: str, mode: str, prompt_tokens: int, completion_tokens: int, latency_ms: int,
            case_id: int | None, org_unit_id: int | None, ok: bool = True, error: str = "") -> None:
    try:
        with session_scope() as db:
            db.add(AICall(feature=feature, model=settings.llm_model if mode == "live" else "rezervni-rezim",
                          mode=mode, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                          latency_ms=latency_ms, case_id=case_id, org_unit_id=org_unit_id, ok=ok, error=error[:500]))
    except Exception as e:  # pragma: no cover
        log.warning("Ne mogu da upisem AI poziv: %s", e)


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 3.6))


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def chat_json(feature: str, messages: list[dict], schema: dict, mock_fn: Callable[[], dict],
              case_id: int | None = None, org_unit_id: int | None = None, max_tokens: int | None = None,
              trace_name: str | None = None, temperature: float = 0.2) -> tuple[dict, dict]:
    """Vraca (rezultat, meta). U mock rezimu poziva mock_fn i procenjuje tokene."""
    mode = effective_mode()
    t0 = time.time()
    if mode == "mock":
        out = mock_fn()
        prompt_text = "\n".join(m["content"] if isinstance(m["content"], str) else json.dumps(m["content"]) for m in messages)
        pt, ct = _estimate_tokens(prompt_text), _estimate_tokens(json.dumps(out, ensure_ascii=False))
        latency = int((time.time() - t0) * 1000) + 5
        _record(feature, "mock", pt, ct, latency, case_id, org_unit_id)
        return out, {"mode": "mock", "model": "rezervni-rezim", "prompt_tokens": pt, "completion_tokens": ct, "latency_ms": latency}

    client = _get_client()
    kwargs: dict[str, Any] = dict(
        model=settings.llm_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens or settings.llm_max_tokens,
        response_format={"type": "json_schema", "json_schema": {"name": feature, "schema": schema, "strict": True}},
    )
    # Iskljuci "thinking" rezim Gemma 4 radi brzine: vLLM kroz chat sablon, Ollama kroz reasoning_effort
    if _is_ollama():
        kwargs["extra_body"] = {"reasoning_effort": "none"}
    else:
        kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
    if _langfuse_enabled:
        kwargs["name"] = trace_name or feature
    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:
        # Neki serveri ne podrzavaju json_schema, pokusaj sa json_object pa slobodnim tekstom
        log.warning("json_schema nije uspeo (%s), pokusavam bez seme", e)
        kwargs.pop("response_format", None)
        kwargs.pop("extra_body", None)
        kwargs["messages"] = messages + [{"role": "user", "content": "Odgovori ISKLJUČIVO validnim JSON objektom prema šemi: " + json.dumps(schema, ensure_ascii=False)}]
        try:
            resp = client.chat.completions.create(**kwargs)
        except Exception as e2:
            latency = int((time.time() - t0) * 1000)
            _record(feature, "live", 0, 0, latency, case_id, org_unit_id, ok=False, error=str(e2))
            if settings.ai_fallback_to_mock:
                _health_cache.update(t=time.time(), ok=False)
                out = mock_fn()
                return out, {"mode": "mock", "model": "rezervni-rezim", "fallback_error": str(e2)[:300]}
            raise
    latency = int((time.time() - t0) * 1000)
    content = resp.choices[0].message.content or "{}"
    usage = getattr(resp, "usage", None)
    pt = getattr(usage, "prompt_tokens", 0) or _estimate_tokens(json.dumps(messages, ensure_ascii=False))
    ct = getattr(usage, "completion_tokens", 0) or _estimate_tokens(content)
    try:
        out = _extract_json(content)
        _record(feature, "live", pt, ct, latency, case_id, org_unit_id)
    except Exception as e:
        _record(feature, "live", pt, ct, latency, case_id, org_unit_id, ok=False, error=f"JSON: {e}")
        out = mock_fn()
        return out, {"mode": "mock", "model": "rezervni-rezim", "fallback_error": "neispravan JSON"}
    return out, {"mode": "live", "model": settings.llm_model, "prompt_tokens": pt, "completion_tokens": ct,
                 "latency_ms": latency, "trace_id": getattr(resp, "id", "")}


def record_image_call(latency_ms: int, ok: bool = True, error: str = "") -> None:
    _record("pozadina_slika", "live", 0, 0, latency_ms, None, None, ok, error)
