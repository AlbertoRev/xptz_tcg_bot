"""Invio su Telegram. Token e chat id arrivano dai segreti di GitHub."""
import os

import requests

LIMITE = 3900


def _api(metodo):
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Manca il segreto TELEGRAM_TOKEN")
    return f"https://api.telegram.org/bot{token}/{metodo}"


def _chat():
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not chat:
        raise RuntimeError("Manca il segreto TELEGRAM_CHAT_ID")
    return chat


def messaggio(testo):
    """Invia testo in formato HTML, spezzandolo se supera il limite di Telegram."""
    blocchi, corrente = [], ""
    for riga in testo.split("\n"):
        if len(corrente) + len(riga) + 1 > LIMITE:
            blocchi.append(corrente)
            corrente = ""
        corrente += riga + "\n"
    if corrente.strip():
        blocchi.append(corrente)
    for b in blocchi:
        r = requests.post(_api("sendMessage"), timeout=60, data={
            "chat_id": _chat(), "text": b, "parse_mode": "HTML", "disable_web_page_preview": "true"})
        r.raise_for_status()


def documento(percorso, didascalia=""):
    with open(percorso, "rb") as f:
        r = requests.post(_api("sendDocument"), timeout=120,
                          data={"chat_id": _chat(), "caption": didascalia[:1000]},
                          files={"document": f})
    r.raise_for_status()
