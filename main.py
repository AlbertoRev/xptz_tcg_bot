"""Avvio del bot.

  python main.py setup         -> riconosce i giochi su Cardmarket e manda un messaggio di prova
  python main.py giornaliero   -> salva i prezzi del giorno e manda gli alert
  python main.py settimanale   -> salva i prezzi (se mancano) e manda il report completo
  python main.py prova_grafica -> prova il nuovo art director Gemini senza inviare PDF
"""
import datetime as dt
import html
import json
import sys
from pathlib import Path

import config as C
from download_assets import scarica_immagini_pokemon
from src import analysis, art_director, cardmarket, news, report, rivista, storage, telegram, verify

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


ORDINE = {"movimento": 0, "occasione": 1, "slancio": 1, "da_osservare": 2}


def _seleziona(candidati, limite, stato, oggi):
    """Sceglie fino a 'limite' alert: prima per tipo di segnale, poi le novità."""
    visti = set()
    unici = []
    for a in candidati:
        if a["id"] in visti:
            continue
        visti.add(a["id"])
        genere = "occasione" if a["genere"] == "da_osservare" else a["genere"]
        a["_chiave"] = f"{genere}:{a['id']}"
        s = stato.get(a["_chiave"])
        continuo = s and (oggi - dt.date.fromisoformat(s["ultimo"])).days <= 2
        a["segnalato_dal"] = s["primo"] if continuo and s["primo"] != oggi.isoformat() else None
        unici.append(a)
    unici.sort(key=lambda a: (ORDINE[a["genere"]], a["segnalato_dal"] is not None))
    scelti = []
    for a in unici:
        if not C.RIPETI_ALERT_ATTIVI and a["segnalato_dal"]:
            continue
        if a["genere"] in ("occasione", "da_osservare"):
            verify.verifica([a], a["lingua"])
        stato[a["_chiave"]] = {"primo": a["segnalato_dal"] or oggi.isoformat(), "ultimo": oggi.isoformat()}
        scelti.append(a)
        if len(scelti) >= limite:
            break
    # nel messaggio i nuovi compaiono per primi, poi quelli ancora attivi (ognuno per tipo di segnale)
    scelti.sort(key=lambda a: (a["segnalato_dal"] is not None, ORDINE[a["genere"]]))
    return scelti


def giornaliero():
    dati = raccogli()
    stato = storage.leggi_json("stato_alert.json", {})
    for k, v in list(stato.items()):          # formato vecchio: solo la data
        if isinstance(v, str):
            stato[k] = {"primo": v, "ultimo": v}
    oggi = dt.date.today()
    singole_occ = verify.attivo() or C.OCCASIONI_SINGOLE_SENZA_VERIFICA

    for chiave, (giorno, prezzi, cat) in dati.items():
        g = C.GIOCHI[chiave]
        if g["livello"] != "principale":
            continue
        slug = g["slug_cardmarket"]
        base = {"gioco": g["nome"], "lingua_it": LINGUE_IT.get(g["lingua"], g["lingua"]), "lingua": g["lingua"]}
        df = analysis.tabella(chiave, giorno, prezzi, cat)
        link = cardmarket.link_ricerca

        movimenti = [{**a, **base, "genere": "movimento"} for a in analysis.alert_movimenti(chiave, giorno, df, slug, link)]

        # --- sigillato
        occ = [{**o, **base, "genere": "occasione"}
               for o in analysis.occasioni(df, slug, link, singole_occ, limite=500) if o["tipo"] == "sigillato"]
        oss = []
        if C.RIEMPI_CON_DA_OSSERVARE:
            oss = [{**o, **base, "genere": "da_osservare"}
                   for o in analysis.occasioni(df, slug, link, singole_occ, limite=500,
                                               rapporto_da=C.SOGLIA_OCCASIONE, rapporto_a=C.SOGLIA_DA_OSSERVARE)
                   if o["tipo"] == "sigillato"]
        mov_sig = [a for a in movimenti if a["tipo"] == "sigillato"]
        sig = _seleziona(mov_sig + occ + oss, C.MAX_ALERT_SIGILLATO, stato, oggi)
        telegram.messaggio(report.telegram_alert(sig, g["nome"], "sigillato", (len(mov_sig), len(occ), len(oss))))

        # --- carte singole
        # carte singole: solo ribassi
        mov_sing = [a for a in movimenti if a["tipo"] == "singola" and a["variazione_7g"] < 0]
        sla = [{**a, **base, "genere": "slancio"} for a in analysis.slancio_singole(df, slug, link)
               if a["variazione"] < 0]
        sing = _seleziona(mov_sing + sla, C.MAX_ALERT_SINGOLE, stato, oggi)
        telegram.messaggio(report.telegram_alert(sing, g["nome"], "singola", (len(mov_sing), len(sla))))
        print(f"{g['nome']}: {len(sig)} alert sigillato, {len(sing)} alert singole")

    stato = {k: v for k, v in stato.items() if (oggi - dt.date.fromisoformat(v["ultimo"])).days < 30}
    storage.scrivi_json("stato_alert.json", stato)


