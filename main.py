"""Avvio del bot.

  python main.py setup         -> riconosce i giochi su Cardmarket e manda un messaggio di prova
  python main.py giornaliero   -> salva i prezzi del giorno e manda gli alert
  python main.py settimanale   -> salva i prezzi (se mancano) e manda il report completo
"""
import datetime as dt
import html
import sys
from pathlib import Path

import config as C
from src import analysis, cardmarket, news, report, storage, telegram, verify

LINGUE_IT = {"italian": "italiano", "english": "inglese", "japanese": "giapponese"}


def id_giochi():
    ids = storage.leggi_json("id_giochi.json", {})
    if not all(k in ids for k in C.GIOCHI):
        trovati = cardmarket.trova_id_giochi(C.GIOCHI)
        ids = {k: trovati.get(k) for k in C.GIOCHI}
        storage.scrivi_json("id_giochi.json", ids)
    return ids


def raccogli():
    """Scarica prezzi e catalogo di ogni gioco e salva l'istantanea del giorno."""
    risultati = {}
    for chiave, g in C.GIOCHI.items():
        gid = id_giochi().get(chiave)
        if not gid:
            print(f"[!] {g['nome']}: gioco non trovato su Cardmarket, salto")
            continue
        data, prezzi = cardmarket.price_guide(gid)
        giorno = dt.date.fromisoformat(data) if data else dt.date.today()
        cat = cardmarket.catalogo(gid, g["escludi_nomi"])
        if not storage.esiste_istantanea(chiave, giorno):
            tipi = cat["tipo"].reindex(prezzi.index)
            minimo = tipi.map(C.MIN_PREZZO_STORICO)
            da_salvare = prezzi[(prezzi["trend"] >= minimo) | (prezzi["avg"] >= minimo)]
            storage.salva_istantanea(chiave, giorno, da_salvare[["trend"]].round(2))
            print(f"{g['nome']}: salvati {len(da_salvare)} prodotti per il {giorno}")
        risultati[chiave] = (giorno, prezzi, cat)
    return risultati


def giornaliero():
    dati = raccogli()
    stato = storage.leggi_json("stato_alert.json", {})
    oggi = dt.date.today()
    singole = verify.attivo() or C.OCCASIONI_SINGOLE_SENZA_VERIFICA
    movimenti, occasioni = [], []
    for chiave, (giorno, prezzi, cat) in dati.items():
        g = C.GIOCHI[chiave]
        if g["livello"] != "principale":
            continue
        slug, lingua = g["slug_cardmarket"], LINGUE_IT.get(g["lingua"], g["lingua"])
        df = analysis.tabella(chiave, giorno, prezzi, cat)
        for a in analysis.alert_movimenti(chiave, giorno, df, slug, cardmarket.link_ricerca):
            movimenti.append({**a, "genere": "movimento", "gioco": g["nome"], "lingua_it": lingua})
        for o in analysis.occasioni(df, slug, cardmarket.link_ricerca, singole):
            occasioni.append({**o, "genere": "occasione", "gioco": g["nome"], "lingua_it": lingua,
                              "lingua": g["lingua"]})

    # prima i movimenti, poi le occasioni più scontate; niente doppioni per 7 giorni
    occasioni.sort(key=lambda o: -o["sconto"])
    nuovi, n_occ = [], 0
    for a in movimenti + occasioni:
        if a["genere"] == "occasione" and n_occ >= C.MAX_OCCASIONI_AL_GIORNO:
            continue
        chiave_alert = f"{a['genere']}:{a['id']}"
        ultimo = stato.get(chiave_alert)
        if ultimo and (oggi - dt.date.fromisoformat(ultimo)).days < 7:
            continue
        if a["genere"] == "occasione":
            verify.verifica([a], a["lingua"])
            n_occ += 1
        nuovi.append(a)
        stato[chiave_alert] = oggi.isoformat()
        if len(nuovi) >= C.MAX_ALERT_AL_GIORNO:
            break
    stato = {k: v for k, v in stato.items() if (oggi - dt.date.fromisoformat(v)).days < 30}
    storage.scrivi_json("stato_alert.json", stato)
    if nuovi:
        telegram.messaggio(report.telegram_alert(nuovi))
    print(f"Alert inviati: {len(nuovi)}")


def settimanale():
    dati = raccogli()
    oggi = dt.date.today()
    ctx = {"data": oggi.isoformat(), "data_it": oggi.strftime("%d/%m/%Y"),
           "mensile": oggi.day <= 7, "giochi": {}, "anomalie": 0}
    for chiave, (giorno, prezzi, cat) in dati.items():
        g = C.GIOCHI[chiave]
        slug = g["slug_cardmarket"]
        df = analysis.tabella(chiave, giorno, prezzi, cat)
        ctx["anomalie"] += analysis.anomalie(df)
        singole = verify.attivo() or C.OCCASIONI_SINGOLE_SENZA_VERIFICA
        occ = analysis.occasioni(df, slug, cardmarket.link_ricerca, singole) if g["livello"] == "principale" else []
        ctx["giochi"][chiave] = {
            "nome": g["nome"], "livello": g["livello"],
            "lingua_it": LINGUE_IT.get(g["lingua"], g["lingua"]),
            "giorni_storico": len(storage.giorni_disponibili(chiave)),
            "classifiche": analysis.classifiche(df, slug, cardmarket.link_ricerca),
            "occasioni": verify.verifica(occ, g["lingua"]),
            "nuovi": analysis.nuovi_prodotti(cat, prezzi, giorno, slug, cardmarket.link_ricerca)
            if g["livello"] == "principale" else [],
            "notizie": news.notizie(chiave),
        }
    ctx["notizie_extra"] = {k: news.notizie(k) for k in C.NOTIZIE_EXTRA}

    Path("output").mkdir(exist_ok=True)
    percorso_pdf = f"output/report_{oggi.isoformat()}.pdf"
    report.pdf(percorso_pdf, ctx)
    storage.scrivi_json("riepilogo/ultimo.json", report.dati_per_claude(ctx))
    telegram.messaggio(report.telegram_settimanale(ctx))
    telegram.documento(percorso_pdf, f"Report TCG {ctx['data_it']}")
    print("Report settimanale inviato")


def setup():
    trovati = cardmarket.trova_id_giochi(C.GIOCHI)
    ids = {k: trovati.get(k) for k in C.GIOCHI}
    storage.scrivi_json("id_giochi.json", ids)
    righe = ["<b>✅ Bot TCG collegato</b>", "", "Giochi trovati su Cardmarket:"]
    for chiave, g in C.GIOCHI.items():
        gid = ids.get(chiave)
        if not gid:
            righe.append(f"• {g['nome']}: NON trovato")
            continue
        cat = cardmarket.catalogo(gid, [])
        esempi = html.escape(", ".join(cat[cat["tipo"] == "sigillato"]["nome"].head(3)))
        righe.append(f"• {g['nome']}: codice {gid}, {len(cat)} prodotti (es. {esempi})")
    righe += ["", "Se i nomi di esempio corrispondono al gioco giusto, è tutto a posto."]
    telegram.messaggio("\n".join(righe))
    print("\n".join(righe))


if __name__ == "__main__":
    comandi = {"setup": setup, "giornaliero": giornaliero, "settimanale": settimanale}
    if len(sys.argv) != 2 or sys.argv[1] not in comandi:
        print(__doc__)
        sys.exit(1)
    comandi[sys.argv[1]]()
