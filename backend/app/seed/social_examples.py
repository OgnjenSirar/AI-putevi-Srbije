"""Primer objava za ekran drustvenih mreza (bez poziva LLM-a)."""
import logging
from datetime import datetime, timedelta, timezone

from ..db import SessionLocal

log = logging.getLogger("seed")


def seed_social_examples() -> None:
    """Dve primer objave (bez poziva LLM-a), da ekran mreza ne bude prazan."""
    from ..models import SocialPost
    from ..social import service

    with SessionLocal() as db:
        if db.query(SocialPost).count():
            return
        examples = [
            dict(brief="Praznično radno vreme korisničkih centara za Dan primirja.", template_code="praznik",
                 fields={"naslov": "Dan primirja", "poruka": "Korisnički centri 11. novembra ne rade. Kontakt centar je dostupan 0-24, a TAG uređaj možete dopuniti preko portala.", "potpis": "Vaš Korisnički centar"},
                 fb_text="Poštovani korisnici, povodom Dana primirja korisnički centri 11. novembra neće raditi. Kontakt centar je dostupan 0-24, a račun TAG uređaja možete dopuniti preko portala i mobilne aplikacije.",
                 ig_text="Povodom Dana primirja korisnički centri 11. novembra ne rade. Kontakt centar je dostupan 0-24. #putarina #TAG #info",
                 alt_text="Grafičko obaveštenje o neradnom danu korisničkih centara 11. novembra.", status="objavljeno"),
            dict(brief="Podsetnik: korisnici TAG-a ostvaruju popust od 10% i brži prolazak.", template_code="naplata",
                 fields={"naslov": "Brže kroz naplatu", "istaknuto": "10% popusta", "poruka": "Korisnici TAG uređaja plaćaju putarinu jeftinije i prolaze ENP trakama bez zaustavljanja.", "poziv": "portal.demo-kc.rs"},
                 fb_text="Da li ste znali da korisnici TAG uređaja ostvaruju popust od 10% na cenu putarine? TAG preuzmite u korisničkim centrima, a račun dopunite preko portala.",
                 ig_text="TAG = 10% popusta i brži prolazak kroz ENP trake. Više informacija na portalu. #TAG #putarina #autoput", alt_text="Grafika sa porukom o popustu od 10% za korisnike TAG uređaja.", status="nacrt"),
        ]
        for ex in examples:
            status = ex.pop("status")
            p = SocialPost(created_by="Nevena Mirković", ai_meta={"mode": "primer"}, **ex)
            db.add(p)
            db.commit()
            try:
                service.render_with_fit(db, p, max_rounds=0)
                if status == "objavljeno":
                    p.status = "odobreno"
                    p.approved_by = "Jasmina Ristić"
                    p.approved_at = datetime.now(timezone.utc) - timedelta(days=3)
                    db.commit()
                    service.publish_simulated(db, p, "Nevena Mirković")
                    p.published_at = datetime.now(timezone.utc) - timedelta(days=3)
                    db.commit()
            except Exception as e:  # pragma: no cover
                log.warning("Primer objave nije renderovan: %s", e)
