"""Generatore della rivista settimanale a tema Pokémon.

La grafica usa il kit scelto ogni settimana da download_assets.py: Pokémon,
Poké Ball, strumenti e sprite di allenatori. Nessuna mascotte o decorazione
generica rimane nel PDF: ogni elemento ornamentale appartiene al mondo Pokémon.
"""
import math
import random
from pathlib import Path
from PIL import Image as PILImage, ImageDraw, ImageFilter
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
INCHIOSTRO = colors.HexColor("#2B2D42")
CIELO = colors.HexColor("#4CC9F0")
SOLE = colors.HexColor("#FFD23F")
ROSSO = colors.HexColor("#EF476F")
VERDE = colors.HexColor("#06D6A0")
PRATO = colors.HexColor("#7BC950")
VIOLA = colors.HexColor("#8338EC")
ARANCIO = colors.HexColor("#FF8C42")
BLU = colors.HexColor("#118AB2")
CARTA = colors.HexColor("#FFF8E7")
CREMA = colors.HexColor("#FFF1C9")
PASTELLO = colors.HexColor("#FFF3DC")
VERDE_SCURO = colors.HexColor("#03A07A")     # per le scritte verdi su fondo bianco
GRIGIO = colors.HexColor("#6B6F80")
BIANCO = colors.white
LEGNO = colors.HexColor("#C8792B")
LEGNO_SCURO = colors.HexColor("#9C5A1C")
ARCOBALENO = [ROSSO, ARANCIO, SOLE, VERDE, CIELO, VIOLA]
HEX = ["#1F5B4A", "#568D55", "#2F7D55", "#356B66", "#6D8452"]
COLORE_STATO = {"caldo": colors.HexColor("#8A4F3D"), "tiepido": colors.HexColor("#9A7540"),
                "freddo": colors.HexColor("#356B66"), "in arrivo": colors.HexColor("#2F7D55"),
                "da valutare": colors.HexColor("#6D8452"), "nessun dato": colors.HexColor("#66736B")}

W, H = A4
MARGINE = 17 * mm
LARGHEZZA = W - 2 * MARGINE
TESTATA = "POKEPUTZU WEEKLY"
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"


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
def _mondo_giorno(c, ctx=None):
    """Sfondo editoriale Hoenn, morbido e senza griglie/pixel."""
    c.setFillColor(colors.HexColor("#E8E8D5")); c.rect(0,0,W,H,stroke=0,fill=1)
    # grandi forme atmosferiche molto leggere
    c.setFillColor(colors.Color(.38,.58,.39,alpha=.10)); c.circle(25*mm,48*mm,55*mm,stroke=0,fill=1)
    c.setFillColor(colors.Color(.25,.55,.58,alpha=.09)); c.circle(W-18*mm,H-72*mm,62*mm,stroke=0,fill=1)
    c.setFillColor(colors.HexColor("#1F5B4A")); c.rect(0,H-19*mm,W,19*mm,stroke=0,fill=1)
    c.setFillColor(colors.HexColor("#79B86B")); c.rect(0,H-21*mm,W,2*mm,stroke=0,fill=1)

