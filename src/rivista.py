"""Il Collezionista: il report settimanale impaginato come una rivista colorata.

Tutte le illustrazioni (paesaggi, carte, stelle, la mascotte Scrigno) sono disegni originali
fatti con forme geometriche: nessuna immagine esterna.
"""
import math
import random
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

import config as C
from src import fonts
from src.report import _eur, _perc, _t

F = fonts.carica()
TESTATA_F, TITOLO_F, CORPO, CORPO_B, SIMBOLI = F["Testata"], F["Titolo"], F["Corpo"], F["CorpoB"], F["Simboli"]

# ---------- palette: colori pieni, da album di figurine ----------
INCHIOSTRO = colors.HexColor("#2B2D42")
CIELO = colors.HexColor("#4CC9F0")
CIELO_CHIARO = colors.HexColor("#CDEFFB")
SOLE = colors.HexColor("#FFD23F")
ROSSO = colors.HexColor("#EF476F")
VERDE = colors.HexColor("#06D6A0")
PRATO = colors.HexColor("#7BC950")
PRATO_SCURO = colors.HexColor("#4E9F3D")
VIOLA = colors.HexColor("#8338EC")
ARANCIO = colors.HexColor("#FF8C42")
BLU = colors.HexColor("#118AB2")
CARTA = colors.HexColor("#FFF8E7")
RIGA = colors.HexColor("#FFF0C2")
LEGNO = colors.HexColor("#C8743A")
LEGNO_CHIARO = colors.HexColor("#E39A5B")
BIANCO = colors.white
COLORE_STATO = {"caldo": ROSSO, "tiepido": ARANCIO, "freddo": BLU, "in arrivo": VIOLA,
                "da valutare": colors.HexColor("#8D99AE"), "nessun dato": colors.HexColor("#8D99AE")}

W, H = A4
MARGINE = 16 * mm
LARGHEZZA = W - 2 * MARGINE
TESTATA = "IL COLLEZIONISTA"


def _alpha(colore, a):
    return colors.Color(colore.red, colore.green, colore.blue, alpha=a)


# =====================================================================
#  DISEGNI ORIGINALI
# =====================================================================
def stella(c, x, y, r, colore, punte=5, bordo=None):
    p = c.beginPath()
    for i in range(punte * 2):
        ang = math.pi / 2 + i * math.pi / punte
        rr = r if i % 2 == 0 else r * 0.45
        px, py = x + rr * math.cos(ang), y + rr * math.sin(ang)
        p.moveTo(px, py) if i == 0 else p.lineTo(px, py)
    p.close()
    c.setFillColor(colore)
    if bordo:
        c.setStrokeColor(bordo)
        c.setLineWidth(max(0.8, r * 0.12))
    c.drawPath(p, stroke=1 if bordo else 0, fill=1)


def scintilla(c, x, y, r, colore):
    p = c.beginPath()
    p.moveTo(x, y + r)
    p.curveTo(x + r * 0.12, y + r * 0.12, x + r * 0.12, y + r * 0.12, x + r, y)
    p.curveTo(x + r * 0.12, y - r * 0.12, x + r * 0.12, y - r * 0.12, x, y - r)
    p.curveTo(x - r * 0.12, y - r * 0.12, x - r * 0.12, y - r * 0.12, x - r, y)
    p.curveTo(x - r * 0.12, y + r * 0.12, x - r * 0.12, y + r * 0.12, x, y + r)
    c.setFillColor(colore)
    c.drawPath(p, stroke=0, fill=1)


def nuvola(c, x, y, s, alpha=0.95):
    c.setFillColor(_alpha(BIANCO, alpha))
    for dx, dy, r in ((0, 0, 0.5), (0.45, 0.15, 0.62), (0.95, 0, 0.5), (0.45, -0.12, 0.45)):
        c.circle(x + dx * s, y + dy * s, r * s, stroke=0, fill=1)


def sole(c, x, y, r):
    c.setStrokeColor(SOLE)
    c.setLineWidth(r * 0.12)
    c.setLineCap(1)
    for i in range(12):
        a = i * math.pi / 6
        c.line(x + math.cos(a) * r * 1.25, y + math.sin(a) * r * 1.25,
               x + math.cos(a) * r * 1.65, y + math.sin(a) * r * 1.65)
    c.setFillColor(SOLE)
    c.circle(x, y, r, stroke=0, fill=1)
    c.setFillColor(_alpha(BIANCO, 0.35))
    c.circle(x - r * 0.3, y + r * 0.3, r * 0.35, stroke=0, fill=1)


def arcobaleno(c, cx, cy, r, spessore):
    c.setLineCap(0)
    for i, col in enumerate((ROSSO, ARANCIO, SOLE, PRATO, CIELO, VIOLA)):
        rr = r - i * spessore
        c.setStrokeColor(_alpha(col, 0.85))
        c.setLineWidth(spessore)
        c.arc(cx - rr, cy - rr, cx + rr, cy + rr, 0, 180)


def colline(c, base, altezza, colore, fase=0.0, onde=3):
    p = c.beginPath()
    p.moveTo(0, 0)
    p.lineTo(0, base)
    passi = 40
    for i in range(1, passi + 1):
        x = W * i / passi
        y = base + altezza * (0.5 + 0.5 * math.sin(fase + onde * math.pi * i / passi))
        p.lineTo(x, y)
    p.lineTo(W, 0)
    p.close()
    c.setFillColor(colore)
    c.drawPath(p, stroke=0, fill=1)


def carta(c, x, y, w, ang, colore):
    """Una carta collezionabile generica, inclinata, con una stella al centro."""
    h = w * 1.4
    c.saveState()
    c.translate(x, y)
    c.rotate(ang)
    c.setFillColor(_alpha(INCHIOSTRO, 0.18))
    c.roundRect(-w / 2 + 2, -h / 2 - 2, w, h, w * 0.08, stroke=0, fill=1)
    c.setFillColor(BIANCO)
    c.setStrokeColor(INCHIOSTRO)
    c.setLineWidth(1)
    c.roundRect(-w / 2, -h / 2, w, h, w * 0.08, stroke=1, fill=1)
    c.setFillColor(colore)
    c.roundRect(-w / 2 + w * 0.08, -h / 2 + w * 0.08, w * 0.84, h - w * 0.16, w * 0.05, stroke=0, fill=1)
    c.setFillColor(_alpha(BIANCO, 0.9))
    c.roundRect(-w * 0.34, h * 0.02, w * 0.68, h * 0.34, w * 0.04, stroke=0, fill=1)
    stella(c, 0, h * 0.19, w * 0.14, colore)
    c.setFillColor(_alpha(BIANCO, 0.8))
    for k in range(3):
        c.roundRect(-w * 0.34, -h * 0.08 - k * h * 0.08, w * (0.68 - k * 0.15), h * 0.035, 1, stroke=0, fill=1)
    c.restoreState()


