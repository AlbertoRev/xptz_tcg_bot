"""Livello 2 (opzionale): prezzo reale delle copie nella lingua scelta.

Attivo solo se esiste il segreto CMAPI_KEY (servizio cardmarketapi.com, a pagamento
dopo la prova gratuita). Senza chiave il report mostra i link per la verifica manuale.
"""
import datetime as dt
import os

import requests

import config as C
from src import storage


def attivo():
    return bool(os.environ.get("CMAPI_KEY", "").strip())


def verifica(prodotti, lingua):
    """Aggiunge a ogni prodotto il prezzo minimo e la disponibilità nella lingua scelta."""
    if not attivo() or not prodotti:
        return prodotti
    stato = storage.leggi_json("verifiche.json", {"giorno": "", "usate": 0})
    oggi = dt.date.today().isoformat()
    if stato["giorno"] != oggi:
        stato = {"giorno": oggi, "usate": 0}
    for p in prodotti:
        if stato["usate"] >= C.MAX_VERIFICHE_AL_GIORNO:
            break
        try:
            r = requests.get(f"https://cardmarketapi.com/api/v1/card/{p['id']}",
                             params={"language": lingua, "condition": "nm"},
                             headers={"X-API-Key": os.environ["CMAPI_KEY"]}, timeout=60)
            stato["usate"] += 1
            if r.status_code == 429:
                break
            r.raise_for_status()
            dettaglio = r.json()
            prezzi = dettaglio.get("prices", {})
            p["verifica_lingua"] = {"lingua": lingua, "da": prezzi.get("from"),
                                    "media5": prezzi.get("avg5"), "disponibili": prezzi.get("available")}
            # The response is keyed by Cardmarket's product ID. Never infer an
            # image from a Pokémon or expansion name: sealed variants differ.
            if str(dettaglio.get("id")) == str(p["id"]):
                p["immagine_prodotto_url"] = dettaglio.get("image_url")
        except (requests.RequestException, ValueError):
            continue
    storage.scrivi_json("verifiche.json", stato)
    return prodotti
