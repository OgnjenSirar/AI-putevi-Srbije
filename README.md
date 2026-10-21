# Korisnički centar, demo sa AI podrškom

Demo informacionog sistema korisničkog centra za elektronsku naplatu putarine, na izmišljenim podacima. Prikazuje ceo tok: prijem i filtriranje pošte, otvaranje predmeta, AI predlog nadležne jedinice, prioriteta i teksta odgovora iz znanja službe, prepoznavanje potrebe za proverom u naplatnom sistemu, evidenciju korisnika sa predlozima spajanja, pripremu objava za Facebook i Instagram, izveštaje sa izvozom u Excel, Word i PDF, praćenje korišćenja predloga i troška AI.

Sve komponente su open-source. Svi podaci (korisnici, tablice, TAG brojevi, cene, adrese, kontakti) su izmišljeni.

## Servisi

| Servis | Uloga | Licenca |
|---|---|---|
| `web` | React aplikacija i nginx sa HTTPS-om, jedini port otvoren spolja (`WEB_PORT`, podrazumevano 8090) | MIT |
| `api`, `worker` | FastAPI aplikacija i pozadinski radnik (obrada pošte, AI) | MIT |
| `db` | PostgreSQL 16 sa pgvector | PostgreSQL |
| `ollama-hostfwd`, `ollama-proxy` | Pristup Ollama serveru koji već radi na hostu (Gemma 4 12B) | GPL 2, BSD |
| `ollama-init` | Jednokratno preuzima model i pravi varijantu `gemma4-kc` sa kontekstom 16k | MIT |
| `embed`, `rerank` | BGE-M3 i bge-reranker-v2-m3 na CPU (Text Embeddings Inference) | MIT, Apache 2.0 |
| `imagegen` | FLUX.2 klein 4B za AI pozadine objava | Apache 2.0 |
| `mailpit` | Prikaz poslatih odgovora (umesto pravog SMTP-a), na putanji `/mailpit/` | MIT |

Servis `imagegen` je u profilu `gpu`, koji workflow sam uključuje kada Docker vidi GPU (NVIDIA Container Toolkit). Bez toga demo radi u celosti, samo se pozadina objave ne generiše nego otprema. Opcioni profili, isključeni na deljenom serveru: `vllm` (sopstveni vLLM umesto Ollama) i `langfuse` (sopstveni Langfuse sa ClickHouse, MinIO i Redis).

## Rad na deljenom serveru

Podrazumevana podešavanja su napravljena tako da demo ne smeta projektima koji već rade na serveru:

- **Portovi**: spolja se otvara samo `WEB_PORT` (8090, HTTPS). Baza, AI servisi i Mailpit nemaju objavljene portove. Workflow pre pokretanja proverava da port nije zauzet.
- **Imena**: Compose projekat se zove `putevi-kc`, pa su kontejneri, mreža i volumeni odvojeni od ostalih (`putevi-kc-api-1` i slično).
- **Jezički model**: koristi se postojeća Ollama na hostu (127.0.0.1:11434), na isti način kao u drugim projektima (socat i nginx). `ollama-init` preuzima `gemma4:12b` samo ako ga nema i pravi `gemma4-kc`. Modeli drugih projekata se ne menjaju. Gemma 4 zahteva Ollama 0.20 ili noviju (`ollama --version`).
- **GPU**: Ollama deli karticu između projekata i model izbacuje iz memorije posle neaktivnosti (podešavanje `OLLAMA_KEEP_ALIVE` na hostu), pa prvi AI poziv posle pauze traje desetak sekundi duže. Model za slike prebacuje komponente na GPU samo tokom generisanja i treba mu oko 9 GB slobodne GPU memorije u tom trenutku. Ako je kartica zauzeta, postaviti `IMAGEGEN_OFFLOAD=sequential` (sporije, oko 2 GB).
- **RAM**: model za slike zauzima oko 16 GB RAM-a dok je učitan i posle 15 minuta bez upotrebe se izbacuje (`IMAGEGEN_IDLE_UNLOAD_MIN`). Embedding i reranker zauzimaju oko 5 GB i ograničeni su na 4 jezgra po servisu (`TEI_CPUS`).
- **Disk**: oko 45 GB (Docker slike oko 15 GB, modeli za embedding i slike oko 20 GB, Gemma 4 u Ollama oko 7 GB).
- **Langfuse**: tragovi idu u postojeći Langfuse na hostu (port 3000), u poseban projekat. Bez ključeva aplikacija radi normalno, samo bez tragova.

