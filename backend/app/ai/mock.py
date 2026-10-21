"""Rezervni (mock) rezim: deterministicka pravila koja oponasaju izlaz LLM-a.
Koristi se za testiranje bez GPU-a i kao rezerva kada LLM nije dostupan."""
import re

from .text_utils import extract_entities, guess_language, normalize

SPAM_WORDS = ["garant", "lottery", "winner", "prize", "crypto", "bitcoin", "investment", "kliknite ovde",
              "seo", "prvo mesto na google", "300%", "ponuda za saradnju", "povoljnu isporuku", "besplatnu dostavu"]
TECH_WORDS = ["undeliverable", "delivery status", "automatski odgovor", "out of office", "godisnjem odmoru",
              "mailer-daemon", "postmaster", "odjavite se", "unsubscribe", "couldn't be delivered"]


def filter_mock(subject: str, body: str, from_addr: str) -> dict:
    t = normalize(f"{subject} {body} {from_addr}")
    if any(w in t for w in TECH_WORDS):
        return {"klasa": "tehnicka", "razlog": "Automatska ili sistemska poruka"}
    if any(w in t for w in SPAM_WORDS):
        return {"klasa": "spam", "razlog": "Komercijalna ponuda ili sumnjiv sadržaj nevezan za rad službe"}
    return {"klasa": "regularno", "razlog": "Obraćanje korisnika"}


def analyze_mock(subject: str, body: str, from_name: str, categories: list[dict]) -> dict:
    t = normalize(f"{subject}\n{body}")
    scores = []
    for c in categories:
        s = sum(1 for kw in c["keywords"] if normalize(kw) in t)
        scores.append((s, c))
    scores.sort(key=lambda x: x[0], reverse=True)
    best_score, best = scores[0]
    if best_score == 0:
        best = next(c for c in categories if c["code"] == "opste_informacije")
    extra = [c["code"] for s, c in scores[1:4] if s >= 1 and s >= best_score - 1 and c["code"] != best["code"]][:2]
    lang = guess_language(f"{subject} {body}")
    ent = extract_entities(f"{subject}\n{body}")
    tone = "neutralan"
    if re.search(r"(videcete sta ce biti|doci cu licno|upozoravam|posledn\w* put)", t):
        tone = "preteci"
    elif re.search(r"(dosta mi je|nezadovolj|sramota|bezobraz)", t):
        tone = "ljut"
    elif re.search(r"(pohval|zahvaljujem|hvala vam)", t):
        tone = "zahvalan"
    checks = []
    if best["needs_check"]:
        mapping = {"tag_neispravan": ["status_taga", "prolasci"], "dopuna_racuna": ["stanje_racuna"],
                   "dupla_naplata": ["prolasci"], "kategorija_vozila": ["obracun", "prolasci"],
                   "povracaj_novca": ["povracaj", "stanje_racuna"], "raskid_ugovora": ["povracaj", "stanje_racuna"],
                   "fakture": ["fakture"], "naknadno_placanje": ["prolasci"], "prekrsaj": ["prolasci"],
                   "tag_zamena": ["status_taga"]}
        checks = mapping.get(best["code"], ["prolasci"])
    what = ""
    if checks:
        bits = []
        if ent["datumi"]:
            bits.append("datum " + ", ".join(ent["datumi"]))
        if ent["naplatne_stanice"]:
            bits.append("stanica " + ", ".join(ent["naplatne_stanice"]))
        if ent["tablice"]:
            bits.append("tablica " + ", ".join(ent["tablice"]))
        if ent["tagovi"]:
            bits.append(", ".join(ent["tagovi"]))
        if ent["iznosi"]:
            bits.append("iznos " + ", ".join(ent["iznosi"]))
        what = "Proveriti u naplatnom sistemu: " + ("; ".join(bits) if bits else "podatke o korisniku i transakcijama")
        what = what.replace(";", ",")
    return {
        "kategorija": best["code"],
        "dodatne_kategorije": extra if len(re.findall(r"^\s*\d\.", body, re.M)) >= 2 else [],
        "jedinica": best["unit"],
        "prioritet": best["priority"],
        "obrazlozenje": f"Rezervni režim (pravila): prepoznata tema \"{best['label']}\" na osnovu ključnih reči, uobičajeno u nadležnosti jedinice {best['unit']}.",
        "pouzdanost": round(min(0.95, 0.45 + 0.15 * best_score), 2),
        "jezik": lang if lang in ("sr", "en", "de") else "ostalo",
        "sazetak": f"{best['label']}.",
        "ton": tone,
        "vise_pitanja": len(re.findall(r"^\s*\d\.", body, re.M)) >= 2,
        "entiteti": {"ime": from_name, "tablice": ent["tablice"], "tagovi": ent["tagovi"], "telefoni": ent["telefoni"],
                     "datumi": ent["datumi"], "iznosi": ent["iznosi"], "naplatne_stanice": ent["naplatne_stanice"]},
        "provera_naplatni_sistem": {"potrebna": bool(checks), "tipovi": checks, "sta_proveriti": what},
    }