def scrigno(c, x, y, s, saluta=False):
    """Scrigno, la mascotte della rivista: un forziere sorridente pieno di tesori."""
    w = 1.3 * s
    lw = max(0.8, s * 0.035)
    c.saveState()
    c.setFillColor(_alpha(INCHIOSTRO, 0.15))
    c.ellipse(x + 0.05 * w, y - 0.06 * s, x + 0.95 * w, y + 0.06 * s, stroke=0, fill=1)
    c.setStrokeColor(INCHIOSTRO)
    c.setLineWidth(lw)
    c.setLineJoin(1)
    # tesori che spuntano
    for dx, col in ((0.3, SOLE), (0.5, ROSSO), (0.68, SOLE)):
        c.setFillColor(col)
        c.circle(x + dx * w, y + 0.8 * s, 0.1 * s, stroke=1, fill=1)
    # coperchio aperto
    c.setFillColor(LEGNO_CHIARO)
    p = c.beginPath()
    p.moveTo(x - 0.02 * w, y + 0.62 * s)
    p.curveTo(x + 0.05 * w, y + 1.05 * s, x + 0.95 * w, y + 1.05 * s, x + 1.02 * w, y + 0.62 * s)
    p.lineTo(x + 0.9 * w, y + 0.7 * s)
    p.curveTo(x + 0.8 * w, y + 0.92 * s, x + 0.2 * w, y + 0.92 * s, x + 0.1 * w, y + 0.7 * s)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    # corpo
    c.setFillColor(LEGNO)
    c.roundRect(x, y, w, 0.64 * s, 0.1 * s, stroke=1, fill=1)
    c.setFillColor(SOLE)
    for bx in (0.12, 0.8):
        c.rect(x + bx * w, y, 0.08 * w, 0.64 * s, stroke=1, fill=1)
    # occhi e sorriso
    for ex in (0.36, 0.64):
        c.setFillColor(BIANCO)
        c.circle(x + ex * w, y + 0.38 * s, 0.1 * s, stroke=1, fill=1)
        c.setFillColor(INCHIOSTRO)
        c.circle(x + ex * w + 0.02 * s, y + 0.37 * s, 0.05 * s, stroke=0, fill=1)
        c.setFillColor(BIANCO)
        c.circle(x + ex * w + 0.04 * s, y + 0.4 * s, 0.018 * s, stroke=0, fill=1)
    c.setFillColor(_alpha(ROSSO, 0.35))
    c.ellipse(x + 0.2 * w, y + 0.2 * s, x + 0.28 * w, y + 0.26 * s, stroke=0, fill=1)
    c.ellipse(x + 0.72 * w, y + 0.2 * s, x + 0.8 * w, y + 0.26 * s, stroke=0, fill=1)
    c.setLineCap(1)
    c.arc(x + 0.42 * w, y + 0.12 * s, x + 0.58 * w, y + 0.28 * s, 200, 140)
    if saluta:
        c.setLineWidth(lw * 2.2)
        c.setStrokeColor(LEGNO)
        c.line(x + w, y + 0.35 * s, x + 1.2 * w, y + 0.7 * s)
        c.setFillColor(LEGNO)
        c.setStrokeColor(INCHIOSTRO)
        c.setLineWidth(lw)
        c.circle(x + 1.22 * w, y + 0.74 * s, 0.09 * s, stroke=1, fill=1)
    scintilla(c, x + 1.05 * w, y + 1.05 * s, 0.12 * s, SOLE)
    scintilla(c, x - 0.08 * w, y + 0.95 * s, 0.08 * s, BIANCO)
    c.restoreState()


def testo_contornato(c, testo, x, y, font, dim, riempimento, contorno, spessore, ombra=True):
    if ombra:
        c.setFillColor(_alpha(INCHIOSTRO, 0.35))
        c.setFont(font, dim)
        c.drawString(x + dim * 0.06, y - dim * 0.06, testo)
    t = c.beginText(x, y)
    t.setFont(font, dim)
    t.setTextRenderMode(2)
    c.setFillColor(riempimento)
    c.setStrokeColor(contorno)
    c.setLineWidth(spessore)
    c.setLineJoin(1)
    t.textOut(testo)
    t.setTextRenderMode(0)
    c.drawText(t)


def pillola(c, x, y, testo, fondo, dim=8, colore_testo=BIANCO, padding=3 * mm):
    w = stringWidth(testo, CORPO_B, dim) + 2 * padding
    h = dim * 1.9
    c.setFillColor(fondo)
    c.roundRect(x, y, w, h, h / 2, stroke=0, fill=1)
    c.setFillColor(colore_testo)
    c.setFont(CORPO_B, dim)
    c.drawString(x + padding, y + h * 0.3, testo)
    return w


def _sfumatura(c, colori, y0=0, y1=H):
    """Sfumatura verticale: colori dall'alto verso il basso."""
    passi = 90
    for i in range(passi):
        t = i / (passi - 1)
        seg = t * (len(colori) - 1)
        k = min(int(seg), len(colori) - 2)
        f = seg - k
        a, b = colori[k], colori[k + 1]
        col = colors.Color(a.red + (b.red - a.red) * f, a.green + (b.green - a.green) * f,
                           a.blue + (b.blue - a.blue) * f)
        c.setFillColor(col)
        yy = y1 - (i + 1) * (y1 - y0) / passi
        c.rect(0, yy, W, (y1 - y0) / passi + 1, stroke=0, fill=1)


