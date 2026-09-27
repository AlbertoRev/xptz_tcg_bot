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
        E.append(Paragraph("Previsioni", st["h2"]))
        E.append(Paragraph(_t(
            f"Sigillato aggiunto su Cardmarket negli ultimi {C.PREVISIONI_GIORNI} giorni: prevendite e uscite "
            "recenti. Caldo = prezzo in salita o poche offerte sotto la tendenza; freddo = prezzo in calo o "
            "molte offerte molto scontate. Le date di uscita ufficiali sono nell'analisi di Claude."), st["nota"]))
        if g["previsioni"]:
            colori = {"caldo": "#c0392b", "tiepido": "#b9770e", "freddo": "#2e6da4"}
            dati = [["Prodotto", "Aggiunto", "Prezzo", "Variaz.", "Stato", "Perché"]]
            for n in g["previsioni"]:
                stato = n["stato"]
                col = colori.get(stato)
                cella_stato = Paragraph(f'<font color="{col}"><b>{stato}</b></font>' if col else _t(stato),
                                        st["cella"])
                dati.append([_link(n["nome"], n["link"], st["cella"]), n["aggiunto"], _eur(n["prezzo"]),
                             _perc(n["variazione"]), cella_stato, Paragraph(_t(n["motivo"]), st["cella"])])
            t = Table(dati, colWidths=[58 * mm, 19 * mm, 19 * mm, 18 * mm, 20 * mm, 52 * mm], repeatRows=1)
            t.setStyle(_stile_tabella())
            E.append(t)
        else:
            E.append(Paragraph("Nessun prodotto sigillato nuovo nel periodo.", st["nota"]))
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
            E.append(Paragraph("Occasioni sul sigillato", st["h2"]))
            E.append(Paragraph(_t("Prezzo minimo in vendita molto sotto la tendenza. Il minimo può riferirsi a "
                                  "un'altra lingua o condizione."), st["nota"]))
            con_lingua = any(o.get("verifica_lingua") for o in g["occasioni"])
            dati = [["Prodotto", "Tipo", "Minimo", "Tendenza", "Sconto"] + (["In lingua"] if con_lingua else [])]
            for o in g["occasioni"]:
                v = o.get("verifica_lingua") or {}
                dati.append([_link(o["nome"], o["link"], st["cella"]), o["tipo"], _eur(o["prezzo_minimo"]),
                             _eur(o["prezzo_tendenza"]), _perc(-o["sconto"])]
                            + ([_eur(v.get("da"))] if con_lingua else []))
            larg = [72 * mm, 18 * mm, 22 * mm, 22 * mm, 18 * mm] + ([24 * mm] if con_lingua else [])
            t = Table(dati, colWidths=larg, repeatRows=1)
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
    """Frasi della rubrica 'La settimana in breve', costruite dai numeri."""
    righe = []
    for g in ctx["giochi"].values():
        if g["livello"] != "principale":
            continue
        for tipo, nome in (("sigillato", "Sigillato"), ("singola", "Carte singole")):
            p, r = _migliore(g, tipo, "rialzi")
            if r:
                righe.append(f"{nome}: il rialzo più forte è {r['nome']}, {_perc(r['variazioni'][str(p)])} in {p} "
                             f"giorni (prezzo {_eur(r['prezzo'])}, incertezza {r['incertezza']}).")
            p, r = _migliore(g, tipo, "ribassi")
            if r:
                righe.append(f"{nome}: il calo più forte è {r['nome']}, {_perc(r['variazioni'][str(p)])} in {p} "
                             f"giorni (prezzo {_eur(r['prezzo'])}).")
        caldi = [p["nome"] for p in g.get("previsioni", []) if p["stato"] == "caldo"]
        if g.get("previsioni"):
            righe.append(f"Novità: {len(caldi)} calde su {len(g['previsioni'])} prodotti in prevendita, in arrivo o "
                         f"appena usciti" + (f"; in testa {caldi[0]}." if caldi else "."))
        if g.get("radar"):
            u = g["radar"][0]
            righe.append(f"Prossima data nel radar: {u['data'][8:10]}/{u['data'][5:7]}, {u['titolo']}.")
        if g["occasioni"]:
            righe.append(f"{len(g['occasioni'])} offerte sul sigillato molto sotto il prezzo di tendenza.")
        righe.append(f"Storico disponibile: {_copertura(g['giorni_storico'])}.")
    return righe or ["Nessun movimento rilevante: servono ancora dati storici."]


