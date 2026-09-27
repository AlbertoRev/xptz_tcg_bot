"""'Il Collezionista': il report settimanale impaginato come una rivista giocosa e colorata.

Tutte le illustrazioni (paesaggi, arcobaleno, carte, stelle, la mascotte Scrigno) sono disegnate
dal codice con forme geometriche: niente immagini esterne. I font li carica src/fonts.py.
"""
import math
import random
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

import config as C
from src import fonts
from src.report import _eur, _perc, _t

def applica_sfondo_e_decorazioni(canvas, doc):
    """Gestisce lo sfondo nella 1a e ultima pagina e le Pokéball trasparenti nelle altre."""
    canvas.saveState()
    pagina_attuale = doc.page
    
    # Se il totale pagine non è ancora calcolato, usiamo un valore stimato o dinamico
    totale_pagine = getattr(doc, 'page_count', 7)
    
    # 1. SFONDO NATURALE SU PRIMA E ULTIMA PAGINA
    if pagina_attuale == 1 or pagina_attuale == totale_pagine:
        sfondo_path = "assets/sfondo_natura.png"
        if os.path.exists(sfondo_path):
            canvas.setFillAlpha(0.12)  # Trasparenza leggera per non coprire il testo
            canvas.drawImage(sfondo_path, 0, 0, width=A4[0], height=A4[1], preserveAspectRatio=False)
            canvas.setFillAlpha(1.0)
            
    # 2. POKÉBALL SPARSE SULLE PAGINE INTERMEDIE (Watermark di sfondo)
    else:
        ball_map = {
            2: "assets/pokeball.png",
            3: "assets/megaball.png",
            4: "assets/ultraball.png",
            5: "assets/masterball.png",
            6: "assets/pokeball.png"
        }
        ball_path = ball_map.get(pagina_attuale, "assets/pokeball.png")
        if os.path.exists(ball_path):
            canvas.setFillAlpha(0.08)  # Trasparenza tenue in sottofondo
            canvas.drawImage(ball_path, A4[0] - 220, 50, width=200, height=200, mask='auto', preserveAspectRatio=True)
            canvas.setFillAlpha(1.0)
            
    canvas.restoreState()
  
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
HEX = ["#EF476F", "#FF8C42", "#06D6A0", "#118AB2", "#8338EC"]
COLORE_STATO = {"caldo": ROSSO, "tiepido": ARANCIO, "freddo": BLU, "in arrivo": VERDE,
                "da valutare": VIOLA, "nessun dato": GRIGIO}

W, H = A4
MARGINE = 17 * mm
LARGHEZZA = W - 2 * MARGINE
TESTATA = "IL COLLEZIONISTA"


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


def _carta(c, x, y, w, angolo, bordo, interno):
    """Carta collezionabile generica, inclinata."""
    h = w * 1.4
    c.saveState()
    c.translate(x, y)
    c.rotate(angolo)
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.15))
    c.roundRect(-w / 2 + 2, -h / 2 - 2, w, h, w * 0.08, stroke=0, fill=1)
    c.setFillColor(bordo)
    c.roundRect(-w / 2, -h / 2, w, h, w * 0.08, stroke=0, fill=1)
    c.setFillColor(interno)
    c.roundRect(-w / 2 + w * 0.08, h * 0.02, w * 0.84, h * 0.42, w * 0.05, stroke=0, fill=1)
    _stella(c, 0, h * 0.23, w * 0.16, BIANCO)
    c.setFillColor(colors.Color(1, 1, 1, alpha=0.75))
    for k in range(3):
        c.roundRect(-w * 0.34, -h * 0.12 - k * h * 0.1, w * 0.68, h * 0.04, h * 0.02, stroke=0, fill=1)
    c.restoreState()


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