MESI_IT = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
           "ottobre", "novembre", "dicembre"]


def _apertura(g):
    """Titolo di copertina scelto con regole fisse: prima i movimenti da storico reale (mai stime)."""
    for tipo in ("sigillato", "singola"):
        for per in sorted(C.PERIODI, reverse=True):
            c = g["classifiche"][tipo][str(per)]
            reali = [r for r in c["rialzi"] if r["fonti"][str(per)] == "storico"]
            if reali:
                r = reali[0]
                return {"titolo": f"{r['nome']} vola: {report._perc(r['variazioni'][str(per)])} in {per} giorni",
                        "sottotitolo": f"Prezzo di tendenza {report._eur(r['prezzo'])}, incertezza {r['incertezza']}."}
    caldi = [p for p in g["previsioni"] if p["stato"] == "caldo"]
    if caldi:
        p = caldi[0]
        return {"titolo": f"{p['nome']}: è la novità più calda della settimana",
                "sottotitolo": f"{p['motivo'].capitalize()}. Prezzo attuale {report._eur(p['prezzo'])}."}
    if g["radar"]:
        u = g["radar"][0]
        return {"titolo": u["titolo"], "sottotitolo": f"Fonte: {u['fonte']}."}
    return {"titolo": "Settimana tranquilla sul mercato Pokémon",
            "sottotitolo": "Pochi movimenti rilevanti: il bot sta ancora accumulando storico."}


