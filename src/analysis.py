"""Tutti i numeri del report vengono calcolati qui, con regole fisse (nessuna AI)."""
import datetime as dt

import numpy as np
import pandas as pd

import config as C
from src import storage


def _tolleranza(periodo):
    return 1 if periodo <= 7 else 3 if periodo <= 30 else 7


def tabella(gioco, giorno, prezzi, catalogo):
    """Unisce prezzi e catalogo e calcola le variazioni per ogni periodo."""
    df = prezzi.join(catalogo[["nome", "tipo", "categoria", "aggiunto"]], how="inner")
    df = df[df["tipo"].isin(["singola", "sigillato"])].copy()

    for p in C.PERIODI:
        df[f"v{p}"] = np.nan
        df[f"f{p}"] = ""
        passato, g = storage.carica_istantanea(gioco, giorno - dt.timedelta(days=p), _tolleranza(p))
        if passato is None or g >= giorno:
            continue
        rif = passato["trend"].reindex(df.index)
        v = df["trend"] / rif - 1
        ok = v.notna() & np.isfinite(v)
        df.loc[ok, f"v{p}"] = v[ok]
        df.loc[ok, f"f{p}"] = "storico"

    # Stime dal primo giorno, solo per le singole (il sigillato non ha medie di vendita)
    sing = df["tipo"] == "singola"
    if 7 in C.PERIODI:
        m = sing & df["v7"].isna() & df["avg7"].notna() & (df["avg30"] > 0)
        df.loc[m, "v7"] = df.loc[m, "avg7"] / df.loc[m, "avg30"] - 1
        df.loc[m, "f7"] = "stima"
    if 30 in C.PERIODI:
        m = sing & df["v30"].isna() & df["trend"].notna() & (df["avg30"] > 0)
        df.loc[m, "v30"] = df.loc[m, "trend"] / df.loc[m, "avg30"] - 1
        df.loc[m, "f30"] = "stima"
    return df


def incertezza(riga, periodo):
    """Regole fisse: più punti = più incertezza."""
    punti, motivi = 0, []
    if riga[f"f{periodo}"] == "stima":
        punti += 2
        motivi.append("stima, non storico reale")
    if riga["tipo"] == "singola" and pd.isna(riga["avg7"]):
        punti += 1
        motivi.append("poche vendite")
    v = riga[f"v{periodo}"]
    if pd.notna(v) and abs(v) > 1:
        punti += 1
        motivi.append("variazione molto ampia")
    if riga["trend"] < 10:
        punti += 1
        motivi.append("prezzo basso")
    livello = "bassa" if punti == 0 else "media" if punti == 1 else "alta"
    return livello, ", ".join(motivi)


def _riga(riga, id_prodotto, periodo, slug, link):
    liv, motivo = incertezza(riga, periodo)
    return {
        "id": int(id_prodotto),
        "nome": riga["nome"],
        "categoria": riga["categoria"],
        "prezzo": round(float(riga["trend"]), 2),
        "variazioni": {str(p): (None if pd.isna(riga[f"v{p}"]) else round(float(riga[f"v{p}"]) * 100, 1))
                       for p in C.PERIODI},
        "fonti": {str(p): riga[f"f{p}"] for p in C.PERIODI},
        "incertezza": liv,
        "motivo_incertezza": motivo,
        "link": link(slug, riga["nome"]),
    }


def classifiche(df, slug, link):
    """Per ogni tipo e periodo: primi rialzi e ribassi."""
    out = {}
    n = C.RIGHE_PER_CLASSIFICA
    for tipo in ("sigillato", "singola"):
        base = df[(df["tipo"] == tipo) & (df["trend"] >= C.MIN_PREZZO_REPORT[tipo])]
        out[tipo] = {}
        for p in C.PERIODI:
            col = f"v{p}"
            el = base[base[col].notna() & (base[col].abs() <= C.VARIAZIONE_MAX_CREDIBILE)]
            su = el[el[col] > 0].nlargest(n, col)
            giu = el[el[col] < 0].nsmallest(n, col)
            out[tipo][str(p)] = {
                "rialzi": [_riga(r, i, p, slug, link) for i, r in su.iterrows()],
                "ribassi": [_riga(r, i, p, slug, link) for i, r in giu.iterrows()],
                # se nessun prodotto è in calo: i più deboli del periodo, per non lasciare vuota la tabella
                "piu_deboli": [] if len(giu) else [_riga(r, i, p, slug, link)
                                                   for i, r in el.nsmallest(n, col).iterrows()],
                "fonte": "storico" if (el[f"f{p}"] == "storico").any() else ("stima" if len(el) else "n.d."),
            }
    return out


