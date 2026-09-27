"""Testi del bot: alert Telegram, frasi della rivista e file dati per l'analisi di Claude."""
import html
import os
from xml.sax.saxutils import escape

import config as C

TIPI = {"sigillato": "Sigillato", "singola": "Carte singole"}

# Se i font di sistema DejaVu mancano, la rivista ripiega su Helvetica, che non ha tutti i caratteri.
UNICODE = any(os.path.exists(base + "DejaVuSans.ttf")
              for base in ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/dejavu/"))


def _t(s):
    """Testo pronto per i paragrafi del PDF."""
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


def _copertura(giorni):
    if giorni >= 181:
        return f"{giorni} giorni di storico: tutte le variazioni sono reali"
    periodi = [str(p) for p in C.PERIODI if giorni > p]
    testo = f"{giorni} giorn{'o' if giorni == 1 else 'i'} di storico"
    return (f"{testo}: variazioni reali a {', '.join(periodi)} giorni, il resto stimato o non ancora disponibile"
            if periodi else f"{testo}: solo stime per le singole")


NOTE_METODO = [
    "Prezzo = prezzo di tendenza Cardmarket (media di tutte le lingue). Variazione = confronto con lo "
    "storico salvato dal bot.",
    "* = stima dal primo giorno, solo per le singole: a 7 giorni media vendite 7 giorni contro media 30 giorni; "
    "a 30 giorni prezzo di tendenza contro media 30 giorni. Le stime vengono sostituite dallo storico reale.",
    "Incertezza: bassa, media o alta secondo regole fisse (stima o storico, numero di vendite, ampiezza della "
    "variazione, prezzo sotto 10 euro).",
    "Il sigillato non ha medie di vendita nei file Cardmarket: le sue variazioni partono dallo storico del bot.",
    "I nomi dei prodotti sono link alla ricerca su Cardmarket: filtra la lingua sulla pagina prima di comprare.",
    "Questa rivista è uno strumento informativo, non una consulenza finanziaria.",
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
            "radar_uscite": [{x: u[x] for x in ("data", "titolo", "fonte", "citazioni", "mercato")}
                             for u in g.get("radar", [])],
            "cosa_farei_con_200_euro": {
                "proposte": [{x: p[x] for x in ("categoria", "nome", "prezzo", "perche", "rischio")}
                             for p in g["carrello"]["proposte"]],
                "speso": g["carrello"]["speso"], "note": g["carrello"]["note"]},
        }
    out["notizie_extra"] = ctx.get("notizie_extra", {})
    return out
