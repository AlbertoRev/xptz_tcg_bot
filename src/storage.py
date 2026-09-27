"""Storico prezzi: un file compresso per gioco e per giorno, dentro la cartella data/."""
import datetime as dt
import json
from pathlib import Path

import pandas as pd

DATI = Path("data")


def _percorso(gioco, giorno):
    return DATI / "storico" / gioco / f"{giorno.isoformat()}.parquet"


def salva_istantanea(gioco, giorno, df):
    p = _percorso(gioco, giorno)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.reset_index().to_parquet(p, compression="zstd", index=False)


def esiste_istantanea(gioco, giorno):
    return _percorso(gioco, giorno).exists()


def carica_istantanea(gioco, giorno, tolleranza=0):
    """Istantanea del giorno richiesto o della più vicina entro 'tolleranza' giorni."""
    for k in range(tolleranza + 1):
        for g in ([giorno] if k == 0 else [giorno - dt.timedelta(days=k), giorno + dt.timedelta(days=k)]):
            p = _percorso(gioco, g)
            if p.exists():
                return pd.read_parquet(p).set_index("id"), g
    return None, None


def giorni_disponibili(gioco):
    cartella = DATI / "storico" / gioco
    if not cartella.exists():
        return []
    return sorted(dt.date.fromisoformat(f.stem) for f in cartella.glob("*.parquet"))


def leggi_json(nome, predefinito):
    p = DATI / nome
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return predefinito
    return predefinito


def scrivi_json(nome, contenuto):
    p = DATI / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(contenuto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
