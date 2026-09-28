"""Generatore della rivista settimanale a tema Pokémon.

La grafica usa il kit scelto ogni settimana da download_assets.py: Pokémon,
Poké Ball, strumenti e sprite di allenatori. Nessuna mascotte o decorazione
generica rimane nel PDF: ogni elemento ornamentale appartiene al mondo Pokémon.
"""
import math
import random
from pathlib import Path
from PIL import Image as PILImage, ImageDraw, ImageFilter, ImageOps, ImageChops
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepTogether, KeepInFrame, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

import config as C
from src import fonts
from src.report import _eur, _perc, _t

# ---------- font ----------
F = fonts.carica()
TITOLO, SOTTO, TESTO, TESTO_B = F["Testata"], F["Titolo"], F["Corpo"], F["CorpoB"]

# ---------- palette giocosa ----------
INCHIOSTRO = colors.HexColor("#17263A")
CIELO = colors.HexColor("#59B9E8")
SOLE = colors.HexColor("#FFD84A")
ROSSO = colors.HexColor("#E84B3C")
VERDE = colors.HexColor("#38A866")
PRATO = colors.HexColor("#74BE68")
VIOLA = colors.HexColor("#5869C9")
ARANCIO = colors.HexColor("#F3A43B")
BLU = colors.HexColor("#1769B0")
CARTA = colors.HexColor("#FFFDF4")
CREMA = colors.HexColor("#FFF5D6")
PASTELLO = colors.HexColor("#F4F8FC")
VERDE_SCURO = colors.HexColor("#23794A")     # per le scritte verdi su fondo bianco
GRIGIO = colors.HexColor("#526173")
BIANCO = colors.white
LEGNO = colors.HexColor("#C8792B")
LEGNO_SCURO = colors.HexColor("#9C5A1C")
ARCOBALENO = [ROSSO, ARANCIO, SOLE, VERDE, CIELO, VIOLA]
HEX = ["#2366B1", "#F04E45", "#42A85A", "#8B62D9", "#FF9D3C"]
COLORE_STATO = {"caldo": ROSSO, "tiepido": ARANCIO,
                "freddo": BLU, "in arrivo": VERDE,
                "da valutare": colors.HexColor("#6D8452"), "nessun dato": colors.HexColor("#66736B")}

W, H = A4
MARGINE = 17 * mm
LARGHEZZA = W - 2 * MARGINE
TESTATA = "POKEPUTZU WEEKLY"
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"


def _logo(c, x, y, width, compact=False):
    """Marchio originale POKèPUTZU WEEKLY, robusto e leggibile anche in piccolo."""
    main="POKèPUTZU"; size=max(10,width/6.1); tw=pdfmetrics.stringWidth(main,TITOLO,size)
    if tw>width: size*=width/tw; tw=pdfmetrics.stringWidth(main,TITOLO,size)
    c.saveState(); c.translate(x,y); c.rotate(-2 if not compact else 0); c.setFont(TITOLO,size)
    # contorno simulato: affidabile in PDF e visivamente più massiccio
    off=max(.8,size*.045); c.setFillColor(colors.HexColor("#123E78"))
    for dx,dy in ((-off,0),(off,0),(0,-off),(0,off),(-off,-off),(off,-off),(-off,off),(off,off)):
        c.drawString(dx,dy,main)
    c.setFillColor(SOLE); c.drawString(0,0,main)
    if not compact:
        rw=min(width*.46,48*mm); rh=max(7*mm,size*.32); rx=max(0,tw-rw*.86); ry=-rh*.90
        c.setFillColor(ROSSO); c.roundRect(rx,ry,rw,rh,rh/2,stroke=0,fill=1)
        c.setFillColor(BIANCO); c.setFont(TESTO_B,max(7,size*.27)); c.drawCentredString(rx+rw/2,ry+rh*.30,"WEEKLY")
    else:
        c.setFillColor(ROSSO); c.setFont(TESTO_B,max(5,size*.22)); c.drawRightString(min(width,tw),-3.1*mm,"WEEKLY")
    c.restoreState()

def _mondo_asset(ctx, gruppo, indice=0):
    """Restituisce un asset del kit settimanale, oppure None se non disponibile."""
    mondo = (ctx or {}).get("pokemon_mondo", {})
    valori = mondo.get(gruppo) or []
    if not valori:
        return None
    return valori[indice % len(valori)]


def _mondo_colore(ctx, fallback):
    temi = {
        "Avventura di Kanto": "#E63946", "Ragazzi di Johto": "#6C8B3C",
        "Tesori di Hoenn": "#0B7FAB", "Sinnoh Expedition": "#6C63A8",
        "Unima in viaggio": "#2D6A4F", "Kalos Style": "#C44536",
        "Alola al tramonto": "#F08C46", "Galar League": "#3D5A80",
        "Tesori di Paldea": "#8E5BB7", "Notte Misteriosa": "#4D4F9A",
        "Palestra Elettrica": "#D6A100", "Cascata Acquatica": "#1678B5",
        "Sentiero Selvaggio": "#4F772D", "Cima Ghiacciata": "#4A9FC8",
        "Zona Vulcanica": "#B23A2B", "Foresta Incantata": "#7A9E35",
    }
    return colors.HexColor(temi.get((ctx or {}).get("pokemon_mondo", {}).get("tema"), fallback))


def _immagine_asset(c, nome, x, y, larghezza, altezza=None, angolo=0):
    """Disegna un PNG decorativo se è stato scaricato."""
    percorso = ASSET_DIR / nome
    if not percorso.exists():
        return
    altezza = larghezza if altezza is None else altezza
    c.saveState()
    c.translate(x, y)
    if angolo:
        c.rotate(angolo)
    c.drawImage(str(percorso), -larghezza / 2, -altezza / 2,
                 width=larghezza, height=altezza, mask="auto", preserveAspectRatio=True)
    c.restoreState()


def _su(colore):
    """Colore del testo leggibile sopra un fondo: bianco sui colori scuri, inchiostro su quelli chiari."""
    luce = 0.299 * colore.red + 0.587 * colore.green + 0.114 * colore.blue
    return INCHIOSTRO if luce > 0.55 else BIANCO


# ---------- piccoli disegni ----------
def _stella(c, x, y, r, colore, punte=5, interno=0.45, angolo=90):
    p = c.beginPath()
    for i in range(punte * 2):
        rr = r if i % 2 == 0 else r * interno
        a = math.radians(angolo + i * 180 / punte)
        (p.moveTo if i == 0 else p.lineTo)(x + rr * math.cos(a), y + rr * math.sin(a))
    p.close()
    c.setFillColor(colore)
    c.drawPath(p, stroke=0, fill=1)


def _scintilla(c, x, y, r, colore):
    _stella(c, x, y, r, colore, punte=4, interno=0.28, angolo=90)


def _nuvola(c, x, y, s, colore=BIANCO):
    c.setFillColor(colore)
    for dx, dy, rr in ((0, 0, 9), (10, 4, 11), (21, 0, 8), (10, -3, 9), (-8, -2, 6)):
        c.circle(x + dx * s, y + dy * s, rr * s, stroke=0, fill=1)