def settimanale():
    oggi = dt.date.today()
    numero = storage.leggi_json("numero_rivista.json", {"numero": 0})["numero"] + 1
    # Prepara subito gli asset: così un eventuale problema grafico è evidente
    # prima di spendere tempo su Cardmarket e notizie. Il downloader è tollerante
    # agli errori e lascia comunque generare il PDF.
    pokemon_mondo = scarica_immagini_pokemon(numero=numero, data=oggi.isoformat())
    dati = raccogli()
    ctx = {"data": oggi.isoformat(), "data_it": oggi.strftime("%d/%m/%Y"), "numero": numero,
           "data_lunga": f"{oggi.day} {MESI_IT[oggi.month - 1]} {oggi.year}",
           "mensile": oggi.day <= 7, "giochi": {}, "anomalie": 0}
    prossima = oggi + dt.timedelta(days=7)
    ctx["prossima"] = f"{prossima.day} {MESI_IT[prossima.month - 1]}"
    radar_grezzo = news.uscite(oggi)
    for chiave, (giorno, prezzi, cat) in dati.items():
        g = C.GIOCHI[chiave]
        slug, link = g["slug_cardmarket"], cardmarket.link_ricerca
        df = analysis.tabella(chiave, giorno, prezzi, cat)
        ctx["anomalie"] += analysis.anomalie(df)
        singole = verify.attivo() or C.OCCASIONI_SINGOLE_SENZA_VERIFICA
        occ = verify.verifica(analysis.occasioni(df, slug, link, singole), g["lingua"])
        classifiche = analysis.classifiche(df, slug, link)
        previsioni = analysis.previsioni(chiave, giorno, prezzi, cat, slug, link)
        giorni_storico = len(storage.giorni_disponibili(chiave))
        minimi = df["tipo"].map(C.MIN_PREZZO_REPORT)
        ctx["giochi"][chiave] = {
            "nome": g["nome"], "livello": g["livello"],
            "lingua_it": LINGUE_IT.get(g["lingua"], g["lingua"]),
            "giorni_storico": giorni_storico,
            "monitorati": int((df["trend"] >= minimi).sum()),
            "classifiche": classifiche,
            "occasioni": occ,
            "previsioni": previsioni,
            "radar": news.collega_previsioni([dict(u) for u in radar_grezzo], previsioni),
            "carrello": analysis.carrello(previsioni, occ, classifiche, giorni_storico),
            "notizie": news.notizie(chiave),
        }
    ctx["notizie_extra"] = {}

    g = next(iter(ctx["giochi"].values()))
    ctx["principale"] = g
    ctx["apertura"] = _apertura(g)
    ctx["kpi"] = [(f"{g['monitorati']:,}".replace(",", "."), "prodotti monitorati"),
                  (sum(1 for p in g["previsioni"] if p["stato"] == "caldo"), "novità calde"),
                  (len(g["occasioni"]), "occasioni sul sigillato"),
                  (len(g["radar"]), "uscite nel radar")]
    ctx["sommario"] = [("La settimana in breve", "i fatti del mercato in pochi punti"),
                       ("Cosa farei con 200 €", "la proposta d'acquisto della settimana"),
                       ("Le uscite in arrivo", "il radar delle date dalle notizie"),
                       ("Il termometro delle novità", "prevendite e uscite: caldo o freddo"),
                       ("Il borsino", "chi sale e chi scende a 7, 30, 90 e 180 giorni"),
                       ("Occasioni e attualità", "affari da controllare e notizie")]
    ctx["sintesi"] = report.sintesi_righe(ctx)
    ctx["note_metodo"] = report.NOTE_METODO
    titoli_art = [x[0] for x in ctx["sommario"]] + [ctx["apertura"]["titolo"]]
    piano = art_director.genera_piano(numero, "hoenn", pokemon_mondo.get("pokemon", []), titoli_art)
    assets_poke = list(pokemon_mondo.get("pokemon", []))
    for i, pagina in enumerate(piano.get("pages", [])):
        pagina["hero_asset"] = assets_poke[i % len(assets_poke)] if assets_poke else None
    ctx["art_direction"] = piano

    Path("output").mkdir(exist_ok=True)
    percorso_pdf = f"output/Il_Collezionista_n{numero}_{oggi.isoformat()}.pdf"
    ctx["pokemon_mondo"] = pokemon_mondo
    rivista.crea(percorso_pdf, ctx)
    storage.scrivi_json("riepilogo/ultimo.json", report.dati_per_claude(ctx))
    telegram.documento(percorso_pdf, f"Il Collezionista n. {numero} - {ctx['data_lunga']}")
    storage.scrivi_json("numero_rivista.json", {"numero": numero})
    print(f"Rivista n. {numero} inviata")


def prova_grafica():
    numero = storage.leggi_json("numero_rivista.json", {"numero": 0})["numero"] + 1
    piano = art_director.salva_piano_test(numero, "hoenn")
    print(json.dumps(piano, ensure_ascii=False, indent=2))


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
    comandi = {"setup": setup, "giornaliero": giornaliero, "settimanale": settimanale, "prova_grafica": prova_grafica}
    if len(sys.argv) != 2 or sys.argv[1] not in comandi:
        print(__doc__)
        sys.exit(1)
    comandi[sys.argv[1]]()