def occasioni(df, slug, link, singole=False, limite=10, rapporto_da=None, rapporto_a=None):
    """Prodotti con prezzo minimo tra rapporto_da e rapporto_a volte il prezzo di tendenza."""
    rapporto_da = C.SOGLIA_OCCASIONE_MIN if rapporto_da is None else rapporto_da
    rapporto_a = C.SOGLIA_OCCASIONE if rapporto_a is None else rapporto_a
    minimo = df["tipo"].map(C.MIN_PREZZO_OCCASIONE)
    ammessa = (df["tipo"] == "sigillato") | ((df["tipo"] == "singola") & df["avg7"].notna() & singole)
    rapporto = df["low"] / df["trend"]
    m = (df["trend"] >= minimo) & df["low"].notna() & (rapporto >= rapporto_da) & \
        (rapporto <= rapporto_a) & ammessa
    sel = df[m].assign(rapporto=lambda x: x["low"] / x["trend"]).nsmallest(limite, "rapporto")
    return [{
        "id": int(i), "nome": r["nome"], "tipo": r["tipo"],
        "prezzo_minimo": round(float(r["low"]), 2), "prezzo_tendenza": round(float(r["trend"]), 2),
        "sconto": round((1 - float(r["rapporto"])) * 100, 1), "link": link(slug, r["nome"]),
    } for i, r in sel.iterrows()]


def nuovi_prodotti(catalogo, prezzi, giorno, slug, link, giorni=7, limite=15):
    da = (giorno - dt.timedelta(days=giorni)).isoformat()
    nuovi = catalogo[(catalogo["tipo"] == "sigillato") & (catalogo["aggiunto"] >= da)]
    nuovi = nuovi.join(prezzi[["trend", "low"]], how="left").sort_values("aggiunto", ascending=False)
    return [{
        "id": int(i), "nome": r["nome"], "categoria": r["categoria"], "aggiunto": r["aggiunto"],
        "prezzo": None if pd.isna(r["trend"]) else round(float(r["trend"]), 2),
        "link": link(slug, r["nome"]),
    } for i, r in nuovi.head(limite).iterrows()]


def anomalie(df):
    """Variazioni non credibili: escluse dalle classifiche, solo conteggiate."""
    tot = 0
    for p in C.PERIODI:
        tot += int((df[f"v{p}"].abs() > C.VARIAZIONE_MAX_CREDIBILE).sum())
    return tot


def alert_movimenti(gioco, giorno, df, slug, link):
    """Movimenti forti a 7 giorni, confermati anche il giorno precedente."""
    ieri, _ = storage.carica_istantanea(gioco, giorno - dt.timedelta(days=1))
    r7, _ = storage.carica_istantanea(gioco, giorno - dt.timedelta(days=7), 1)
    r8, _ = storage.carica_istantanea(gioco, giorno - dt.timedelta(days=8), 1)
    if ieri is None or r7 is None or r8 is None:
        return []
    ora = df["trend"] / r7["trend"].reindex(df.index) - 1
    prima = ieri["trend"].reindex(df.index) / r8["trend"].reindex(df.index) - 1
    minimo = df["tipo"].map(C.MIN_PREZZO_ALERT)
    m = (ora.abs() >= C.SOGLIA_ALERT_MOVIMENTO) & (prima.abs() >= C.SOGLIA_CONFERMA) & \
        (np.sign(ora) == np.sign(prima)) & (ora.abs() <= C.VARIAZIONE_MAX_CREDIBILE) & (df["trend"] >= minimo)
    sel = df[m].assign(v=ora[m]).sort_values("v", key=abs, ascending=False)
    return [{
        "id": int(i), "nome": r["nome"], "tipo": r["tipo"], "prezzo": round(float(r["trend"]), 2),
        "variazione_7g": round(float(r["v"]) * 100, 1), "link": link(slug, r["nome"]),
    } for i, r in sel.iterrows()]