def draft_mock(templates: list, language: str) -> dict:
    if not templates:
        return {"odgovor": "Poštovani/a {{korisnik.ime}},\n\nzahvaljujemo na obraćanju. Vaš zahtev je evidentiran pod brojem {{predmet.broj}} i biće obrađen u najkraćem roku.",
                "korisceni_obrasci": [], "napomena_za_operatera": "Nije pronađen odgovarajući obrazac, proverite odgovor."}
    if language in ("en", "de"):
        en = next((t for t in templates if t.code.startswith("EN-")), None)
        if en:
            return {"odgovor": en.body, "korisceni_obrasci": [en.code],
                    "napomena_za_operatera": "Korisnik piše na stranom jeziku, proverite prevod i podatke o prolasku."}
        body = ("Dear {{korisnik.ime}},\n\nthank you for contacting us. Your request has been registered under number {{predmet.broj}}. "
                "Our team will review it and reply shortly. For urgent questions please call {{var.kontakt.call_centar}}.")
        return {"odgovor": body, "korisceni_obrasci": [templates[0].code],
                "napomena_za_operatera": "Rezervni režim ne prevodi obrasce, dopunite odgovor na jeziku korisnika."}
    t = templates[0]
    note = "Zameniti oznake [PROVERA] podacima iz naplatnog sistema." if "[PROVERA" in t.body else "Proveriti da li odgovor pokriva sva pitanja korisnika."
    return {"odgovor": t.body, "korisceni_obrasci": [t.code], "napomena_za_operatera": note}


def social_mock(brief: str, templates: list[dict]) -> dict:
    n = normalize(brief)
    code = "radovi"
    if any(w in n for w in ["cena", "popust", "tag", "dopun", "portal", "naplat"]):
        code = "naplata"
    if any(w in n for w in ["radov", "zatvar", "traka", "sanacij", "obilaz"]):
        code = "radovi"
    if any(w in n for w in ["praznik", "nova godina", "bozic", "uskrs", "sretan", "srecn"]):
        code = "praznik"
    if any(w in n for w in ["upozor", "magl", "sneg", "led", "nevrem", "bezbedn"]):
        code = "obavestenje"
    tpl = next((t for t in templates if t["code"] == code), templates[0])
    sentences = [s.strip().rstrip(".") for s in re.split(r"(?<=[.!?])\s+(?=[A-ZČĆŠŽĐ])", brief) if s.strip()]
    first = sentences[0] if sentences else "Obaveštenje"
    period = ""
    m = re.search(r"od\s+(\d{1,2}\.?)\s*(?:\w+\s+)?do\s+(\d{1,2}\.?\s*\w+)", brief, re.I)
    if m:
        period = f"{m.group(1).rstrip('.')}. - {m.group(2)}"
    loc = ""
    m = re.search(r"((?:autoput\w*|deonic\w*)\s+[A-ZČĆŠŽĐ0-9][\w-]*(?:\s+kod\s+[A-ZČĆŠŽĐ]\w+)?)", brief)
    if m:
        loc = m.group(1)
    title = re.split(r"\s+(?:od|kod)\s+", first)[0]
    rest = " ".join(s + "." for s in sentences[1:]) or brief
    fields = {}
    for f in tpl["fields"]:
        if f["type"] == "choice":
            fields[f["key"]] = f["options"][0]
        elif f["key"] == "naslov":
            fields[f["key"]] = title[: f["max"]]
        elif f["key"] == "period":
            fields[f["key"]] = period[: f["max"]]
        elif f["key"] == "deonica":
            fields[f["key"]] = loc[: f["max"]]
        elif f["key"] in ("istaknuto",):
            m2 = re.search(r"\d+\s?%", brief)
            fields[f["key"]] = (m2.group(0) + " popusta") if m2 else ""
        elif f["key"] == "poziv":
            fields[f["key"]] = "portal.demo-kc.rs"
        elif f["key"] == "potpis":
            fields[f["key"]] = "Vaš Korisnički centar"
        elif f["key"] == "napomena":
            fields[f["key"]] = ""
        else:
            fields[f["key"]] = rest[: f["max"]].rsplit(" ", 1)[0] if len(rest) > f["max"] else rest
    return {
        "sablon": tpl["code"],
        "polja": fields,
        "tekst_facebook": brief.strip(),
        "tekst_instagram": brief.strip()[:300] + "\n\n#putarina #saobracaj #info",
        "alt_tekst": f"Grafičko obaveštenje: {title}",
        "prompt_slike": "wide empty highway at dusk, soft light, realistic photo, no text, no people, no logos",
    }
