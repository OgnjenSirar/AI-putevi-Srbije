"""Izmisljeni mejlovi za demo. Polje "expected" sluzi samo za evaluaciju tacnosti AI predloga."""

INBOX = [
    dict(
        from_name="Marko Petrović", from_addr="marko.petrovic@example.rs", hours_ago=20,
        subject="TAG nije očitan na naplatnoj stanici Vrčin",
        body="""Poštovani,

juče, 19. oktobra oko 17:40, prolazio sam kroz naplatnu stanicu Vrčin u pravcu Niša. Rampa se nije podigla iako imam TAG uređaj, pa sam morao da platim gotovinom 640 dinara. Na računu imam dovoljno sredstava.

Registarska oznaka vozila je BG 123-AB, broj TAG-a TAG-40112233.

Molim vas da proverite šta se desilo i da mi vratite novac.

Srdačan pozdrav,
Marko Petrović
064 111 2233""",
        expected=("tag_neispravan", "ENP"),
    ),
    dict(
        from_name="Jelena Jovanović", from_addr="jelena.jovanovic@example.rs", hours_ago=26,
        subject="Uplata nije legla na pretplatni račun",
        body="""Dobar dan,

17.10. sam preko e-bankinga uplatila 3.000 dinara na pretplatni račun za TAG-40112234 (vozilo NS 456-CD). Prošla su četiri dana, a na portalu i dalje vidim stanje od 120 dinara.

U prilogu vam šaljem potvrdu o uplati. Molim vas da proverite gde je novac.

Hvala,
Jelena Jovanović""",
        attachments=[dict(name="potvrda_uplate.pdf", type="application/pdf", size=48211,
                          text="POTVRDA O IZVRŠENOM PLAĆANJU\nNalogodavac: Jelena Jovanović, Novi Sad\nIznos: 3.000,00 RSD\nDatum izvršenja: 17.10.2026.\nSvrha: Dopuna TAG računa TAG-40112234\nStatus: Izvršeno")],
        expected=("dopuna_racuna", "FIN"),
    ),
    dict(
        from_name="Ana Stojanović", from_addr="ana.stojanovic@example.rs", hours_ago=30,
        subject="Kako da dobijem TAG uređaj?",
        body="""Poštovani,

kupila sam novi automobil i želela bih da koristim TAG. Šta je potrebno od dokumentacije, koliko košta i da li u Kragujevcu postoji mesto gde mogu da ga preuzmem?

Unapred zahvalna,
Ana Stojanović""",
        expected=("tag_izdavanje", "ENP"),
    ),
    dict(
        from_name="Snežana Obradović", from_addr="nabavka@agrosumadija.example", hours_ago=6,
        subject="TAG uređaji za dva kamiona - Agro Šumadija d.o.o.",
        body="""Poštovani,

naša firma Agro Šumadija d.o.o. (PIB 100000002) planira da za dva teretna vozila nabavi TAG uređaje. Molimo vas da nam pošaljete spisak potrebne dokumentacije i informaciju o depozitu, kao i da li je moguće da oba vozila koriste isti račun.

S poštovanjem,
Snežana Obradović
Služba nabavke""",
        expected=("tag_izdavanje", "ENP"),
    ),
    dict(
        from_name="Никола Илић", from_addr="nikola.ilic@example.rs", hours_ago=14,
        subject="Двострука наплата 14. октобра",
        body="""Поштовани,

на изводу са претплатног рачуна видим да ми је пролазак кроз наплатну станицу Ниш 14. октобра наплаћен два пута, обе трансакције по 1.960 динара, у размаку од два минута. Возило је NI 789-EF, ТАГ TAG-40112235.

Молим вас да проверите и да ми вратите погрешно наплаћен износ.

Поздрав,
Никола Илић""",
        expected=("dupla_naplata", "NAP"),
    ),
    dict(
        from_name="Milan Đorđević", from_addr="milan.djordjevic@example.rs", hours_ago=40,
        subject="Naplaćena pogrešna kategorija za kombi",
        body="""Poštovani,

vozim putnički kombi (BG 345-IJ) i kod vas je registrovan u kategoriji I. Međutim, prilikom poslednja tri prolaska kroz Bubanj Potok naplaćena mi je kategorija II. Kombi ima dve osovine i nije viši od propisanog.

Molim vas da ispravite kategoriju i vratite razliku.

Milan Đorđević""",
        expected=("kategorija_vozila", "NAP"),
    ),
    dict(
        from_name="Ivana Marković", from_addr="ivana.markovic@example.rs", hours_ago=50,
        subject="Prodala sam auto - raskid ugovora",
        body="""Poštovani,

prodala sam automobil CA 567-KL i više mi ne treba TAG. Kako mogu da raskinem ugovor i da mi vratite preostali iznos sa računa i depozit? Živim u Čačku, da li mogu TAG da pošaljem poštom?

Pozdrav,
Ivana Marković""",
        expected=("raskid_ugovora", "ENP"),
    ),
    dict(
        from_name="Stefan Nikolić", from_addr="stefan.nikolic@example.rs", hours_ago=18,
        subject="Promena tablica",
        body="""Pozdrav,

promenio sam tablice na vozilu, stare su BG 678-MN, a nove BG 111-ZZ. Šta treba da uradim da bi TAG i dalje radio bez problema?

Stefan""",
        expected=("promena_podataka", "ENP"),
    ),
    dict(
        from_name="Milica Pavlović", from_addr="milica.p@example.rs", hours_ago=5,
        subject="cena putarine",
        body="""Postovani, koliko kosta putarina od Beograda do Novog Sada za auto i da li ima popust ako imam tag? Hvala""",
        expected=("cenovnik", "KC"),
    ),
    dict(
        from_name="Dušan Popović", from_addr="dusan.popovic@example.rs", hours_ago=9,
        subject="Udarne rupe na izlazu sa autoputa",
        body="""Poštovani,

na izlazu sa autoputa kod petlje Ub u smeru Valjeva već nedelju dana postoje dve velike udarne rupe u desnoj traci. Noću se ne vide i vozači naglo koče. Molim vas da to sanirate pre nego što neko strada.

Dušan Popović""",
        expected=("stanje_puteva", "ODR"),
    ),
    dict(
        from_name="Marija Lazić", from_addr="marija.lazic@example.rs", hours_ago=33,
        subject="Pukla guma zbog rupe na autoputu - zahtev za naknadu",
        body="""Poštovani,

20. oktobra oko 21h, na autoputu kod Subotice u smeru Novog Sada, naletela sam na rupu u kolovozu i pukle su mi obe desne gume, a oštećen je i felna. Policija je izašla na uviđaj. Šaljem fotografije i račun iz vulkanizerske radnje.

Kako da podnesem zahtev za naknadu štete?

Marija Lazić
SU 112-ST""",
        attachments=[
            dict(name="guma_1.jpg", type="image/jpeg", size=1843000, text="[fotografija oštećene gume, prednja desna]"),
            dict(name="racun_vulkanizer.pdf", type="application/pdf", size=91200, text="RAČUN br. 452/2026\nZamena 2 pneumatika 205/55 R16 i popravka felne\nUkupno: 28.400,00 RSD"),
        ],
        expected=("ostecenje_vozila", "PRA"),
    ),
    dict(
        from_name="Vladimir Stanković", from_addr="vladimir.stankovic@example.rs", hours_ago=22,
        subject="Neljubazan radnik na naplatnoj stanici",
        body="""Poštovani,

danas oko 8 ujutru na naplatnoj stanici Leskovac centar radnik u drugoj traci mi se obratio veoma bezobrazno kada sam pitao za potvrdu o plaćanju. Smatram da takvo ponašanje nije prihvatljivo.

Vladimir Stanković""",
        expected=("prituzba_osoblje", "NAP"),
    ),
    dict(
        from_name="Tamara Ristić", from_addr="tamara.ristic@example.rs", hours_ago=60,
        subject="Pohvala za koleginicu iz korisničkog centra",
        body="""Poštovani,

želim da pohvalim vašu koleginicu iz korisničkog centra u Zrenjaninu koja mi je juče strpljivo objasnila sve oko dopune i portala. Izuzetno profesionalno i ljubazno!

Tamara Ristić""",
        expected=("pohvala", "KC"),
    ),
    dict(
        from_name="Udruženje Građanski nadzor", from_addr="kancelarija@gradjanskinadzor.example", hours_ago=4,
        subject="Zahtev za pristup informacijama od javnog značaja",
        body="""Poštovani,

na osnovu Zakona o slobodnom pristupu informacijama od javnog značaja, tražimo sledeće informacije:

1. Ukupan broj prolazaka kroz naplatnu stanicu Beograd u 2025. godini, po kategorijama vozila.
2. Ukupan iznos naplaćene putarine na toj stanici u 2025. godini.
3. Broj podnetih reklamacija korisnika ENP sistema u 2025. godini.

Informacije molimo dostaviti elektronskom poštom.

S poštovanjem,
Udruženje Građanski nadzor""",
        expected=("pristup_informacijama", "PRA"),
    ),
    dict(
        from_name="Ivan Marjanović, Dnevni glasnik", from_addr="redakcija@dnevniglasnik.example", hours_ago=2,
        subject="Upit za tekst: gužve na naplatnim stanicama tokom vikenda",
        body="""Poštovani,

pripremam tekst o gužvama na naplatnim stanicama prošlog vikenda, kada su vozači na stanici Beograd čekali i do 40 minuta. Zanima nas:

- koliko je traka bilo otvoreno i zašto,
- da li planirate dodatne mere za predstojeće praznike.

Tekst izlazi sutra, pa bih vas molio za izjavu danas do 15 časova.

Ivan Marjanović
novinar, Dnevni glasnik""",
        expected=("medijski_upit", "KOM"),
    ),
    dict(
        from_name="Rade Vukić", from_addr="rade.vukic@example.rs", hours_ago=3,
        subject="POSLEDNJI PUT VAS UPOZORAVAM",
        body="""Treći put pišem zbog novca koji ste mi skinuli sa računa bez razloga. Niko mi ne odgovara. Ako mi do petka ne vratite novac, doći ću lično u vašu kancelariju i videćete šta će biti. Dosta mi je vašeg bahaćenja.

Rade Vukić, KG 999-RV""",
        expected=("povracaj_novca", "FIN"),
    ),
    dict(
        from_name="Nemanja Jovanović", from_addr="nemanja.j@example.rs", hours_ago=44,
        subject="TAG u Makedoniji i Crnoj Gori",
        body="""Poštovani,

idem na more preko Severne Makedonije, a kasnije i u Crnu Goru. Da li mogu da koristim svoj TAG (TAG-40112249) i u tim zemljama i kako se naplaćuje?

Hvala,
Nemanja""",
        expected=("interoperabilnost", "ENP"),
    ),
    dict(
        from_name="John Miller", from_addr="john.miller@example.co.uk", hours_ago=12,
        subject="Unpaid toll - card not accepted",
        body="""Hello,

I drove through the toll station Preševo on 18 October in a rental car (UK plate LK19 ABC). The machine did not accept my card and the staff gave me a slip saying I can pay later. How can I pay the outstanding toll? I am leaving Serbia on Friday.

Kind regards,
John Miller""",
        expected=("naknadno_placanje", "NAP"),
    ),
    dict(
        from_name="Thomas Becker", from_addr="t.becker@example.de", hours_ago=28,
        subject="Frage zur Mautgebühr für Wohnmobil",
        body="""Sehr geehrte Damen und Herren,

wir planen im November eine Reise mit unserem Wohnmobil (zwei Achsen, Höhe 3,2 m) von Subotica nach Niš. In welche Kategorie fällt unser Fahrzeug und wie viel kostet die Maut ungefähr?

Mit freundlichen Grüßen
Thomas Becker""",
        expected=("cenovnik", "KC"),
    ),
    dict(
        from_name="Mehmet Yılmaz", from_addr="mehmet.yilmaz@example.com.tr", hours_ago=36,
        subject="Toll device for foreign trucks",
        body="""Dear Sir or Madam,

our company Yılmaz Lojistik operates 12 trucks that regularly transit Serbia. Is it possible for a foreign company to get toll devices (TAG) for our trucks, and which documents are required?

Best regards,
Mehmet Yılmaz""",
        expected=("tag_izdavanje", "ENP"),
    ),
    dict(
        from_name="Sanja Kovačević", from_addr="sanja.kovacevic@example.rs", hours_ago=16,
        subject="Dva pitanja",
        body="""Poštovani,

imam dva pitanja:

1. Pre tri dana sam dopunila račun sa 2.000 dinara preko aplikacije, ali na računu i dalje vidim 250 dinara.
2. Kupili smo drugi automobil, da li mogu da dodam još jedan TAG na isti ugovor?

Hvala unapred,
Sanja Kovačević, PA 667-CD""",
        expected=("dopuna_racuna", "FIN"),
    ),
    dict(
        from_name="Bojan Todorović", from_addr="bojan.todorovic@example.rs", hours_ago=7,
        subject="Skinut novac sa kartice, nema ga na TAG računu",
        body="""Pozdrav,

juče sam preko mobilne aplikacije dopunio TAG račun sa 1.500 dinara. Novac mi je skinut sa kartice, ali stanje na TAG računu je i dalje 15 dinara, pa ne mogu da prođem kroz ENP traku. Molim hitnu proveru.

Bojan Todorović
SD 556-AB""",
        expected=("dopuna_racuna", "FIN"),
    ),
    dict(
        from_name="Katarina Živković", from_addr="katarina.zivkovic@example.rs", hours_ago=29,
        subject="TAG ne pišti kod prolaska",
        body="""Poštovani,

moj TAG više ne daje zvučni signal pri prolasku, a na stanici Novi Sad jug je rampa jednom kasnila sa podizanjem. Da li treba da ga zamenim i da li se zamena plaća?

Katarina Živković, NS 434-QR""",
        expected=("tag_neispravan", "ENP"),
    ),
    dict(
        from_name="Miloš Radovanović", from_addr="milos.radovanovic@example.rs", hours_ago=55,
        subject="Raskid ugovora zbog odlaska u inostranstvo",
        body="""Poštovani,

od decembra odlazim na rad u inostranstvo i želim da raskinem ugovor za TAG-40112255. Kako da vratim uređaj i na koji račun mogu da dobijem preostala sredstva?

Miloš Radovanović""",
        expected=("raskid_ugovora", "ENP"),
    ),
    dict(
        from_name="Nataša Vuković", from_addr="office@beokurir.example", hours_ago=24,
        subject="Faktura za prolaske - septembar",
        body="""Poštovani,

potrebna nam je zbirna faktura za sve prolaske naša četiri vozila (BG 301-BK do BG 304-BK) za septembar 2026, za potrebe knjigovodstva. Na portalu vidimo samo pojedinačne izveštaje.

Beo Kurir d.o.o.
Nataša Vuković, finansije""",
        expected=("fakture", "FIN"),
    ),
    dict(
        from_name="Dragan Kostić", from_addr="logistika@transport-morava.example", hours_ago=11,
        subject="Pogrešna kategorija za kamion na Batočini",
        body="""Poštovani,

naš kamion KS 103-TM, koji je registrovan u kategoriji III, na naplatnoj stanici Batočina 15. i 16. oktobra naplaćen je kao kategorija IV. Vozilo ima tri osovine. Molimo proveru i povraćaj razlike na pretplatni račun.

Transport Morava d.o.o.
Dragan Kostić""",
        expected=("kategorija_vozila", "NAP"),
    ),
    dict(
        from_name="Ljiljana Mitrović", from_addr="ljiljana.mitrovic@example.rs", hours_ago=21,
        subject="Izgubila sam TAG",
        body="""Poštovani,

zvala sam juče kontakt centar i rečeno mi je da pošaljem mejl. Izgubila sam TAG uređaj (TAG-40112252, vozilo VR 101-KL). Molim vas da ga blokirate da neko ne bi koristio moj račun i da mi kažete kako da dobijem novi.

Ljiljana Mitrović""",
        expected=("tag_zamena", "ENP"),
    ),
    dict(
        from_name="Đorđe Vasić", from_addr="djordje.vasic@example.rs", hours_ago=70,
        subject="Nova adresa",
        body="""Poštovani, preselio sam se, nova adresa je Venac Radomira Putnika 14, Sombor. Molim vas da izmenite podatke u ugovoru za TAG-40112259. Đorđe Vasić""",
        expected=("promena_podataka", "ENP"),
    ),
    dict(
        from_name="Aleksandar Pavlović", from_addr="a.pavlovic@example.rs", hours_ago=15,
        subject="Cena za motor do Niša",
        body="""Pozdrav, koliko je putarina za motocikl od Beograda do Niša? Imam TAG na motoru (BG 990-IJ). Aleksandar""",
        expected=("cenovnik", "KC"),
    ),
    dict(
        from_name="Весна Илић", from_addr="vesna.ilic@example.rs", hours_ago=19,
        subject="Повраћај дуплe допуне",
        body="""Поштовани,

18. октобра сам грешком два пута допунила рачун за TAG-40112260 преко апликације, по 2.000 динара. Молим вас да ми један износ вратите на текући рачун.

Весна Илић""",
        expected=("povracaj_novca", "FIN"),
    ),
    dict(
        from_name="Petar Milošević", from_addr="petar.milosevic@example.rs", hours_ago=48,
        subject="Kamen razbio vetrobran na autoputu",
        body="""Poštovani,

19.10. na autoputu kod Kraljeva kamen je pao sa kamiona za održavanje puta i razbio mi vetrobransko staklo. Imam snimak sa kamere u autu. Ko snosi troškove zamene stakla?

Petar Milošević, NP 334-WX""",
        expected=("ostecenje_vozila", "PRA"),
    ),
    dict(
        from_name="Jovana Stefanović", from_addr="jovana.stefanovic@example.rs", hours_ago=31,
        subject="Prekršajni nalog za putarinu koju sam platila",
        body="""Poštovani,

dobila sam prekršajni nalog za neplaćenu putarinu na stanici Vrčin 2. septembra. Tog dana sam putarinu platila karticom, imam izvod iz banke. Kako da uložim prigovor?

Jovana Stefanović, BG 889-GH""",
        expected=("prekrsaj", "PRA"),
    ),
    dict(
        from_name="Zoran Petković", from_addr="zoran.petkovic@example.rs", hours_ago=8,
        subject="Radno vreme subotom",
        body="""Da li korisnički centar u Novom Sadu radi subotom i do koliko sati? Zoran""",
        expected=("opste_informacije", "KC"),
    ),
    dict(
        from_name="Luka M", from_addr="luka.m@example.com", hours_ago=1,
        subject="tag ne radi",
        body="""brate tag mi ne radi vec 3 dana, svaki put moram da cekam u redu za gotovinu, sta se desava?? imam para na racunu. tablice BG 742-LM""",
        expected=("tag_neispravan", "ENP"),
    ),
    dict(
        from_name="Dragan Kostić", from_addr="logistika@transport-morava.example", hours_ago=52,
        subject="Raspodela uplate na tri TAG-a",
        body="""Poštovani,

uplatili smo 50.000 dinara na račun ugovora. Kako da sredstva rasporedimo na sva tri vozila (KS 101-TM, KS 102-TM i KS 103-TM)? Trenutno vidimo da je ceo iznos na prvom TAG-u.

Dragan Kostić""",
        expected=("dopuna_racuna", "FIN"),
    ),
    dict(
        from_name="Gordana Lukić", from_addr="gordana.lukic@example.rs", hours_ago=10,
        subject="Gužva na naplatnoj stanici Beograd",
        body="""Zašto su u nedelju popodne na naplatnoj stanici Beograd otvorene samo dve trake za TAG, a kolona je bila dva kilometra? Zar nije smisao TAG-a da se brže prolazi?

Gordana Lukić""",
        expected=("guzve_naplata", "NAP"),
    ),
    dict(
        from_name="Vesna Ilić", from_addr="vesna.ilic@example.rs", hours_ago=26,
        subject="Da li će biti zatvorena traka vikendom?",
        body="""Poštovani, da li će ovog vikenda na autoputu Niš - Beograd kod Ćuprije biti zatvorena traka zbog radova? Putujem u subotu ujutru. Vesna""",
        expected=("stanje_puteva", "ODR"),
    ),
]