def slancio_singole(df, slug, link):
    """Singole con vendite dell'ultima settimana molto diverse dalla media del mese (stima)."""
    v = df["avg7"] / df["avg30"] - 1
    m = (df["tipo"] == "singola") & df["avg7"].notna() & (df["avg30"] > 0) & \
        (df["trend"] >= C.MIN_PREZZO_ALERT["singola"]) & (v.abs() >= C.SOGLIA_SLANCIO) & \
        (v.abs() <= C.VARIAZIONE_MAX_CREDIBILE)
    sel = df[m].assign(v=v[m]).sort_values("v", key=abs, ascending=False)
    return [{
        "id": int(i), "nome": r["nome"], "tipo": r["tipo"], "prezzo": round(float(r["trend"]), 2),
        "variazione": round(float(r["v"]) * 100, 1), "link": link(slug, r["nome"]),
    } for i, r in sel.iterrows()]


ORDINE_STATO = {"caldo": 0, "tiepido": 1, "in arrivo": 2, "da valutare": 3, "freddo": 4}


def previsioni(gioco, giorno, prezzi, catalogo, slug, link):
    """Sigillato in prevendita o appena uscito: caldo, tiepido o freddo secondo regole fisse."""
    inizio = giorno - dt.timedelta(days=C.PREVISIONI_GIORNI)
    cand = catalogo[(catalogo["tipo"] == "sigillato") & (catalogo["aggiunto"] >= inizio.isoformat())]
    if cand.empty:
        return []
    cand = cand.join(prezzi[["trend", "low"]], how="left")
    primo = pd.Series(np.nan, index=cand.index)
    giorni_dati = pd.Series(0, index=cand.index)
    for g in storage.giorni_disponibili(gioco):
        if g < inizio or g >= giorno:
            continue
        snap, _ = storage.carica_istantanea(gioco, g)
        t = snap["trend"].reindex(cand.index)
        nuovo = primo.isna() & t.notna()
        primo[nuovo] = t[nuovo]
        giorni_dati += t.notna().astype(int)

    out = []
    for i, r in cand.iterrows():
        prezzo, basso = r["trend"], r["low"]
        var = prezzo / primo[i] - 1 if pd.notna(prezzo) and pd.notna(primo[i]) and primo[i] > 0 else np.nan
        rapp = basso / prezzo if pd.notna(prezzo) and pd.notna(basso) and prezzo > 0 else np.nan
        if pd.isna(prezzo):
            stato, motivo = "in arrivo", "in prevendita o appena listato, nessuna vendita ancora"
        elif giorni_dati[i] < 7:
            stato, motivo = "da valutare", f"solo {int(giorni_dati[i])} giorni di prezzi"
        elif var >= C.CALDO_VARIAZIONE or (var > 0 and pd.notna(rapp) and rapp >= C.CALDO_RAPPORTO):
            stato = "caldo"
            motivo = f"prezzo {_segno(var)} dal primo rilevamento" + \
                     (", poche offerte sotto la tendenza" if pd.notna(rapp) and rapp >= C.CALDO_RAPPORTO else "")
        elif var <= C.FREDDO_VARIAZIONE or (pd.notna(rapp) and rapp < C.FREDDO_RAPPORTO):
            stato = "freddo"
            motivo = f"prezzo {_segno(var)} dal primo rilevamento" + \
                     (", molte offerte molto sotto la tendenza" if pd.notna(rapp) and rapp < C.FREDDO_RAPPORTO else "")
        else:
            stato, motivo = "tiepido", f"prezzo {_segno(var)} dal primo rilevamento, stabile"
        out.append({
            "id": int(i), "nome": r["nome"], "categoria": r["categoria"], "aggiunto": r["aggiunto"],
            "prezzo": None if pd.isna(prezzo) else round(float(prezzo), 2),
            "variazione": None if pd.isna(var) else round(float(var) * 100, 1),
            "stato": stato, "motivo": motivo, "link": link(slug, r["nome"]),
        })
    # i prodotti in arrivo hanno sempre posto (fino a 10), il resto per stato e prezzo
    in_arrivo = sorted([x for x in out if x["stato"] == "in arrivo"], key=lambda x: x["aggiunto"], reverse=True)[:10]
    altri = sorted([x for x in out if x["stato"] != "in arrivo"],
                   key=lambda x: (ORDINE_STATO[x["stato"]], -(x["prezzo"] or 0)))
    scelti = altri[:max(0, C.PREVISIONI_MAX_RIGHE - len(in_arrivo))] + in_arrivo
    return sorted(scelti, key=lambda x: ORDINE_STATO[x["stato"]])


