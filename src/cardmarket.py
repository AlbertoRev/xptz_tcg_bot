"""Scarica catalogo prodotti e price guide pubblici di Cardmarket (file ufficiali, gratuiti)."""
import re
import time
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

BASE = "https://downloads.s3.cardmarket.com/productCatalog"
CATEGORIE_ESCLUSE = ("accessor", "sleeve", "binder", "playmat", "deck box", "coin",
                     "dice", "album", "portfolio", "storage", "figure")
COLONNE_PREZZO = ["trend", "low", "avg", "avg1", "avg7", "avg30"]


def _scarica(url, tentativi=3):
    for i in range(tentativi):
        try:
            r = requests.get(url, timeout=180)
            if r.status_code in (403, 404):
                return None
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if i == tentativi - 1:
                raise
            time.sleep(15 * (i + 1))
    return None


def trova_id_giochi(giochi, max_id=30):
    """Scorre i giochi di Cardmarket e riconosce quelli configurati dai nomi delle carte."""
    migliori = {k: (0, None) for k in giochi}
    for gid in range(1, max_id + 1):
        dati = _scarica(f"{BASE}/productList/products_singles_{gid}.json")
        if not dati:
            continue
        testo = " ".join(p.get("name", "") for p in dati.get("products", [])).lower()
        for chiave, g in giochi.items():
            punti = sum(len(re.findall(r"\b" + re.escape(w.lower()) + r"\b", testo)) for w in g["riconosci"])
            if punti > migliori[chiave][0]:
                migliori[chiave] = (punti, gid)
    return {k: v[1] for k, v in migliori.items() if v[0] >= 20}


def catalogo(id_gioco, escludi_nomi):
    righe = []
    for tipo_file, tipo in (("singles", "singola"), ("nonsingles", "sigillato")):
        dati = _scarica(f"{BASE}/productList/products_{tipo_file}_{id_gioco}.json")
        if not dati:
            continue
        for p in dati.get("products", []):
            righe.append({
                "id": int(p["idProduct"]),
                "nome": (p.get("name") or "").strip(),
                "categoria": p.get("categoryName") or "",
                "tipo": tipo,
                "aggiunto": (p.get("dateAdded") or "")[:10],
            })
    if not righe:
        raise RuntimeError(f"Catalogo vuoto per il gioco {id_gioco}")
    df = pd.DataFrame(righe).drop_duplicates("id").set_index("id")
    cat = df["categoria"].str.lower()
    df.loc[(df["tipo"] == "sigillato") & cat.str.contains("|".join(CATEGORIE_ESCLUSE)), "tipo"] = "altro"
    if escludi_nomi:
        parole = [w.lower() for w in escludi_nomi]
        altra_lingua = df["nome"].str.lower().apply(lambda n: any(w in n for w in parole))
        df.loc[altra_lingua & (df["tipo"] == "sigillato"), "tipo"] = "altra_lingua"
    return df


def price_guide(id_gioco):
    dati = _scarica(f"{BASE}/priceGuide/price_guide_{id_gioco}.json")
    if not dati:
        raise RuntimeError(f"Price guide non disponibile per il gioco {id_gioco}")
    data = (dati.get("createdAt") or "")[:10]
    df = pd.DataFrame(dati.get("priceGuides", []))
    df = df.rename(columns={"idProduct": "id"})
    for c in COLONNE_PREZZO:
        if c not in df.columns:
            df[c] = np.nan
    df = df[["id"] + COLONNE_PREZZO].copy()
    df["id"] = df["id"].astype("int64")
    df = df.set_index("id").apply(pd.to_numeric, errors="coerce").astype("float32")
    df.loc[~(df["trend"] > 0), "trend"] = np.nan
    return data, df


def link_ricerca(slug, nome, lingua_sito="it"):
    return f"https://www.cardmarket.com/{lingua_sito}/{slug}/Products/Search?searchString={quote(nome)}"