def _mondo_tramonto(c, ctx=None):
    """Quarta di copertina elegante, senza scanline o reticoli."""
    c.setFillColor(colors.HexColor("#183A34")); c.rect(0,0,W,H,stroke=0,fill=1)
    c.setFillColor(colors.HexColor("#2E6757")); c.rect(0,0,W,34*mm,stroke=0,fill=1)
    c.setFillColor(colors.Color(.55,.78,.62,alpha=.08)); c.circle(W*.18,H*.20,48*mm,stroke=0,fill=1)
    c.setFillColor(colors.Color(.25,.58,.60,alpha=.08)); c.circle(W*.82,H*.15,58*mm,stroke=0,fill=1)
    _art_map(c,MARGINE,20*mm,72*mm,48*mm,71)
    hero=(_art_piano(ctx,7).get("hero_asset") if ctx else None) or _mondo_asset(ctx,"pokemon",6)
    c.setFillAlpha(1)
    c.saveState(); c.setFillColor(colors.Color(1,1,1,alpha=.14)); c.circle(W-43*mm,46*mm,38*mm,stroke=0,fill=1); c.restoreState()
    _immagine_asset(c,hero,W-43*mm,46*mm,76*mm)


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
        "sotto": ParagraphStyle("s", fontName=SOTTO, fontSize=14, leading=17, textColor=INCHIOSTRO,
                                spaceBefore=8, spaceAfter=4, keepWithNext=1),
        "box_titolo": ParagraphStyle("bt", fontName=TITOLO, fontSize=22, leading=26, textColor=colors.HexColor("#173C35")),
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
    """Intestazione editoriale ispirata alle interfacce di gioco, senza stile pixel."""

    def __init__(self, occhiello, titolo, colore=ROSSO):
        super().__init__()
        self.occhiello, self.titolo, self.colore = occhiello.upper(), titolo, colore

    def wrap(self, *_):
        return LARGHEZZA, 18 * mm

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor("#173C35"))
        c.roundRect(0, 2 * mm, LARGHEZZA, 14 * mm, 2 * mm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#8CCB78"))
        c.rect(0, 13.5 * mm, LARGHEZZA, 2.5 * mm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#DCEBCB"))
        c.setFont(SOTTO, 7.5)
        c.drawString(5 * mm, 10 * mm, self.occhiello)
        c.setFillColor(BIANCO)
        fs=17
        while fs>10 and pdfmetrics.stringWidth(self.titolo,TITOLO,fs)>LARGHEZZA-10*mm: fs-=.5
        c.setFont(TITOLO,fs)
        c.drawString(5*mm,4.2*mm,self.titolo)

class Fumetto(Flowable):
    """Box dialogo GBA con ritratto allenatore."""

    def __init__(self, testo, st, ctx=None, indice=0):
        super().__init__()
        self.par = Paragraph(_t(testo), st["fumetto"])
        self.ctx = ctx or {}
        self.indice = indice

    def wrap(self, aw, ah):
        self.larg_box = LARGHEZZA - 29 * mm
        _, self.alt_testo = self.par.wrap(self.larg_box - 10 * mm, ah)
        self.altezza = max(self.alt_testo + 10 * mm, 27 * mm)
        return LARGHEZZA, self.altezza

    def draw(self):
        c = self.canv
        trainer=_mondo_asset(self.ctx,"allenatori",self.indice)
        if trainer: _immagine_asset(c,trainer,12*mm,self.altezza/2,24*mm)
        x, y, h = 27 * mm, 2 * mm, self.altezza - 4 * mm
        c.setFillColor(colors.HexColor("#173C35"))
        c.roundRect(x, y, self.larg_box, h, 2 * mm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#E7F0D0"))
        c.roundRect(x + 2 * mm, y + 2 * mm, self.larg_box - 4 * mm, h - 4 * mm, 1 * mm, stroke=0, fill=1)
        self.par.drawOn(c, x + 5 * mm, y + (h - self.alt_testo) / 2)

class PokemonHero(Flowable):
    """Illustrazione Pokémon grande dentro il normale flusso: non può coprire testo o tabelle."""
    def __init__(self,ctx,indice=0,altezza=52*mm):
        super().__init__(); self.ctx=ctx or {}; self.indice=indice; self.altezza=altezza
    def wrap(self,*_): return LARGHEZZA,self.altezza
    def draw(self):
        c=self.canv
        c.setFillColor(colors.HexColor("#DCE7CF")); c.roundRect(0,2*mm,LARGHEZZA,self.altezza-4*mm,4*mm,stroke=0,fill=1)
        c.saveState(); c.setFillColor(colors.Color(.25,.55,.58,alpha=.10)); c.circle(LARGHEZZA*.76,self.altezza*.50,25*mm,stroke=0,fill=1); c.restoreState()
        asset=_mondo_asset(self.ctx,"pokemon",self.indice)
        if asset: _immagine_asset(c,asset,LARGHEZZA*.76,self.altezza*.50,46*mm)
        _art_map(c,8*mm,8*mm,58*mm,self.altezza-16*mm,self.indice+1)

class Decoro(Flowable):
    """Separatore essenziale: una riga di inventario, senza stelline o ornamenti cartoon."""

    def __init__(self, ctx=None, seme=1, altezza=28 * mm):
        super().__init__()
        self.ctx, self.seme, self.altezza = ctx or {}, seme, altezza

    def wrap(self, *_):
        return LARGHEZZA, self.altezza

    def draw(self):
        c=self.canv
        c.setFillColor(colors.HexColor("#DCE7CF")); c.roundRect(0,2*mm,LARGHEZZA,self.altezza-4*mm,3*mm,stroke=0,fill=1)
        specs=(("pokeball",.32,18*mm),("oggetti",.50,18*mm),("allenatori",.70,27*mm))
        for k,(gruppo,px,size) in enumerate(specs):
            asset=_mondo_asset(self.ctx,gruppo,self.seme+k)
            if asset: _immagine_asset(c,asset,LARGHEZZA*px,self.altezza/2,size)

def _tag(testo, colore, larghezza=21 * mm):
    t = Table([[Paragraph(_t(testo.upper()), _stile_tag(colore))]], colWidths=[larghezza])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colore), ("TOPPADDING", (0, 0), (-1, -1), 1.8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("ROUNDEDCORNERS", [4, 4, 4, 4])]))
    return t


