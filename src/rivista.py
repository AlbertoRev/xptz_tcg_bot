"""Il report settimanale impaginato come una rivista: copertina, rubriche, grafici."""
import os
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

import config as C
from src.report import FONT, FONT_B, _eur, _perc, _t

# ---------- palette ----------
NOTTE = colors.HexColor("#14213D")
NOTTE_2 = colors.HexColor("#22335C")
GIALLO = colors.HexColor("#FFC72C")
ROSSO = colors.HexColor("#E63946")
VERDE = colors.HexColor("#2A9D8F")
AZZURRO = colors.HexColor("#3A86FF")
CREMA = colors.HexColor("#FFF6E0")
GRIGIO = colors.HexColor("#5C677D")
CHIARO = colors.HexColor("#F4F6FB")
COLORE_STATO = {"caldo": ROSSO, "tiepido": colors.HexColor("#F4A261"), "freddo": AZZURRO,
                "in arrivo": VERDE, "da valutare": GRIGIO, "nessun dato": GRIGIO}

W, H = A4
MARGINE = 15 * mm
LARGHEZZA = W - 2 * MARGINE
TESTATA = "IL COLLEZIONISTA"


def _serif():
    for base in ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/dejavu/"):
        if os.path.exists(base + "DejaVuSerif-Bold.ttf"):
            pdfmetrics.registerFont(TTFont("Titolo", base + "DejaVuSerif-Bold.ttf"))
            pdfmetrics.registerFont(TTFont("TitoloR", base + "DejaVuSerif.ttf"))
            return "Titolo", "TitoloR"
    return "Times-Bold", "Times-Roman"


SERIF_B, SERIF = _serif()


def _stili():
    return {
        "kicker": ParagraphStyle("k", fontName=FONT_B, fontSize=8, leading=10, textColor=ROSSO),
        "titolo": ParagraphStyle("ti", fontName=SERIF_B, fontSize=20, leading=24, textColor=NOTTE),
        "occhiello": ParagraphStyle("o", fontName=SERIF, fontSize=10, leading=14, textColor=GRIGIO),
        "p": ParagraphStyle("p", fontName=FONT, fontSize=9.5, leading=13.5, textColor=colors.HexColor("#222222")),
        "cella": ParagraphStyle("c", fontName=FONT, fontSize=7.8, leading=9.6),
        "cella_b": ParagraphStyle("cb", fontName=FONT_B, fontSize=7.8, leading=9.6),
        "nota": ParagraphStyle("n", fontName=FONT, fontSize=7.5, leading=10, textColor=GRIGIO),
        "sotto": ParagraphStyle("s", fontName=FONT_B, fontSize=11, leading=14, textColor=NOTTE, spaceBefore=8,
                                spaceAfter=4, keepWithNext=1),
        "box_titolo": ParagraphStyle("bt", fontName=SERIF_B, fontSize=22, leading=26, textColor=NOTTE),
        "box_nome": ParagraphStyle("bn", fontName=FONT_B, fontSize=10.5, leading=13, textColor=NOTTE),
        "tag": ParagraphStyle("tg", fontName=FONT_B, fontSize=7, leading=9, textColor=colors.white,
                              alignment=TA_CENTER),
    }


# ---------- elementi grafici ----------
class Rubrica(Flowable):
    """Intestazione di rubrica: barra colorata, occhiello e titolo."""

    def __init__(self, occhiello, titolo, colore=ROSSO):
        super().__init__()
        self.occhiello, self.titolo, self.colore = occhiello, titolo, colore

    def wrap(self, *_):
        return LARGHEZZA, 16 * mm

    def draw(self):
        c = self.canv
        c.setFillColor(self.colore)
        c.rect(0, 2 * mm, 3 * mm, 13 * mm, stroke=0, fill=1)
        c.setFont(FONT_B, 8)
        c.drawString(6 * mm, 12 * mm, self.occhiello.upper())
        c.setFillColor(NOTTE)
        c.setFont(SERIF_B, 19)
        c.drawString(6 * mm, 3.5 * mm, self.titolo)
        c.setStrokeColor(colors.HexColor("#D9DEE8"))
        c.setLineWidth(0.6)
        c.line(6 * mm, 0.5 * mm, LARGHEZZA, 0.5 * mm)