def _scrigno(c, x, y, scala=1.0, occhiolino=False):
    """Scrigno, la mascotte: un forziere sorridente. (x, y) = centro della base. Alto circa 24 mm * scala."""
    s = scala * mm
    lw = max(0.6, 1.3 * scala)
    c.saveState()
    c.setStrokeColor(INCHIOSTRO)
    c.setLineWidth(lw)
    # ombra
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.18))
    c.ellipse(x - 14 * s, y - 1.6 * s, x + 14 * s, y + 1.6 * s, stroke=0, fill=1)
    # coperchio a cupola
    p = c.beginPath()
    p.moveTo(x - 13 * s, y + 14 * s)
    p.lineTo(x - 13 * s, y + 17 * s)
    p.curveTo(x - 13 * s, y + 24.5 * s, x + 13 * s, y + 24.5 * s, x + 13 * s, y + 17 * s)
    p.lineTo(x + 13 * s, y + 14 * s)
    p.close()
    c.setFillColor(LEGNO_SCURO)
    c.drawPath(p, stroke=1, fill=1)
    # monete che spuntano dal coperchio
    for dx, col in ((-6, SOLE), (5.5, ARANCIO)):
        c.setFillColor(col)
        c.circle(x + dx * s, y + 22.3 * s, 1.9 * s, stroke=1, fill=1)
    # corpo
    c.setFillColor(LEGNO)
    c.roundRect(x - 12 * s, y, 24 * s, 14 * s, 2 * s, stroke=1, fill=1)
    # fasce dorate
    c.setFillColor(SOLE)
    c.rect(x - 13 * s, y + 12.8 * s, 26 * s, 2.4 * s, stroke=1, fill=1)
    for dx in (-10.5, 8.5):
        c.rect(x + dx * s, y, 2 * s, 12.8 * s, stroke=0, fill=1)
    # serratura
    c.roundRect(x - 2.4 * s, y + 11 * s, 4.8 * s, 4.6 * s, 1 * s, stroke=1, fill=1)
    c.setFillColor(INCHIOSTRO)
    c.circle(x, y + 13.6 * s, 0.7 * s, stroke=0, fill=1)
    # occhi
    for k, dx in enumerate((-4.5, 4.5)):
        if occhiolino and k == 1:
            q = c.beginPath()
            q.moveTo(x + (dx - 1.8) * s, y + 8 * s)
            q.curveTo(x + (dx - 0.8) * s, y + 9.3 * s, x + (dx + 0.8) * s, y + 9.3 * s, x + (dx + 1.8) * s, y + 8 * s)
            c.drawPath(q, stroke=1, fill=0)
            continue
        c.setFillColor(BIANCO)
        c.circle(x + dx * s, y + 8 * s, 2.2 * s, stroke=1, fill=1)
        c.setFillColor(INCHIOSTRO)
        c.circle(x + (dx + 0.3) * s, y + 7.8 * s, 1.2 * s, stroke=0, fill=1)
        c.setFillColor(BIANCO)
        c.circle(x + (dx + 0.7) * s, y + 8.3 * s, 0.45 * s, stroke=0, fill=1)
    # guance
    c.setFillColor(colors.Color(0.94, 0.28, 0.44, alpha=0.45))
    for dx in (-7.6, 7.6):
        c.circle(x + dx * s, y + 5 * s, 1.3 * s, stroke=0, fill=1)
    # sorriso
    q = c.beginPath()
    q.moveTo(x - 3.8 * s, y + 4.6 * s)
    q.curveTo(x - 2 * s, y + 1.8 * s, x + 2 * s, y + 1.8 * s, x + 3.8 * s, y + 4.6 * s)
    c.setLineWidth(lw * 1.1)
    c.drawPath(q, stroke=1, fill=0)
    c.restoreState()
    _scintilla(c, x + 15 * s, y + 22 * s, 2.2 * s, SOLE)
    _scintilla(c, x - 15.5 * s, y + 18 * s, 1.5 * s, BIANCO)


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
def _mondo_giorno(c):
    c.linearGradient(0, H, 0, 0, (colors.HexColor("#8EDCFB"), colors.HexColor("#FFF1C1")), extend=False)
    # sole
    sx, sy = W - 38 * mm, H - 40 * mm
    c.setFillColor(colors.HexColor("#FFE58A"))
    for k in range(12):
        a = math.radians(k * 30)
        p = c.beginPath()
        p.moveTo(sx + 21 * mm * math.cos(a - 0.12), sy + 21 * mm * math.sin(a - 0.12))
        p.lineTo(sx + 31 * mm * math.cos(a), sy + 31 * mm * math.sin(a))
        p.lineTo(sx + 21 * mm * math.cos(a + 0.12), sy + 21 * mm * math.sin(a + 0.12))
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(SOLE)
    c.circle(sx, sy, 18 * mm, stroke=0, fill=1)
    # arcobaleno dietro le colline
    _arcobaleno(c, W * 0.42, 40 * mm, 118 * mm, 5.5 * mm)
    # nuvole
    for x, y, s in ((25 * mm, H - 70 * mm, 1.0), (W - 85 * mm, H - 88 * mm, 0.8), (W / 2, H - 20 * mm, 0.7)):
        _nuvola(c, x, y, s)
    # colline
    _collina(c, 0, W, 62 * mm, 7 * mm, colors.HexColor("#A8DE84"), 0.5, 22 * mm)
    _collina(c, 0, W, 44 * mm, 9 * mm, PRATO, 2.0, 28 * mm)
    _collina(c, 0, W, 24 * mm, 6 * mm, colors.HexColor("#4FA23A"), 4.0, 18 * mm)
    # sentiero
    c.setFillColor(colors.HexColor("#F3D9A4"))
    p = c.beginPath()
    p.moveTo(W / 2 - 22 * mm, 0)
    p.curveTo(W / 2 - 5 * mm, 18 * mm, W / 2 + 20 * mm, 28 * mm, W / 2 + 6 * mm, 46 * mm)
    p.lineTo(W / 2 + 12 * mm, 46 * mm)
    p.curveTo(W / 2 + 30 * mm, 28 * mm, W / 2 + 12 * mm, 16 * mm, W / 2 + 22 * mm, 0)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    rnd = random.Random(7)
    for _ in range(40):
        _ciuffo(c, rnd.uniform(0, W), rnd.uniform(2 * mm, 20 * mm), colors.HexColor("#3A8A2E"), 0.9)
    for _ in range(18):
        _fiore(c, rnd.uniform(0, W), rnd.uniform(3 * mm, 18 * mm), rnd.choice([ROSSO, VIOLA, BIANCO, ARANCIO]))
    # carte in volo e scintille
    for x, y, a, b, i in ((W - 22 * mm, H - 98 * mm, -12, ROSSO, SOLE), (9 * mm, 118 * mm, 14, CIELO, VIOLA),
                          (W - 12 * mm, 60 * mm, 8, VIOLA, ROSSO)):
        _carta(c, x, y, 17 * mm, a, b, i)
    for _ in range(14):
        _scintilla(c, rnd.uniform(0, W), rnd.uniform(70 * mm, H), rnd.uniform(1.5, 3.5) * mm, BIANCO)


