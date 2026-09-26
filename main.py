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
    for k, v in list(stato.items()):          # formato vecchio: solo la data
        if isinstance(v, str):
            stato[k] = {"primo": v, "ultimo": v}
    oggi = dt.date.today()
    singole = verify.attivo() or C.OCCASIONI_SINGOLE_SENZA_VERIFICA
    n = C.MAX_ALERT_PER_GIOCO
    inviati, conteggi = [], {}

    for chiave, (giorno, prezzi, cat) in dati.items():
        g = C.GIOCHI[chiave]
        if g["livello"] != "principale":
            continue
        slug, lingua = g["slug_cardmarket"], LINGUE_IT.get(g["lingua"], g["lingua"])
        base = {"gioco": g["nome"], "lingua_it": lingua, "lingua": g["lingua"]}
        df = analysis.tabella(chiave, giorno, prezzi, cat)

        movimenti = [{**a, **base, "genere": "movimento"}
                     for a in analysis.alert_movimenti(chiave, giorno, df, slug, cardmarket.link_ricerca)]
        occasioni = [{**o, **base, "genere": "occasione"}
                     for o in analysis.occasioni(df, slug, cardmarket.link_ricerca, singole, limite=500)]
        da_osservare = []
        if C.RIEMPI_CON_DA_OSSERVARE:
            gia = {o["id"] for o in occasioni}
            da_osservare = [{**o, **base, "genere": "da_osservare"}
                            for o in analysis.occasioni(df, slug, cardmarket.link_ricerca, singole, limite=500,
                                                        rapporto_da=C.SOGLIA_OCCASIONE,
                                                        rapporto_a=C.SOGLIA_DA_OSSERVARE)
                            if o["id"] not in gia]
        conteggi[g["nome"]] = (len(movimenti), len(occasioni), len(da_osservare))

        # data della prima segnalazione per i prodotti ancora in allerta
        candidati = movimenti + occasioni + da_osservare
        for a in candidati:
            k = f"{'occasione' if a['genere'] == 'da_osservare' else a['genere']}:{a['id']}"
            s = stato.get(k)
            continuo = s and (oggi - dt.date.fromisoformat(s["ultimo"])).days <= 2
            a["segnalato_dal"] = s["primo"] if continuo and s["primo"] != oggi.isoformat() else None
            a["_chiave"] = k

        # priorità: movimenti, occasioni, da osservare; dentro ogni gruppo prima le novità
        ordine = {"movimento": 0, "occasione": 1, "da_osservare": 2}
        candidati.sort(key=lambda a: (ordine[a["genere"]], a["segnalato_dal"] is not None))
        scelti = []
        for a in candidati:
            if not C.RIPETI_ALERT_ATTIVI and a["segnalato_dal"]:
                continue
            if a["genere"] != "movimento":
                verify.verifica([a], a["lingua"])
            stato[a["_chiave"]] = {"primo": a["segnalato_dal"] or oggi.isoformat(), "ultimo": oggi.isoformat()}
            scelti.append(a)
            if len(scelti) >= n:
                break
        inviati += scelti

    stato = {k: v for k, v in stato.items() if (oggi - dt.date.fromisoformat(v["ultimo"])).days < 30}
    storage.scrivi_json("stato_alert.json", stato)
    if inviati:
        telegram.messaggio(report.telegram_alert(inviati, conteggi))
    print(f"Alert inviati: {len(inviati)} - candidati per gioco (movimenti, occasioni, da osservare): {conteggi}")


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
