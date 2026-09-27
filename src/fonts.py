"""Font della rivista: scaricati da Google Fonts (licenze libere OFL/Apache) al primo uso.

Se il download non riesce, la rivista usa i font di sistema: il PDF viene creato comunque.
"""
import os
from pathlib import Path

import requests
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE = "https://raw.githubusercontent.com/google/fonts/main/"
SCELTI = {
    "Testata": "apache/luckiestguy/LuckiestGuy-Regular.ttf",   # testata in stile cartone animato
    "Titolo": "ofl/lilitaone/LilitaOne-Regular.ttf",            # titoli tondeggianti
    "Corpo": "ofl/comicneue/ComicNeue-Regular.ttf",             # testo
    "CorpoB": "ofl/comicneue/ComicNeue-Bold.ttf",               # testo in grassetto
}
RISERVA = {"Testata": "DejaVuSans-Bold.ttf", "Titolo": "DejaVuSans-Bold.ttf",
           "Corpo": "DejaVuSans.ttf", "CorpoB": "DejaVuSans-Bold.ttf"}
RISERVA_BASE = {"Testata": "Helvetica-Bold", "Titolo": "Helvetica-Bold", "Corpo": "Helvetica", "CorpoB": "Helvetica-Bold"}
CARTELLA = Path("font_cache")
CARTELLE_SISTEMA = ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/dejavu/")


def _sistema(file):
    for base in CARTELLE_SISTEMA:
        if os.path.exists(base + file):
            return base + file
    return None


def carica():
    nomi = {}
    for nome, percorso in SCELTI.items():
        locale = CARTELLA / Path(percorso).name
        try:
            if not locale.exists():
                CARTELLA.mkdir(exist_ok=True)
                r = requests.get(BASE + percorso, timeout=60)
                r.raise_for_status()
                locale.write_bytes(r.content)
            pdfmetrics.registerFont(TTFont(nome, str(locale)))
            nomi[nome] = nome
            continue
        except Exception:
            pass
        file = _sistema(RISERVA[nome])
        if file:
            pdfmetrics.registerFont(TTFont(nome + "R", file))
            nomi[nome] = nome + "R"
        else:
            nomi[nome] = RISERVA_BASE[nome]
    simboli = _sistema("DejaVuSans.ttf")
    if simboli:
        pdfmetrics.registerFont(TTFont("Simboli", simboli))
        nomi["Simboli"] = "Simboli"
    else:
        nomi["Simboli"] = "Helvetica"
    return nomi
