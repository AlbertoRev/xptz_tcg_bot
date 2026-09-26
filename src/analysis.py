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
