"""Genera il PDF settimanale, il riepilogo per Telegram e il file dati per l'analisi di Claude."""
import html
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import config as C

TIPI = {"sigillato": "Sigillato", "singola": "Carte singole"}


# ---------- font ----------
def _font():
    for base in ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/dejavu/"):
        if os.path.exists(base + "DejaVuSans.ttf"):
            pdfmetrics.registerFont(TTFont("Testo", base + "DejaVuSans.ttf"))
            pdfmetrics.registerFont(TTFont("TestoB", base + "DejaVuSans-Bold.ttf"))
            return "Testo", "TestoB", True
    return "Helvetica", "Helvetica-Bold", False


FONT, FONT_B, UNICODE = _font()


def _t(s):
    s = "" if s is None else str(s)
    if not UNICODE:
        s = s.encode("cp1252", "replace").decode("cp1252")
    return escape(s)


def _perc(v):
    if v is None:
        return "n.d."
    return f"{'+' if v > 0 else ''}{v:.1f}%".replace(".", ",")


def _eur(v):
    return "n.d." if v is None else f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _stili():
    s = getSampleStyleSheet()
    return {
        "titolo": ParagraphStyle("t", parent=s["Title"], fontName=FONT_B, fontSize=17),
        "h1": ParagraphStyle("h1", parent=s["Heading1"], fontName=FONT_B, fontSize=14, spaceBefore=10),
        "h2": ParagraphStyle("h2", parent=s["Heading2"], fontName=FONT_B, fontSize=11.5, spaceBefore=8),
        "h3": ParagraphStyle("h3", parent=s["Heading3"], fontName=FONT_B, fontSize=9.5, spaceBefore=4,
                             keepWithNext=1),
        "p": ParagraphStyle("p", parent=s["Normal"], fontName=FONT, fontSize=9, leading=12),
        "cella": ParagraphStyle("c", parent=s["Normal"], fontName=FONT, fontSize=7.5, leading=9),
        "nota": ParagraphStyle("n", parent=s["Normal"], fontName=FONT, fontSize=7.5, leading=10,
                               textColor=colors.HexColor("#555555")),
    }