def _collina(c, x0, x1, base, ampiezza, colore, fase, lunghezza):
    p = c.beginPath()
    p.moveTo(x0, 0)
    x = x0
    while x <= x1:
        p.lineTo(x, base + ampiezza * math.sin(fase + x / lunghezza))
        x += 4
    p.lineTo(x1, 0)
    p.close()
    c.setFillColor(colore)
    c.drawPath(p, stroke=0, fill=1)


def _ciuffo(c, x, y, colore, s=1):
    c.setFillColor(colore)
    for dx, h in ((-3, 7), (0, 10), (3, 7)):
        p = c.beginPath()
        p.moveTo(x + dx * s - 1.5 * s, y)
        p.lineTo(x + dx * s, y + h * s)
        p.lineTo(x + dx * s + 1.5 * s, y)
        p.close()
        c.drawPath(p, stroke=0, fill=1)


def _fiore(c, x, y, colore, s=1):
    c.setFillColor(colore)
    for k in range(5):
        a = math.radians(k * 72)
        c.circle(x + 2.2 * s * math.cos(a), y + 2.2 * s * math.sin(a), 1.8 * s, stroke=0, fill=1)
    c.setFillColor(SOLE)
    c.circle(x, y, 1.4 * s, stroke=0, fill=1)



def _nuvoletta(c, x, y, w, h, punta_x, punta_y):
    """Fumetto bianco con bordo e punta verso (punta_x, punta_y)."""
    c.saveState()
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.15))
    c.roundRect(x + 1.5, y - 1.5, w, h, 5 * mm, stroke=0, fill=1)
    c.setFillColor(BIANCO)
    c.setStrokeColor(INCHIOSTRO)
    c.setLineWidth(1.4)
    c.roundRect(x, y, w, h, 5 * mm, stroke=1, fill=1)
    a = (x + 0.8, y + h * 0.3)
    b = (x + 0.8, y + h * 0.3 + 6 * mm)
    p = c.beginPath()
    p.moveTo(*a)
    p.lineTo(punta_x, punta_y)
    p.lineTo(*b)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    p = c.beginPath()
    p.moveTo(*a)
    p.lineTo(punta_x, punta_y)
    p.lineTo(*b)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def _testo_cartoon(c, x, y, testo, font, size, riempimento, contorno=INCHIOSTRO, ombra=3, centrato=False):
    if centrato:
        x -= pdfmetrics.stringWidth(testo, font, size) / 2
    c.saveState()
    c.setFillColor(contorno)
    c.setFont(font, size)
    c.drawString(x + ombra, y - ombra, testo)
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setTextRenderMode(2)
    c.setFillColor(riempimento)
    c.setStrokeColor(contorno)
    c.setLineWidth(max(1, size / 18))
    t.textOut(testo)
    t.setTextRenderMode(0)
    c.drawText(t)
    c.restoreState()


def _pannello(c, x, y, w, h, colore=CARTA, alpha=0.94, raggio=5 * mm, bordo=None):
    c.saveState()
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.18))
    c.roundRect(x + 2, y - 2, w, h, raggio, stroke=0, fill=1)
    c.setFillColor(colore)
    c.setFillAlpha(alpha)
    if bordo:
        c.setStrokeColor(bordo)
        c.setLineWidth(2)
    c.roundRect(x, y, w, h, raggio, stroke=1 if bordo else 0, fill=1)
    c.restoreState()


def _arcobaleno(c, cx, cy, r, spessore):
    c.saveState()
    c.setLineWidth(spessore)
    c.setStrokeAlpha(0.8)
    for k, col in enumerate(ARCOBALENO):
        rr = r - k * spessore
        c.setStrokeColor(col)
        c.arc(cx - rr, cy - rr, cx + rr, cy + rr, 0, 180)
    c.restoreState()


# ---------- scenari a tutta pagina ----------
def _sfondo_mappa(c, alpha=.12, wash="#F1EFE4"):
    """Mappa Hoenn full-page come texture editoriale, con velo uniforme per la leggibilità."""
    path=_topographic_map_path()
    c.saveState()
    c.setFillColor(colors.HexColor(wash)); c.rect(0,0,W,H,stroke=0,fill=1)
    try:
        c.setFillAlpha(alpha)
        # leggero overscan: la mappa diventa ambiente, non un riquadro.
        c.drawImage(str(path),-16*mm,-4*mm,W+32*mm,H+8*mm,preserveAspectRatio=False,mask="auto")
        c.setFillAlpha(1)
    except Exception:
        pass
    c.setFillColor(colors.Color(1,1,.98,alpha=.48)); c.rect(0,0,W,H,stroke=0,fill=1)
    c.restoreState()

def _panel(c,x,y,w,h,r=3*mm,alpha=.94,stroke="#8CB5D9"):
    c.saveState()
    c.setFillColor(colors.Color(1,1,1,alpha=alpha)); c.roundRect(x,y,w,h,r,stroke=0,fill=1)
    c.setStrokeColor(colors.HexColor(stroke)); c.setLineWidth(.65); c.roundRect(x,y,w,h,r,stroke=1,fill=0)
    c.restoreState()

def _mondo_giorno(c, ctx=None):
    _sfondo_mappa(c,.24,"#FFFDF4")
    c.setFillColor(BLU); c.rect(0,H-19*mm,W,19*mm,stroke=0,fill=1)
    c.setFillColor(SOLE); c.rect(0,H-21*mm,W,2*mm,stroke=0,fill=1)

def _mondo_tramonto(c, ctx=None):
    _sfondo_mappa(c,.52,"#9BD6F2")
    c.saveState(); c.setFillColor(colors.Color(.025,.14,.32,alpha=.42)); c.rect(0,0,W,H,stroke=0,fill=1); c.restoreState()
    hero=(_art_piano(ctx,7).get("hero_asset") if ctx else None) or _mondo_asset(ctx,"pokemon",6)
    c.setFillAlpha(1)
    if hero: _immagine_asset(c,hero,W-42*mm,60*mm,94*mm)
    # Ensemble finale: artwork veri, distribuiti nel grande spazio negativo.
    support=_mondo_asset(ctx,"pokemon",5)
    trainer=_mondo_asset(ctx,"allenatori",1)
    ball=_mondo_asset(ctx,"pokeball",1)
    item=_mondo_asset(ctx,"oggetti",1)
    if support and support != hero: _immagine_asset(c,support,35*mm,66*mm,61*mm)
    if trainer: _immagine_asset(c,trainer,34*mm,122*mm,61*mm)
    if ball: _immagine_asset(c,ball,W-31*mm,137*mm,31*mm)
    if item: _immagine_asset(c,item,W-32*mm,105*mm,34*mm)

# ---------- stili ----------