FILTERED = [
    dict(
        from_name="Mail Delivery System", from_addr="MAILER-DAEMON@mail.demo-kc.rs", hours_ago=13,
        subject="Undeliverable: Odgovor na Vaš upit",
        body="Delivery has failed to these recipients or groups:\n\nmarko.p.stari@example.rs\nThe email address you entered couldn't be found.",
        headers={"Auto-Submitted": "auto-generated", "Content-Type": "multipart/report; report-type=delivery-status"},
        expected=("tehnicka", None),
    ),
    dict(
        from_name="Petar Ilić", from_addr="petar.ilic@example.rs", hours_ago=12,
        subject="Automatski odgovor: Na godišnjem odmoru sam",
        body="Poštovani, na godišnjem odmoru sam do 3. novembra. Za hitna pitanja obratite se kolegi.",
        headers={"Auto-Submitted": "auto-replied", "X-Autoreply": "yes"},
        expected=("tehnicka", None),
    ),
    dict(
        from_name="SEO Expert Team", from_addr="offers@seo-boost.example", hours_ago=9,
        subject="Vaš sajt na PRVOM mestu na Google-u!!! Garantovano",
        body="Poštovani vlasniče sajta, garantujemo PRVO mesto na Google-u za samo 99 EUR mesečno!!! Kliknite ovde: http://seo-boost.example/ponuda http://seo-boost.example/akcija Ponuda važi samo danas!!!",
        expected=("spam", None),
    ),
    dict(
        from_name="International Lottery", from_addr="winner@lottery-intl.example", hours_ago=30,
        subject="CONGRATULATIONS!!! You have won 1.000.000 EUR",
        body="Dear Winner, your email was selected in our international lottery. To claim your prize send your bank details and a processing fee of 250 EUR.",
        expected=("spam", None),
    ),
    dict(
        from_name="Auto Gume Plus", from_addr="newsletter@autogume.example", hours_ago=40,
        subject="Novi popusti na zimske gume - do 30%",
        body="Iskoristite jesenju akciju! Zimske gume po sniženim cenama. Ako ne želite da primate ove poruke, odjavite se ovde.",
        headers={"List-Unsubscribe": "<mailto:unsubscribe@autogume.example>", "Precedence": "bulk"},
        expected=("tehnicka", None),
    ),
    dict(
        from_name="Crypto Capital", from_addr="invest@cryptocap.example", hours_ago=18,
        subject="Guaranteed 300% return - crypto investment",
        body="Invest now in our crypto fund and get guaranteed 300% returns in 30 days. Limited spots! bitcoin bitcoin",
        expected=("spam", None),
    ),
    dict(
        from_name="Mail Delivery Subsystem", from_addr="postmaster@mail.demo-kc.rs", hours_ago=6,
        subject="Delivery Status Notification (Failure)",
        body="Your message to info@nepostojeci-domen.example couldn't be delivered. The domain does not exist.",
        headers={"Auto-Submitted": "auto-generated"},
        expected=("tehnicka", None),
    ),
    dict(
        from_name="Biro Kancelarija d.o.o.", from_addr="prodaja@biro-kancelarija.example", hours_ago=35,
        subject="Ponuda za saradnju - kancelarijski materijal",
        body="Poštovani, nudimo vam povoljnu isporuku kancelarijskog materijala i tonera za vaše poslovne prostorije, uz besplatnu dostavu u celoj Srbiji. Cenovnik u prilogu.",
        expected=("spam", None),
    ),
]

