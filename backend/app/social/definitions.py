"""Definicije sablona slika za drustvene mreze: polja i ogranicenja koja LLM mora da postuje."""

FORMATS = {
    "kvadrat": {"w": 1080, "h": 1080, "label": "Kvadrat 1:1 (Instagram i Facebook feed)"},
    "portret": {"w": 1080, "h": 1350, "label": "Portret 4:5 (Instagram feed)"},
    "story": {"w": 1080, "h": 1920, "label": "Story 9:16"},
}

TEMPLATES = [
    {
        "code": "radovi",
        "label": "Radovi na putu",
        "description": "Najava radova, zatvaranja traka ili izmene režima saobraćaja",
        "accent": "#FFB000",
        "fields": [
            {"key": "naslov", "label": "Naslov", "type": "text", "max": 38},
            {"key": "deonica", "label": "Deonica / lokacija", "type": "text", "max": 40},
            {"key": "period", "label": "Period", "type": "text", "max": 32},
            {"key": "poruka", "label": "Poruka", "type": "text", "max": 120},
            {"key": "ikonica", "label": "Ikonica", "type": "choice", "options": ["radovi", "zatvaranje", "obilazak"]},
        ],
    },
    {
        "code": "obavestenje",
        "label": "Saobraćajno obaveštenje",
        "description": "Upozorenja vozačima, vremenski uslovi, bezbednosne poruke",
        "accent": "#FF5A3C",
        "fields": [
            {"key": "naslov", "label": "Naslov", "type": "text", "max": 38},
            {"key": "poruka", "label": "Poruka", "type": "text", "max": 150},
            {"key": "napomena", "label": "Napomena", "type": "text", "max": 60},
            {"key": "ikonica", "label": "Ikonica", "type": "choice", "options": ["upozorenje", "info", "vreme"]},
        ],
    },
    {
        "code": "naplata",
        "label": "Naplata i TAG",
        "description": "Informacije o TAG-u, popustima, dopuni i portalu",
        "accent": "#2EC4B6",
        "fields": [
            {"key": "naslov", "label": "Naslov", "type": "text", "max": 38},
            {"key": "istaknuto", "label": "Istaknuta poruka", "type": "text", "max": 18},
            {"key": "poruka", "label": "Poruka", "type": "text", "max": 130},
            {"key": "poziv", "label": "Poziv na akciju", "type": "text", "max": 40},
        ],
    },
    {
        "code": "praznik",
        "label": "Praznik i radno vreme",
        "description": "Čestitke i obaveštenja o radnom vremenu tokom praznika",
        "accent": "#7B61FF",
        "fields": [
            {"key": "naslov", "label": "Naslov", "type": "text", "max": 32},
            {"key": "poruka", "label": "Poruka", "type": "text", "max": 140},
            {"key": "potpis", "label": "Potpis", "type": "text", "max": 40},
        ],
    },
]

BY_CODE = {t["code"]: t for t in TEMPLATES}


def social_schema() -> dict:
    """JSON sema za LLM: polja svih sablona kao opcioni stringovi (vLLM guided decoding)."""
    keys = sorted({f["key"] for t in TEMPLATES for f in t["fields"]})
    return {
        "type": "object",
        "properties": {
            "sablon": {"type": "string", "enum": [t["code"] for t in TEMPLATES]},
            "polja": {"type": "object", "properties": {k: {"type": "string"} for k in keys},
                      "required": keys, "additionalProperties": False},
            "tekst_facebook": {"type": "string"},
            "tekst_instagram": {"type": "string"},
            "alt_tekst": {"type": "string"},
            "prompt_slike": {"type": "string"},
        },
        "required": ["sablon", "polja", "tekst_facebook", "tekst_instagram", "alt_tekst", "prompt_slike"],
        "additionalProperties": False,
    }


def templates_prompt() -> str:
    lines = []
    for t in TEMPLATES:
        fl = ", ".join(
            f"{f['key']} (najviše {f['max']} znakova)" if f["type"] == "text" else f"{f['key']} (jedno od: {', '.join(f['options'])})"
            for f in t["fields"])
        lines.append(f"- {t['code']}: {t['label']}. {t['description']}. Polja: {fl}. Ostala polja ostavi prazna.")
    return "\n".join(lines)