# ---------- stili ----------
def _stili():
    return {
        "occhiello": ParagraphStyle("o", fontName=TESTO, fontSize=10, leading=13.5, textColor=GRIGIO),
        "p": ParagraphStyle("p", fontName=TESTO, fontSize=10.5, leading=14.5, textColor=INCHIOSTRO),
        "fumetto": ParagraphStyle("f", fontName=TESTO_B, fontSize=10.5, leading=14, textColor=INCHIOSTRO),
        "cella": ParagraphStyle("c", fontName=TESTO, fontSize=8.6, leading=10.4, textColor=INCHIOSTRO),
        "cella_b": ParagraphStyle("cb", fontName=TESTO_B, fontSize=8.6, leading=10.4, textColor=INCHIOSTRO),
        "nota": ParagraphStyle("n", fontName=TESTO, fontSize=8.5, leading=11.5, textColor=GRIGIO),
        "sotto": ParagraphStyle("s", fontName=TITOLO, fontSize=15.5, leading=18, textColor=BLU,
                                spaceBefore=8, spaceAfter=4, keepWithNext=1),
        "box_titolo": ParagraphStyle("bt", fontName=TITOLO, fontSize=23, leading=25, textColor=BLU),
        "box_nome": ParagraphStyle("bn", fontName=SOTTO, fontSize=11.5, leading=14, textColor=INCHIOSTRO),
    }


def _stile_tag(colore):
    return ParagraphStyle("tg", fontName=SOTTO, fontSize=7.8, leading=9.5, textColor=_su(colore),
                          alignment=TA_CENTER)


def _pokeball_vector(c,x,y,r=7*mm):
    c.saveState(); c.setStrokeColor(colors.HexColor("#263238")); c.setLineWidth(1.2)
    c.setFillColor(colors.HexColor("#D9534F")); c.wedge(x-r,y-r,x+r,y+r,0,180,stroke=0,fill=1)
    c.setFillColor(BIANCO); c.wedge(x-r,y-r,x+r,y+r,180,180,stroke=0,fill=1)
    c.setFillColor(colors.HexColor("#263238")); c.rect(x-r,y-1.2*mm,2*r,2.4*mm,stroke=0,fill=1)
    c.setFillColor(BIANCO); c.circle(x,y,2.5*mm,stroke=1,fill=1); c.restoreState()

def _item_vector(c,x,y,s=1):
    c.saveState(); c.setFillColor(colors.HexColor("#5B9DB0")); c.setStrokeColor(colors.HexColor("#315D68")); c.setLineWidth(1)
    p=c.beginPath(); p.moveTo(x,y+8*mm*s); p.curveTo(x+8*mm*s,y+4*mm*s,x+7*mm*s,y-5*mm*s,x,y-8*mm*s)
    p.curveTo(x-7*mm*s,y-5*mm*s,x-8*mm*s,y+4*mm*s,x,y+8*mm*s); p.close(); c.drawPath(p,stroke=1,fill=1)
    c.setStrokeColor(colors.Color(1,1,1,alpha=.55)); c.line(x-2*mm*s,y+4*mm*s,x+2*mm*s,y-4*mm*s); c.restoreState()

def _trainer_vector(c,x,y,s=1):
    c.saveState(); c.setFillColor(colors.HexColor("#D9B08C")); c.circle(x,y+7*mm*s,4*mm*s,stroke=0,fill=1)
    c.setFillColor(colors.HexColor("#355F4E")); c.roundRect(x-5*mm*s,y-8*mm*s,10*mm*s,12*mm*s,2*mm*s,stroke=0,fill=1)
    c.setStrokeColor(colors.HexColor("#355F4E")); c.setLineWidth(2.2*s)
    c.line(x-3*mm*s,y-8*mm*s,x-6*mm*s,y-15*mm*s); c.line(x+3*mm*s,y-8*mm*s,x+6*mm*s,y-15*mm*s)
    c.setFillColor(colors.HexColor("#B84A45")); c.wedge(x-5*mm*s,y+5*mm*s,x+5*mm*s,y+13*mm*s,0,180,stroke=0,fill=1)
    c.restoreState()

# ---------- flowable ----------
class Rubrica(Flowable):
    """Intestazione content-driven: il box segue il testo, non viceversa."""
    def __init__(self, occhiello, titolo, colore=ROSSO):
        super().__init__(); self.occhiello=occhiello.upper(); self.titolo=titolo; self.colore=colore
    def wrap(self,aw,ah):
        self.w=max(40*mm,aw)
        self.p=Paragraph(_t(self.titolo),ParagraphStyle("rubrica_dynamic",fontName=TITOLO,fontSize=16.2,leading=17.2,textColor=BLU,alignment=TA_CENTER))
        _,self.th=self.p.wrap(self.w-18*mm,ah)
        self.h=max(17*mm,self.th+11*mm)
        return self.w,self.h
    def draw(self):
        c=self.canv
        c.setFillColor(colors.Color(.05,.15,.30,alpha=.12)); c.roundRect(1*mm,0,self.w-2*mm,self.h-1*mm,3*mm,stroke=0,fill=1)
        c.setFillColor(colors.Color(1,1,1,alpha=.96)); c.setStrokeColor(colors.HexColor("#72B7E4")); c.setLineWidth(.8)
        c.roundRect(0,1*mm,self.w-2*mm,self.h-1*mm,3*mm,stroke=1,fill=1)
        # taglio giallo diagonale da magazine
        p=c.beginPath(); p.moveTo(0,self.h); p.lineTo(14*mm,self.h); p.lineTo(8*mm,1*mm); p.lineTo(0,1*mm); p.close()
        c.setFillColor(SOLE); c.drawPath(p,stroke=0,fill=1)
        # occhiello dimensionato sul testo
        ow=max(29*mm,min(48*mm,pdfmetrics.stringWidth(self.occhiello,TESTO_B,6)*1.18+8*mm))
        c.setFillColor(ROSSO); c.roundRect((self.w-ow)/2,self.h-7.3*mm,ow,5.7*mm,2.8*mm,stroke=0,fill=1)
        c.setFillColor(BIANCO); c.setFont(TESTO_B,6); c.drawCentredString(self.w/2,self.h-5.45*mm,self.occhiello[:34])
        self.p.drawOn(c,9*mm,4.2*mm)

class Fumetto(Flowable):
    """Callout con box alto esattamente quanto richiede il testo."""
    def __init__(self,testo,st,ctx=None,indice=0):
        super().__init__(); self.par=Paragraph(_t(testo),st["fumetto"]); self.ctx=ctx or {}; self.indice=indice
    def wrap(self,aw,ah):
        self.w=max(70*mm,aw); self.larg_box=self.w-38*mm
        _,self.alt_testo=self.par.wrap(self.larg_box-12*mm,ah)
        self.altezza=max(30*mm,self.alt_testo+12*mm)
        return self.w,self.altezza
    def draw(self):
        c=self.canv; h=self.altezza-2*mm; x=38*mm
        trainer=_mondo_asset(self.ctx,"allenatori",self.indice)
        if trainer: _immagine_asset(c,trainer,17*mm,self.altezza/2,min(36*mm,self.altezza*.92))
        _panel(c,x,1*mm,self.larg_box,h,3*mm,.96,"#72B7E4")
        c.setFillColor(SOLE); c.roundRect(x,1*mm,3*mm,h,1.5*mm,stroke=0,fill=1)
        # centratura verticale reale del paragrafo
        py=1*mm+(h-self.alt_testo)/2
        self.par.drawOn(c,x+6*mm,py)