def telegram_settimanale(ctx):
    g = ctx["principale"]
    r = [f"<b>🗞 Il Collezionista n. {ctx['numero']}</b>",
         f"<i>Settimanale del mercato Pokémon · {ctx['data_lunga']}</i>", "",
         f"<b>In primo piano:</b> {html.escape(ctx['apertura']['titolo'])}", ""]
    car = g["carrello"]
    if car["proposte"]:
        r.append(f"<b>💶 Cosa farei con 200 €</b> ({_eur(car['speso'])})")
        for x in car["proposte"]:
            r.append(f"• {html.escape(x['categoria'])}: <a href=\"{html.escape(x['link'])}\">"
                     f"{html.escape(x['nome'][:50])}</a> {_eur(x['prezzo'])}")
    else:
        r.append("<b>💶 Cosa farei con 200 €:</b> niente, li terrei da parte")
    r.append("")
    if g["radar"]:
        u = g["radar"][0]
        r.append(f"📅 Prossima uscita nel radar: {u['data'][8:10]}/{u['data'][5:7]} - {html.escape(u['titolo'][:70])}")
    conta = {k: sum(1 for p in g["previsioni"] if p["stato"] == k) for k in ("caldo", "tiepido", "freddo")}
    r.append(f"🔮 Novità: {conta['caldo']} calde, {conta['tiepido']} tiepide, {conta['freddo']} fredde")
    r.append(f"💡 {len(g['occasioni'])} occasioni sul sigillato")
    r += ["", "La rivista completa è nel PDF qui sotto."]
    return "\n".join(r)


def telegram_alert(alert, gioco, tipo, conteggi):
    titolo = "Sigillato" if tipo == "sigillato" else "Carte singole in ribasso"
    icona_t = "📦" if tipo == "sigillato" else "🃏"
    r = [f"<b>{icona_t} Alert {html.escape(gioco)} · {titolo}</b>"]
    if not alert:
        r += ["", "Nessun segnale oggi."]
    else:
        n_nuovi = sum(1 for a in alert if not a.get("segnalato_dal"))
        r += [f"{len(alert)} alert: {n_nuovi} nuovi, {len(alert) - n_nuovi} ancora attivi", ""]
    for a in alert:
        link = f"<a href=\"{html.escape(a['link'])}\">{html.escape(a['nome'][:55])}</a>"
        if a["genere"] == "movimento":
            icona = "🔺" if a["variazione_7g"] > 0 else "🔻"
            riga = f"{icona} {link}: {_perc(a['variazione_7g'])} in 7 giorni, ora {_eur(a['prezzo'])}"
        elif a["genere"] == "slancio":
            icona = "📈" if a["variazione"] > 0 else "📉"
            riga = (f"{icona} {link}: vendite 7 giorni {_perc(a['variazione'])} rispetto al mese, "
                    f"prezzo {_eur(a['prezzo'])}")
        else:
            icona = "💡" if a["genere"] == "occasione" else "👀"
            riga = (f"{icona} {link}: minimo {_eur(a['prezzo_minimo'])} contro tendenza "
                    f"{_eur(a['prezzo_tendenza'])} (-{a['sconto']:.0f}%)")
            v = a.get("verifica_lingua")
            if v and v.get("da"):
                riga += f" · in {a['lingua_it']} da {_eur(v['da'])}"
        if a.get("segnalato_dal"):
            d = a["segnalato_dal"]
            riga += f" · <i>attivo dal {d[8:10]}/{d[5:7]}</i>"
        else:
            riga += " · <b>nuovo</b>"
        r.append(riga)
    r.append("")
    if tipo == "sigillato":
        r.append(f"<i>Trovati oggi: {conteggi[0]} movimenti, {conteggi[1]} occasioni, {conteggi[2]} da osservare</i>")
        r.append("<i>🔺🔻 movimento forte confermato · 💡 minimo sotto il 70% della tendenza · "
                 "👀 minimo tra 70% e 85%</i>")
    else:
        r.append(f"<i>Trovati oggi: {conteggi[0]} ribassi forti, {conteggi[1]} carte con vendite in calo</i>")
        r.append("<i>🔻 ribasso forte confermato · 📉 vendite dell'ultima settimana sotto la media del mese "
                 "(stima)</i>")
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
            "previsioni": [{x: n[x] for x in ("nome", "categoria", "aggiunto", "prezzo", "variazione", "stato", "motivo")}
                           for n in g["previsioni"]],
            "notizie": g["notizie"],
        }
    for k, g in ctx["giochi"].items():
        out["giochi"][k]["radar_uscite"] = [{x: u[x] for x in ("data", "titolo", "fonte", "citazioni", "mercato")}
                                            for u in g.get("radar", [])]
        out["giochi"][k]["cosa_farei_con_200_euro"] = {
            "proposte": [{x: p[x] for x in ("categoria", "nome", "prezzo", "perche", "rischio")}
                         for p in g["carrello"]["proposte"]],
            "speso": g["carrello"]["speso"], "note": g["carrello"]["note"]}
    out["notizie_extra"] = ctx.get("notizie_extra", {})
    return out