## Deploy preko GitHub Actions

### 1. Runner na serveru

Runner registrovan za drugi repozitorijum na ličnom GitHub nalogu ne može da preuzima poslove ovog repozitorijuma, pa se na istom serveru pravi još jedna instanca runnera, u posebnom direktorijumu i kao poseban servis. Postojeći runner se ne dira.

1. GitHub, ovaj repozitorijum, Settings, Actions, Runners, **New self-hosted runner**, Linux x64. Stranica prikazuje komande sa aktuelnom verzijom i jednokratnim tokenom (važi sat vremena).
2. Na serveru, kao isti korisnik pod kojim radi postojeći runner (mora biti u grupi `docker`):
   ```bash
   mkdir -p ~/actions-runner-putevi && cd ~/actions-runner-putevi
   # komande "Download" sa GitHub stranice (curl ... i tar xzf ...)
   ./config.sh --url https://github.com/OgnjenSirar/AI-putevi-Srbije \
     --token TOKEN_SA_STRANICE --name putevi-demo --labels putevi-demo \
     --work _work --unattended
   sudo ./svc.sh install $USER
   sudo ./svc.sh start
   sudo ./svc.sh status
   ```
3. Runner se pojavljuje u Settings, Actions, Runners kao `putevi-demo` sa statusom Idle. Workflow ga bira po labeli `putevi-demo`.

### 2. Podešavanja repozitorijuma

Settings, Secrets and variables, Actions:

| Vrsta | Naziv | Vrednost |
|---|---|---|
| Variable | `DEMO_HOST` | opciono, javna IP adresa ili domen (ako nije zadata, workflow je sam određuje) |
| Secret | `DEMO_PASSWORD` | opciono, lozinka demo naloga (najmanje 10 znakova) |
| Secret | `ADMIN_PASSWORD` | opciono, lozinka naloga `admin` |
| Variable | `WEB_PORT` | `8090` (ili drugi slobodan port) |
| Variable | `LANGFUSE_UI_URL` | `http://DEMO_HOST:3000/project/ID_PROJEKTA/traces` |
| Secret | `LANGFUSE_PUBLIC_KEY` | `pk-lf-...` iz novog Langfuse projekta |
| Secret | `LANGFUSE_SECRET_KEY` | `sk-lf-...` iz novog Langfuse projekta |
| Secret | `HF_TOKEN` | samo ako neki model na Hugging Face-u zahteva prihvatanje uslova |
| Variable | `OLLAMA_BASE_MODEL` | opciono, ako se koristi drugi model iz Ollama (podrazumevano `gemma4:12b`) |
| Variable | `CONFIG_DIR` | opciono, gde se čuva `.env` na serveru (podrazumevano `~/putevi-kc-config`) |

Langfuse ključevi: u postojećem Langfuse-u napraviti projekat (npr. `putevi-demo`), pa u njemu Settings, API Keys, Create new API keys. ID projekta se vidi u adresi stranice projekta.

### 3. Pokretanje

Push na `main` pokreće build i deploy. Pri prvom pokretanju workflow pravi `.env` sa nasumičnim lozinkama i preuzima modele (prvi deploy traje 20 do 40 minuta, sledeći nekoliko minuta). Port `WEB_PORT` treba otvoriti u firewall-u servera (security group).

Ručno pokretanje workflow-a (Actions, Deploy demo, Run workflow) nudi i opciju vraćanja demo baze na početno stanje.

## Ručno pokretanje

```bash
cp .env.example .env        # promeniti DEMO_HOST i lozinke
docker compose --env-file .env up -d --build            # bez generisanja slika
COMPOSE_PROFILES=gpu docker compose --env-file .env up -d --build   # sa generisanjem slika
docker compose ps
docker compose logs ollama-init
```