class PokemonHero(Flowable):
    """Feature illustrata: artwork grandi in uno spazio realmente riservato."""
    def __init__(self,ctx,indice=0,altezza=58*mm):
        super().__init__(); self.ctx=ctx or {}; self.indice=indice; self.altezza=altezza
    def wrap(self,*_): return LARGHEZZA,self.altezza
    def draw(self):
        c=self.canv; _panel(c,0,2*mm,LARGHEZZA,self.altezza-4*mm,4*mm,.90,"#7DB7E3")
        asset=_mondo_asset(self.ctx,"pokemon",self.indice)
        if asset: _immagine_asset(c,asset,LARGHEZZA*.70,self.altezza*.50,55*mm)
        ball=_mondo_asset(self.ctx,"pokeball",self.indice)
        item=_mondo_asset(self.ctx,"oggetti",self.indice)
        trainer=_mondo_asset(self.ctx,"allenatori",self.indice)
        if ball: _immagine_asset(c,ball,LARGHEZZA*.16,self.altezza*.64,28*mm)
        if item: _immagine_asset(c,item,LARGHEZZA*.30,self.altezza*.34,30*mm)
        if trainer: _immagine_asset(c,trainer,LARGHEZZA*.88,self.altezza*.52,47*mm)

class Decoro(Flowable):
    """Separatore essenziale: una riga di inventario, senza stelline o ornamenti cartoon."""

    def __init__(self, ctx=None, seme=1, altezza=42 * mm):
        super().__init__()
        self.ctx, self.seme, self.altezza = ctx or {}, seme, altezza

    def wrap(self, *_):
        return LARGHEZZA, self.altezza

    def draw(self):
        c=self.canv
        _panel(c,0,2*mm,LARGHEZZA,self.altezza-4*mm,4*mm,.90,"#7DB7E3")
        specs=(("pokeball",.27,29*mm),("oggetti",.50,31*mm),("allenatori",.75,43*mm))
        for k,(gruppo,px,size) in enumerate(specs):
            asset=_mondo_asset(self.ctx,gruppo,self.seme+k)
            if asset: _immagine_asset(c,asset,LARGHEZZA*px,self.altezza/2,size)

def _tag(testo, colore, larghezza=21 * mm):
    t = Table([[Paragraph(_t(testo.upper()), _stile_tag(colore))]], colWidths=[larghezza])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colore), ("TOPPADDING", (0, 0), (-1, -1), 1.8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("ROUNDEDCORNERS", [4, 4, 4, 4])]))
    return t