# Mejlovi za simulaciju novog talasa obracanja (dugme "Simuliraj prijem")
POOL = [
    dict(from_name="Dejan Ristić", from_addr="dejan.ristic@example.rs", subject="Rampa se nije podigla na Vrčinu",
         body="Poštovani, danas oko 7:15 na Vrčinu rampa se nije podigla, iako mi je TAG nov. Morao sam da platim 640 dinara gotovinom. Tablice BG 515-DR. Molim povraćaj. Dejan"),
    dict(from_name="Maja Kostić", from_addr="maja.kostic@example.rs", subject="Koliko košta TAG?",
         body="Pozdrav, koliko košta TAG uređaj i gde mogu da ga kupim u Beogradu? Maja"),
    dict(from_name="Ненад Јовић", from_addr="nenad.jovic@example.rs", subject="Уплата није видљива",
         body="Поштовани, уплатио сам 2.500 динара пре два дана, а на рачуну није видљиво. TAG-40119911. Ненад Јовић"),
    dict(from_name="Laura Rossi", from_addr="laura.rossi@example.it", subject="Toll price for campervan",
         body="Hello, how much is the toll from Horgoš to Preševo for a campervan with two axles? Thank you, Laura"),
    dict(from_name="Branko Ilić", from_addr="branko.ilic@example.rs", subject="Rupa na kolovozu kod Jagodine",
         body="Na autoputu kod Jagodine u smeru Niša, u levoj traci, ogromna rupa. Hitno sanirati! Branko"),
    dict(from_name="Teodora Matić", from_addr="teodora.matic@example.rs", subject="Hvala!",
         body="Želim da se zahvalim kolegi iz kontakt centra koji mi je juče pomogao oko blokade izgubljenog TAG-a. Sve pohvale! Teodora"),
    dict(from_name="Siniša Popov", from_addr="sinisa.popov@example.rs", subject="Duplo naplaćeno na Bubanj Potoku",
         body="Poštovani, 20.10. mi je prolazak kroz Bubanj Potok naplaćen dva puta po 820 dinara. Vozilo BG 774-SP, TAG-40115577. Siniša Popov"),
    dict(from_name="Jasna Đokić", from_addr="jasna.djokic@example.rs", subject="Promena adrese za račune",
         body="Molim vas da promenite adresu za dostavu računa na Kneza Miloša 20, Beograd. TAG-40113344. Jasna Đokić"),
    dict(from_name="Stevan Lazarević, portal Info Put", from_addr="stevan@infoput.example", subject="Upit za izjavu - novi sistem naplate",
         body="Poštovani, za naš portal pripremamo tekst o planovima za uvođenje naplate bez zaustavljanja. Da li možemo dobiti izjavu ili sagovornika do sutra? Stevan Lazarević, novinar"),
    dict(from_name="Mirjana Todić", from_addr="mirjana.todic@example.rs", subject="Prekršajni nalog",
         body="Stigao mi je prekršajni nalog za neplaćenu putarinu, a tada sam imala dovoljno na TAG računu. TAG-40116688, vozilo NS 220-MT. Kako da se žalim? Mirjana"),
]

