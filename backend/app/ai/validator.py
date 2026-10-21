"""Renderovanje promenljivih u predlogu odgovora i provera da podaci poticu iz znanja sluzbe."""
import re

from rapidfuzz.distance import Levenshtein

from .text_utils import lat_to_cyr, normalize

PLACEHOLDER_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")
CHECK_RE = re.compile(r"\[PROVERA:([^\]]*)\]")
URL_RE = re.compile(r"https?://[^\s)]+")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
NUM_RE = re.compile(r"(?<![\w{])\d[\d.,:/ ]*\d(?![\w}])|(?<![\w{])\d(?![\w}])")


def render(text: str, variables: dict[str, str], context: dict[str, str]) -> tuple[str, list[str], list[str]]:
    """Zamenjuje {{var.x}}, {{korisnik.ime}}... Vraca (tekst, koriscene promenljive, nepoznate)."""
    used, unknown = [], []

    def repl(m):
        key = m.group(1)
        if key.startswith("var."):
            k = key[4:]
            if k in variables:
                used.append(k)
                return variables[k]
            unknown.append(key)
            return m.group(0)
        if key in context:
            return context[key]
        unknown.append(key)
        return m.group(0)

    return PLACEHOLDER_RE.sub(repl, text), sorted(set(used)), sorted(set(unknown))


def _literals(text: str) -> set[str]:
    """Brojevi, mejlovi i linkovi napisani direktno (ne kroz promenljivu)."""
    stripped = PLACEHOLDER_RE.sub(" ", text)
    stripped = CHECK_RE.sub(" ", stripped)
    found = set(URL_RE.findall(stripped)) | set(EMAIL_RE.findall(stripped))
    no_links = EMAIL_RE.sub(" ", URL_RE.sub(" ", stripped))
    for m in NUM_RE.findall(no_links):
        v = m.strip(" .,:/")
        if v and len(re.sub(r"\D", "", v)) >= 1:
            found.add(v)
    return found


def validate(draft_template: str, email_text: str, allowed_extra: list[str], forbidden: list[str],
             known_unknown: list[str]) -> list[dict]:
    """Vraca listu upozorenja {nivo, tip, poruka}."""
    warnings: list[dict] = []
    allowed_norm = normalize(email_text + " " + " ".join(allowed_extra))
    allowed_digits = re.sub(r"\D", "", email_text + " " + " ".join(allowed_extra))
    for lit in sorted(_literals(draft_template)):
        digits = re.sub(r"\D", "", lit)
        if "@" in lit or lit.startswith("http"):
            if normalize(lit) not in allowed_norm:
                warnings.append({"nivo": "upozorenje", "tip": "podatak_van_znanja",
                                 "poruka": f"Kontakt ili link \"{lit}\" nije iz znanja službe niti iz mejla korisnika."})
        elif digits and digits not in allowed_digits:
            # mali redni brojevi (1., 2.) u nabrajanju nisu sporni
            if len(digits) <= 1 and re.fullmatch(r"\d\.?", lit):
                continue
            warnings.append({"nivo": "upozorenje", "tip": "podatak_van_znanja",
                             "poruka": f"Broj \"{lit}\" nije iz znanja službe niti iz mejla korisnika. Proverite tačnost."})
    for key in known_unknown:
        warnings.append({"nivo": "upozorenje", "tip": "nepoznata_promenljiva",
                         "poruka": f"Promenljiva {{{{{key}}}}} ne postoji u znanju službe."})
    low = draft_template.lower()
    for phrase in forbidden:
        if phrase.lower() in low:
            warnings.append({"nivo": "upozorenje", "tip": "zabranjena_formulacija",
                             "poruka": f"Zabranjena formulacija: \"{phrase}\"."})
    checks = [c.strip() for c in CHECK_RE.findall(draft_template)]
    for c in checks:
        warnings.append({"nivo": "info", "tip": "provera",
                         "poruka": f"Popuniti podatak iz naplatnog sistema: {c}"})
    return warnings


def finalize_text(text: str, script: str) -> str:
    return lat_to_cyr(text) if script == "cyrillic" else text


def edit_metrics(suggested: str, final: str, thresholds: dict) -> tuple[float, str]:
    if not suggested:
        return 1.0, "napisan_iznova"
    ratio = Levenshtein.normalized_distance(suggested.strip(), final.strip())
    if ratio < thresholds.get("bez_izmena", 0.05):
        cls = "bez_izmena"
    elif ratio < thresholds.get("manje", 0.30):
        cls = "manje_izmene"
    elif ratio < thresholds.get("vece", 0.70):
        cls = "vece_izmene"
    else:
        cls = "napisan_iznova"
    return round(ratio, 4), cls
