"""Servis za generisanje pozadinskih slika (FLUX.2 klein 4B, Apache 2.0).

Na L4 (24 GB) radi uz vLLM na istoj kartici: model se drzi u RAM-u i komponente se
prebacuju na GPU samo tokom generisanja (enable_model_cpu_offload), pa vrsno zauzece
GPU memorije traje samo nekoliko sekundi.
"""
import base64
import io
import logging
import os
import threading
import time

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s imagegen: %(message)s")
log = logging.getLogger("imagegen")

MODEL_ID = os.getenv("IMAGEGEN_MODEL", "black-forest-labs/FLUX.2-klein-4B")
OFFLOAD = os.getenv("IMAGEGEN_OFFLOAD", "model")  # model | sequential | none
DTYPE = torch.bfloat16

app = FastAPI(title="Generisanje slika (demo)")
_pipe = None
_state = {"status": "ucitavanje", "error": "", "loaded_at": None}
_lock = threading.Lock()


def _load():
    global _pipe
    try:
        from diffusers import Flux2KleinPipeline

        log.info("Ucitavam %s (offload=%s)...", MODEL_ID, OFFLOAD)
        t0 = time.time()
        pipe = Flux2KleinPipeline.from_pretrained(MODEL_ID, torch_dtype=DTYPE)
        if not torch.cuda.is_available():
            log.warning("CUDA nije dostupna, generisanje ce raditi na CPU (veoma sporo)")
        elif OFFLOAD == "sequential":
            pipe.enable_sequential_cpu_offload()
        elif OFFLOAD == "model":
            pipe.enable_model_cpu_offload()
        else:
            pipe.to("cuda")
        _pipe = pipe
        _state.update(status="ok", loaded_at=time.time())
        log.info("Model ucitan za %.0f s", time.time() - t0)
    except Exception as e:  # pragma: no cover
        log.exception("Ucitavanje modela nije uspelo")
        _state.update(status="greska", error=str(e)[:500])


@app.on_event("startup")
def startup():
    threading.Thread(target=_load, daemon=True).start()


@app.get("/health")
def health():
    info = {"status": _state["status"], "model": MODEL_ID, "offload": OFFLOAD, "cuda": torch.cuda.is_available()}
    if _state["error"]:
        info["error"] = _state["error"]
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        info["gpu_free_gb"] = round(free / 1e9, 1)
        info["gpu_total_gb"] = round(total / 1e9, 1)
    return info


class GenIn(BaseModel):
    prompt: str
    width: int = 768
    height: int = 960
    steps: int = 4
    seed: int = 0


@app.post("/generate")
def generate(body: GenIn):
    if _pipe is None:
        raise HTTPException(503, f"Model nije spreman ({_state['status']})")
    w = max(256, min(1536, body.width // 16 * 16))
    h = max(256, min(1536, body.height // 16 * 16))
    with _lock:  # jedna slika u isto vreme, da ne bi doslo do nedostatka GPU memorije
        t0 = time.time()
        try:
            gen = torch.Generator(device="cpu").manual_seed(body.seed)
            image = _pipe(prompt=body.prompt, width=w, height=h, num_inference_steps=body.steps, generator=gen).images[0]
        except torch.cuda.OutOfMemoryError as e:
            torch.cuda.empty_cache()
            raise HTTPException(503, f"Nedovoljno GPU memorije: {e}")
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        ms = int((time.time() - t0) * 1000)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    log.info("Slika %sx%s za %s ms", w, h, ms)
    return {"image_b64": base64.b64encode(buf.getvalue()).decode(), "model": MODEL_ID, "ms": ms, "width": w, "height": h}