def _tabella(dati, larghezze, colore=colors.HexColor("#2366B1"), allinea_destra_da=1):
    t = Table(dati, colWidths=larghezze, repeatRows=1)
    stile = [
        ("FONTNAME", (0, 0), (-1, 0), SOTTO), ("FONTSIZE", (0, 0), (-1, 0), 7.8),
        ("TEXTCOLOR", (0, 0), (-1, 0), _su(colore)), ("BACKGROUND", (0, 0), (-1, 0), colore), ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("FONTNAME", (0, 1), (-1, -1), TESTO), ("FONTSIZE", (0, 1), (-1, -1), 7.8),
        ("TEXTCOLOR", (0, 1), (-1, -1), INCHIOSTRO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("BOX", (0, 0), (-1, -1), 1.2, colore),
    ]
    if allinea_destra_da is not None:
        stile.append(("ALIGN", (allinea_destra_da, 1), (-1, -1), "RIGHT"))
    for i in range(1, len(dati)):
        stile.append(("BACKGROUND", (0, i), (-1, i), colors.Color(.98,.985,1,alpha=.94) if i % 2 else colors.Color(.92,.96,1,alpha=.94)))
    t.setStyle(TableStyle(stile))
    return t


def _link(nome, url, stile, n=62):
    return Paragraph(f'<link href="{escape(url)}" color="#118AB2">{_t(nome[:n])}</link>', stile)


def _grafico(righe, periodo, titolo):
    """Barre divergenti: i nomi stanno sempre dal lato opposto alla barra, senza sovrapporsi."""
    righe = [r for r in righe if r["variazioni"].get(str(periodo)) is not None][:10]
    if not righe:
        return None
    valori = [r["variazioni"][str(periodo)] for r in righe]
    n = len(righe)
    alt_riga = 7.5 * mm
    altezza = n * alt_riga + 20 * mm
    x0, larg = 14 * mm, LARGHEZZA - 28 * mm
    spazio_nomi = 64 * mm / larg
    vmin, vmax = min(valori + [0]), max(valori + [0])
    if any(v < 0 for v in valori) and vmax < spazio_nomi * (vmax - vmin):
        vmax = spazio_nomi * (-vmin) / (1 - spazio_nomi)
    if any(v >= 0 for v in valori) and -vmin < spazio_nomi * (vmax - vmin):
        vmin = -spazio_nomi * vmax / (1 - spazio_nomi)
    ampiezza = (vmax - vmin) or 1
    xz = x0 + (0 - vmin) / ampiezza * larg

    d = Drawing(LARGHEZZA, altezza)
    d.add(Rect(0, 0, LARGHEZZA, altezza, rx=10, ry=10, fillColor=BIANCO, strokeColor=CIELO, strokeWidth=1.2))
    d.add(String(6 * mm, altezza - 9 * mm, titolo, fontName=SOTTO, fontSize=11, fillColor=INCHIOSTRO))
    base = 7 * mm
    d.add(Line(xz, base - 2 * mm, xz, base + n * alt_riga, strokeColor=GRIGIO, strokeWidth=0.8,
               strokeDashArray=[2, 2]))
    d.add(String(xz, base - 5.5 * mm, "0%", fontName=TESTO, fontSize=7, fillColor=GRIGIO, textAnchor="middle"))
    for i, (r, v) in enumerate(zip(righe, valori)):
        y = base + (n - 1 - i) * alt_riga + 1.5 * mm
        fine = xz + v / ampiezza * larg
        barra, scritta = (VERDE, VERDE_SCURO) if v >= 0 else (ROSSO, ROSSO)
        d.add(Rect(min(xz, fine), y, max(abs(fine - xz), 1), 4.6 * mm, rx=4, ry=4, fillColor=barra, strokeColor=None))
        spazio = (xz - x0) if v >= 0 else (x0 + larg - xz)
        max_car = max(8, int(spazio / (8 * 0.5)) - 2)
        nome = r["nome"] if len(r["nome"]) <= max_car else r["nome"][:max_car - 1] + "…"
        if v >= 0:
            d.add(String(xz - 2.5 * mm, y + 1.3 * mm, nome, fontName=TESTO, fontSize=8, fillColor=INCHIOSTRO,
                         textAnchor="end"))
            d.add(String(fine + 1.5 * mm, y + 1.3 * mm, _perc(v), fontName=TESTO_B, fontSize=8, fillColor=scritta))
        else:
            d.add(String(xz + 2.5 * mm, y + 1.3 * mm, nome, fontName=TESTO, fontSize=8, fillColor=INCHIOSTRO))
            d.add(String(fine - 1.5 * mm, y + 1.3 * mm, _perc(v), fontName=TESTO_B, fontSize=8, fillColor=scritta,
                         textAnchor="end"))
    return d


# ---------- pagine ----------
def _copertina(c, ctx):
    c.saveState(); _sfondo_mappa(c,.62,"#BFEAFF")
    # Full bleed, contrasto acqua/fuoco come nella reference senza replicarne la composizione.
    c.setFillColor(colors.Color(.03,.35,.72,alpha=.16)); c.rect(0,0,W,H,stroke=0,fill=1)
    p=c.beginPath(); p.moveTo(W*.48,0); p.lineTo(W,0); p.lineTo(W,H*.72); p.lineTo(W*.73,H*.56); p.close()
    c.setFillColor(colors.Color(.92,.20,.10,alpha=.32)); c.drawPath(p,stroke=0,fill=1)
    p=c.beginPath(); p.moveTo(0,0); p.lineTo(W*.58,0); p.lineTo(W*.36,H*.55); p.lineTo(0,H*.70); p.close()
    c.setFillColor(colors.Color(.02,.45,.82,alpha=.28)); c.drawPath(p,stroke=0,fill=1)
    # numero/data e claim
    c.setFillColor(BIANCO); c.setFont(TITOLO,12); c.drawString(8*mm,H-12*mm,f"N.{ctx['numero']}")
    c.setFont(TESTO_B,6.5); c.drawString(8*mm,H-18*mm,ctx['data_lunga'].upper())
    c.drawRightString(W-8*mm,H-11*mm,"LA TUA GUIDA SETTIMANALE")
    c.drawRightString(W-8*mm,H-16*mm,"AL MONDO POKÉMON TCG")
    _logo(c,10*mm,H-43*mm,160*mm)
    hero=(_art_piano(ctx,1).get("hero_asset") or _mondo_asset(ctx,"pokemon",0)); support=_mondo_asset(ctx,"pokemon",1); trainer=_mondo_asset(ctx,"allenatori",0)
    ball=_mondo_asset(ctx,"pokeball",0); item=_mondo_asset(ctx,"oggetti",0)
    if support and support!=hero: _immagine_asset(c,support,W-43*mm,H-132*mm,82*mm)
    if hero: _immagine_asset(c,hero,47*mm,H-151*mm,112*mm)
    if trainer: _immagine_asset(c,trainer,W-27*mm,57*mm,48*mm)
    if ball: _immagine_asset(c,ball,21*mm,59*mm,24*mm)
    if item: _immagine_asset(c,item,W-19*mm,92*mm,23*mm)
    # cover line: niente box dashboard, solo ribbon e headline.
    x=10*mm; y=18*mm; w=158*mm
    c.saveState(); c.rotate(-2)
    c.setFillColor(ROSSO); c.roundRect(x,y+52*mm,62*mm,9*mm,2*mm,stroke=0,fill=1)
    c.setFillColor(BIANCO); c.setFont(TITOLO,10); c.drawCentredString(x+31*mm,y+55*mm,"IN PRIMO PIANO")
    title=_t(ctx["apertura"]["titolo"]).upper(); deck=_t(ctx["apertura"]["sottotitolo"]).upper()
    tp=Paragraph(title,ParagraphStyle("cover_title_ref",fontName=TITOLO,fontSize=28,leading=25,textColor=SOLE))
    _,th=tp.wrap(w,48*mm); tp.drawOn(c,x,y+47*mm-th)
    dp=Paragraph(deck,ParagraphStyle("cover_deck_ref",fontName=TESTO_B,fontSize=9.5,leading=10.5,textColor=BIANCO))
    _,dh=dp.wrap(w,24*mm); dp.drawOn(c,x,y+42*mm-th-dh)
    c.restoreState(); c.restoreState()


def _art_piano(ctx, numero):
    pages=((ctx or {}).get("art_direction") or {}).get("pages") or []
    return next((p for p in pages if p.get("page")==numero), {})

def _topographic_map_path():
    """Mappa illustrata di Hoenn; fallback locale a rilievo."""
    realistic=ASSET_DIR/"hoenn_realistic.png"
    if realistic.exists() and realistic.stat().st_size > 10000:
        return realistic
    out=ASSET_DIR/"hoenn_topographic.png"
    ASSET_DIR.mkdir(parents=True,exist_ok=True)
    Wm,Hm=1600,1000

    # mare con profondità e variazioni naturali
    sea_noise=PILImage.effect_noise((400,250),28).resize((Wm,Hm),PILImage.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(8))
    sea=ImageOps.colorize(sea_noise,(63,124,151),(174,216,220)).convert("RGB")

    # sagoma Hoenn organica
    mask=PILImage.new("L",(Wm,Hm),0); md=ImageDraw.Draw(mask)
    coast=[(90,475),(115,330),(220,225),(385,210),(500,145),(610,190),(710,125),(835,190),(920,285),(1110,285),(1225,375),(1160,470),(1235,575),(1075,665),(920,640),(815,760),(665,700),(535,765),(405,680),(270,715),(145,610)]
    md.polygon(coast,fill=255)
    for box in ((1190,230,1300,330),(1315,420,1385,490),(1050,790,1145,870),(790,805,870,875),(470,810,540,860)):
        md.ellipse(box,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(5))

    # elevazione multiscala
    n1=PILImage.effect_noise((400,250),50).resize((Wm,Hm),PILImage.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(13))
    n2=PILImage.effect_noise((200,125),32).resize((Wm,Hm),PILImage.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(25))
    elev=ImageChops.blend(n1,n2,.42)
    # catena montuosa centrale
    ridge=PILImage.new("L",(Wm,Hm),0); rd=ImageDraw.Draw(ridge)
    for cx,cy,rx,ry,v in ((680,420,230,165,150),(780,385,175,135,125),(575,475,150,110,105),(905,420,115,95,80)):
        rd.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=v)
    ridge=ridge.filter(ImageFilter.GaussianBlur(48))
    elev=ImageChops.add(elev,ridge,scale=1.35,offset=-25)
    elev=ImageOps.autocontrast(elev)

    # tavolozza naturale per quota
    terrain=ImageOps.colorize(elev,(52,86,58),(211,198,153),mid=(111,145,83)).convert("RGB")
    # hillshade semplice da differenza di elevazione traslata
    shifted=ImageChops.offset(elev,7,7)
    shade=ImageChops.subtract(elev,shifted,scale=1.0,offset=128).filter(ImageFilter.GaussianBlur(2))
    shade_rgb=ImageOps.colorize(shade,(55,61,53),(245,239,214)).convert("RGB")
    terrain=PILImage.blend(terrain,shade_rgb,.24)
    sea.paste(terrain,(0,0),mask)

    dr=ImageDraw.Draw(sea,"RGBA")
    # foreste semitrasparenti e zone vulcaniche
    for cx,cy,rx,ry in ((330,390,150,100),(395,280,100,75),(955,430,155,100),(1020,550,125,82)):
        dr.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=(30,86,50,45))
    for r,alpha in ((145,34),(100,42),(62,52)):
        dr.ellipse((680-r,420-r*.72,680+r,420+r*.72),outline=(92,76,58,alpha),width=5)

    # fiumi
    for pts in ([(660,300),(635,385),(570,475),(500,575)],[(855,310),(890,400),(980,485),(1080,535)]):
        dr.line(pts,fill=(66,139,172,180),width=6,joint="curve")

    # rotte sottili, realistiche e subordinate al terreno
    routes=[[(190,520),(390,535),(640,470),(900,535),(1150,455)],[(390,535),(420,325),(680,300),(925,270),(1195,285)]]
    for pts in routes:
        dr.line(pts,fill=(78,70,58,100),width=6,joint="curve")
        dr.line(pts,fill=(225,207,166,205),width=3,joint="curve")

    # località discrete
    cities=[(190,520,"Petalburg"),(390,535,"Mauville"),(420,325,"Rustboro"),(640,470,"Mt. Chimney"),(900,535,"Lilycove"),(1150,455,"Mossdeep")]
    for x0,y0,name in cities:
        dr.ellipse((x0-8,y0-8,x0+8,y0+8),fill=(242,235,211,255),outline=(48,71,61,255),width=3)
        dr.rounded_rectangle((x0+13,y0-15,x0+20+len(name)*7,y0+8),5,fill=(245,241,222,190))
        dr.text((x0+18,y0-12),name,fill=(43,61,54,235))

    # cartografia
    dr.text((45,38),"HOENN · CARTA FISICA",fill=(37,57,53,255))
    dr.polygon([(1490,55),(1503,92),(1477,92)],fill=(38,58,54,230)); dr.text((1486,28),"N",fill=(38,58,54,255))
    dr.line((55,930,245,930),fill=(42,61,56,220),width=4); dr.text((105,943),"100 km",fill=(42,61,56,230))
    sea.save(out,"PNG")
    return out

