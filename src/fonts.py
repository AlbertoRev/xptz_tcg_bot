"""Tipografia editoriale contemporanea per POKEPUTZU WEEKLY."""
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os, glob

def _find(patterns):
    for pattern in patterns:
        hits=glob.glob(pattern,recursive=True)
        if hits: return hits[0]
    return None

def _reg(alias, patterns, fallback):
    path=_find(patterns)
    if path and os.path.exists(path):
        pdfmetrics.registerFont(TTFont(alias,path))
        return alias
    return fallback

def carica():
    regular=_reg("PokeBody",["/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf","/usr/share/fonts/**/*NotoSans-Regular.ttf"],"Helvetica")
    medium=_reg("PokeMedium",["/usr/share/fonts/truetype/noto/NotoSans-Medium.ttf","/usr/share/fonts/**/*NotoSans-Medium.ttf"],"Helvetica")
    bold=_reg("PokeBold",["/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf","/usr/share/fonts/**/*NotoSans-Bold.ttf"],"Helvetica-Bold")
    title=_reg("PokeTitle",["/usr/share/fonts/truetype/liberation2/LiberationSans-BoldItalic.ttf","/usr/share/fonts/**/*LiberationSans-BoldItalic.ttf","/usr/share/fonts/truetype/noto/NotoSans-Black.ttf"],bold)
    return {"Testata":title,"Titolo":title,"Corpo":regular,"CorpoB":medium,"Simboli":regular}