def _stile_tabella():
    return TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), FONT_B), ("FONTNAME", (0, 1), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8ECF2")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#BBBBBB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ])


def _link(nome, url, st):
    return Paragraph(f'<link href="{escape(url)}" color="#1a4fa0">{_t(nome[:60])}</link>', st)


def _tabella_classifica(righe, st):
    intest = ["Prodotto", "Prezzo"] + [f"{p}g" for p in C.PERIODI] + ["Incertezza"]
    dati = [intest]
    for r in righe:
        var = [_perc(r["variazioni"][str(p)]) + ("*" if r["fonti"][str(p)] == "stima" else "")
               for p in C.PERIODI]
        dati.append([_link(r["nome"], r["link"], st["cella"]), _eur(r["prezzo"])] + var + [r["incertezza"]])
    larghezze = [66 * mm, 20 * mm] + [15 * mm] * len(C.PERIODI) + [20 * mm]
    t = Table(dati, colWidths=larghezze, repeatRows=1)
    t.setStyle(_stile_tabella())
    return t


def _copertura(giorni):
    if giorni >= 181:
        return f"{giorni} giorni di storico: tutte le variazioni sono reali"
    periodi = [str(p) for p in C.PERIODI if giorni > p]
    testo = f"{giorni} giorn{'o' if giorni == 1 else 'i'} di storico"
    return (f"{testo}: variazioni reali a {', '.join(periodi)} giorni, il resto stimato o non ancora disponibile"
            if periodi else f"{testo}: solo stime per le singole")


# ---------- PDF ----------
def pdf(percorso, ctx):
    st = _stili()
    doc = SimpleDocTemplate(percorso, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title="Report TCG settimanale")
    E = [Paragraph(f"Report TCG settimanale - {ctx['data_it']}", st["titolo"])]

    E.append(Paragraph("Sintesi", st["h1"]))
    for riga in sintesi_righe(ctx):
        E.append(Paragraph(_t(riga), st["p"]))

    E.append(Paragraph("Copertura dei dati", st["h2"]))
    for g in ctx["giochi"].values():
        E.append(Paragraph(_t(f"{g['nome']}: {_copertura(g['giorni_storico'])}."), st["p"]))
    if ctx.get("anomalie"):
        E.append(Paragraph(_t(f"Variazioni escluse perché non credibili (oltre +300%): {ctx['anomalie']}."),
                           st["nota"]))

    for chiave, g in ctx["giochi"].items():
        if g["livello"] != "principale":
            continue
        E.append(Paragraph(_t(g["nome"]), st["h1"]))
        if g["nuovi"]:
            E.append(Paragraph("Nuovi prodotti sigillati aggiunti su Cardmarket (ultimi 7 giorni)", st["h2"]))
            dati = [["Prodotto", "Categoria", "Aggiunto", "Prezzo"]]
            for n in g["nuovi"]:
                dati.append([_link(n["nome"], n["link"], st["cella"]), _t(n["categoria"])[:30],
                             n["aggiunto"], _eur(n["prezzo"])])
            t = Table(dati, colWidths=[80 * mm, 50 * mm, 22 * mm, 24 * mm], repeatRows=1)
            t.setStyle(_stile_tabella())
            E.append(t)
        for tipo, nome_tipo in TIPI.items():
            E.append(Paragraph(nome_tipo, st["h2"]))
            vuoto = True
            for p in C.PERIODI:
                c = g["classifiche"][tipo][str(p)]
                if not (c["rialzi"] or c["ribassi"]):
                    continue
                vuoto = False
                for verso in ("rialzi", "ribassi"):
                    if c[verso]:
                        E.append(Paragraph(f"{verso.capitalize()} a {p} giorni", st["h3"]))
                        E.append(_tabella_classifica(c[verso], st))
            if vuoto:
                E.append(Paragraph("Dati non ancora sufficienti per questa sezione.", st["nota"]))
        if g["occasioni"]:
            E.append(Paragraph("Occasioni da verificare", st["h2"]))
            E.append(Paragraph(_t(
                f"Prezzo minimo in vendita molto sotto la tendenza. Il prezzo minimo può riferirsi a un'altra "
                f"lingua o condizione: verifica sempre la copia in {g['lingua_it']} prima di comprare."), st["nota"]))
            dati = [["Prodotto", "Tipo", "Minimo", "Tendenza", "Sconto", "In lingua"]]
            for o in g["occasioni"]:
                v = o.get("verifica_lingua")
                dati.append([_link(o["nome"], o["link"], st["cella"]), o["tipo"], _eur(o["prezzo_minimo"]),
                             _eur(o["prezzo_tendenza"]), _perc(o["sconto"]),
                             _eur(v["da"]) if v and v.get("da") else "da verificare"])
            t = Table(dati, colWidths=[72 * mm, 18 * mm, 22 * mm, 22 * mm, 18 * mm, 24 * mm], repeatRows=1)
            t.setStyle(_stile_tabella())
            E.append(t)
        if g["notizie"]:
            E.append(Paragraph("Notizie della settimana", st["h2"]))
            for n in g["notizie"]:
                E.append(Paragraph(f'{_t(n["data"])} - <link href="{escape(n["link"])}" color="#1a4fa0">'
                                   f'{_t(n["titolo"])}</link>', st["p"]))

    osservati = [g for g in ctx["giochi"].values() if g["livello"] == "osservazione"]
    if osservati or ctx.get("notizie_extra"):
        E.append(Paragraph("In osservazione", st["h1"]))
        for g in osservati:
            E.append(Paragraph(_t(g["nome"]), st["h2"]))
            if ctx["mensile"]:
                for tipo, nome_tipo in TIPI.items():
                    c = g["classifiche"][tipo]["30"]
                    righe = (c["rialzi"][:3] + c["ribassi"][:3])
                    if righe:
                        E.append(Paragraph(f"{nome_tipo}: maggiori movimenti a 30 giorni", st["h3"]))
                        E.append(_tabella_classifica(righe, st))
            else:
                E.append(Paragraph("Prezzi nella prima domenica del mese; qui solo notizie.", st["nota"]))
            for n in g["notizie"]:
                E.append(Paragraph(f'{_t(n["data"])} - <link href="{escape(n["link"])}" color="#1a4fa0">'
                                   f'{_t(n["titolo"])}</link>', st["p"]))
        for nome, lista in ctx.get("notizie_extra", {}).items():
            E.append(Paragraph(_t(nome.capitalize()), st["h2"]))
            if not lista:
                E.append(Paragraph("Nessuna notizia questa settimana.", st["nota"]))
            for n in lista:
                E.append(Paragraph(f'{_t(n["data"])} - <link href="{escape(n["link"])}" color="#1a4fa0">'
                                   f'{_t(n["titolo"])}</link>', st["p"]))

    E.append(Paragraph("Come leggere il report", st["h2"]))
    for nota in NOTE_METODO:
        E.append(Paragraph(_t(nota), st["nota"]))
    E.append(Spacer(1, 4))
    doc.build(E)


NOTE_METODO = [
    "Prezzo = prezzo di tendenza Cardmarket (media di tutte le lingue). Variazione = confronto con lo "
    "storico salvato dal bot.",
    "* = stima dal primo giorno, solo per le singole: a 7 giorni media vendite 7 giorni contro media 30 giorni; "
    "a 30 giorni prezzo di tendenza contro media 30 giorni. Le stime vengono sostituite dallo storico reale.",
    "Incertezza: bassa, media o alta secondo regole fisse (stima o storico, numero di vendite, ampiezza della "
    "variazione, prezzo sotto 10 euro).",
    "Il sigillato non ha medie di vendita nei file Cardmarket: le sue variazioni partono dallo storico del bot.",
    "I nomi dei prodotti sono link alla ricerca su Cardmarket: filtra la lingua sulla pagina prima di comprare.",
    "Questo report è uno strumento informativo, non una consulenza finanziaria.",
]


# ---------- riepilogo testuale ----------
def _migliore(g, tipo, verso):
    """Primo prodotto della classifica sul periodo più lungo disponibile."""
    for p in sorted(C.PERIODI, reverse=True):
        c = g["classifiche"][tipo][str(p)]
        if c[verso]:
            return p, c[verso][0]
    return None, None


def sintesi_righe(ctx):
    righe = []
    for g in ctx["giochi"].values():
        if g["livello"] != "principale":
            continue
        for tipo in TIPI:
            for verso in ("rialzi", "ribassi"):
                p, r = _migliore(g, tipo, verso)
                if r:
                    righe.append(f"{g['nome']}, {TIPI[tipo].lower()}, maggiore {verso[:-1] + 'o'} a {p} giorni: "
                                 f"{r['nome']} {_perc(r['variazioni'][str(p)])} (prezzo {_eur(r['prezzo'])}, "
                                 f"incertezza {r['incertezza']}).")
        if g["occasioni"]:
            righe.append(f"{g['nome']}: {len(g['occasioni'])} possibili occasioni da verificare.")
        if g["nuovi"]:
            righe.append(f"{g['nome']}: {len(g['nuovi'])} nuovi prodotti sigillati su Cardmarket.")
    return righe or ["Nessun movimento rilevante: servono ancora dati storici."]


def telegram_settimanale(ctx):
    r = [f"<b>📊 Report TCG settimanale - {ctx['data_it']}</b>", ""]
    for g in ctx["giochi"].values():
        if g["livello"] != "principale":
            continue
        r.append(f"<b>{html.escape(g['nome'])}</b> <i>({_copertura(g['giorni_storico'])})</i>")
        for tipo in TIPI:
            for verso, icona in (("rialzi", "🔺"), ("ribassi", "🔻")):
                p, x = _migliore(g, tipo, verso)
                if x:
                    r.append(f"{icona} {TIPI[tipo]} {p}g: <a href=\"{html.escape(x['link'])}\">"
                             f"{html.escape(x['nome'][:45])}</a> {_perc(x['variazioni'][str(p)])} "
                             f"({_eur(x['prezzo'])}, inc. {x['incertezza']})")
        if g["occasioni"]:
            r.append(f"💡 {len(g['occasioni'])} occasioni da verificare")
        if g["nuovi"]:
            r.append(f"🆕 {len(g['nuovi'])} nuovi prodotti sigillati")
        r.append("")
    r.append("Report completo nel PDF qui sotto.")
    return "\n".join(r)


def telegram_alert(alert):
    r = ["<b>🚨 Alert mercato TCG</b>", ""]
    for a in alert:
        if a["genere"] == "movimento":
            icona = "🔺" if a["variazione_7g"] > 0 else "🔻"
            r.append(f"{icona} <b>{html.escape(a['gioco'])}</b> - <a href=\"{html.escape(a['link'])}\">"
                     f"{html.escape(a['nome'][:50])}</a>: {_perc(a['variazione_7g'])} in 7 giorni, "
                     f"ora {_eur(a['prezzo'])} (confermato 2 giorni)")
        else:
            riga = (f"💡 <b>{html.escape(a['gioco'])}</b> - <a href=\"{html.escape(a['link'])}\">"
                    f"{html.escape(a['nome'][:50])}</a>: minimo {_eur(a['prezzo_minimo'])} contro tendenza "
                    f"{_eur(a['prezzo_tendenza'])} (-{a['sconto']:.0f}%)")
            v = a.get("verifica_lingua")
            riga += (f" · in {a['lingua_it']} da {_eur(v['da'])}" if v and v.get("da")
                     else f" · verifica la copia in {a['lingua_it']}")
            r.append(riga)
    return "\n".join(r)


# ---------- dati per Claude ----------
def dati_per_claude(ctx):
    """Versione compatta dei numeri, letta dall'attività pianificata di Claude."""
    out = {"data": ctx["data"], "nota": "Tutti i numeri sono calcolati dal codice. Variazioni in percentuale. "
           "Prezzi in euro, prezzo di tendenza Cardmarket (tutte le lingue).", "giochi": {}}
    for k, g in ctx["giochi"].items():
        classifiche = {}
        for tipo in TIPI:
            classifiche[tipo] = {}
            for p in C.PERIODI:
                c = g["classifiche"][tipo][str(p)]
                classifiche[tipo][str(p)] = {
                    "fonte": c["fonte"],
                    "rialzi": [{x: r[x] for x in ("nome", "prezzo", "variazioni", "incertezza")} for r in c["rialzi"]],
                    "ribassi": [{x: r[x] for x in ("nome", "prezzo", "variazioni", "incertezza")} for r in c["ribassi"]],
                }
        out["giochi"][k] = {
            "nome": g["nome"], "livello": g["livello"], "lingua_investimento": g["lingua_it"],
            "giorni_storico": g["giorni_storico"], "classifiche": classifiche,
            "occasioni": [{x: o[x] for x in ("nome", "tipo", "prezzo_minimo", "prezzo_tendenza", "sconto")}
                          for o in g["occasioni"]],
            "nuovi_prodotti": [{x: n[x] for x in ("nome", "categoria", "aggiunto", "prezzo")} for n in g["nuovi"]],
            "notizie": g["notizie"],
        }
    out["notizie_extra"] = ctx.get("notizie_extra", {})
    return out