def _art_map(c,x,y,w,h,seed=1):
    path=_topographic_map_path()
    c.saveState()
    c.setFillColor(colors.HexColor("#E9EEE7")); c.roundRect(x-1.2*mm,y-1.2*mm,w+2.4*mm,h+2.4*mm,2.8*mm,stroke=0,fill=1)
    c.drawImage(str(path),x,y,w,h,preserveAspectRatio=False,mask="auto")
    c.setStrokeColor(colors.HexColor("#71847A")); c.setLineWidth(.7); c.roundRect(x,y,w,h,2*mm,stroke=1,fill=0)
    c.restoreState()

def _art_ui(c, x, y, w, h, kind="pokedex"):
    c.saveState()
    c.setFillColor(colors.HexColor("#263238"))
    c.roundRect(x,y,w,h,3*mm,stroke=0,fill=1)
    c.setFillColor(colors.HexColor("#BFE8C0"))
    c.roundRect(x+3*mm,y+3*mm,w-6*mm,h-6*mm,2*mm,stroke=0,fill=1)
    c.setFillColor(colors.HexColor("#214A3A"))
    c.setFont(SOTTO,6.5)
    c.drawString(x+6*mm,y+h-9*mm,kind.upper())
    c.setStrokeColor(colors.HexColor("#5E9273"))
    for i in range(3):
        c.line(x+6*mm,y+h-(14+i*6)*mm,x+w-6*mm,y+h-(14+i*6)*mm)
    c.restoreState()

def _art_overlay(c, ctx, page):
    plan=_art_piano(ctx,page)
    if not plan:
        return
    _art_map(c,W-58*mm,H-54*mm,44*mm,30*mm,page)
    _art_ui(c,MARGINE,H-48*mm,40*mm,23*mm,plan.get("ui","pokedex"))
    asset=plan.get("hero_asset")
    if asset:
        _immagine_asset(c,asset,W-20*mm,H/2+8*mm,42*mm,angolo=5 if page%2 else -5)
    c.setFillColor(colors.Color(1,1,1,alpha=.82))
    c.roundRect(MARGINE+45*mm,H-19*mm,72*mm,8*mm,2*mm,stroke=0,fill=1)
    c.setFillColor(INCHIOSTRO)
    c.setFont(SOTTO,7)
    c.drawString(MARGINE+48*mm,H-16*mm,f"{plan.get('layout','editorial').upper()} · {plan.get('hero_pokemon','POKEMON').upper()}")

def _pagina_interna(c, doc, ctx):
    c.saveState(); page=doc.page; plan=_art_piano(ctx,page)
    # Reference magazine: scenario visibile, velo leggero, testata diagonale ad alto contrasto.
    _sfondo_mappa(c,.28,"#EAF8FC")
    c.setFillColor(colors.Color(.86,.96,1,alpha=.28)); c.rect(0,0,W,H,stroke=0,fill=1)
    # fascia superiore obliqua
    p=c.beginPath(); p.moveTo(0,H); p.lineTo(W,H); p.lineTo(W,H-20*mm); p.lineTo(0,H-14*mm); p.close()
    c.setFillColor(colors.HexColor("#0E4C91")); c.drawPath(p,stroke=0,fill=1)
    p=c.beginPath(); p.moveTo(0,H-14*mm); p.lineTo(W,H-20*mm); p.lineTo(W,H-23*mm); p.lineTo(0,H-17*mm); p.close()
    c.setFillColor(SOLE); c.drawPath(p,stroke=0,fill=1)
    titles={2:("MERCATO","ANDAMENTI, TREND E OPPORTUNITÀ"),3:("NOVITÀ","TUTTE LE NEWS DAL MONDO POKÉMON TCG"),4:("ANALISI","APPROFONDIMENTI E STRATEGIE"),5:("FOCUS COLLEZIONE","LE CARTE E I PRODOTTI DA TENERE D'OCCHIO"),6:("GUIDA MERCATO","CONSIGLI PRATICI PER COLLEZIONISTI")}
    titolo,sottotitolo=titles.get(page,("POKEPUTZU WEEKLY","IL MAGAZINE SETTIMANALE"))
    c.setFillColor(BIANCO); c.setFont(TITOLO,19 if page!=5 else 16); c.drawString(MARGINE,H-11.2*mm,titolo)
    c.setFont(TESTO_B,6.3); c.drawString(MARGINE+2*mm,H-16.3*mm,sottotitolo)
    c.drawRightString(W-MARGINE,H-10.5*mm,f"N.{ctx['numero']} · P.{page}")
    # piccoli elementi illustrati solo nella fascia sicura superiore/destra.
    hero=plan.get("hero_asset")
    if hero and page in (3,4,6): _immagine_asset(c,hero,W-18*mm,H-33*mm,31*mm)
    # Terzo inferiore = scena illustrata, non spazio residuo.
    scene_y=13*mm
    p=c.beginPath(); p.moveTo(0,scene_y); p.lineTo(W,scene_y); p.lineTo(W,154*mm); p.lineTo(0,132*mm); p.close()
    c.setFillColor(colors.Color(.05,.34,.68,alpha=.12)); c.drawPath(p,stroke=0,fill=1)
    hero=plan.get("hero_asset") or _mondo_asset(ctx,"pokemon",max(0,page-1))
    trainer=_mondo_asset(ctx,"allenatori",page-2); ball=_mondo_asset(ctx,"pokeball",page-2); item=_mondo_asset(ctx,"oggetti",page-2)
    if hero: _immagine_asset(c,hero,W-48*mm,91*mm,96*mm)
    if trainer and page in (2,4,6): _immagine_asset(c,trainer,29*mm,83*mm,65*mm)
    if ball and page in (2,3,5): _immagine_asset(c,ball,21*mm,47*mm,29*mm)
    if item and page in (3,5,6): _immagine_asset(c,item,58*mm,43*mm,32*mm)
    # footer chiaro e marchio costante.
    c.setFillColor(colors.Color(1,1,1,alpha=.90)); c.rect(0,0,W,10*mm,stroke=0,fill=1)
    _logo(c,MARGINE,5.8*mm,39*mm,compact=True)
    c.setFillColor(BLU); c.setFont(TESTO_B,6.5); c.drawRightString(W-MARGINE,3.4*mm,str(page))
    c.restoreState()


