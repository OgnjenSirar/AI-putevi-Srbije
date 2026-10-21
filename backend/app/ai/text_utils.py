"""Pomocne funkcije za srpski tekst: pismo, transliteracija, normalizacija, ciscenje prepiske, entiteti."""
import re
import unicodedata

CYR_TO_LAT = {
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Ђ": "Đ", "Е": "E", "Ж": "Ž", "З": "Z", "И": "I",
    "Ј": "J", "К": "K", "Л": "L", "Љ": "Lj", "М": "M", "Н": "N", "Њ": "Nj", "О": "O", "П": "P", "Р": "R",
    "С": "S", "Т": "T", "Ћ": "Ć", "У": "U", "Ф": "F", "Х": "H", "Ц": "C", "Ч": "Č", "Џ": "Dž", "Ш": "Š",
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ђ": "đ", "е": "e", "ж": "ž", "з": "z", "и": "i",
    "ј": "j", "к": "k", "л": "l", "љ": "lj", "м": "m", "н": "n", "њ": "nj", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "ћ": "ć", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "č", "џ": "dž", "ш": "š",
}

LAT_DIGRAPHS = [("Lj", "Љ"), ("LJ", "Љ"), ("lj", "љ"), ("Nj", "Њ"), ("NJ", "Њ"), ("nj", "њ"),
                ("Dž", "Џ"), ("DŽ", "Џ"), ("dž", "џ")]
LAT_SINGLE = {v: k for k, v in CYR_TO_LAT.items() if len(v) == 1}

# Tokeni koji ostaju u latinici i pri prevodu na cirilicu
_PROTECT = re.compile(
    r"(https?://\S+|[\w.+-]+@[\w-]+\.[\w.-]+|\{\{[^}]+\}\}|\[PROVERA:[^\]]*\]|TAG-\d+|"
    r"\b[A-ZČĆŠŽĐ]{2}\s?\d{3,4}-?[A-ZČĆŠŽĐ]{2}\b|\b(?:KC|ENP|FIN|NAP|ODR|PRA|KOM|EN)-[\w-]+|\bI{1,3}A?\b|\bIV\b|\bTAG\b|\bENP\b|\bAPR\b|\bPIB\b)"
)


def detect_script(text: str) -> str:
    cyr = sum(1 for ch in text if "Ѐ" <= ch <= "ӿ")
    lat = sum(1 for ch in text if ch.isalpha() and ch.isascii())
    if cyr > lat * 0.5 and cyr > 10:
        return "cyrillic"
    return "latin"


def cyr_to_lat(text: str) -> str:
    return "".join(CYR_TO_LAT.get(ch, ch) for ch in text)


def lat_to_cyr(text: str) -> str:
    """Prevodi latinicu u cirilicu, a URL-ove, mejlove, tablice, sifre i promenljive ostavlja netaknute."""
    parts = []
    last = 0
    for m in _PROTECT.finditer(text):
        parts.append(_lat_to_cyr_plain(text[last:m.start()]))
        parts.append(m.group(0))
        last = m.end()
    parts.append(_lat_to_cyr_plain(text[last:]))
    return "".join(parts)


def _lat_to_cyr_plain(text: str) -> str:
    for a, b in LAT_DIGRAPHS:
        text = text.replace(a, b)
    return "".join(LAT_SINGLE.get(ch, ch) for ch in text)


def strip_diacritics(text: str) -> str:
    text = text.replace("đ", "dj").replace("Đ", "Dj")
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize(text: str) -> str:
    """Za pretragu i pravila: latinica, bez dijakritika, mala slova."""
    return re.sub(r"\s+", " ", strip_diacritics(cyr_to_lat(text)).lower()).strip()


_QUOTE_MARKERS = [
    re.compile(r"^-{2,}\s*(Original Message|Originalna poruka|Prosleđena poruka|Forwarded message)", re.I),
    re.compile(r"^(On|Dana|Am|Le)\s.+(wrote|napisao|napisala|je napisao|schrieb|a écrit):\s*$", re.I),
    re.compile(r"^(From|Od|Šalje|Sent|Poslato):\s", re.I),
]


def clean_email_body(body: str) -> str:
    """Uklanja citiranu prepisku (> linije, 'Dana ... je napisao:', originalne poruke)."""
    out = []
    for line in body.splitlines():
        stripped = line.strip()
        if any(p.match(stripped) for p in _QUOTE_MARKERS):
            break
        if stripped.startswith(">"):
            continue
        out.append(line.rstrip())
    text = "\n".join(out).strip()
    return re.sub(r"\n{3,}", "\n\n", text)


PLATE_RE = re.compile(r"\b([A-ZČĆŠŽĐ]{2})\s?(\d{3,4})[-\s]?([A-ZČĆŠŽĐ]{2})\b")
TAG_RE = re.compile(r"\bTAG-?\s?(\d{8})\b", re.I)
PHONE_RE = re.compile(r"(?:\+381|\b0)\s?\(?\d{2}\)?[\s/-]?\d{3}[\s-]?\d{3,4}\b")
AMOUNT_RE = re.compile(r"\b(\d{1,3}(?:[.\s]\d{3})+|\d+)(?:,\d{2})?\s?(?:din(?:ara)?|RSD|динара)\b", re.I)
DATE_RE = re.compile(r"\b\d{1,2}\.\s?(?:\d{1,2}\.(?:\s?\d{4}\.?)?|(?:januar|februar|mart|april|maj|jun|jul|avgust|septemb|oktob|novemb|decemb)\w*)", re.I)
STATIONS = ["Vrčin", "Bubanj Potok", "Beograd", "Niš", "Preševo", "Batočina", "Leskovac", "Novi Sad", "Subotica",
            "Horgoš", "Ćuprija", "Jagodina", "Pojate", "Kragujevac", "Ub", "Šabac", "Doljevac", "Vranje"]


def normalize_plate(p: str) -> str:
    return re.sub(r"[\s-]", "", p.upper())


def extract_entities(text: str) -> dict:
    lat = cyr_to_lat(text)
    plates = sorted({f"{a} {b}-{c}" for a, b, c in PLATE_RE.findall(lat)})
    tags = sorted({f"TAG-{t}" for t in TAG_RE.findall(lat)})
    phones = sorted({re.sub(r"\s+", " ", p).strip() for p in PHONE_RE.findall(lat)})
    amounts = sorted({m.group(0) for m in AMOUNT_RE.finditer(lat)})
    dates = sorted({m.group(0).strip() for m in DATE_RE.finditer(lat)})
    stations = [s for s in STATIONS if normalize(s) in normalize(lat)]
    return {"tablice": plates, "tagovi": tags, "telefoni": phones, "iznosi": amounts,
            "datumi": dates, "naplatne_stanice": stations}


def guess_language(text: str) -> str:
    t = normalize(text)
    en = len(re.findall(r"\b(the|and|toll|please|thank|you|my|is|for|hello|dear)\b", t))
    de = len(re.findall(r"\b(und|die|der|wir|sehr|geehrte|maut|unser|mit|ist)\b", t))
    sr = len(re.findall(r"\b(je|da|sam|na|se|i|u|za|postovani|molim|hvala)\b", t))
    best = max([("sr", sr), ("en", en), ("de", de)], key=lambda x: x[1])
    return best[0] if best[1] > 0 else "sr"