def _tabella(dati, larghezze, colore=colors.HexColor("#2F5D50"), allinea_destra_da=1):
    t = Table(dati, colWidths=larghezze, repeatRows=1)
    stile = [
        ("FONTNAME", (0, 0), (-1, 0), SOTTO), ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("TEXTCOLOR", (0, 0), (-1, 0), _su(colore)), ("BACKGROUND", (0, 0), (-1, 0), colore),
        ("FONTNAME", (0, 1), (-1, -1), TESTO), ("FONTSIZE", (0, 1), (-1, -1), 8.6),
        ("TEXTCOLOR", (0, 1), (-1, -1), INCHIOSTRO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("BOX", (0, 0), (-1, -1), 1.2, colore),
    ]
    if allinea_destra_da is not None:
        stile.append(("ALIGN", (allinea_destra_da, 1), (-1, -1), "RIGHT"))
    for i in range(1, len(dati)):
        stile.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F5F3E3") if i % 2 else colors.HexColor("#E6EDD4")))
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
    g = ctx["principale"]
    c.saveState()
    _mondo_giorno(c, ctx)
    # testata dentro la fascia GBA
    c.setFillColor(BIANCO)
    c.setFont(TITOLO, 27)
    c.drawString(MARGINE, H - 13 * mm, "POKEPUTZU WEEKLY")
    c.setFont(TESTO_B, 8)
    c.setFillColor(colors.HexColor("#DCEBCB"))
    c.drawRightString(W - MARGINE, H - 12 * mm, f"N. {ctx['numero']} · {ctx['data_lunga'].upper()}")

    # cartuccia / scheda principale
    x0, y0, pw, ph = MARGINE, H - 132 * mm, 112 * mm, 91 * mm
    c.setFillColor(colors.HexColor("#173C35"))
    c.roundRect(x0, y0, pw, ph, 3 * mm, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#EFF3D8"))
    c.roundRect(x0 + 3 * mm, y0 + 3 * mm, pw - 6 * mm, ph - 6 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#568D55"))
    c.rect(x0 + 3 * mm, y0 + ph - 18 * mm, pw - 6 * mm, 15 * mm, stroke=0, fill=1)
    c.setFillColor(BIANCO)
    c.setFont(SOTTO, 8)
    c.drawString(x0 + 7 * mm, y0 + ph - 12 * mm, "IN PRIMO PIANO")
    titolo = Paragraph(_t(ctx["apertura"]["titolo"]), ParagraphStyle("ct2", fontName=TITOLO, fontSize=15, leading=17.5, textColor=INCHIOSTRO))
    sotto = Paragraph(_t(ctx["apertura"]["sottotitolo"]), ParagraphStyle("cs2", fontName=TESTO, fontSize=8.6, leading=10.5, textColor=GRIGIO))
    area_t=KeepInFrame(pw-14*mm,40*mm,[titolo],mode="shrink")
    area_t.canv=c; _,ht=area_t.wrap(pw-14*mm,40*mm); area_t.drawOn(c,x0+7*mm,y0+ph-24*mm-ht)
    area_s=KeepInFrame(pw-14*mm,18*mm,[sotto],mode="shrink")
    area_s.canv=c; _,hs=area_s.wrap(pw-14*mm,18*mm); area_s.drawOn(c,x0+7*mm,y0+7*mm)
    # colonna visuale dedicata: mappa e Pokémon non possono sovrapporsi ai dati
    _art_map(c, W-69*mm, H-87*mm, 52*mm, 38*mm, ctx["numero"])
    hero=(_art_piano(ctx,1).get("hero_asset") or _mondo_asset(ctx,"pokemon",0))
    if hero:
        _immagine_asset(c,hero,W-42*mm,H-133*mm,54*mm)

    # KPI come menu di stato, non adesivi
    ky = y0 - 30 * mm
    kw = (112 * mm - 6 * mm) / 4
    for i, (numero, etichetta) in enumerate(ctx["kpi"]):
        x = MARGINE + i * (kw + 2 * mm)
        c.setFillColor(colors.HexColor("#173C35"))
        c.roundRect(x, ky, kw, 23 * mm, 2 * mm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#DCEBCB"))
        c.setFont(TITOLO, 17)
        c.drawCentredString(x + kw/2, ky + 12 * mm, str(numero))
        c.setFont(TESTO_B, 6.5)
        c.drawCentredString(x + kw/2, ky + 5 * mm, etichetta.upper())

    # indice stile Pokédex/menu
    sy = ky - 67 * mm
    c.setFillColor(colors.HexColor("#173C35"))
    c.roundRect(MARGINE, sy, 112 * mm, 60 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#EFF3D8"))
    c.roundRect(MARGINE + 3 * mm, sy + 3 * mm, 106 * mm, 54 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#355F4E"))
    c.setFont(SOTTO, 9)
    c.drawString(MARGINE + 7 * mm, sy + 45 * mm, "INDICE / HOENN DATA")
    yy = sy + 37 * mm
    for k, (titolo_r, descrizione) in enumerate(ctx["sommario"], 1):
        c.setFillColor(INCHIOSTRO); c.setFont(TESTO_B, 8.2)
        c.drawString(MARGINE + 8 * mm, yy, f"{k:02d}  {titolo_r[:27]}")
        yy -= 6.3 * mm

    c.setFillColor(colors.HexColor("#173C35"))
    c.rect(0, 0, W, 12 * mm, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#DCEBCB"))
    c.setFont(TESTO_B, 7)
    c.drawString(MARGINE, 4.5 * mm, f"CARDMARKET DATA · {g['giorni_storico']} GIORNI DI STORICO · INFORMATIVO")
    c.restoreState()


def _art_piano(ctx, numero):
    pages=((ctx or {}).get("art_direction") or {}).get("pages") or []
    return next((p for p in pages if p.get("page")==numero), {})

def _topographic_map_path():
    """Genera una carta fisica raster ad alta risoluzione, riutilizzata nel numero."""
    out=ASSET_DIR/"hoenn_topographic.png"
    if out.exists(): return out
    ASSET_DIR.mkdir(parents=True,exist_ok=True)
    Wm,Hm=1200,760
    sea=PILImage.new("RGB",(Wm,Hm),(154,195,204))
    # batimetria/texture acqua
    noise=PILImage.effect_noise((300,190),18).resize((Wm,Hm),PILImage.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(5))
    tint=PILImage.new("RGB",(Wm,Hm),(120,170,182)); sea=PILImage.blend(sea,tint,.12)
    sea=PILImage.blend(sea,noise.convert("RGB"),.045)
    mask=PILImage.new("L",(Wm,Hm),0); d=ImageDraw.Draw(mask)
    coast=[(75,350),(105,235),(215,160),(360,170),(455,110),(565,150),(650,105),(755,160),(835,235),(985,245),(1045,335),(980,415),(1040,500),(910,565),(785,545),(700,625),(575,585),(470,625),(365,555),(250,590),(135,505)]
    d.polygon(coast,fill=255)
    for box in ((1010,210,1080,270),(1080,340,1125,385),(890,650,955,700),(690,655,745,700),(405,660,455,695)): d.ellipse(box,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(8))
    elev=PILImage.effect_noise((300,190),42).resize((Wm,Hm),PILImage.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(10))
    low=PILImage.new("RGB",(Wm,Hm),(157,174,112)); high=PILImage.new("RGB",(Wm,Hm),(105,126,83))
    terrain=PILImage.blend(low,high,.28); terrain=PILImage.blend(terrain,elev.convert("RGB"),.10)
    sea.paste(terrain,(0,0),mask)
    dr=ImageDraw.Draw(sea,"RGBA")
    # catena montuosa centrale con ombreggiatura naturale
    for cx,cy,rx,ry in ((555,330,150,115),(620,315,105,85),(470,360,95,70)):
        dr.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=(95,91,72,45))
        dr.ellipse((cx-rx*.65,cy-ry*.65,cx+rx*.65,cy+ry*.65),outline=(105,96,75,95),width=3)
        dr.ellipse((cx-rx*.40,cy-ry*.40,cx+rx*.40,cy+ry*.40),outline=(115,104,81,90),width=2)
    # foreste
    for cx,cy,rx,ry in ((280,315,115,80),(330,220,85,65),(760,325,120,78),(835,430,95,60)):
        dr.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=(52,103,65,48))
    # strade e rotte sottili
    routes=[[(155,390),(310,410),(510,360),(735,420),(965,350)],[(310,410),(335,255),(555,245),(770,215),(1010,235)]]
    for pts in routes:
        dr.line(pts,fill=(248,232,190,230),width=8,joint="curve"); dr.line(pts,fill=(176,151,111,150),width=2,joint="curve")
    for x0,y0 in [(155,390),(310,410),(335,255),(510,360),(555,245),(735,420),(770,215),(965,350),(1010,235)]:
        dr.ellipse((x0-9,y0-9,x0+9,y0+9),fill=(245,239,216,255),outline=(69,91,74,255),width=3)
    dr.text((42,35),"HOENN · CARTA FISICA",fill=(42,65,61,255))
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
    c.saveState()
    page=doc.page
    # Ogni rubrica ha un ambiente Hoenn distinto, molto tenue per mantenere leggibili i dati.
    temi={
        2:("#E7E6C8","#C7D79A","route"), 3:("#D8E8E1","#9BC9C5","sea"),
        4:("#EEE1C8","#D2B477","volcano"), 5:("#DDE7D2","#A9C58E","forest"),
        6:("#E5E1D1","#B9C7B2","city")
    }
    bg,accent,kind=temi.get(page,("#E8E5D5","#B7C7A5","route"))
    c.setFillColor(colors.HexColor(bg)); c.rect(0,0,W,H,stroke=0,fill=1)
    # texture ambientale, non una griglia neutra
    c.setFillColor(colors.HexColor(accent))
    if kind=="sea":
        for k in range(12):
            yy=18*mm+k*18*mm
            c.setStrokeColor(colors.Color(.20,.45,.48,alpha=.13)); c.setLineWidth(1)
            c.arc(-10*mm,yy,W*.55,yy+8*mm,0,180); c.arc(W*.45,yy,W+10*mm,yy+8*mm,0,180)
    elif kind=="volcano":
        for k in range(7):
            xx=10*mm+k*34*mm
            p=c.beginPath(); p.moveTo(xx,10*mm); p.lineTo(xx+20*mm,42*mm); p.lineTo(xx+40*mm,10*mm); p.close()
            c.setFillColor(colors.Color(.45,.32,.20,alpha=.07)); c.drawPath(p,stroke=0,fill=1)
    elif kind=="forest":
        for k in range(18):
            xx=(8+k*13)*mm; yy=(18+(k%4)*49)*mm
            c.setFillColor(colors.Color(.18,.42,.23,alpha=.07)); c.circle(xx,yy,10*mm,stroke=0,fill=1)
    elif kind=="city":
        for k in range(8):
            c.setFillColor(colors.Color(.25,.35,.30,alpha=.055)); c.rect((8+k*27)*mm,12*mm,(16+(k%3)*5)*mm,(38+(k%4)*13)*mm,stroke=0,fill=1)
    else:
        p=c.beginPath(); p.moveTo(0,30*mm); p.curveTo(W*.25,55*mm,W*.55,18*mm,W,48*mm); p.lineTo(W,0); p.lineTo(0,0); p.close()
        c.setFillColor(colors.Color(.30,.50,.25,alpha=.08)); c.drawPath(p,stroke=0,fill=1)

    # barra titolo
    c.setFillColor(colors.HexColor("#173C35")); c.rect(0,H-18*mm,W,18*mm,stroke=0,fill=1)
    c.setFillColor(colors.HexColor(accent)); c.rect(0,H-20*mm,W,2*mm,stroke=0,fill=1)
    c.setFillColor(BIANCO); c.setFont(SOTTO,11); c.drawString(MARGINE,H-11.5*mm,"POKEPUTZU WEEKLY")
    c.setFont(TESTO_B,7.5); c.setFillColor(colors.HexColor("#DCEBCB"))
    c.drawRightString(W-MARGINE,H-11*mm,f"N.{ctx['numero']} · {ctx['data_lunga']} · P.{page}")

    plan=_art_piano(ctx,page)
    # Nessuna immagine flottante: evita in modo strutturale coperture di testi e tabelle.

    c.setFillColor(colors.HexColor("#173C35")); c.rect(0,0,W,9*mm,stroke=0,fill=1)
    c.setFillColor(colors.HexColor("#DCEBCB")); c.setFont(TESTO_B,6.5)
    c.drawString(MARGINE,3.2*mm,(plan.get("layout") or "editorial").upper())
    c.drawRightString(W-MARGINE,3.2*mm,str(page))
    c.restoreState()


def _retro(c, ctx):
    c.saveState()
    _mondo_tramonto(c, ctx)
    c.setFillColor(BIANCO)
    c.setFont(TITOLO, 31)
    c.drawString(MARGINE, H - 31 * mm, "SALVATAGGIO COMPLETATO")
    c.setFont(SOTTO, 12)
    c.setFillColor(colors.HexColor("#B9DBA5"))
    c.drawString(MARGINE, H - 42 * mm, f"POKEPUTZU WEEKLY N.{ctx['numero']} · PROSSIMO NUMERO {ctx['prossima']}")
    # pannello metodo
    c.setFillColor(colors.HexColor("#102D28"))
    c.roundRect(MARGINE, H - 172 * mm, LARGHEZZA, 108 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#EFF3D8"))
    c.roundRect(MARGINE + 3 * mm, H - 169 * mm, LARGHEZZA - 6 * mm, 102 * mm, 2 * mm, stroke=0, fill=1)
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
    colori = {"Occasione": colors.HexColor("#2F7D55"), "Novità calda": colors.HexColor("#8A4F3D"), "Tendenza solida": colors.HexColor("#356B66")}
    for x in car["proposte"]:
        scheda = Table([
            [_tag(x["categoria"], colori.get(x["categoria"], VIOLA), 27 * mm),
             Paragraph(f'<link href="{escape(x["link"])}" color="#2B2D42">{_t(x["nome"][:70])}</link>',
                       st["box_nome"]),
             Paragraph(f"{_eur(x['prezzo'])}", ParagraphStyle("pz", parent=st["box_nome"], alignment=2,
                                                              textColor=colors.HexColor("#8A4F3D")))],
            ["", Paragraph(_t("Perché: " + x["perche"]), st["cella"]), ""],
            ["", Paragraph(_t("Rischio: " + x["rischio"]), ParagraphStyle("rs", parent=st["cella"],
                                                                          textColor=GRIGIO)), ""],
        ], colWidths=[30 * mm, LARGHEZZA - 30 * mm - 28 * mm - 14 * mm, 28 * mm])
        scheda.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("BACKGROUND", (0, 0), (-1, -1), BIANCO),
                                    ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#568D55")),
                                    ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        righe.append([scheda])
    if car["proposte"]:
        righe.append([Paragraph(f"<b>Totale: {_eur(car['speso'])}</b>  ·  restano {_eur(car['residuo'])}",
                                ParagraphStyle("tot", parent=st["p"], fontName=TESTO_B))])
    for n in car["note"]:
        righe.append([Paragraph(_t(n), ParagraphStyle("bn2", parent=st["p"], textColor=colors.HexColor("#8A4F3D")))])
    righe.append([Paragraph(_t("Proposta automatica, non consulenza finanziaria. Il ragionamento completo è "
                               "nell'analisi di Claude della domenica."), st["nota"])])
    box = Table(righe, colWidths=[LARGHEZZA])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E6EDD4")),
                             ("ROUNDEDCORNERS", [4, 4, 4, 4]),
                             ("BOX", (0, 0), (-1, -1), 2.0, colors.HexColor("#173C35")),
                             ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
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


def crea(percorso, ctx):
    st = _stili()
    g = ctx["principale"]
    doc = BaseDocTemplate(percorso, pagesize=A4, title=f"{TESTATA} n. {ctx['numero']}",
                          leftMargin=MARGINE, rightMargin=MARGINE, topMargin=24 * mm, bottomMargin=18 * mm)
    cornice = Frame(MARGINE, 18 * mm, LARGHEZZA, H - 43 * mm, id="testo", leftPadding=0, rightPadding=0)
    cornice_retro = Frame(MARGINE + 7 * mm, H - 166 * mm, LARGHEZZA - 14 * mm, 96 * mm, id="retro",
                          leftPadding=0, rightPadding=0)
    doc.addPageTemplates([
        PageTemplate(id="copertina", frames=[Frame(0, 0, W, H, id="vuota")],
                     onPage=lambda c, d: _copertina(c, ctx)),
        PageTemplate(id="interna", frames=[cornice], onPage=lambda c, d: _pagina_interna(c, d, ctx)),
        PageTemplate(id="retro", frames=[cornice_retro], onPage=lambda c, d: _retro(c, ctx)),
    ])
    E = [NextPageTemplate("interna"), Spacer(1, 1), PageBreak()]

    # 1. La settimana in breve + 200 euro
    E += [Rubrica("Editoriale", "La settimana in breve", colors.HexColor("#568D55")), Spacer(1, 3)]
    for k, riga in enumerate(ctx["sintesi"]):
        E.append(Paragraph(f'<font color="{HEX[k % 5]}" name="{SOTTO}">»</font>  {_t(riga)}', st["p"]))
        E.append(Spacer(1, 2.5))
    E += [Spacer(1, 6), Fumetto(_battuta_iniziale(ctx), st, ctx, indice=0), Spacer(1, 6),
          _box_200(g["carrello"], st), Spacer(1, 6), Decoro(ctx, seme=ctx["numero"])]

    # 2. Radar uscite
    E += [Spacer(1, 6), CondPageBreak(60 * mm), Rubrica("Radar", "Le uscite in arrivo", colors.HexColor("#356B66")),
          Paragraph(_t("Date di uscita trovate nelle notizie delle ultime settimane (siti ufficiali, italiani e "
                       "internazionali) per i prossimi 60 giorni. Più fonti = più interesse. Controlla sempre la "
                       "data sul link."), st["occhiello"]), Spacer(1, 5)]
    if g["radar"]:
        dati = [["Data", "Uscita", "Fonte", "Fonti", "Mercato"]]
        for u in g["radar"]:
            d = u["data"]
            dati.append([Paragraph(f"{d[8:10]}/{d[5:7]}", st["cella_b"]),
                         _link(u["titolo"], u["link"], st["cella"], 110), Paragraph(_t(u["fonte"]), st["cella"]),
                         str(u["citazioni"]), _stato(u["mercato"])])
        E.append(_tabella(dati, [15 * mm, 88 * mm, 30 * mm, 12 * mm, 31 * mm], colors.HexColor("#356B66"), allinea_destra_da=None))
    else:
        E.append(Paragraph("Nessuna data di uscita trovata nelle notizie di questa settimana.", st["nota"]))

    # 3. Termometro delle novità
    E += [Spacer(1, 10), CondPageBreak(60 * mm), Rubrica("Previsioni", "Il termometro delle novità", colors.HexColor("#6D8452")),
          Paragraph(_t(f"Sigillato comparso su Cardmarket negli ultimi {C.PREVISIONI_GIORNI} giorni: prevendite, "
                       "prodotti in arrivo e appena usciti. Caldo = prezzo in salita o poche offerte sotto la "
                       "tendenza. Freddo = prezzo in calo o molte offerte scontate. In arrivo = ancora nessuna "
                       "vendita."), st["occhiello"]), Spacer(1, 5)]
    if g["previsioni"]:
        dati = [["Prodotto", "Listato", "Prezzo", "Variaz.", "Stato", "Perché"]]
        for p in g["previsioni"]:
            a = p["aggiunto"]
            dati.append([_link(p["nome"], p["link"], st["cella"], 55), f"{a[8:10]}/{a[5:7]}", _eur(p["prezzo"]),
                         _perc(p["variazione"]), _stato(p["stato"]), Paragraph(_t(p["motivo"]), st["cella"])])
        E.append(_tabella(dati, [50 * mm, 13 * mm, 19 * mm, 15 * mm, 25 * mm, 54 * mm], colors.HexColor("#6D8452")))
    else:
        E.append(Paragraph("Nessun prodotto sigillato nuovo nel periodo.", st["nota"]))

    # 4. Il borsino
    E += [Spacer(1, 10), CondPageBreak(110 * mm), Rubrica("Mercato", "Il borsino della settimana", colors.HexColor("#2F7D55")),
          Paragraph(_t("Chi sale e chi scende. Prezzo = tendenza Cardmarket. * = stima dal primo giorno, "
                       "sostituita dallo storico reale man mano che si accumula."), st["occhiello"])]
    for tipo, nome_tipo in (("sigillato", "Sigillato"), ("singola", "Carte singole")):
        cl = g["classifiche"][tipo]
        periodo = _periodo_grafico(cl)
        E.append(Paragraph(nome_tipo, st["sotto"]))
        if periodo is None:
            E.append(Paragraph("Dati non ancora sufficienti.", st["nota"]))
            continue
        c = cl[str(periodo)]
        grafico = _grafico(c["rialzi"] + c["ribassi"], periodo, f"Maggiori movimenti a {periodo} giorni")
        if grafico:
            E += [grafico, Spacer(1, 6)]
        for p in C.PERIODI:
            c = cl[str(p)]
            if c["rialzi"]:
                E += [_tabella_classifica(f"Rialzi a {p} giorni", c["rialzi"], colors.HexColor("#2F7D55")), Spacer(1, 6)]
            if c["ribassi"]:
                E += [_tabella_classifica(f"Ribassi a {p} giorni", c["ribassi"], colors.HexColor("#8A4F3D")), Spacer(1, 6)]
            elif c.get("piu_deboli"):
                E += [_tabella_classifica(f"Più deboli a {p} giorni (nessun calo)", c["piu_deboli"], colors.HexColor("#9A7540")),
                      Spacer(1, 6)]

    # 5. Occasioni
    if g["occasioni"]:
        E += [Spacer(1, 6), CondPageBreak(80 * mm), Rubrica("Affari", "Le occasioni della settimana", colors.HexColor("#8A7545")),
              Paragraph(_t("Sigillato con un'offerta molto sotto il prezzo di tendenza."), st["occhiello"]),
              Spacer(1, 4),
              Fumetto("Occhio: l'offerta più bassa può essere in un'altra lingua o rovinata. Apri il link e "
                      "filtra l'italiano prima di comprare!", st, ctx, indice=1), Spacer(1, 5)]
        dati = [["Prodotto", "Offerta", "Tendenza", "Sconto"]]
        for o in g["occasioni"]:
            dati.append([_link(o["nome"], o["link"], st["cella"], 80), _eur(o["prezzo_minimo"]),
                         _eur(o["prezzo_tendenza"]), _perc(-o["sconto"])])
        E.append(_tabella(dati, [104 * mm, 24 * mm, 24 * mm, 24 * mm], colors.HexColor("#9A7540")))

    # 6. Notizie
    if g["notizie"]:
        E += [Spacer(1, 10), CondPageBreak(45 * mm), Rubrica("Attualità", "Dal mondo Pokémon", colors.HexColor("#356B66")), Spacer(1, 3)]
        for k, n in enumerate(g["notizie"]):
            E.append(Paragraph(f'<font color="{HEX[k % 5]}" name="{SOTTO}" size="8">'
                               f'{_t((n.get("fonte") or "").upper())}  ·  {_t(n["data"])}</font><br/>'
                               f'<link href="{escape(n["link"])}" color="#2B2D42">'
                               f'<font name="{TESTO_B}">{_t(n["titolo"])}</font></link>', st["p"]))
            E.append(Spacer(1, 6))
    E += [Spacer(1, 8), PokemonHero(ctx, indice=5, altezza=50*mm)]

    # 7. Quarta di copertina: come leggere la rivista
    E += [NextPageTemplate("retro"), PageBreak(), Rubrica("Metodo", "Come leggere la rivista", colors.HexColor("#568D55")), Spacer(1, 3)]
    for nota in ctx["note_metodo"]:
        E.append(Paragraph(f'<font color="#568D55" name="{SOTTO}">›</font>  {_t(nota)}', st["p"]))
        E.append(Spacer(1, 4))
    doc.build(E)