Bez GPU-a i bez Ollama (samo za pregled interfejsa): u `.env` postaviti `AI_MODE=mock` i pokrenuti bez AI servisa:

```bash
docker compose --env-file .env up -d --build db api worker web mailpit
```

## Pristup i zaštita

| Šta | Adresa |
|---|---|
| Aplikacija | `https://DEMO_HOST:8090` |
| Poslati odgovori (Mailpit) | `https://DEMO_HOST:8090/mailpit/` (samo za prijavljene) |
| Langfuse | postojeći Langfuse na serveru, projekat napravljen za demo (link i u Administraciji) |

Demo je na javnoj adresi, pa je zaštićen ovako:

- **HTTPS**: nginx pri prvom startu pravi self-signed sertifikat za `DEMO_HOST` (volumen `web-certs`, važi 825 dana). Pregledač prikazuje upozorenje jer sertifikat nije izdao poznati izdavalac, što je očekivano za demo. Zahtev preko `http://` se preusmerava na `https://`. Za pravi sertifikat: kopirati `server.crt` i `server.key` u volumen `web-certs` i napraviti u njemu prazan fajl `.sopstveni`.
- **Prijava**: bez naloga nije dostupno ništa osim ekrana za prijavu. API traži token, a slike i Mailpit nginx pušta tek posle provere sesije. Lozinke se čuvaju kao PBKDF2 heš.
- **Lozinke**: demo nalozi (`jasmina` supervizor, `ivana` operater KC, `petar` ENP, `mina` FIN, `uros` NAP, `lazar` ODR, `tijana` PRA, `nevena` KOM) koriste `DEMO_PASSWORD`, a nalog `admin` koristi `ADMIN_PASSWORD`. Obe se zadaju kao GitHub tajne ili ih workflow pri prvom deploy-u pravi nasumično i čuva samo u `.env` na serveru:
  ```bash
  grep -E '^(DEMO|ADMIN)_PASSWORD=' ~/putevi-kc-config/.env
  ```
  Lozinke ovih naloga se postavljaju pri svakom startu, pa se menjaju kroz tajne ili `.env`, ne kroz aplikaciju.
- **Lični nalozi**: admin u Administraciji, Nalozi, pravi naloge za kolege ili klijenta (lozinka najmanje 10 znakova). Ti nalozi se ne menjaju pri deploy-u.
- **Ograničenja**: najviše 10 pokušaja prijave u minuti po IP adresi, API dokumentacija je isključena, baza i AI servisi nisu dostupni spolja.
- **Logovi**: repozitorijum je javan, pa workflow ne ispisuje ni adresu servera ni lozinke. Posle svakog deploy-a proverava da bez prijave nema pristupa (napomena „Zastita pristupa” uz run).

## Predlog scenarija za prezentaciju

1. Prijava kao `jasmina` (lozinka iz `DEMO_PASSWORD`). U listi predmeta su obraćanja razvrstana po prioritetu i roku. Isprekidana linija označava AI predlog rasporeda, puna linija potvrđen raspored.
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

- **AI ne radi, Administracija prikazuje jezički model kao nedostupan**: `docker compose -p putevi-kc logs ollama-init`. Najčešći uzroci su stara verzija Ollama na hostu (Gemma 4 traži 0.20 ili noviju) ili Ollama koja ne radi (`systemctl status ollama`, `curl 127.0.0.1:11434/api/version`). Ako se Ollama ne može ažurirati, u `OLLAMA_BASE_MODEL` upisati model koji već postoji na serveru (`ollama list`), npr. `gemma3:12b`.
- **Odgovori su spori**: drugi projekti istovremeno koriste istu Ollama i GPU. Ollama obrađuje zahteve redom, pa se vreme odgovora produžava dok drugi projekat radi.
- **Nedovoljno GPU memorije pri generisanju slika**: postaviti `IMAGEGEN_OFFLOAD=sequential` (sporije, ali troši najmanje memorije).
- **Sopstveni vLLM umesto Ollama** (samo ako GPU nije deljen): `docker compose --profile vllm up -d llm`, a u `.env` postaviti `LLM_BASE_URL=http://llm:8000/v1` i `LLM_SERVED_NAME=gemma-4`.
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