def _segno(v):
    if pd.isna(v):
        return "n.d."
    return f"{'+' if v > 0 else ''}{v * 100:.0f}%"


def carrello(previsioni, occasioni, classifiche, giorni_storico, budget=200):
    """'Cosa farei con 200 euro': proposta automatica con regole fisse, al massimo 3 acquisti."""
    gruppi = []
    occ = sorted([o for o in occasioni if o["tipo"] == "sigillato" and o["prezzo_minimo"] <= budget],
                 key=lambda o: -o["sconto"])
    gruppi.append([{
        "categoria": "Occasione", "nome": o["nome"], "prezzo": o["prezzo_minimo"], "link": o["link"],
        "perche": f"offerta a {_euro(o['prezzo_minimo'])} contro un prezzo di tendenza di "
                  f"{_euro(o['prezzo_tendenza'])} (-{o['sconto']:.0f}%)",
        "rischio": "l'offerta più bassa può essere in un'altra lingua o in condizioni peggiori",
    } for o in occ])
    caldi = sorted([p for p in previsioni if p["stato"] == "caldo" and p["prezzo"] and p["prezzo"] <= budget],
                   key=lambda p: -(p["variazione"] or 0))
    gruppi.append([{
        "categoria": "Novità calda", "nome": p["nome"], "prezzo": p["prezzo"], "link": p["link"],
        "perche": p["motivo"],
        "rischio": "i prodotti nuovi possono calare quando arrivano le ristampe",
    } for p in caldi])
    solidi = []
    for p in ("90", "30"):
        for r in classifiche["sigillato"][p]["rialzi"]:
            v7 = r["variazioni"].get("7")
            if r["incertezza"] != "alta" and r["fonti"][p] == "storico" and (v7 is None or v7 >= -5) \
                    and r["prezzo"] <= budget:
                solidi.append({
                    "categoria": "Tendenza solida", "nome": r["nome"], "prezzo": r["prezzo"], "link": r["link"],
                    "perche": f"in salita del {r['variazioni'][p]:.0f}% a {p} giorni, senza cali nell'ultima settimana",
                    "rischio": "chi compra dopo un rialzo può trovare il picco",
                })
        if solidi:
            break
    gruppi.append(solidi)

    proposte, residuo, nomi = [], float(budget), set()
    for gruppo in gruppi:
        for x in gruppo:
            if x["prezzo"] <= residuo and x["nome"] not in nomi:
                proposte.append(x)
                nomi.add(x["nome"])
                residuo -= x["prezzo"]
                break
    note = []
    if giorni_storico < 30:
        note.append(f"Lo storico copre solo {giorni_storico} giorni: prudenza, i segnali sono ancora deboli.")
    if not proposte:
        note.append("Nessun segnale abbastanza forte questa settimana: terrei i 200 € da parte.")
    return {"proposte": proposte, "speso": round(budget - residuo, 2), "residuo": round(residuo, 2), "note": note}


def _euro(v):
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