def _tag(testo, colore, st, larghezza=20 * mm):
    t = Table([[Paragraph(_t(testo.upper()), st["tag"])]], colWidths=[larghezza])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colore), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
    return t


def _tabella(dati, larghezze, allinea_destra_da=1):
    t = Table(dati, colWidths=larghezze, repeatRows=1)
    stile = [
        ("FONTNAME", (0, 0), (-1, 0), FONT_B), ("FONTSIZE", (0, 0), (-1, 0), 7.8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), NOTTE),
        ("FONTNAME", (0, 1), (-1, -1), FONT), ("FONTSIZE", (0, 1), (-1, -1), 7.8),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#E1E5EE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    if allinea_destra_da is not None:
        stile.append(("ALIGN", (allinea_destra_da, 1), (-1, -1), "RIGHT"))
    for i in range(1, len(dati)):
        if i % 2 == 0:
            stile.append(("BACKGROUND", (0, i), (-1, i), CHIARO))
    t.setStyle(TableStyle(stile))
    return t


def _link(nome, url, stile, n=62):
    return Paragraph(f'<link href="{escape(url)}" color="#1d3f8f">{_t(nome[:n])}</link>', stile)


def _grafico(righe, periodo, titolo):
    """Barre orizzontali: verde in salita, rosso in discesa."""
    righe = [r for r in righe if r["variazioni"].get(str(periodo)) is not None][:10]
    if not righe:
        return None
    valori = [r["variazioni"][str(periodo)] for r in righe]
    alt_barre = len(righe) * 6.5 * mm
    altezza = alt_barre + 17 * mm
    d = Drawing(LARGHEZZA, altezza)
    d.add(String(0, altezza - 9, titolo, fontName=FONT_B, fontSize=9, fillColor=NOTTE))
    b = HorizontalBarChart()
    b.x, b.y = 62 * mm, 7 * mm
    b.width, b.height = LARGHEZZA - 72 * mm, alt_barre
    b.data = [valori[::-1]]
    b.categoryAxis.categoryNames = [r["nome"][:34] for r in righe][::-1]
    b.categoryAxis.labels.fontName = FONT
    b.categoryAxis.labels.fontSize = 7
    b.categoryAxis.labels.boxAnchor = "e"
    b.categoryAxis.strokeColor = colors.HexColor("#C9CFDB")
    b.valueAxis.labels.fontName = FONT
    b.valueAxis.labels.fontSize = 7
    b.valueAxis.labelTextFormat = lambda v: f"{v:+.0f}%"
    b.valueAxis.strokeColor = colors.HexColor("#C9CFDB")
    b.valueAxis.gridStrokeColor = colors.HexColor("#EEF0F5")
    b.valueAxis.visibleGrid = True
    minimo, massimo = min(valori + [0]), max(valori + [0])
    margine = max(5, (massimo - minimo) * 0.08)
    b.valueAxis.valueMin, b.valueAxis.valueMax = minimo - margine, massimo + margine
    b.bars.strokeColor = None
    b.barWidth = 4
    for i, v in enumerate(valori[::-1]):
        b.bars[(0, i)].fillColor = VERDE if v >= 0 else ROSSO
    d.add(b)
    return d