def _mondo_tramonto(c):
    c.linearGradient(0, H, 0, 0, (colors.HexColor("#4A2A85"), colors.HexColor("#C4568A"),
                                  colors.HexColor("#FF8C42"), colors.HexColor("#FFD27A")),
                     positions=(0, 0.45, 0.75, 1), extend=False)
    rnd = random.Random(11)
    # prime stelle in alto
    for _ in range(60):
        c.setFillColor(colors.Color(1, 1, 1, alpha=rnd.uniform(0.3, 0.9)))
        c.circle(rnd.uniform(0, W), rnd.uniform(H - 70 * mm, H), rnd.uniform(0.3, 1.0), stroke=0, fill=1)
    for _ in range(6):   # solo sopra la scritta, per non coprirla
        _scintilla(c, rnd.uniform(0, W), rnd.uniform(H - 18 * mm, H - 4 * mm), rnd.uniform(1.5, 2.8) * mm, SOLE)
    # sole che tramonta, con alone
    sx, sy = W * 0.62, 50 * mm
    for r, a in ((46, 0.12), (36, 0.18), (28, 0.25)):
        c.setFillColor(colors.Color(1, 0.85, 0.35, alpha=a))
        c.circle(sx, sy, r * mm, stroke=0, fill=1)
    c.setFillColor(SOLE)
    c.circle(sx, sy, 21 * mm, stroke=0, fill=1)
    # nuvole rosate
    for x, y, s in ((18 * mm, 92 * mm, 0.9), (W - 60 * mm, 100 * mm, 0.7)):
        _nuvola(c, x, y, s, colors.HexColor("#FFC6D3"))
    # colline in controluce
    _collina(c, 0, W, 46 * mm, 8 * mm, colors.HexColor("#7A3F7E"), 1.0, 24 * mm)
    _collina(c, 0, W, 32 * mm, 9 * mm, colors.HexColor("#4E2F6B"), 3.0, 28 * mm)
    _collina(c, 0, W, 16 * mm, 6 * mm, colors.HexColor("#33244F"), 5.0, 18 * mm)
    for _ in range(30):
        _ciuffo(c, rnd.uniform(0, W), rnd.uniform(1 * mm, 12 * mm), colors.HexColor("#271B3D"), 0.9)
    for x, y, a, b, i in ((24 * mm, 70 * mm, -10, VIOLA, CIELO), (W - 20 * mm, 80 * mm, 12, ROSSO, SOLE)):
        _carta(c, x, y, 15 * mm, a, b, i)


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
        "box_titolo": ParagraphStyle("bt", fontName=TITOLO, fontSize=24, leading=28, textColor=ROSSO),
        "box_nome": ParagraphStyle("bn", fontName=SOTTO, fontSize=11.5, leading=14, textColor=INCHIOSTRO),
    }