def mondo_di_giorno(c):
    _sfumatura(c, [colors.HexColor("#3FB6E8"), colors.HexColor("#8FDDF7"), colors.HexColor("#E3F7FD")])
    arcobaleno(c, W * 0.72, 62 * mm, 105 * mm, 7 * mm)
    sole(c, W - 30 * mm, H - 30 * mm, 13 * mm)
    for x, y, s in ((20 * mm, H - 95 * mm, 12 * mm), (W - 75 * mm, H - 62 * mm, 9 * mm),
                    (W * 0.45, H - 150 * mm, 8 * mm), (W - 45 * mm, H - 175 * mm, 10 * mm)):
        nuvola(c, x, y, s)
    colline(c, 52 * mm, 16 * mm, colors.HexColor("#9ADE7B"), fase=0.4, onde=2)
    colline(c, 36 * mm, 14 * mm, PRATO, fase=2.1, onde=3)
    colline(c, 18 * mm, 10 * mm, PRATO_SCURO, fase=1.0, onde=4)
    rng = random.Random(7)
    for _ in range(26):
        x, y = rng.uniform(5 * mm, W - 5 * mm), rng.uniform(4 * mm, 30 * mm)
        c.setFillColor(rng.choice([SOLE, ROSSO, BIANCO, VIOLA]))
        c.circle(x, y, rng.uniform(0.8, 1.6) * mm, stroke=0, fill=1)


def mondo_di_sera(c):
    _sfumatura(c, [colors.HexColor("#240046"), colors.HexColor("#7B2CBF"), colors.HexColor("#F72585"),
                   colors.HexColor("#FFB703")])
    rng = random.Random(11)
    for _ in range(70):
        x, y = rng.uniform(0, W), rng.uniform(H * 0.45, H)
        c.setFillColor(_alpha(BIANCO, rng.uniform(0.4, 1)))
        c.circle(x, y, rng.uniform(0.3, 0.9) * mm, stroke=0, fill=1)
    for _ in range(8):
        scintilla(c, rng.uniform(10 * mm, W - 10 * mm), rng.uniform(H * 0.6, H - 10 * mm), rng.uniform(2, 4) * mm,
                  _alpha(SOLE, 0.9))
    c.setFillColor(colors.HexColor("#FFF3B0"))
    c.circle(W - 35 * mm, H - 40 * mm, 14 * mm, stroke=0, fill=1)
    c.setFillColor(_alpha(colors.HexColor("#E9D98B"), 0.9))
    for dx, dy, r in ((-4, 3, 2.5), (4, -3, 1.8), (1, 6, 1.2)):
        c.circle(W - 35 * mm + dx * mm, H - 40 * mm + dy * mm, r * mm, stroke=0, fill=1)
    colline(c, 50 * mm, 14 * mm, colors.HexColor("#5A189A"), fase=0.8, onde=2)
    colline(c, 32 * mm, 12 * mm, colors.HexColor("#3C096C"), fase=2.4, onde=3)
    colline(c, 16 * mm, 9 * mm, colors.HexColor("#10002B"), fase=1.3, onde=4)
    for _ in range(30):
        c.setFillColor(_alpha(SOLE, rng.uniform(0.5, 1)))
        c.circle(rng.uniform(0, W), rng.uniform(8 * mm, 60 * mm), rng.uniform(0.5, 1.1) * mm, stroke=0, fill=1)


# =====================================================================
#  STILI E ELEMENTI DI IMPAGINAZIONE
# =====================================================================
def _stili():
    return {
        "p": ParagraphStyle("p", fontName=CORPO, fontSize=10.5, leading=14, textColor=INCHOSTRO_T),
        "occhiello": ParagraphStyle("o", fontName=CORPO, fontSize=10, leading=13.5, textColor=GRIGIO_T),
        "cella": ParagraphStyle("c", fontName=CORPO, fontSize=8.6, leading=10.4, textColor=INCHOSTRO_T),
        "cella_b": ParagraphStyle("cb", fontName=CORPO_B, fontSize=8.6, leading=10.4, textColor=INCHOSTRO_T),
        "nota": ParagraphStyle("n", fontName=CORPO, fontSize=8.6, leading=11.5, textColor=GRIGIO_T),
        "sotto": ParagraphStyle("s", fontName=TITOLO_F, fontSize=14, leading=17, textColor=VIOLA, spaceBefore=8,
                                spaceAfter=4, keepWithNext=1),
        "box_titolo": ParagraphStyle("bt", fontName=TITOLO_F, fontSize=24, leading=28, textColor=INCHIOSTRO),
        "box_nome": ParagraphStyle("bn", fontName=CORPO_B, fontSize=11, leading=13.5, textColor=INCHIOSTRO),
        "prezzo": ParagraphStyle("pz", fontName=TITOLO_F, fontSize=13, leading=15, textColor=ROSSO, alignment=TA_RIGHT),
        "titolo_chiusura": ParagraphStyle("tc", fontName=TITOLO_F, fontSize=20, leading=24, textColor=VIOLA),
    }


INCHOSTRO_T = INCHIOSTRO
GRIGIO_T = colors.HexColor("#5A5F73")


class Rubrica(Flowable):
    """Intestazione di rubrica: etichetta a pillola, titolo con ombra colorata e stelline."""

    def __init__(self, occhiello, titolo, colore=ROSSO):
        super().__init__()
        self.occhiello, self.titolo, self.colore = occhiello, titolo, colore

    def wrap(self, *_):
        return LARGHEZZA, 20 * mm

    def draw(self):
        c = self.canv
        pillola(c, 0, 13 * mm, self.occhiello.upper(), self.colore, dim=8)
        c.setFont(TITOLO_F, 23)
        c.setFillColor(_alpha(self.colore, 0.45))
        c.drawString(1.2, 2.5 * mm - 1.2, self.titolo)
        c.setFillColor(INCHIOSTRO)
        c.drawString(0, 2.5 * mm, self.titolo)
        fine = stringWidth(self.titolo, TITOLO_F, 23)
        stella(c, fine + 6 * mm, 6 * mm, 2.6 * mm, SOLE, bordo=INCHIOSTRO)
        scintilla(c, fine + 11 * mm, 10 * mm, 1.6 * mm, self.colore)
        c.setStrokeColor(self.colore)
        c.setLineWidth(1.5)
        c.setDash(1, 3)
        c.setLineCap(1)
        c.line(0, 0.5 * mm, LARGHEZZA, 0.5 * mm)
        c.setDash()