def _retro(c, ctx):
    c.saveState()
    _mondo_tramonto(c, ctx)
    _logo(c,MARGINE,H-34*mm,132*mm)
    c.setFillColor(BIANCO); c.setFont(TITOLO,23); c.drawString(MARGINE,H-57*mm,"CI VEDIAMO AL PROSSIMO NUMERO!")
    c.setFont(SOTTO,11); c.setFillColor(SOLE)
    c.drawString(MARGINE,H-67*mm,f"N.{ctx['numero']} · PROSSIMO NUMERO {ctx['prossima']}")
    # Nessun pannello fisso: i flowable sottostanti seguono l’altezza reale del testo.
    c.restoreState()


# ---------- rubriche ----------

# ---------- rubriche ----------
def _battuta_iniziale(ctx):
    g = ctx["principale"]
    if g["giorni_storico"] < 30:
        n = g["giorni_storico"]
        return (f"Nota dell'allenatore: Lo storico ha solo {n} giorn{'o' if n == 1 else 'i'}: per ora guardo, "
                "prendo appunti e aspetto il prossimo aggiornamento del mercato.")
    if g["carrello"]["proposte"]:
        return (f"Nota dell'allenatore: Ho tenuto d'occhio {g['monitorati']:,} prodotti e ho trovato qualche idea "
                "per i tuoi 200 €: la trovi qui sotto.".replace(",", "."))
    return (f"Nota dell'allenatore: Ho tenuto d'occhio {g['monitorati']:,} prodotti, ma niente mi ha convinto: "
            "questa settimana non vedo occasioni abbastanza convincenti.".replace(",", "."))


def _box_200(car, st):
    righe = [[Paragraph("Cosa farei con 200 €", st["box_titolo"])],
             [Paragraph(_t("La proposta della settimana, calcolata con regole fisse sui dati: al massimo tre "
                           "acquisti, uno per tipo di segnale, senza superare il budget."), st["occhiello"])]]
    colori = {"Occasione": VERDE, "Novità calda": ROSSO, "Tendenza solida": BLU}
    for x in car["proposte"]:
        scheda = Table([
            [_tag(x["categoria"], colori.get(x["categoria"], VIOLA), 27 * mm),
             Paragraph(f'<link href="{escape(x["link"])}" color="#2B2D42">{_t(x["nome"][:70])}</link>',
                       st["box_nome"]),
             Paragraph(f"{_eur(x['prezzo'])}", ParagraphStyle("pz", parent=st["box_nome"], alignment=2,
                                                              textColor=ROSSO))],
            ["", Paragraph(_t("Perché: " + x["perche"]), st["cella"]), ""],
            ["", Paragraph(_t("Rischio: " + x["rischio"]), ParagraphStyle("rs", parent=st["cella"],
                                                                          textColor=GRIGIO)), ""],
        ], colWidths=[30 * mm, LARGHEZZA - 30 * mm - 28 * mm - 14 * mm, 28 * mm])
        scheda.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("BACKGROUND", (0, 0), (-1, -1), BIANCO),
                                    ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                                    ("BOX", (0, 0), (-1, -1), 1, BLU),
                                    ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        righe.append([scheda])
    if car["proposte"]:
        righe.append([Paragraph(f"<b>Totale: {_eur(car['speso'])}</b>  ·  restano {_eur(car['residuo'])}",
                                ParagraphStyle("tot", parent=st["p"], fontName=TESTO_B))])
    for n in car["note"]:
        righe.append([Paragraph(_t(n), ParagraphStyle("bn2", parent=st["p"], textColor=ROSSO))])
    righe.append([Paragraph(_t("Proposta automatica, non consulenza finanziaria. Il ragionamento completo è "
                               "nell'analisi di Claude della domenica."), st["nota"])])
    box = Table(righe, colWidths=[LARGHEZZA])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
                             ("ROUNDEDCORNERS", [4, 4, 4, 4]),
                             ("BOX", (0, 0), (-1, -1), 1.2, BLU),
                             ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return KeepTogether([box])


def _stato(stato):
    return _tag(stato, COLORE_STATO.get(stato, GRIGIO), 22 * mm)


def _periodo_grafico(cl):
    """Periodo più lungo con sia rialzi sia ribassi; se non c'è, il più lungo con almeno uno dei due."""
    ordine = sorted(C.PERIODI, reverse=True)
    entrambi = [p for p in ordine if cl[str(p)]["rialzi"] and cl[str(p)]["ribassi"]]
    almeno = [p for p in ordine if cl[str(p)]["rialzi"] or cl[str(p)]["ribassi"]]
    return (entrambi or almeno or [None])[0]


def _tabella_classifica(titolo, righe, colore):
    dati = [[titolo, "Prezzo"] + [f"{q}g" for q in C.PERIODI] + ["Incertezza"]]
    st = _stili()
    for r in righe:
        dati.append([_link(r["nome"], r["link"], st["cella"], 52), _eur(r["prezzo"])]
                    + [_perc(r["variazioni"][str(q)]) + ("*" if r["fonti"][str(q)] == "stima" else "")
                       for q in C.PERIODI] + [r["incertezza"]])
    larghezze = [LARGHEZZA - 98 * mm, 20 * mm] + [15 * mm] * len(C.PERIODI) + [18 * mm]
    return KeepTogether([_tabella(dati, larghezze, colore)])


def _layout_profile(ctx, compact=False):
    """Seleziona densità/template dai contenuti reali."""
    g=ctx["principale"]; score=len(ctx.get("sintesi",[]))*2+len(g.get("radar",[]))*3+len(g.get("previsioni",[]))*2+len(g.get("occasioni",[]))*2
    for tipo in ("sigillato","singola"):
        for periodo in C.PERIODI:
            blocco=(g.get("classifiche",{}).get(tipo,{}) or {}).get(str(periodo),{})
            score+=len(blocco.get("rialzi",[]))+len(blocco.get("ribassi",[]))
    mode="data-heavy" if score>52 else ("balanced" if score>24 else "visual")
    return {"mode":mode,"compact":compact,"space":3 if compact else (5 if mode=="data-heavy" else 7),"hero":43*mm if compact else (48*mm if mode=="data-heavy" else 58*mm)}

def _top_rows(g, tipo, limite=5):
    """Top movimenti reali, compatti per una pagina magazine."""
    out=[]
    cl=g.get("classifiche",{}).get(tipo,{})
    for periodo in C.PERIODI:
        blocco=cl.get(str(periodo),{})
        for direzione,segno in (("rialzi",1),("ribassi",-1)):
            for r in blocco.get(direzione,[])[:limite]:
                var=r.get("variazioni",{}).get(str(periodo),0)
                out.append((abs(var),r,periodo,var))
    out.sort(key=lambda x:x[0],reverse=True)
    return out[:limite]