def _stile_tag(colore):
    return ParagraphStyle("tg", fontName=SOTTO, fontSize=7.8, leading=9.5, textColor=_su(colore),
                          alignment=TA_CENTER)


# ---------- flowable ----------
class Rubrica(Flowable):
    """Intestazione di rubrica: adesivo colorato, titolo cartoon e linea ondulata."""

    def __init__(self, occhiello, titolo, colore=ROSSO):
        super().__init__()
        self.occhiello, self.titolo, self.colore = occhiello.upper(), titolo, colore

    def wrap(self, *_):
        return LARGHEZZA, 21 * mm

    def draw(self):
        c = self.canv
        larg = pdfmetrics.stringWidth(self.occhiello, SOTTO, 9) + 8 * mm
        c.saveState()
        c.translate(0, 15 * mm)
        c.rotate(-2)
        c.setFillColor(self.colore)
        c.roundRect(0, 0, larg, 6 * mm, 3 * mm, stroke=0, fill=1)
        c.setFillColor(_su(self.colore))
        c.setFont(SOTTO, 9)
        c.drawString(4 * mm, 1.8 * mm, self.occhiello)
        c.restoreState()
        c.setFillColor(INCHIOSTRO)
        c.setFont(TITOLO, 21)
        c.drawString(0, 5.5 * mm, self.titolo)
        fine = pdfmetrics.stringWidth(self.titolo, TITOLO, 21) + 4 * mm
        _stella(c, fine + 3 * mm, 8 * mm, 3 * mm, SOLE)
        c.setStrokeColor(self.colore)
        c.setLineWidth(2)
        p = c.beginPath()
        p.moveTo(0, 2 * mm)
        x = 0
        while x < min(fine + 8 * mm, LARGHEZZA):
            p.lineTo(x, 2 * mm + 1.1 * mm * math.sin(x / (2.2 * mm)))
            x += 1.5
        c.drawPath(p, stroke=1, fill=0)


class Fumetto(Flowable):
    """Scrigno che parla: mascotte a sinistra, nuvoletta con il testo a destra."""

    def __init__(self, testo, st):
        super().__init__()
        self.par = Paragraph(_t(testo), st["fumetto"])

    def wrap(self, aw, ah):
        self.larg_nuvola = LARGHEZZA - 34 * mm
        _, self.alt_testo = self.par.wrap(self.larg_nuvola - 10 * mm, ah)
        self.altezza = max(self.alt_testo + 10 * mm, 27 * mm)
        return LARGHEZZA, self.altezza

    def draw(self):
        c = self.canv
        _scrigno(c, 13 * mm, 1.5 * mm, 0.95)
        x, y = 32 * mm, 2 * mm
        h = self.altezza - 4 * mm
        _nuvoletta(c, x, y, self.larg_nuvola, h, 25 * mm, 13 * mm)
        self.par.drawOn(c, x + 5 * mm, y + (h - self.alt_testo) / 2)


class Decoro(Flowable):
    """Striscia decorativa per riempire gli spazi: carte in volo, stelle e scintille."""

    def __init__(self, seme=1, altezza=24 * mm):
        super().__init__()
        self.seme, self.altezza = seme, altezza

    def wrap(self, *_):
        return LARGHEZZA, self.altezza

    def draw(self):
        c = self.canv
        rnd = random.Random(self.seme)
        palette = ARCOBALENO[:]
        rnd.shuffle(palette)
        for k in range(5):
            x = LARGHEZZA * (0.12 + 0.19 * k)
            _carta(c, x, self.altezza / 2, 12 * mm, rnd.uniform(-18, 18), palette[k], palette[(k + 2) % 6])
        for _ in range(12):
            _stella(c, rnd.uniform(0, LARGHEZZA), rnd.uniform(2 * mm, self.altezza - 2 * mm),
                    rnd.uniform(1.2, 2.4) * mm, rnd.choice(ARCOBALENO))


def _tag(testo, colore, larghezza=21 * mm):
    t = Table([[Paragraph(_t(testo.upper()), _stile_tag(colore))]], colWidths=[larghezza])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colore), ("TOPPADDING", (0, 0), (-1, -1), 1.8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("ROUNDEDCORNERS", [4, 4, 4, 4])]))
    return t