class Pillola(Flowable):
    def __init__(self, testo, colore, larghezza=22 * mm):
        super().__init__()
        self.testo, self.colore, self.larghezza = testo, colore, larghezza

    def wrap(self, *_):
        return self.larghezza, 5.2 * mm

    def draw(self):
        c = self.canv
        c.setFillColor(self.colore)
        c.roundRect(0, 0, self.larghezza, 5.2 * mm, 2.6 * mm, stroke=0, fill=1)
        c.setFillColor(BIANCO)
        c.setFont(CORPO_B, 7.8)
        c.drawCentredString(self.larghezza / 2, 1.6 * mm, self.testo.upper())


class Mascotte(Flowable):
    """Scrigno con un fumetto: riempie gli spazi tra una rubrica e l'altra."""

    def __init__(self, testo, a_destra=False):
        super().__init__()
        self.testo, self.a_destra = testo, a_destra

    def wrap(self, *_):
        return LARGHEZZA, 24 * mm

    def draw(self):
        c = self.canv
        s = 15 * mm
        fumetto_w = min(LARGHEZZA - 40 * mm, stringWidth(self.testo, CORPO_B, 10.5) + 12 * mm)
        if self.a_destra:
            xm = LARGHEZZA - 1.3 * s - 4 * mm
            xf = xm - fumetto_w - 8 * mm
        else:
            xm = 4 * mm
            xf = xm + 1.3 * s + 8 * mm
        scrigno(c, xm, 2 * mm, s)
        yf = 9 * mm
        c.setFillColor(BIANCO)
        c.setStrokeColor(INCHIOSTRO)
        c.setLineWidth(1.2)
        c.roundRect(xf, yf, fumetto_w, 11 * mm, 5 * mm, stroke=1, fill=1)
        p = c.beginPath()
        if self.a_destra:
            p.moveTo(xf + fumetto_w - 2, yf + 3 * mm)
            p.lineTo(xf + fumetto_w + 6 * mm, yf - 1 * mm)
            p.lineTo(xf + fumetto_w - 2, yf + 7 * mm)
        else:
            p.moveTo(xf + 2, yf + 3 * mm)
            p.lineTo(xf - 6 * mm, yf - 1 * mm)
            p.lineTo(xf + 2, yf + 7 * mm)
        c.drawPath(p, stroke=1, fill=1)
        c.setStrokeColor(BIANCO)
        c.setLineWidth(2)
        x_bordo = xf + fumetto_w - 1 if self.a_destra else xf + 1
        c.line(x_bordo, yf + 3.4 * mm, x_bordo, yf + 6.6 * mm)
        c.setFillColor(INCHIOSTRO)
        c.setFont(CORPO_B, 10.5)
        c.drawString(xf + 6 * mm, yf + 3.9 * mm, self.testo)


class Barre(Flowable):
    """Grafico a barre con lo zero al centro.

    Rialzi: barra verde verso destra, scritte a sinistra (nome, poi percentuale accanto alla barra).
    Ribassi: barra rossa verso sinistra, scritte a destra (percentuale accanto alla barra, poi nome).
    """

    RIGA = 7.5 * mm

    def __init__(self, righe, periodo, titolo):
        super().__init__()
        self.righe = [r for r in righe if r["variazioni"].get(str(periodo)) is not None][:12]
        self.periodo, self.titolo = periodo, titolo

    def wrap(self, *_):
        return LARGHEZZA, 16 * mm + len(self.righe) * self.RIGA

    @staticmethod
    def _accorcia(nome, spazio, font, dim):
        if stringWidth(nome, font, dim) <= spazio:
            return nome
        while nome and stringWidth(nome + "…", font, dim) > spazio:
            nome = nome[:-1]
        return nome.rstrip() + "…"

    def draw(self):
        c = self.canv
        if not self.righe:
            return
        valori = [r["variazioni"][str(self.periodo)] for r in self.righe]
        altezza = 16 * mm + len(self.righe) * self.RIGA
        c.setFillColor(colors.HexColor("#F3FBFF"))
        c.setStrokeColor(CIELO)
        c.setLineWidth(1.2)
        c.roundRect(0, 0, LARGHEZZA, altezza, 4 * mm, stroke=1, fill=1)
        c.setFillColor(BLU)
        c.setFont(TITOLO_F, 12)
        c.drawString(5 * mm, altezza - 8 * mm, self.titolo)

        zero = LARGHEZZA / 2
        max_barra = LARGHEZZA * 0.22
        massimo = max(abs(v) for v in valori) or 1
        scala = max_barra / massimo
        top = altezza - 13 * mm
        c.setStrokeColor(colors.HexColor("#9BB7C9"))
        c.setLineWidth(0.8)
        c.setDash(2, 2)
        c.line(zero, 3 * mm, zero, top + 2 * mm)
        c.setDash()
        dim_p, dim_n = 9.5, 8.6
        for i, (r, v) in enumerate(zip(self.righe, valori)):
            y = top - (i + 1) * self.RIGA + 2 * mm
            lung = max(abs(v) * scala, 1.5)
            colore = VERDE if v >= 0 else ROSSO
            valore = _perc(v)
            larg_p = stringWidth(valore, TITOLO_F, dim_p)
            c.setFillColor(colore)
            if v >= 0:
                # barra a destra dello zero, scritte a sinistra: nome ... percentuale | barra
                c.roundRect(zero, y, lung, 5 * mm, 2 * mm, stroke=0, fill=1)
                x_p = zero - 2.5 * mm - larg_p
                c.setFont(TITOLO_F, dim_p)
                c.drawString(x_p, y + 1.4 * mm, valore)
                spazio = x_p - 2.5 * mm - 5 * mm
                nome = self._accorcia(r["nome"], spazio, CORPO, dim_n)
                c.setFillColor(INCHIOSTRO)
                c.setFont(CORPO, dim_n)
                c.drawRightString(x_p - 2.5 * mm, y + 1.4 * mm, nome)
            else:
                # barra a sinistra dello zero, scritte a destra: barra | percentuale ... nome
                c.roundRect(zero - lung, y, lung, 5 * mm, 2 * mm, stroke=0, fill=1)
                x_p = zero + 2.5 * mm
                c.setFont(TITOLO_F, dim_p)
                c.drawString(x_p, y + 1.4 * mm, valore)
                x_n = x_p + larg_p + 2.5 * mm
                spazio = LARGHEZZA - 5 * mm - x_n
                nome = self._accorcia(r["nome"], spazio, CORPO, dim_n)
                c.setFillColor(INCHIOSTRO)
                c.setFont(CORPO, dim_n)
                c.drawString(x_n, y + 1.4 * mm, nome)