# Kratka tela za istorijske (zatvorene) predmete, po kategoriji
HISTORICAL_BODIES = {
    "tag_neispravan": ["Rampa se nije podigla iako imam TAG, platio sam gotovinom.", "TAG nije očitan na izlazu, molim proveru."],
    "dopuna_racuna": ["Uplata od pre tri dana nije vidljiva na računu.", "Dopunio sam preko aplikacije, novac nije legao."],
    "tag_izdavanje": ["Šta je potrebno za izdavanje TAG-a?", "Zanima me kako da dobijem TAG za službeno vozilo."],
    "dupla_naplata": ["Naplaćeno mi je dva puta za isti prolazak.", "Na izvodu imam dve iste transakcije."],
    "kategorija_vozila": ["Naplaćena mi je viša kategorija od one u ugovoru.", "Kombi mi je naplaćen kao kategorija II."],
    "povracaj_novca": ["Molim povraćaj preostalih sredstava.", "Tražim povraćaj pogrešno naplaćenog iznosa."],
    "raskid_ugovora": ["Želim da raskinem ugovor i vratim TAG.", "Prodao sam vozilo, kako da raskinem ugovor?"],
    "promena_podataka": ["Promenio sam tablice, kako da ažuriram podatke?", "Molim promenu adrese u ugovoru."],
    "cenovnik": ["Koliko košta putarina do Niša?", "Koja je cena za Beograd - Novi Sad?"],
    "stanje_puteva": ["Prijavljujem rupu na kolovozu.", "Da li su radovi na deonici završeni?"],
    "ostecenje_vozila": ["Oštetio sam vozilo zbog rupe na putu.", "Kamen je razbio vetrobran, tražim naknadu."],
    "prituzba_osoblje": ["Radnik na naplati je bio neljubazan.", "Nezadovoljan sam odnosom osoblja."],
    "pohvala": ["Pohvala za ljubaznu koleginicu.", "Hvala na brzom rešavanju problema."],
    "opste_informacije": ["Koje je radno vreme centra?", "Gde se nalazi korisnički centar u Nišu?"],
    "fakture": ["Potrebna nam je mesečna faktura.", "Molimo zbirni izveštaj o prolascima."],
    "interoperabilnost": ["Da li TAG radi u Severnoj Makedoniji?", "Mogu li da koristim TAG u Crnoj Gori?"],
    "naknadno_placanje": ["Kako da platim neplaćenu putarinu?", "Nisam mogao da platim na stanici, kako sada?"],
    "tag_zamena": ["Izgubio sam TAG, molim blokadu.", "TAG je polomljen, potrebna zamena."],
    "guzve_naplata": ["Zašto je otvoreno malo traka?", "Velike gužve na naplati vikendom."],
    "prekrsaj": ["Dobio sam prekršajni nalog, a platio sam putarinu.", "Prigovor na prekršajni nalog."],
    "pristup_informacijama": ["Zahtev za pristup informacijama o broju prolazaka.", "Tražimo podatke o naplati za 2025."],
    "medijski_upit": ["Novinarski upit o radovima na autoputu.", "Molimo izjavu za emisiju o gužvama."],
}