def _tabella(dati, larghezze, colore=CIELO, allinea_destra_da=1):
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
        stile.append(("BACKGROUND", (0, i), (-1, i), BIANCO if i % 2 else PASTELLO))
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
    _mondo_giorno(c)

    # nastro con numero e data
    nastro = f"SETTIMANALE DEL MERCATO POKÉMON GCC  ·  N. {ctx['numero']}  ·  {ctx['data_lunga'].upper()}"
    larg = pdfmetrics.stringWidth(nastro, SOTTO, 9) + 10 * mm
    c.saveState()
    c.translate(MARGINE, H - 22 * mm)
    c.rotate(1.5)
    c.setFillColor(ROSSO)
    c.roundRect(0, 0, larg, 7 * mm, 3.5 * mm, stroke=0, fill=1)
    c.setFillColor(BIANCO)
    c.setFont(SOTTO, 9)
    c.drawString(5 * mm, 2.2 * mm, nastro)
    c.restoreState()

    # testata
    _testo_cartoon(c, MARGINE, H - 45 * mm, TESTATA, TITOLO, 46, SOLE, ombra=4)
    c.setFont(SOTTO, 12)
    c.setFillColor(INCHIOSTRO)
    c.drawString(MARGINE + 1 * mm, H - 53 * mm, "Il giornalino di chi colleziona e investe in carte Pokémon")

    # primo piano
    y_top = H - 60 * mm
    titolo = Paragraph(_t(ctx["apertura"]["titolo"]),
                       ParagraphStyle("ct", fontName=TITOLO, fontSize=19, leading=23, textColor=INCHIOSTRO))
    sotto = Paragraph(_t(ctx["apertura"]["sottotitolo"]),
                      ParagraphStyle("cs", fontName=TESTO, fontSize=11, leading=14.5, textColor=GRIGIO))
    lp = LARGHEZZA - 45 * mm
    _, h1 = titolo.wrap(lp - 12 * mm, 80 * mm)
    _, h2 = sotto.wrap(lp - 12 * mm, 40 * mm)
    alt = h1 + h2 + 20 * mm
    _pannello(c, MARGINE, y_top - alt, lp, alt)
    c.setFillColor(ROSSO)
    c.roundRect(MARGINE + 6 * mm, y_top - 10 * mm, 30 * mm, 6 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(BIANCO)
    c.setFont(SOTTO, 8.5)
    c.drawCentredString(MARGINE + 21 * mm, y_top - 8.2 * mm, "IN PRIMO PIANO")
    titolo.drawOn(c, MARGINE + 6 * mm, y_top - 13 * mm - h1)
    sotto.drawOn(c, MARGINE + 6 * mm, y_top - 15 * mm - h1 - h2)
    y = y_top - alt - 8 * mm

    # numeri della settimana: adesivi colorati
    larg_card = (LARGHEZZA - 3 * 4 * mm) / 4
    for i, ((numero, etichetta), colore) in enumerate(zip(ctx["kpi"], (BLU, ROSSO, ARANCIO, VIOLA))):
        x = MARGINE + i * (larg_card + 4 * mm)
        c.saveState()
        c.translate(x + larg_card / 2, y - 12 * mm)
        c.rotate((-2, 1.5, -1, 2)[i])
        c.setFillColor(colors.Color(0, 0, 0, alpha=0.18))
        c.roundRect(-larg_card / 2 + 1.5, -12 * mm - 1.5, larg_card, 24 * mm, 4 * mm, stroke=0, fill=1)
        c.setFillColor(colore)
        c.setStrokeColor(BIANCO)
        c.setLineWidth(2.5)
        c.roundRect(-larg_card / 2, -12 * mm, larg_card, 24 * mm, 4 * mm, stroke=1, fill=1)
        c.setFillColor(_su(colore))
        c.setFont(TITOLO, 22)
        c.drawCentredString(0, -1 * mm, str(numero))
        c.setFont(SOTTO, 8)
        c.drawCentredString(0, -8 * mm, etichetta)
        c.restoreState()
    y -= 32 * mm

    # sommario
    alt_s = 13 * mm + len(ctx["sommario"]) * 7 * mm
    _pannello(c, MARGINE, y - alt_s, LARGHEZZA, alt_s)
    c.setFillColor(VIOLA)
    c.setFont(TITOLO, 13)
    c.drawString(MARGINE + 6 * mm, y - 9 * mm, "IN QUESTO NUMERO")
    yy = y - 17 * mm
    for k, (titolo_r, descrizione) in enumerate(ctx["sommario"]):
        _stella(c, MARGINE + 8 * mm, yy + 1.2 * mm, 2 * mm, ARCOBALENO[k % 6])
        c.setFillColor(INCHIOSTRO)
        c.setFont(SOTTO, 11)
        c.drawString(MARGINE + 12 * mm, yy, titolo_r)
        c.setFillColor(GRIGIO)
        c.setFont(TESTO, 9.5)
        c.drawString(MARGINE + 75 * mm, yy, descrizione)
        yy -= 7 * mm
    y -= alt_s + 6 * mm

    # anteprima 200 euro
    car = g["carrello"]
    righe = car["proposte"] or [None]
    alt_c = 13 * mm + len(righe) * 6.5 * mm
    _pannello(c, MARGINE, y - alt_c, LARGHEZZA, alt_c, colore=SOLE, alpha=1)
    c.setFillColor(INCHIOSTRO)
    c.setFont(TITOLO, 14)
    c.drawString(MARGINE + 6 * mm, y - 9 * mm, "CON 200 € FAREI...")
    yy = y - 16 * mm
    for x in righe:
        if x is None:
            c.setFont(TESTO_B, 10)
            c.drawString(MARGINE + 6 * mm, yy, "Niente: questa settimana li terrei da parte.")
            break
        c.setFont(SOTTO, 9.5)
        c.drawString(MARGINE + 6 * mm, yy, x["categoria"].upper())
        c.setFont(TESTO_B, 10)
        c.drawString(MARGINE + 42 * mm, yy, x["nome"][:58])
        c.drawRightString(W - MARGINE - 6 * mm, yy, _eur(x["prezzo"]))
        yy -= 6.5 * mm

    c.setFillColor(colors.Color(0.1, 0.2, 0.15, alpha=0.55))
    c.roundRect(MARGINE - 3 * mm, 2.5 * mm, LARGHEZZA + 6 * mm, 7 * mm, 3.5 * mm, stroke=0, fill=1)
    c.setFillColor(BIANCO)
    c.setFont(TESTO_B, 8)
    c.drawString(MARGINE, 5 * mm, f"Dati: Cardmarket e siti di notizie  ·  {g['giorni_storico']} giorni di storico  ·  "
                                  "rivista informativa, non è consulenza finanziaria")
    c.restoreState()


def _pagina_interna(c, doc, ctx):
    c.saveState()
    c.setFillColor(CARTA)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    # testata azzurra ondulata, con un bordino giallo che segue l'onda
    for colore, profondita in ((SOLE, 15.5 * mm), (CIELO, 13 * mm)):
        p = c.beginPath()
        p.moveTo(0, H)
        p.lineTo(W, H)
        x = W
        while x >= 0:
            p.lineTo(x, H - profondita + 1.8 * mm * math.sin(x / (9 * mm)))
            x -= 3
        p.lineTo(0, H - profondita + 1.8 * mm * math.sin(0))
        p.close()
        c.setFillColor(colore)
        c.drawPath(p, stroke=0, fill=1)
    _testo_cartoon(c, MARGINE, H - 9 * mm, TESTATA, TITOLO, 14, SOLE, ombra=1.5)
    c.setFillColor(BIANCO)
    c.setFont(SOTTO, 9)
    c.drawRightString(W - MARGINE, H - 8 * mm, f"N. {ctx['numero']}  ·  {ctx['data_lunga']}")
    # prato in fondo pagina
    _collina(c, 0, W, 7 * mm, 1.6 * mm, colors.HexColor("#A8DE84"), doc.page, 14 * mm)
    _collina(c, 0, W, 4 * mm, 1.2 * mm, PRATO, doc.page + 2, 10 * mm)
    rnd = random.Random(doc.page)
    for _ in range(14):
        _fiore(c, rnd.uniform(0, W), rnd.uniform(1.5 * mm, 4 * mm), rnd.choice([ROSSO, SOLE, VIOLA, BIANCO]), 0.7)
    # Scrigno seduto sul prato, alternato a destra e a sinistra
    x_scrigno = MARGINE + 4 * mm if doc.page % 2 == 0 else W / 2
    _scrigno(c, x_scrigno, 2.5 * mm, 0.46, occhiolino=doc.page % 3 == 0)
    # numero di pagina in un bollino giallo
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.18))
    c.circle(W - MARGINE + 0.8, 11 * mm - 0.8, 5.2 * mm, stroke=0, fill=1)
    c.setFillColor(SOLE)
    c.setStrokeColor(BIANCO)
    c.setLineWidth(2)
    c.circle(W - MARGINE, 11 * mm, 5.2 * mm, stroke=1, fill=1)
    c.setFillColor(INCHIOSTRO)
    c.setFont(TITOLO, 10)
    c.drawCentredString(W - MARGINE, 9.6 * mm, str(doc.page))
    # decorazioni nei margini
    for _ in range(9):
        lato = rnd.choice((rnd.uniform(3 * mm, MARGINE - 5 * mm), rnd.uniform(W - MARGINE + 5 * mm, W - 3 * mm)))
        yy = rnd.uniform(25 * mm, H - 30 * mm)
        colore = rnd.choice(ARCOBALENO)
        (_stella if rnd.random() < 0.5 else _scintilla)(c, lato, yy, rnd.uniform(1.5, 3) * mm, colore)
    if doc.page % 2 == 0:
        _carta(c, 7 * mm, H / 2 - 20 * mm, 9 * mm, 12, rnd.choice(ARCOBALENO), BIANCO)
    else:
        _carta(c, W - 7 * mm, H / 2 + 25 * mm, 9 * mm, -12, rnd.choice(ARCOBALENO), BIANCO)
    c.restoreState()


