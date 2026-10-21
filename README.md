# Korisnički centar, demo sa AI podrškom

Demo informacionog sistema korisničkog centra za elektronsku naplatu putarine, na izmišljenim podacima. Prikazuje ceo tok: prijem i filtriranje pošte, otvaranje predmeta, AI predlog nadležne jedinice, prioriteta i teksta odgovora iz znanja službe, prepoznavanje potrebe za proverom u naplatnom sistemu, evidenciju korisnika sa predlozima spajanja, pripremu objava za Facebook i Instagram, izveštaje sa izvozom u Excel, Word i PDF, praćenje korišćenja predloga i troška AI.

Sve komponente su open-source. Svi podaci (korisnici, tablice, TAG brojevi, cene, adrese, kontakti) su izmišljeni.

## Servisi

| Servis | Uloga | Licenca |
|---|---|---|
| `web` | React aplikacija i nginx (port `WEB_PORT`, podrazumevano 8080) | MIT |
| `api`, `worker` | FastAPI aplikacija i pozadinski radnik (obrada pošte, AI) | MIT |
| `db` | PostgreSQL 16 sa pgvector | PostgreSQL |
| `llm` | vLLM sa modelom Gemma 4 12B (4 bita) | Apache 2.0 |
| `embed`, `rerank` | BGE-M3 i bge-reranker-v2-m3 na CPU (Text Embeddings Inference) | MIT, Apache 2.0 |
| `imagegen` | FLUX.2 klein 4B za AI pozadine objava | Apache 2.0 |
| `mailpit` | Prikaz poslatih odgovora (umesto pravog SMTP-a) | MIT |
| `langfuse-*`, `clickhouse`, `minio`, `redis` | Langfuse, tragovi i kvalitet AI poziva (port `LANGFUSE_PORT`, podrazumevano 3001) | MIT |

Na kartici L4 (24 GB) jezički model i model za slike dele GPU: vLLM zauzima oko polovine memorije, a model za slike se drži u RAM-u i komponente prebacuje na GPU samo tokom generisanja.

## Zahtevi servera

- Linux, Docker sa Compose dodatkom
- NVIDIA drajver i NVIDIA Container Toolkit (`docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi` mora da radi)
- 32 GB RAM ili više, 120 GB slobodnog diska za modele i slike
- Izlaz na internet pri prvom pokretanju (preuzimanje modela sa Hugging Face-a i Docker slika)

## Deploy preko GitHub Actions

1. Na demo serveru registrovati self-hosted runner za ovaj repozitorijum. Korisnik pod kojim radi runner mora biti u grupi `docker`.
2. U `.github/workflows/deploy.yml` proveriti labelu u `runs-on` (podrazumevano `[self-hosted, linux]`).
3. U podešavanjima repozitorijuma (Settings, Secrets and variables, Actions) po potrebi dodati:
   - promenljivu `DEMO_HOST`: IP adresa ili domen servera kako ga vide korisnici
   - promenljivu `WEB_PORT`: port aplikacije (podrazumevano 8080)
   - promenljivu `CONFIG_DIR`: gde se čuva `.env` na serveru (podrazumevano `~/kc-demo-config`)
   - tajnu `HF_TOKEN`: samo ako neki model na Hugging Face-u zahteva prihvatanje uslova
4. Push na `main` pokreće build i deploy. Pri prvom pokretanju workflow pravi `.env` sa nasumičnim lozinkama.

Ručno pokretanje workflow-a (Actions, Deploy demo, Run workflow) nudi i opciju vraćanja demo baze na početno stanje.

## Ručno pokretanje

```bash
cp .env.example .env        # promeniti DEMO_HOST i lozinke
docker compose --env-file .env up -d --build
docker compose ps
```

Bez GPU-a (samo za pregled interfejsa): u `.env` postaviti `AI_MODE=mock` i pokrenuti bez AI servisa:

```bash
docker compose --env-file .env up -d --build db api worker web mailpit
```

## Pristup

| Šta | Adresa |
|---|---|
| Aplikacija | `http://DEMO_HOST:8080` |
| Poslati odgovori (Mailpit) | `http://DEMO_HOST:8080/mailpit/` |
| Langfuse | `http://DEMO_HOST:3001`, nalog iz `.env` (`LANGFUSE_INIT_USER_EMAIL` i `LANGFUSE_INIT_USER_PASSWORD`) |

