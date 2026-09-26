"""Notizie della settimana da Google News (feed RSS gratuiti, nessuna AI)."""
import datetime as dt
import time
from urllib.parse import quote

import feedparser

RICERCHE = {
    "pokemon": [("Pokémon TCG carte nuova espansione", "it"), ("Pokemon TCG new set release", "en")],
    "onepiece": [("One Piece Card Game new set", "en"), ("One Piece Card Game reprint", "en")],
    "dragonball": [("Dragon Ball Super Card Game Fusion World", "en")],
    "naruto": [("Naruto Kayou carte", "it"), ("Naruto Kayou cards", "en")],
}


def _url(q, lingua):
    if lingua == "it":
        return f"https://news.google.com/rss/search?q={quote(q)}+when:7d&hl=it&gl=IT&ceid=IT:it"
    return f"https://news.google.com/rss/search?q={quote(q)}+when:7d&hl=en-US&gl=US&ceid=US:en"


def notizie(gioco, max_per_gioco=6):
    visti, out = set(), []
    limite = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=8)
    for q, lingua in RICERCHE.get(gioco, []):
        try:
            feed = feedparser.parse(_url(q, lingua))
        except Exception:
            continue
        for e in feed.entries:
            titolo = (e.get("title") or "").strip()
            chiave = titolo.lower()[:80]
            if not titolo or chiave in visti:
                continue
            pub = e.get("published_parsed")
            if pub and dt.datetime.fromtimestamp(time.mktime(pub), dt.timezone.utc) < limite:
                continue
            visti.add(chiave)
            out.append({"titolo": titolo, "link": e.get("link", ""),
                        "data": time.strftime("%d/%m", pub) if pub else ""})
            if len(out) >= max_per_gioco:
                return out
    return out
