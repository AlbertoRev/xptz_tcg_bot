"""Tipografia editoriale pulita, senza estetica pixel/cartoon."""
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

SYSTEM="/usr/share/fonts/truetype/dejavu"
def _reg(alias, filename, fallback):
    path=os.path.join(SYSTEM,filename)
    if os.path.exists(path):
        pdfmetrics.registerFont(TTFont(alias,path))
        return alias
    return fallback

def carica():
    regular=_reg("PokeBody","DejaVuSans.ttf","Helvetica")
    bold=_reg("PokeBold","DejaVuSans-Bold.ttf","Helvetica-Bold")
    condensed=_reg("PokeTitle","DejaVuSansCondensed-Bold.ttf","Helvetica-Bold")
    return {"Testata":condensed,"Titolo":condensed,"Corpo":regular,"CorpoB":bold,"Simboli":regular}