def _retro(c, ctx):
    c.saveState()
    _mondo_tramonto(c)
    _testo_cartoon(c, W / 2, H - 36 * mm, "ARRIVEDERCI", TITOLO, 40, SOLE, ombra=4, centrato=True)
    _testo_cartoon(c, W / 2, H - 50 * mm, "AL PROSSIMO NUMERO!", TITOLO, 24, BIANCO, ombra=3, centrato=True)
    c.setFillColor(BIANCO)
    c.setFont(SOTTO, 12)
    c.drawCentredString(W / 2, H - 60 * mm, f"Il Collezionista n. {ctx['numero'] + 1} arriva domenica {ctx['prossima']}")
    _pannello(c, MARGINE, H - 190 * mm, LARGHEZZA, 122 * mm, alpha=0.95)
    # Scrigno saluta davanti al tramonto
    _scrigno(c, 42 * mm, 14 * mm, 1.35, occhiolino=True)
    testo = "Ci vediamo domenica!"
    larg = pdfmetrics.stringWidth(testo, TESTO_B, 12) + 12 * mm
    _nuvoletta(c, 68 * mm, 36 * mm, larg, 12 * mm, 58 * mm, 30 * mm)
    c.setFillColor(INCHIOSTRO)
    c.setFont(TESTO_B, 12)
    c.drawString(74 * mm, 40.3 * mm, testo)
    c.restoreState()


