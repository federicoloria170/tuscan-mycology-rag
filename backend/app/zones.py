"""Zone forestali della Toscana.

ATTENZIONE: sono aree *indicative* (centro + raggio), non confini amministrativi.
Servono sia per disegnare la mappa sia come coordinate per il meteo.
"""
import unicodedata

FOREST_LABELS = {
    "faggeta": "Faggeta",
    "castagneto": "Castagneto",
    "querceto": "Querceto (cerro, roverella, rovere)",
    "abetina": "Abetina",
    "lecceta": "Lecceta",
    "pineta": "Pineta",
    "bosco_misto": "Bosco misto",
}

ZONES = [
    dict(id="casentino", name="Casentino", lat=43.80, lon=11.82, radius_km=16, altitude_min=400, altitude_max=1650,
         forests={"faggeta": .30, "abetina": .20, "castagneto": .20, "querceto": .30},
         description="Foreste Casentinesi: faggete e abetine storiche (Camaldoli, Badia Prataglia)."),
    dict(id="mugello", name="Mugello", lat=44.00, lon=11.40, radius_km=15, altitude_min=250, altitude_max=1200,
         forests={"castagneto": .40, "querceto": .30, "faggeta": .20, "bosco_misto": .10},
         description="Appennino fiorentino con castagneti e querceti."),
    dict(id="amiata", name="Monte Amiata", lat=42.89, lon=11.62, radius_km=13, altitude_min=600, altitude_max=1738,
         forests={"faggeta": .40, "castagneto": .40, "querceto": .20},
         description="Vulcano spento con grandi faggete sommitali e castagneti."),
    dict(id="garfagnana", name="Garfagnana", lat=44.10, lon=10.42, radius_km=15, altitude_min=200, altitude_max=1900,
         forests={"castagneto": .45, "faggeta": .25, "bosco_misto": .20, "querceto": .10},
         description="Valle del Serchio, patria del castagno da frutto."),
    dict(id="pratomagno", name="Pratomagno", lat=43.66, lon=11.70, radius_km=13, altitude_min=400, altitude_max=1592,
         forests={"faggeta": .35, "castagneto": .30, "querceto": .20, "abetina": .15},
         description="Dorsale tra Valdarno e Casentino (Vallombrosa)."),
    dict(id="apuane", name="Alpi Apuane", lat=44.08, lon=10.25, radius_km=13, altitude_min=100, altitude_max=1947,
         forests={"castagneto": .40, "faggeta": .30, "lecceta": .10, "bosco_misto": .20},
         description="Montagne calcaree vicine al mare, forte variabilità climatica."),
    dict(id="pistoiese", name="Appennino Pistoiese", lat=44.07, lon=10.85, radius_km=14, altitude_min=400, altitude_max=1900,
         forests={"faggeta": .40, "abetina": .25, "castagneto": .25, "querceto": .10},
         description="Faggete e abetine tra Abetone e San Marcello."),
    dict(id="maremma", name="Maremma", lat=42.72, lon=11.10, radius_km=20, altitude_min=0, altitude_max=500,
         forests={"lecceta": .40, "pineta": .30, "querceto": .30},
         description="Boschi costieri mediterranei, lecceti e pinete."),
    dict(id="metallifere", name="Colline Metallifere", lat=43.10, lon=10.95, radius_km=16, altitude_min=200, altitude_max=1050,
         forests={"querceto": .40, "lecceta": .30, "castagneto": .15, "bosco_misto": .15},
         description="Querceti e lecceti dell'entroterra grossetano e senese."),
    dict(id="chianti", name="Chianti", lat=43.46, lon=11.35, radius_km=13, altitude_min=250, altitude_max=890,
         forests={"querceto": .50, "castagneto": .15, "pineta": .10, "bosco_misto": .25},
         description="Colline boscate tra Firenze e Siena."),
    dict(id="lunigiana", name="Lunigiana", lat=44.28, lon=9.97, radius_km=15, altitude_min=100, altitude_max=1800,
         forests={"castagneto": .40, "faggeta": .20, "querceto": .20, "bosco_misto": .20},
         description="Alta Toscana nord-occidentale, castagneti e faggete."),
]


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def get_zone(zone_id: str | None) -> dict | None:
    return next((z for z in ZONES if z["id"] == zone_id), None)


def find_zone_in_text(text: str) -> dict | None:
    t = _norm(text)
    for z in ZONES:
        if _norm(z["name"]) in t or z["id"] in t:
            return z
    return None