# ---------- pagine ----------
def _copertina(c, ctx):
    g = ctx["principale"]
    c.saveState()
    c.setFillColor(NOTTE)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    # decorazione: anelli concentrici e punti
    c.setFillColor(GIALLO)
    c.setFillAlpha(0.06)
    for r in (110 * mm, 80 * mm, 50 * mm):
        c.circle(W + 10 * mm, H - 10 * mm, r, stroke=0, fill=1)
    c.setFillAlpha(0.18)
    for i in range(10):
        for j in range(4):
            c.circle(W - 60 * mm + i * 5 * mm, 22 * mm + j * 5 * mm, 0.6 * mm, stroke=0, fill=1)
    c.setFillAlpha(1)

    # testata
    c.setFillColor(GIALLO)
    c.setFont(FONT_B, 8.5)
    c.drawString(MARGINE, H - 22 * mm, f"SETTIMANALE DEL MERCATO POKÉMON GCC  ·  N. {ctx['numero']}  ·  "
                                       f"{ctx['data_lunga'].upper()}")
    c.setFillColor(colors.white)
    c.setFont(SERIF_B, 46)
    c.drawString(MARGINE, H - 42 * mm, TESTATA)
    c.setFillColor(GIALLO)
    c.rect(MARGINE, H - 47 * mm, 70 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColor(ROSSO)
    c.rect(MARGINE + 72 * mm, H - 47 * mm, 18 * mm, 2 * mm, stroke=0, fill=1)

    # primo piano
    c.setFillColor(ROSSO)
    c.roundRect(MARGINE, H - 66 * mm, 32 * mm, 6.5 * mm, 1.5 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont(FONT_B, 8)
    c.drawCentredString(MARGINE + 16 * mm, H - 63.8 * mm, "IN PRIMO PIANO")
    titolo = Paragraph(_t(ctx["apertura"]["titolo"]),
                       ParagraphStyle("ct", fontName=SERIF_B, fontSize=25, leading=30, textColor=colors.white))
    _, h = titolo.wrap(LARGHEZZA - 10 * mm, 60 * mm)
    titolo.drawOn(c, MARGINE, H - 72 * mm - h)
    sotto = Paragraph(_t(ctx["apertura"]["sottotitolo"]),
                      ParagraphStyle("cs", fontName=SERIF, fontSize=11.5, leading=16,
                                     textColor=colors.HexColor("#C9D3EA")))
    _, h2 = sotto.wrap(LARGHEZZA - 30 * mm, 40 * mm)
    y_sotto = H - 76 * mm - h - h2
    sotto.drawOn(c, MARGINE, y_sotto)

    # numeri della settimana
    y = min(y_sotto - 18 * mm, H - 150 * mm)
    card_w = (LARGHEZZA - 3 * 4 * mm) / 4
    for i, (numero, etichetta) in enumerate(ctx["kpi"]):
        x = MARGINE + i * (card_w + 4 * mm)
        c.setFillColor(NOTTE_2)
        c.roundRect(x, y, card_w, 26 * mm, 3 * mm, stroke=0, fill=1)
        c.setFillColor(GIALLO)
        c.setFont(SERIF_B, 24)
        c.drawString(x + 4 * mm, y + 13 * mm, str(numero))
        c.setFillColor(colors.HexColor("#C9D3EA"))
        c.setFont(FONT, 7.5)
        c.drawString(x + 4 * mm, y + 5 * mm, etichetta)

    # sommario
    y -= 14 * mm
    c.setFillColor(GIALLO)
    c.setFont(FONT_B, 9)
    c.drawString(MARGINE, y, "IN QUESTO NUMERO")
    y -= 3 * mm
    c.setStrokeColor(GIALLO)
    c.setLineWidth(0.8)
    c.line(MARGINE, y, MARGINE + 40 * mm, y)
    y -= 8 * mm
    for titolo_r, descrizione in ctx["sommario"]:
        c.setFillColor(colors.white)
        c.setFont(SERIF_B, 12)
        c.drawString(MARGINE, y, titolo_r)
        c.setFillColor(colors.HexColor("#AEB9D3"))
        c.setFont(FONT, 8.5)
        c.drawString(MARGINE + 72 * mm, y + 0.5, descrizione)
        y -= 8.5 * mm

    # anteprima: cosa farei con 200 euro
    car = g["carrello"]
    y -= 6 * mm
    alt = 12 * mm + max(1, len(car["proposte"])) * 7 * mm
    c.setFillColor(GIALLO)
    c.roundRect(MARGINE, y - alt, LARGHEZZA, alt, 3 * mm, stroke=0, fill=1)
    c.setFillColor(NOTTE)
    c.setFont(SERIF_B, 14)
    c.drawString(MARGINE + 5 * mm, y - 8 * mm, "Cosa farei con 200 €")
    c.setFont(FONT, 8)
    yy = y - 15 * mm
    if car["proposte"]:
        for x in car["proposte"]:
            c.setFont(FONT_B, 8.5)
            c.drawString(MARGINE + 5 * mm, yy, x["categoria"].upper())
            c.setFont(FONT, 8.5)
            c.drawString(MARGINE + 40 * mm, yy, x["nome"][:62])
            c.setFont(FONT_B, 8.5)
            c.drawRightString(W - MARGINE - 5 * mm, yy, _eur(x["prezzo"]))
            yy -= 7 * mm
    else:
        c.drawString(MARGINE + 5 * mm, yy, "Niente: questa settimana li terrei da parte.")

    # piede
    c.setFillColor(GIALLO)
    c.rect(0, 14 * mm, W, 1.2 * mm, stroke=0, fill=1)
    c.setFillColor(ROSSO)
    c.rect(0, 11.5 * mm, W, 0.8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#AEB9D3"))
    c.setFont(FONT, 7)
    c.drawString(MARGINE, 6 * mm, f"Dati: Cardmarket e fonti di notizie  ·  {g['giorni_storico']} giorni di "
                                   "storico  ·  Rivista informativa, non è consulenza finanziaria")
    c.restoreState()


def _pagina_interna(c, doc, ctx):
    c.saveState()
    c.setFillColor(NOTTE)
    c.rect(0, H - 11 * mm, W, 11 * mm, stroke=0, fill=1)
    c.setFillColor(GIALLO)
    c.setFont(SERIF_B, 10)
    c.drawString(MARGINE, H - 7.3 * mm, TESTATA)
    c.setFillColor(colors.white)
    c.setFont(FONT, 7.5)
    c.drawRightString(W - MARGINE, H - 7 * mm, f"N. {ctx['numero']}  ·  {ctx['data_lunga']}")
    c.setFillColor(GIALLO)
    c.rect(MARGINE, 10 * mm, LARGHEZZA, 0.6 * mm, stroke=0, fill=1)
    c.setFillColor(GRIGIO)
    c.setFont(FONT_B, 8)
    c.drawRightString(W - MARGINE, 5.5 * mm, str(doc.page))
    c.restoreState()


# ---------- rubriche ----------
def _box_200(car, st):
    righe = [[Paragraph("Cosa farei con 200 €", st["box_titolo"])],
             [Paragraph(_t("La proposta della settimana, calcolata con regole fisse sui dati: al massimo tre "
                           "acquisti, uno per tipo di segnale, senza superare il budget."), st["occhiello"])]]
    colori = {"Occasione": VERDE, "Novità calda": ROSSO, "Tendenza solida": AZZURRO}
    for x in car["proposte"]:
        scheda = Table([
            [_tag(x["categoria"], colori.get(x["categoria"], GRIGIO), st, 26 * mm),
             Paragraph(f'<link href="{escape(x["link"])}" color="#14213D">{_t(x["nome"][:70])}</link>',
                       st["box_nome"]),
             Paragraph(f"<b>{_eur(x['prezzo'])}</b>", ParagraphStyle("pz", parent=st["box_nome"], alignment=2))],
            ["", Paragraph(_t("Perché: " + x["perche"]), st["cella"]), ""],
            ["", Paragraph(_t("Rischio: " + x["rischio"]), ParagraphStyle("rs", parent=st["cella"],
                                                                          textColor=GRIGIO)), ""],
        ], colWidths=[29 * mm, LARGHEZZA - 29 * mm - 30 * mm - 12 * mm, 30 * mm])
        scheda.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#F1DCA7")),
                                    ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        righe.append([scheda])
    if car["proposte"]:
        righe.append([Paragraph(f"<b>Totale: {_eur(car['speso'])}</b>  ·  restano {_eur(car['residuo'])}",
                                st["p"])])
    for n in car["note"]:
        righe.append([Paragraph(_t(n), ParagraphStyle("bn2", parent=st["p"], textColor=ROSSO))])
    righe.append([Paragraph(_t("Proposta automatica, non consulenza finanziaria. Il ragionamento completo è "
                               "nell'analisi di Claude della domenica."), st["nota"])])
    box = Table(righe, colWidths=[LARGHEZZA - 6 * mm])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CREMA),
                             ("LINEBEFORE", (0, 0), (0, -1), 4, GIALLO),
                             ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return KeepTogether([box])


def _stato(stato, st):
    return _tag(stato, COLORE_STATO.get(stato, GRIGIO), st, 21 * mm)


def crea(percorso, ctx):
    st = _stili()
    g = ctx["principale"]
    doc = BaseDocTemplate(percorso, pagesize=A4, title=f"{TESTATA} n. {ctx['numero']}",
                          leftMargin=MARGINE, rightMargin=MARGINE, topMargin=16 * mm, bottomMargin=15 * mm)
    cornice = Frame(MARGINE, 14 * mm, LARGHEZZA, H - 30 * mm, id="testo", leftPadding=0, rightPadding=0)
    doc.addPageTemplates([
        PageTemplate(id="copertina", frames=[Frame(0, 0, W, H, id="vuota")],
                     onPage=lambda c, d: _copertina(c, ctx)),
        PageTemplate(id="interna", frames=[cornice], onPage=lambda c, d: _pagina_interna(c, d, ctx)),
    ])
    E = [NextPageTemplate("interna"), Spacer(1, 1), PageBreak()]

    # 1. La settimana in breve
    E += [Rubrica("Editoriale", "La settimana in breve", NOTTE), Spacer(1, 3)]
    for riga in ctx["sintesi"]:
        E.append(Paragraph(f'<font color="#E63946">●</font>  {_t(riga)}', st["p"]))
        E.append(Spacer(1, 2))
    E += [Spacer(1, 8), _box_200(g["carrello"], st), Spacer(1, 10)]

    # 2. Radar uscite
    E += [CondPageBreak(60 * mm), Rubrica("Radar", "Le uscite in arrivo", ROSSO),
          Paragraph(_t(f"Date di uscita trovate nelle notizie delle ultime settimane (siti ufficiali, "
                       f"italiani e internazionali) per i prossimi 60 giorni. Più fonti = più interesse. "
                       f"Controlla sempre la data sul link."), st["occhiello"]), Spacer(1, 5)]
    if g["radar"]:
        dati = [["Data", "Uscita", "Fonte", "Fonti", "Mercato"]]
        for u in g["radar"]:
            d = u["data"]
            dati.append([Paragraph(f"<b>{d[8:10]}/{d[5:7]}</b>", st["cella_b"]),
                         _link(u["titolo"], u["link"], st["cella"], 110), Paragraph(_t(u["fonte"]), st["cella"]),
                         str(u["citazioni"]), _stato(u["mercato"], st)])
        E.append(_tabella(dati, [15 * mm, 92 * mm, 32 * mm, 12 * mm, 29 * mm], allinea_destra_da=None))
    else:
        E.append(Paragraph("Nessuna data di uscita trovata nelle notizie di questa settimana.", st["nota"]))

    # 3. Previsioni
    E += [Spacer(1, 10), CondPageBreak(60 * mm), Rubrica("Previsioni", "Il termometro delle novità", ROSSO),
          Paragraph(_t(f"Sigillato comparso su Cardmarket negli ultimi {C.PREVISIONI_GIORNI} giorni: prevendite, "
                       "prodotti in arrivo e appena usciti. Caldo = prezzo in salita o poche offerte sotto la "
                       "tendenza. Freddo = prezzo in calo o molte offerte scontate. In arrivo = ancora nessuna "
                       "vendita."), st["occhiello"]), Spacer(1, 5)]
    if g["previsioni"]:
        dati = [["Prodotto", "Listato", "Prezzo", "Variaz.", "Stato", "Perché"]]
        for p in g["previsioni"]:
            a = p["aggiunto"]
            dati.append([_link(p["nome"], p["link"], st["cella"], 55), f"{a[8:10]}/{a[5:7]}", _eur(p["prezzo"]),
                         _perc(p["variazione"]), _stato(p["stato"], st), Paragraph(_t(p["motivo"]), st["cella"])])
        E.append(_tabella(dati, [54 * mm, 14 * mm, 19 * mm, 15 * mm, 25 * mm, 53 * mm]))
    else:
        E.append(Paragraph("Nessun prodotto sigillato nuovo nel periodo.", st["nota"]))

    # 4. Il borsino
    E += [Spacer(1, 10), CondPageBreak(110 * mm), Rubrica("Mercato", "Il borsino della settimana", VERDE),
          Paragraph(_t("Chi sale e chi scende. Prezzo = tendenza Cardmarket. * = stima dal primo giorno, "
                       "sostituita dallo storico reale man mano che si accumula."), st["occhiello"])]
    for tipo, nome_tipo in (("sigillato", "Sigillato"), ("singola", "Carte singole")):
        periodo = next((p for p in sorted(C.PERIODI, reverse=True)
                        if g["classifiche"][tipo][str(p)]["rialzi"] or g["classifiche"][tipo][str(p)]["ribassi"]),
                       None)
        E.append(Paragraph(nome_tipo, st["sotto"]))
        if periodo is None:
            E.append(Paragraph("Dati non ancora sufficienti.", st["nota"]))
            continue
        c = g["classifiche"][tipo][str(periodo)]
        grafico = _grafico(c["rialzi"] + c["ribassi"], periodo, f"{nome_tipo}: maggiori movimenti a {periodo} giorni")
        if grafico:
            E += [grafico, Spacer(1, 4)]
        for p in C.PERIODI:
            c = g["classifiche"][tipo][str(p)]
            for verso in ("rialzi", "ribassi"):
                if not c[verso]:
                    continue
                dati = [[f"{verso.capitalize()} a {p} giorni", "Prezzo"] + [f"{q}g" for q in C.PERIODI]
                        + ["Incertezza"]]
                for r in c[verso]:
                    dati.append([_link(r["nome"], r["link"], st["cella"], 58), _eur(r["prezzo"])]
                                + [_perc(r["variazioni"][str(q)]) + ("*" if r["fonti"][str(q)] == "stima" else "")
                                   for q in C.PERIODI] + [r["incertezza"]])
                E += [KeepTogether([_tabella(dati, [64 * mm, 20 * mm] + [15 * mm] * len(C.PERIODI) + [20 * mm])]),
                      Spacer(1, 5)]

    # 5. Occasioni
    if g["occasioni"]:
        E += [Spacer(1, 6), CondPageBreak(50 * mm), Rubrica("Affari", "Le occasioni della settimana", GIALLO),
              Paragraph(_t("Sigillato con un'offerta molto sotto il prezzo di tendenza. L'offerta più bassa può "
                           "riferirsi a un'altra lingua o condizione."), st["occhiello"]), Spacer(1, 5)]
        dati = [["Prodotto", "Offerta", "Tendenza", "Sconto"]]
        for o in g["occasioni"]:
            dati.append([_link(o["nome"], o["link"], st["cella"], 80), _eur(o["prezzo_minimo"]),
                         _eur(o["prezzo_tendenza"]), _perc(-o["sconto"])])
        E.append(_tabella(dati, [110 * mm, 24 * mm, 24 * mm, 22 * mm]))

    # 6. Notizie
    if g["notizie"]:
        E += [Spacer(1, 10), CondPageBreak(45 * mm), Rubrica("Attualità", "Dal mondo Pokémon", AZZURRO), Spacer(1, 3)]
        for n in g["notizie"]:
            E.append(Paragraph(f'<font color="#5C677D" size="7">{_t((n.get("fonte") or "").upper())}  ·  '
                               f'{_t(n["data"])}</font><br/><link href="{escape(n["link"])}" color="#14213D">'
                               f'<b>{_t(n["titolo"])}</b></link>', st["p"]))
            E.append(Spacer(1, 5))

    # 7. Come leggere la rivista
    E += [Spacer(1, 10), CondPageBreak(40 * mm), Rubrica("Metodo", "Come leggere la rivista", GRIGIO)]
    for nota in ctx["note_metodo"]:
        E.append(Paragraph(_t(nota), st["nota"]))
        E.append(Spacer(1, 2))
    doc.build(E)