def _tabella(dati, larghezze, colore=CIELO, allinea_destra_da=1):
    t = Table(dati, colWidths=larghezze, repeatRows=1)
    stile = [
        ("FONTNAME", (0, 0), (-1, 0), CORPO_B), ("FONTSIZE", (0, 0), (-1, 0), 8.8),
        ("TEXTCOLOR", (0, 0), (-1, 0), BIANCO), ("BACKGROUND", (0, 0), (-1, 0), colore),
        ("FONTNAME", (0, 1), (-1, -1), CORPO), ("FONTSIZE", (0, 1), (-1, -1), 8.6),
        ("TEXTCOLOR", (0, 1), (-1, -1), INCHIOSTRO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("BOX", (0, 0), (-1, -1), 1.2, colore),
    ]
    if allinea_destra_da is not None:
        stile.append(("ALIGN", (allinea_destra_da, 1), (-1, -1), "RIGHT"))
    for i in range(1, len(dati)):
        stile.append(("BACKGROUND", (0, i), (-1, i), RIGA if i % 2 == 0 else BIANCO))
    t.setStyle(TableStyle(stile))
    return t


def _link(nome, url, stile, n=62):
    return Paragraph(f'<link href="{escape(url)}" color="#1B6FA8">{_t(nome[:n])}</link>', stile)


def _pallino(colore="#EF476F"):
    return f'<font name="{SIMBOLI}" color="{colore}">★</font>'


# =====================================================================
#  PAGINE
# =====================================================================
def _copertina(c, ctx):
    g = ctx["principale"]
    c.saveState()
    mondo_di_giorno(c)
    # carte che volano ai bordi
    for x, y, w, a, col in ((W - 22 * mm, H - 118 * mm, 17 * mm, -14, ROSSO), (14 * mm, H - 128 * mm, 14 * mm, 12, VIOLA),
                            (W - 14 * mm, 88 * mm, 13 * mm, 18, SOLE), (12 * mm, 70 * mm, 15 * mm, -10, CIELO)):
        carta(c, x, y, w, a, col)
    for x, y, r, col in ((W * 0.62, H - 22 * mm, 2.5, BIANCO), (22 * mm, H - 58 * mm, 2, SOLE),
                         (W - 55 * mm, H - 100 * mm, 2.2, BIANCO)):
        scintilla(c, x, y, r * mm, col)

    # testata
    pillola(c, MARGINE, H - 24 * mm, f"IL SETTIMANALE DEL COLLEZIONISMO POKÉMON  ·  N. {ctx['numero']}  ·  "
                                     f"{ctx['data_lunga'].upper()}", ROSSO, dim=8.5)
    dim_testata = 40
    while stringWidth(TESTATA, TESTATA_F, dim_testata) > LARGHEZZA - 30 * mm and dim_testata > 20:
        dim_testata -= 1
    testo_contornato(c, TESTATA, MARGINE, H - 48 * mm, TESTATA_F, dim_testata, SOLE, INCHIOSTRO, 2.4)

    # primo piano: il riquadro si adatta al testo
    titolo = Paragraph(_t(ctx["apertura"]["titolo"]),
                       ParagraphStyle("ct", fontName=TITOLO_F, fontSize=21, leading=24, textColor=INCHIOSTRO))
    _, h = titolo.wrap(LARGHEZZA - 24 * mm, 50 * mm)
    sotto = Paragraph(_t(ctx["apertura"]["sottotitolo"]),
                      ParagraphStyle("cs", fontName=CORPO, fontSize=11, leading=14, textColor=GRIGIO_T))
    _, h2 = sotto.wrap(LARGHEZZA - 24 * mm, 20 * mm)
    alt_pannello = h + h2 + 20 * mm
    cima = H - 58 * mm
    pannello_y = cima - alt_pannello
    c.setFillColor(_alpha(BIANCO, 0.93))
    c.setStrokeColor(INCHIOSTRO)
    c.setLineWidth(1.5)
    c.roundRect(MARGINE, pannello_y, LARGHEZZA - 12 * mm, alt_pannello, 6 * mm, stroke=1, fill=1)
    pillola(c, MARGINE + 5 * mm, cima - 9 * mm, "IN PRIMO PIANO", VIOLA, dim=8)
    titolo.drawOn(c, MARGINE + 5 * mm, cima - 12 * mm - h)
    sotto.drawOn(c, MARGINE + 5 * mm, cima - 14 * mm - h - h2)

    # i numeri della settimana: quattro "gettoni" colorati
    y = pannello_y - 33 * mm
    card_w = (LARGHEZZA - 3 * 4 * mm) / 4
    for i, ((numero, etichetta), col) in enumerate(zip(ctx["kpi"], (CIELO, ROSSO, VERDE, VIOLA))):
        x = MARGINE + i * (card_w + 4 * mm)
        c.setFillColor(_alpha(INCHIOSTRO, 0.2))
        c.roundRect(x + 1.2 * mm, y - 1.2 * mm, card_w, 25 * mm, 5 * mm, stroke=0, fill=1)
        c.setFillColor(col)
        c.setStrokeColor(INCHIOSTRO)
        c.setLineWidth(1.5)
        c.roundRect(x, y, card_w, 25 * mm, 5 * mm, stroke=1, fill=1)
        testo_contornato(c, str(numero), x + 4 * mm, y + 11 * mm, TITOLO_F, 25, BIANCO, INCHIOSTRO, 1.2, ombra=False)
        c.setFillColor(BIANCO)
        c.setFont(CORPO_B, 9)
        c.drawString(x + 4 * mm, y + 4.5 * mm, etichetta)

    # sommario
    y_som = y - 8 * mm
    alt_som = 10 * mm + len(ctx["sommario"]) * 7 * mm
    c.setFillColor(_alpha(BIANCO, 0.9))
    c.setStrokeColor(INCHIOSTRO)
    c.roundRect(MARGINE, y_som - alt_som, LARGHEZZA * 0.58, alt_som, 5 * mm, stroke=1, fill=1)
    c.setFillColor(ROSSO)
    c.setFont(TITOLO_F, 13)
    c.drawString(MARGINE + 5 * mm, y_som - 8 * mm, "In questo numero")
    yy = y_som - 15 * mm
    for i, (titolo_r, _) in enumerate(ctx["sommario"]):
        stella(c, MARGINE + 7 * mm, yy + 1.2 * mm, 1.8 * mm, (SOLE, CIELO, ROSSO, VERDE, VIOLA, ARANCIO)[i % 6],
               bordo=INCHIOSTRO)
        c.setFillColor(INCHIOSTRO)
        c.setFont(CORPO_B, 10.5)
        c.drawString(MARGINE + 11 * mm, yy, titolo_r)
        yy -= 7 * mm

    # biglietto: cosa farei con 200 euro
    car = g["carrello"]
    bx, bw = MARGINE + LARGHEZZA * 0.62, LARGHEZZA * 0.38
    c.setFillColor(SOLE)
    c.setStrokeColor(INCHIOSTRO)
    c.setLineWidth(1.5)
    c.roundRect(bx, y_som - alt_som, bw, alt_som, 5 * mm, stroke=1, fill=1)
    c.setDash(3, 2)
    c.roundRect(bx + 2 * mm, y_som - alt_som + 2 * mm, bw - 4 * mm, alt_som - 4 * mm, 4 * mm, stroke=1, fill=0)
    c.setDash()
    c.setFillColor(INCHIOSTRO)
    c.setFont(TITOLO_F, 14)
    c.drawString(bx + 6 * mm, y_som - 9 * mm, "Con 200 € farei…")
    yy = y_som - 17 * mm
    if car["proposte"]:
        for x in car["proposte"]:
            c.setFont(CORPO_B, 8.5)
            c.drawString(bx + 6 * mm, yy, x["categoria"].upper())
            c.setFont(TITOLO_F, 10)
            c.drawRightString(bx + bw - 6 * mm, yy, _eur(x["prezzo"]))
            c.setFont(CORPO, 8.5)
            nome = x["nome"]
            while stringWidth(nome, CORPO, 8.5) > bw - 12 * mm:
                nome = nome[:-2]
            c.drawString(bx + 6 * mm, yy - 4 * mm, nome)
            yy -= 11 * mm
    else:
        c.setFont(CORPO_B, 9.5)
        c.drawString(bx + 6 * mm, yy, "...niente: li terrei")
        c.drawString(bx + 6 * mm, yy - 5 * mm, "da parte questa settimana.")

    scrigno(c, W - 50 * mm, 8 * mm, 22 * mm)
    c.setFillColor(_alpha(INCHIOSTRO, 0.75))
    c.roundRect(MARGINE - 2 * mm, 3 * mm, 108 * mm, 6 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(BIANCO)
    c.setFont(CORPO_B, 7.5)
    c.drawString(MARGINE + 1 * mm, 5 * mm, f"Dati Cardmarket e notizie  ·  {g['giorni_storico']} giorni di storico  ·  "
                                         "non è consulenza finanziaria")
    c.restoreState()


def _pagina_interna(c, doc, ctx):
    c.saveState()
    c.setFillColor(CARTA)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    # puntini da album di figurine
    c.setFillColor(_alpha(colors.HexColor("#F3D9A4"), 0.6))
    for i in range(0, int(W / (8 * mm)) + 1):
        for j in range(0, int(H / (8 * mm)) + 1):
            if i < 2 or i > W / (8 * mm) - 3:
                c.circle(4 * mm + i * 8 * mm, 4 * mm + j * 8 * mm, 0.5 * mm, stroke=0, fill=1)
    # testata ondulata
    p = c.beginPath()
    p.moveTo(0, H)
    p.lineTo(W, H)
    p.lineTo(W, H - 14 * mm)
    onde, seg = 7, W / 7
    for i in range(onde):
        x1 = W - i * seg
        p.curveTo(x1 - seg * 0.25, H - 18 * mm, x1 - seg * 0.75, H - 10 * mm, x1 - seg, H - 14 * mm)
    p.close()
    c.setFillColor(CIELO)
    c.drawPath(p, stroke=0, fill=1)
    testo_contornato(c, TESTATA, MARGINE, H - 10 * mm, TESTATA_F, 15, SOLE, INCHIOSTRO, 1.1)
    c.setFillColor(BIANCO)
    c.setFont(CORPO_B, 9)
    c.drawRightString(W - MARGINE, H - 9 * mm, f"N. {ctx['numero']}  ·  {ctx['data_lunga']}")
    rng = random.Random(doc.page)
    for _ in range(3):
        scintilla(c, rng.uniform(70 * mm, W - 70 * mm), H - rng.uniform(4, 9) * mm, rng.uniform(1.2, 2) * mm, BIANCO)
    # carte e stelle nei bordi
    lato = MARGINE / 2
    carta(c, lato if doc.page % 2 else W - lato, H - rng.uniform(60, 120) * mm, 9 * mm,
          rng.uniform(-15, 15), rng.choice([ROSSO, VIOLA, CIELO, SOLE]))
    stella(c, W - lato if doc.page % 2 else lato, rng.uniform(80, 180) * mm, 2.8 * mm,
           rng.choice([SOLE, ROSSO, VERDE]), bordo=INCHIOSTRO)
    scintilla(c, lato if doc.page % 2 == 0 else W - lato, rng.uniform(190, 240) * mm, 2 * mm, VIOLA)
    # prato in fondo
    c.setFillColor(PRATO)
    p = c.beginPath()
    p.moveTo(0, 0)
    p.lineTo(0, 7 * mm)
    for i in range(1, 41):
        x = W * i / 40
        p.lineTo(x, 7 * mm + 2.5 * mm * math.sin(doc.page + i * math.pi / 5))
    p.lineTo(W, 0)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(PRATO_SCURO)
    c.rect(0, 0, W, 3.5 * mm, stroke=0, fill=1)
    # numero di pagina in un bollino
    c.setFillColor(SOLE)
    c.setStrokeColor(INCHIOSTRO)
    c.setLineWidth(1.2)
    c.circle(W / 2, 8 * mm, 5 * mm, stroke=1, fill=1)
    c.setFillColor(INCHIOSTRO)
    c.setFont(TITOLO_F, 11)
    c.drawCentredString(W / 2, 6.6 * mm, str(doc.page))
    if doc.page % 2 == 0:
        scrigno(c, W - MARGINE - 16 * mm, 4 * mm, 11 * mm)
    c.restoreState()


def _chiusura(c, doc, ctx):
    c.saveState()
    mondo_di_sera(c)
    testo_contornato(c, "Arrivederci al prossimo numero!", MARGINE, H - 30 * mm, TESTATA_F, 24, SOLE, INCHIOSTRO, 1.8)
    c.setFillColor(BIANCO)
    c.setFont(CORPO_B, 11)
    c.drawString(MARGINE, H - 40 * mm, f"Il Collezionista n. {ctx['numero']} ti aspetta ogni domenica mattina.")
    c.setFillColor(_alpha(BIANCO, 0.94))
    c.setStrokeColor(INCHIOSTRO)
    c.setLineWidth(1.5)
    c.roundRect(MARGINE - 4 * mm, 80 * mm, LARGHEZZA + 8 * mm, H - 135 * mm, 7 * mm, stroke=1, fill=1)
    scrigno(c, W / 2 - 18 * mm, 18 * mm, 26 * mm, saluta=True)
    for x in (30 * mm, W - 40 * mm):
        carta(c, x, 40 * mm, 13 * mm, 10 if x < W / 2 else -12, SOLE if x < W / 2 else CIELO)
    c.restoreState()


# =====================================================================
#  RUBRICHE
# =====================================================================
def _box_200(car, st):
    righe = [[Paragraph("Cosa farei con 200 €", st["box_titolo"])],
             [Paragraph(_t("La proposta della settimana: al massimo tre acquisti, uno per tipo di segnale, "
                           "calcolati con regole fisse senza superare il budget."), st["occhiello"])]]
    colori = {"Occasione": VERDE, "Novità calda": ROSSO, "Tendenza solida": BLU}
    for x in car["proposte"]:
        scheda = Table([
            [Pillola(x["categoria"], colori.get(x["categoria"], VIOLA), 27 * mm),
             Paragraph(f'<link href="{escape(x["link"])}" color="#2B2D42">{_t(x["nome"][:70])}</link>',
                       st["box_nome"]),
             Paragraph(_eur(x["prezzo"]), st["prezzo"])],
            ["", Paragraph(_t("Perché: " + x["perche"]), st["cella"]), ""],
            ["", Paragraph(_t("Rischio: " + x["rischio"]), ParagraphStyle("rs", parent=st["cella"],
                                                                          textColor=GRIGIO_T)), ""],
        ], colWidths=[30 * mm, LARGHEZZA - 30 * mm - 30 * mm - 16 * mm, 30 * mm])
        scheda.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("BACKGROUND", (0, 0), (-1, -1), BIANCO),
                                    ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                                    ("BOX", (0, 0), (-1, -1), 1, INCHIOSTRO),
                                    ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]))
        righe.append([scheda])
    if car["proposte"]:
        righe.append([Paragraph(f"<b>Totale: {_eur(car['speso'])}</b>  ·  restano {_eur(car['residuo'])}", st["p"])])
    for n in car["note"]:
        righe.append([Paragraph(_t(n), ParagraphStyle("bn2", parent=st["p"], textColor=ROSSO, fontName=CORPO_B))])
    righe.append([Paragraph(_t("Proposta automatica, non consulenza finanziaria. Il ragionamento completo è "
                               "nell'analisi di Claude della domenica."), st["nota"])])
    box = Table(righe, colWidths=[LARGHEZZA - 4 * mm])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFE58F")),
                             ("ROUNDEDCORNERS", [10, 10, 10, 10]),
                             ("BOX", (0, 0), (-1, -1), 1.8, INCHIOSTRO),
                             ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return KeepTogether([box])