Demo nalozi (lozinka za sve je `demo`): `jasmina` (supervizor), `ivana` (operater KC), `petar` (ENP), `mina` (FIN), `uros` (NAP), `lazar` (ODR), `tijana` (PRA), `nevena` (KOM), `admin`.

## Predlog scenarija za prezentaciju

1. Prijava kao `jasmina`. U listi predmeta su obraćanja razvrstana po prioritetu i roku. Isprekidana linija označava AI predlog rasporeda, puna linija potvrđen raspored.
2. Otvoriti predmet „TAG nije očitan na naplatnoj stanici Vrčin”: prepiska, AI razvrstavanje sa obrazloženjem, provera u naplatnom sistemu sa izdvojenim tablicama i TAG brojem, predlog odgovora sa oznakom `[PROVERA]`.
3. Uneti rezultat provere, zameniti oznaku u tekstu, poslati odgovor. Sistem beleži koliko je predlog izmenjen. Odgovor se vidi u Mailpit-u, sa očuvanom prepiskom.
4. Predmet „POSLEDNJI PUT VAS UPOZORAVAM”: pravilo za pretnje podiže prioritet nezavisno od modela.
5. Predmeti na ćirilici, engleskom i nemačkom: odgovor se piše na jeziku i pismu korisnika.
6. Pošta, Simulacija prijema: poslati test mejl (npr. „Pokušaj manipulacije AI-jem”) i pokazati kako validator označava zabranjene formulacije i brojeve koji nisu iz znanja službe.
7. Korisnici: predlozi za spajanje duplih zapisa (ime bez dijakritika, ćirilica, isti telefon ili tablica).
8. Znanje službe: izmena promenljive (npr. depozit za TAG) odmah menja sve nove predloge, uz istoriju izmena.
9. Društvene mreže: opis objave, AI tekst i polja šablona, AI pozadina, odobrenje i simulirana objava sa tačnim pozivima Meta Graph API-ja.
10. Izveštaji: rad službe, tačnost AI predloga, udeo odgovora bez većih izmena, trošak AI po funkciji, izvoz u Excel, Word i PDF.

## Šta je u demou simulirano

- Prijem pošte ide preko ekrana „Simulacija prijema” umesto službenog IMAP ili Microsoft 365 sandučeta.
- Naplatni sistem ne postoji: AI prepoznaje šta treba proveriti, a operater upisuje rezultat. Stanja računa u evidenciji korisnika su izmišljena.
- Objava na Facebook i Instagram pravi tačne zahteve, ali ih ne šalje.
- Tekst iz priloga je za početne mejlove unapred pripremljen, a za nove PDF priloge izdvaja se automatski.
- Interna cena AI (RSD po milionu tokena) podešava se u Administraciji.

## Rešavanje problema

- **vLLM ne podiže model** (`docker compose logs llm`): proveriti verziju vLLM slike (`VLLM_IMAGE`) i model (`LLM_MODEL_ID`). Alternativa je Ollama: `docker compose stop llm`, zatim `docker compose --profile ollama up -d ollama`, a u `.env` postaviti `LLM_BASE_URL=http://ollama:11434/v1` i `LLM_SERVED_NAME=gemma4:12b`, pa ponovo pokrenuti `api` i `worker`.
- **Nedovoljno GPU memorije pri generisanju slika**: smanjiti `VLLM_GPU_UTIL` na 0.45 ili postaviti `IMAGEGEN_OFFLOAD=sequential` (sporije, ali troši najmanje memorije).
- **Model zahteva prihvatanje uslova na Hugging Face-u**: prihvatiti uslove na stranici modela i dodati `HF_TOKEN`.
- **AI je u rezervnom režimu**: dok se modeli preuzimaju, radnik čeka do sat vremena pre nego što obradi mejlove pravilima. Stanje servisa se vidi u Administraciji. Svaki predmet se može ponovo analizirati dugmetom „Nova AI analiza”.

## Razvoj bez Docker-a

```bash
# backend (potreban PostgreSQL sa pgvector)
cd backend && pip install -r requirements.txt && playwright install chromium
AI_MODE=mock DATABASE_URL=postgresql+psycopg://demo:demo@localhost:5432/kcdemo MEDIA_DIR=/tmp/media uvicorn app.main:app --port 8000
AI_MODE=mock DATABASE_URL=postgresql+psycopg://demo:demo@localhost:5432/kcdemo python -m app.worker

# frontend
cd frontend && npm install && npm run dev
```