def _market_table(g, st):
    su=_top_rows(g,"singola",4); sig=_top_rows(g,"sigillato",4)
    rows=[["Movimento","Prodotto","Prezzo","Var."]]
    for _,r,p,v in (su+sig)[:7]:
        rows.append([Paragraph("IN SALITA" if v>=0 else "IN DISCESA",st["cella_b"]),
                     Paragraph(_t(r.get("nome","—")),st["cella"]),
                     _eur(r.get("prezzo",0)),_perc(v)])
    return _tabella(rows,[27*mm,91*mm,28*mm,30*mm],BLU)

def _crea_legacy(percorso, ctx, compact=False):
    """Sette template verticali espliciti, modellati sulla reference editoriale."""
    profile=_layout_profile(ctx,compact); ctx["_layout_profile"]=profile; st=_stili(); g=ctx["principale"]
    doc=BaseDocTemplate(percorso,pagesize=A4,title=f"{TESTATA} n. {ctx['numero']}",
        leftMargin=MARGINE,rightMargin=MARGINE,topMargin=25*mm,bottomMargin=15*mm)
    frame=Frame(MARGINE,68*mm,LARGHEZZA,H-94*mm,id="testo",leftPadding=0,rightPadding=0,topPadding=3*mm,bottomPadding=2*mm)
    retro=Frame(MARGINE+7*mm,H-151*mm,LARGHEZZA-14*mm,78*mm,id="retro",leftPadding=0,rightPadding=0)
    doc.addPageTemplates([
        PageTemplate(id="copertina",frames=[Frame(0,0,W,H,id="cover")],onPage=lambda c,d:_copertina(c,ctx)),
        PageTemplate(id="interna",frames=[frame],onPage=lambda c,d:_pagina_interna(c,d,ctx)),
        PageTemplate(id="retro",frames=[retro],onPage=lambda c,d:_retro(c,ctx))])
    E=[NextPageTemplate("interna"),Spacer(1,1),PageBreak()]

    # P2 MERCATO — intro + movimenti + focus, come la reference.
    E += [Rubrica("L'andamento generale","Mercato della settimana",BLU),Spacer(1,3)]
    for r in ctx.get("sintesi",[])[:3]:
        E += [Paragraph("»  "+_t(r),st["p"]),Spacer(1,2)]
    E += [Spacer(1,3),_market_table(g,st),Spacer(1,5)]
    focus=ctx.get("apertura",{})
    E += [Rubrica("Focus settimanale",focus.get("titolo","Il punto sul mercato"),ROSSO),
          Paragraph(_t(focus.get("sottotitolo","")),st["p"]),Spacer(1,4),
          NextPageTemplate("interna"),PageBreak()]

    # P3 NOVITÀ — uscite, annunci, notizie.
    E += [Rubrica("Nuove uscite in arrivo","Radar Pokémon TCG",ROSSO),Spacer(1,3)]
    if g.get("radar"):
        rows=[["Data","Uscita","Mercato"]]
        for u in g["radar"][:4]:
            d=u.get("data",""); rows.append([d[8:10]+"/"+d[5:7] if len(d)>=10 else "—",
                Paragraph(_t(u.get("titolo","")),st["cella"]),_stato(u.get("mercato","radar"))])
        E += [_tabella(rows,[23*mm,116*mm,37*mm],ROSSO),Spacer(1,5)]
    E += [Rubrica("Annunci e segnali","Cosa succede questa settimana",BLU),Spacer(1,2)]
    for n in g.get("notizie",[])[:3]:
        E += [Paragraph(f'<font name="{TESTO_B}">{_t(n.get("titolo",""))}</font><br/><font size="7">{_t(n.get("fonte",""))} · {_t(n.get("data",""))}</font>',st["p"]),Spacer(1,3)]
    E += [PageBreak()]

    # P4 ANALISI — protagonista + dati principali + interpretazione.
    E += [Rubrica("Carta / prodotto protagonista",focus.get("titolo","Analisi della settimana"),ROSSO),Spacer(1,3),
          Spacer(1,2)]
    tops=_top_rows(g,"singola",3)
    if tops:
        rows=[["Prodotto","Prezzo","Periodo","Variazione"]]
        for _,r,p,v in tops: rows.append([Paragraph(_t(r.get("nome","")),st["cella"]),_eur(r.get("prezzo",0)),f"{p}g",_perc(v)])
        E += [_tabella(rows,[86*mm,30*mm,25*mm,35*mm],BLU),Spacer(1,5)]
    E += [Rubrica("Perché è importante","Lettura del dato",SOLE),
          Paragraph(_t(focus.get("sottotitolo","Il movimento va letto insieme a disponibilità, ristampe e profondità dello storico.")),st["p"]),
          Spacer(1,4),Fumetto(_battuta_iniziale(ctx),st,ctx,indice=0),PageBreak()]

    # P5 FOCUS COLLEZIONE — selezione visiva e occasioni.
    E += [Rubrica("Le icone di Hoenn","Focus collezione",BLU),Spacer(1,3),
          Paragraph("Una selezione compatta dei segnali più interessanti emersi dai dati di questa settimana.",st["occhiello"]),
          Spacer(1,4)]
    if g.get("occasioni"):
        rows=[["Prodotto","Offerta","Tendenza","Sconto"]]
        for o in g["occasioni"][:5]:
            rows.append([Paragraph(_t(o.get("nome","")),st["cella"]),_eur(o.get("prezzo_minimo",0)),_eur(o.get("prezzo_tendenza",0)),_perc(-o.get("sconto",0))])
        E += [_tabella(rows,[98*mm,27*mm,27*mm,24*mm],ARANCIO),Spacer(1,5)]
    else:
        E += [Rubrica("Perché collezionare","Qualità prima della quantità",ROSSO),
              Paragraph("Questa settimana non emergono occasioni abbastanza forti: meglio osservare il mercato che riempire la pagina con falsi affari.",st["p"])]
    E += [PageBreak()]

    # P6 GUIDA MERCATO — strategia, rischio, allenatore.
    E += [Rubrica("Strategia della settimana","Guida mercato",BLU),Spacer(1,4),
          _box_200(g.get("carrello",[]),st),Spacer(1,6),
          Fumetto("Monitora prima di comprare: confronta storico, lingua, condizioni e disponibilità. Un prezzo basso da solo non è ancora un'occasione.",st,ctx,indice=1),
          Spacer(1,6),Rubrica("Livello di rischio","Come leggere i segnali",ROSSO)]
    for nota in ctx.get("note_metodo",[])[:4]:
        E += [Paragraph("✓  "+_t(nota),st["p"]),Spacer(1,2.5)]
    E += [NextPageTemplate("retro"),PageBreak()]

    # P7 SALUTO — quarta illustrata, poche note e nessuna tabella.
    E += [Rubrica("Alla prossima settimana","Continueremo a seguire il mercato",BLU),Spacer(1,3)]
    E += [Paragraph("POKEPUTZU WEEKLY torna con nuovi movimenti, uscite, opportunità e approfondimenti dal mondo Pokémon TCG.",ParagraphStyle("bye",parent=st["p"],fontSize=10,leading=13,textColor=BIANCO))]
    doc.build(E)


def crea(percorso, ctx, compact=False):
    """Measured editorial layouts; continuation pages follow the content."""
    from src.editorial import crea as render_editorial
    return render_editorial(percorso, ctx, compact=compact)