def _stato(stato):
    return Pillola(stato, COLORE_STATO.get(stato, VIOLA), 22 * mm)


def crea(percorso, ctx):
    st = _stili()
    g = ctx["principale"]
    doc = BaseDocTemplate(percorso, pagesize=A4, title=f"{TESTATA} n. {ctx['numero']}",
                          leftMargin=MARGINE, rightMargin=MARGINE, topMargin=22 * mm, bottomMargin=18 * mm)
    cornice = Frame(MARGINE, 18 * mm, LARGHEZZA, H - 42 * mm, id="testo", leftPadding=0, rightPadding=0)
    cornice_chiusura = Frame(MARGINE + 2 * mm, 84 * mm, LARGHEZZA - 4 * mm, H - 143 * mm, id="chiusura",
                             leftPadding=0, rightPadding=0)
    doc.addPageTemplates([
        PageTemplate(id="copertina", frames=[Frame(0, 0, W, H, id="vuota")], onPage=lambda c, d: _copertina(c, ctx)),
        PageTemplate(id="interna", frames=[cornice], onPage=lambda c, d: _pagina_interna(c, d, ctx)),
        PageTemplate(id="chiusura", frames=[cornice_chiusura], onPage=lambda c, d: _chiusura(c, d, ctx)),
    ])
    E = [NextPageTemplate("interna"), Spacer(1, 1), PageBreak()]

    # 1. La settimana in breve + 200 euro
    E += [Rubrica("Editoriale", "La settimana in breve", VIOLA), Spacer(1, 4)]
    for i, riga in enumerate(ctx["sintesi"]):
        col = ("#EF476F", "#118AB2", "#06D6A0", "#8338EC", "#FF8C42")[i % 5]
        E.append(Paragraph(f"{_pallino(col)}  {_t(riga)}", st["p"]))
        E.append(Spacer(1, 3))
    E += [Spacer(1, 8), _box_200(g["carrello"], st), Spacer(1, 6),
          Mascotte("Ricorda: si compra con la testa, non con la pancia!", a_destra=True)]

    # 2. Radar uscite
    E += [Spacer(1, 6), CondPageBreak(70 * mm), Rubrica("Radar", "Le uscite in arrivo", ROSSO),
          Paragraph(_t("Date di uscita trovate nelle notizie delle ultime settimane, da siti ufficiali, italiani "
                       "e internazionali, per i prossimi 60 giorni. Più fonti = più interesse."), st["occhiello"]),
          Spacer(1, 5)]
    if g["radar"]:
        dati = [["Data", "Uscita", "Fonte", "Fonti", "Mercato"]]
        for u in g["radar"]:
            d = u["data"]
            dati.append([Paragraph(f"<b>{d[8:10]}/{d[5:7]}</b>", st["cella_b"]),
                         _link(u["titolo"], u["link"], st["cella"], 110), Paragraph(_t(u["fonte"]), st["cella"]),
                         str(u["citazioni"]), _stato(u["mercato"])])
        E.append(_tabella(dati, [15 * mm, 88 * mm, 32 * mm, 13 * mm, 30 * mm], ROSSO, allinea_destra_da=None))
        E += [Spacer(1, 6), Mascotte("Controlla sempre la data sul link della fonte!")]
    else:
        E.append(Paragraph("Nessuna data di uscita trovata nelle notizie di questa settimana.", st["nota"]))

    # 3. Previsioni
    E += [Spacer(1, 8), CondPageBreak(70 * mm), Rubrica("Previsioni", "Il termometro delle novità", ARANCIO),
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
        E.append(_tabella(dati, [52 * mm, 14 * mm, 19 * mm, 16 * mm, 25 * mm, 52 * mm], ARANCIO))
    else:
        E.append(Paragraph("Nessun prodotto sigillato nuovo nel periodo.", st["nota"]))

    # 4. Il borsino
    E += [Spacer(1, 10), CondPageBreak(110 * mm), Rubrica("Mercato", "Il borsino della settimana", VERDE),
          Paragraph(_t("Chi sale e chi scende. Prezzo = tendenza Cardmarket. * = stima dal primo giorno, "
                       "sostituita dallo storico reale man mano che si accumula."), st["occhiello"])]
    for tipo, nome_tipo, colore in (("sigillato", "Sigillato", CIELO), ("singola", "Carte singole", VIOLA)):
        per_desc = sorted(C.PERIODI, reverse=True)
        cl = g["classifiche"][tipo]
        # per il grafico: il periodo più lungo con sia rialzi sia ribassi, altrimenti il più lungo con dati
        periodo = next((p for p in per_desc if cl[str(p)]["rialzi"] and cl[str(p)]["ribassi"]),
                       next((p for p in per_desc if cl[str(p)]["rialzi"] or cl[str(p)]["ribassi"]), None))
        E += [CondPageBreak(95 * mm), Paragraph(nome_tipo, st["sotto"])]
        if periodo is None:
            E.append(Paragraph("Dati non ancora sufficienti.", st["nota"]))
            continue
        c = g["classifiche"][tipo][str(periodo)]
        E += [KeepTogether([Barre(c["rialzi"] + c["ribassi"], periodo,
                                  f"{nome_tipo}: chi sale e chi scende a {periodo} giorni")]), Spacer(1, 6)]
        for p in C.PERIODI:
            c = g["classifiche"][tipo][str(p)]
            for verso in ("rialzi", "ribassi"):
                righe_t = c[verso]
                intest = f"{verso.capitalize()} a {p} giorni"
                if verso == "ribassi" and not righe_t and c.get("piu_deboli"):
                    righe_t = c["piu_deboli"]
                    intest = f"Più deboli a {p} giorni (nessun calo)"
                if not righe_t:
                    continue
                dati = [[intest, "Prezzo"] + [f"{q}g" for q in C.PERIODI] + ["Incertezza"]]
                for r in righe_t:
                    dati.append([_link(r["nome"], r["link"], st["cella"], 58), _eur(r["prezzo"])]
                                + [_perc(r["variazioni"][str(q)]) + ("*" if r["fonti"][str(q)] == "stima" else "")
                                   for q in C.PERIODI] + [r["incertezza"]])
                E += [KeepTogether([_tabella(dati, [62 * mm, 20 * mm] + [15 * mm] * len(C.PERIODI) + [20 * mm],
                                             VERDE if verso == "rialzi" else
                                             (ROSSO if c[verso] else ARANCIO))]), Spacer(1, 6)]

    # 5. Occasioni
    if g["occasioni"]:
        E += [Spacer(1, 6), CondPageBreak(60 * mm), Rubrica("Affari", "Le occasioni della settimana", BLU),
              Paragraph(_t("Sigillato con un'offerta molto sotto il prezzo di tendenza. L'offerta più bassa può "
                           "riferirsi a un'altra lingua o condizione."), st["occhiello"]), Spacer(1, 5)]
        dati = [["Prodotto", "Offerta", "Tendenza", "Sconto"]]
        for o in g["occasioni"]:
            dati.append([_link(o["nome"], o["link"], st["cella"], 80), _eur(o["prezzo_minimo"]),
                         _eur(o["prezzo_tendenza"]), _perc(-o["sconto"])])
        E.append(_tabella(dati, [104 * mm, 24 * mm, 24 * mm, 22 * mm], BLU))

    # 6. Notizie
    if g["notizie"]:
        E += [Spacer(1, 10), CondPageBreak(50 * mm), Rubrica("Attualità", "Dal mondo Pokémon", ROSSO), Spacer(1, 3)]
        for i, n in enumerate(g["notizie"]):
            col = ("#EF476F", "#118AB2", "#06D6A0", "#8338EC")[i % 4]
            E.append(Paragraph(f'{_pallino(col)} <font name="{CORPO_B}" color="{col}" size="8">'
                               f'{_t((n.get("fonte") or "").upper())}  ·  {_t(n["data"])}</font><br/>'
                               f'<link href="{escape(n["link"])}" color="#2B2D42">'
                               f'<font name="{CORPO_B}">{_t(n["titolo"])}</font></link>', st["p"]))
            E.append(Spacer(1, 6))

    # 7. Chiusura: come leggere la rivista
    E += [NextPageTemplate("chiusura"), PageBreak(),
          Paragraph("Come leggere la rivista", st["titolo_chiusura"]), Spacer(1, 6)]
    for i, nota in enumerate(ctx["note_metodo"]):
        E.append(Paragraph(f"{_pallino(('#EF476F', '#118AB2', '#06D6A0', '#8338EC')[i % 4])}  {_t(nota)}", st["p"]))
        E.append(Spacer(1, 4))
    doc.build(E)