# ---------- rubriche ----------
def _battuta_iniziale(ctx):
    g = ctx["principale"]
    if g["giorni_storico"] < 30:
        n = g["giorni_storico"]
        return (f"Ciao, sono Scrigno! Lo storico ha solo {n} giorn{'o' if n == 1 else 'i'}: per ora guardo, "
                "prendo appunti e tengo il coperchio ben chiuso.")
    if g["carrello"]["proposte"]:
        return (f"Ciao, sono Scrigno! Ho tenuto d'occhio {g['monitorati']:,} prodotti e ho trovato qualche idea "
                "per i tuoi 200 €: la trovi qui sotto.".replace(",", "."))
    return (f"Ciao, sono Scrigno! Ho tenuto d'occhio {g['monitorati']:,} prodotti, ma niente mi ha convinto: "
            "questa settimana il salvadanaio resta chiuso.".replace(",", "."))


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
                                    ("BOX", (0, 0), (-1, -1), 1, SOLE),
                                    ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        righe.append([scheda])
    if car["proposte"]:
        righe.append([Paragraph(f"<b>Totale: {_eur(car['speso'])}</b>  ·  restano {_eur(car['residuo'])}",
                                ParagraphStyle("tot", parent=st["p"], fontName=TESTO_B))])
    for n in car["note"]:
        righe.append([Paragraph(_t(n), ParagraphStyle("bn2", parent=st["p"], textColor=ROSSO))])
    righe.append([Paragraph(_t("Proposta automatica, non consulenza finanziaria. Il ragionamento completo è "
                               "nell'analisi di Claude della domenica."), st["nota"])])
    box = Table(righe, colWidths=[LARGHEZZA])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CREMA),
                             ("ROUNDEDCORNERS", [12, 12, 12, 12]),
                             ("BOX", (0, 0), (-1, -1), 2.5, SOLE),
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
    cornice_retro = Frame(MARGINE + 7 * mm, H - 186 * mm, LARGHEZZA - 14 * mm, 114 * mm, id="retro",
                          leftPadding=0, rightPadding=0)
    doc.addPageTemplates([
        PageTemplate(id="copertina", frames=[Frame(0, 0, W, H, id="vuota")],
                     onPage=lambda c, d: _copertina(c, ctx)),
        PageTemplate(id="interna", frames=[cornice], onPage=lambda c, d: _pagina_interna(c, d, ctx)),
        PageTemplate(id="retro", frames=[cornice_retro], onPage=lambda c, d: _retro(c, ctx)),
    ])
    E = [NextPageTemplate("interna"), Spacer(1, 1), PageBreak()]

    # 1. La settimana in breve + 200 euro
    E += [Rubrica("Editoriale", "La settimana in breve", VIOLA), Spacer(1, 3)]
    for k, riga in enumerate(ctx["sintesi"]):
        E.append(Paragraph(f'<font color="{HEX[k % 5]}" name="{SOTTO}">»</font>  {_t(riga)}', st["p"]))
        E.append(Spacer(1, 2.5))
    E += [Spacer(1, 6), Fumetto(_battuta_iniziale(ctx), st), Spacer(1, 6),
          _box_200(g["carrello"], st), Spacer(1, 6), Decoro(seme=ctx["numero"])]

    # 2. Radar uscite
    E += [Spacer(1, 6), CondPageBreak(60 * mm), Rubrica("Radar", "Le uscite in arrivo", ROSSO),
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
        E.append(_tabella(dati, [15 * mm, 88 * mm, 30 * mm, 12 * mm, 31 * mm], ROSSO, allinea_destra_da=None))
    else:
        E.append(Paragraph("Nessuna data di uscita trovata nelle notizie di questa settimana.", st["nota"]))

    # 3. Termometro delle novità
    E += [Spacer(1, 10), CondPageBreak(60 * mm), Rubrica("Previsioni", "Il termometro delle novità", ARANCIO),
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
        E.append(_tabella(dati, [50 * mm, 13 * mm, 19 * mm, 15 * mm, 25 * mm, 54 * mm], ARANCIO))
    else:
        E.append(Paragraph("Nessun prodotto sigillato nuovo nel periodo.", st["nota"]))

    # 4. Il borsino
    E += [Spacer(1, 10), CondPageBreak(110 * mm), Rubrica("Mercato", "Il borsino della settimana", VERDE),
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
                E += [_tabella_classifica(f"Rialzi a {p} giorni", c["rialzi"], VERDE), Spacer(1, 6)]
            if c["ribassi"]:
                E += [_tabella_classifica(f"Ribassi a {p} giorni", c["ribassi"], ROSSO), Spacer(1, 6)]
            elif c.get("piu_deboli"):
                E += [_tabella_classifica(f"Più deboli a {p} giorni (nessun calo)", c["piu_deboli"], ARANCIO),
                      Spacer(1, 6)]

    # 5. Occasioni
    if g["occasioni"]:
        E += [Spacer(1, 6), CondPageBreak(80 * mm), Rubrica("Affari", "Le occasioni della settimana", SOLE),
              Paragraph(_t("Sigillato con un'offerta molto sotto il prezzo di tendenza."), st["occhiello"]),
              Spacer(1, 4),
              Fumetto("Occhio: l'offerta più bassa può essere in un'altra lingua o rovinata. Apri il link e "
                      "filtra l'italiano prima di comprare!", st), Spacer(1, 5)]
        dati = [["Prodotto", "Offerta", "Tendenza", "Sconto"]]
        for o in g["occasioni"]:
            dati.append([_link(o["nome"], o["link"], st["cella"], 80), _eur(o["prezzo_minimo"]),
                         _eur(o["prezzo_tendenza"]), _perc(-o["sconto"])])
        E.append(_tabella(dati, [104 * mm, 24 * mm, 24 * mm, 24 * mm], ARANCIO))

    # 6. Notizie
    if g["notizie"]:
        E += [Spacer(1, 10), CondPageBreak(45 * mm), Rubrica("Attualità", "Dal mondo Pokémon", CIELO), Spacer(1, 3)]
        for k, n in enumerate(g["notizie"]):
            E.append(Paragraph(f'<font color="{HEX[k % 5]}" name="{SOTTO}" size="8">'
                               f'{_t((n.get("fonte") or "").upper())}  ·  {_t(n["data"])}</font><br/>'
                               f'<link href="{escape(n["link"])}" color="#2B2D42">'
                               f'<font name="{TESTO_B}">{_t(n["titolo"])}</font></link>', st["p"]))
            E.append(Spacer(1, 6))
    E += [Spacer(1, 6), Decoro(seme=ctx["numero"] + 5)]

    # 7. Quarta di copertina: come leggere la rivista
    E += [NextPageTemplate("retro"), PageBreak(), Rubrica("Metodo", "Come leggere la rivista", VIOLA), Spacer(1, 3)]
    for nota in ctx["note_metodo"]:
        E.append(Paragraph(f'<font color="#FF8C42" name="{SOTTO}">»</font>  {_t(nota)}', st["p"]))
        E.append(Spacer(1, 4))
   # Passa la funzione 'applica_sfondo_e_decorazioni' a sia onFirstPage che onLaterPages:
  doc.build(E, onFirstPage=applica_sfondo_e_decorazioni, onLaterPages=applica_sfondo_e_decorazioni)
