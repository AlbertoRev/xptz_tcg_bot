"""Notizie e uscite in arrivo da più fonti RSS gratuite (nessuna AI).

Fonti: Google News in italiano e in inglese (compresi articoli del sito ufficiale Pokémon,
di Pokémon Millennium e di PokéBeach) e il feed diretto di PokéBeach.
Le date di uscita vengono estratte in automatico da titoli e sommari: vanno sempre
controllate sul link della fonte.
"""
import datetime as dt
import re
import time
from html import unescape
from urllib.parse import quote, urlparse

import feedparser

RICERCHE = {
    "pokemon": [("Pokémon GCC carte nuova espansione", "it"), ("Pokemon TCG new set", "en")],
}

RICERCHE_USCITE = [
    ("GCC Pokémon uscita espansione", "it"),
    ("Pokémon GCC data di uscita", "it"),
    ("Pokémon GCC prevendita", "it"),
    ("site:pokemon.com GCC Pokémon espansione", "it"),
    ("site:pokemonmillennium.net GCC", "it"),
    ("Pokemon TCG release date", "en"),
    ("Pokemon TCG upcoming set", "en"),
    ("site:pokebeach.com release", "en"),
]
FEED_DIRETTI = ["https://www.pokebeach.com/feed"]

MESI = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6, "luglio": 7,
    "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
    "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
_MESI_RE = "|".join(MESI)
DATA_GIORNO_MESE = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MESI_RE})(?:\s+(20\d\d))?\b", re.I)
DATA_MESE_GIORNO = re.compile(rf"\b({_MESI_RE})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?\b", re.I)


def _url(q, lingua, giorni):
    q = quote(f"{q} when:{giorni}d")
    if lingua == "it":
        return f"https://news.google.com/rss/search?q={q}&hl=it&gl=IT&ceid=IT:it"
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _pulisci(testo):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(testo or ""))).strip()


def _fonte(e):
    s = e.get("source")
    if s and s.get("title"):
        return s["title"]
    return urlparse(e.get("link", "")).netloc.replace("www.", "")


def _voci(url):
    try:
        return feedparser.parse(url).entries
    except Exception:
        return []


def notizie(gioco, max_per_gioco=8):
    visti, out = set(), []
    limite = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=8)
    for q, lingua in RICERCHE.get(gioco, []):
        for e in _voci(_url(q, lingua, 7)):
            titolo = _pulisci(e.get("title"))
            chiave = titolo.lower()[:80]
            if not titolo or chiave in visti:
                continue
            pub = e.get("published_parsed")
            if pub and dt.datetime.fromtimestamp(time.mktime(pub), dt.timezone.utc) < limite:
                continue
            visti.add(chiave)
            out.append({"titolo": titolo, "link": e.get("link", ""), "fonte": _fonte(e),
                        "data": time.strftime("%d/%m", pub) if pub else ""})
            if len(out) >= max_per_gioco:
                return out
    return out


def _date(testo, oggi, orizzonte):
    """Date nel testo comprese tra oggi e oggi + orizzonte giorni."""
    trovate = []
    for m in DATA_GIORNO_MESE.finditer(testo):
        trovate.append((int(m.group(1)), MESI[m.group(2).lower()], m.group(3)))
    for m in DATA_MESE_GIORNO.finditer(testo):
        trovate.append((int(m.group(2)), MESI[m.group(1).lower()], m.group(3)))
    out = []
    for giorno, mese, anno in trovate:
        anni = [int(anno)] if anno else [oggi.year, oggi.year + 1]
        for a in anni:
            try:
                d = dt.date(a, mese, giorno)
            except ValueError:
                continue
            if oggi <= d <= oggi + dt.timedelta(days=orizzonte):
                out.append(d)
                break
    return sorted(set(out))


VUOTE = {"pokemon", "pokémon", "gcc", "tcg", "the", "and", "for", "set", "box", "della", "delle", "degli",
         "nuova", "nuovo", "new", "card", "cards", "carte", "gioco", "game", "with", "from", "sono", "sarà",
         "espansione", "expansion", "release", "date", "uscita", "data", "booster", "elite", "trainer",
         "arriva", "arrivo", "releases", "coming", "prevendita", "annunciata", "announced"} | set(MESI)


def _parole(testo):
    return {w for w in re.findall(r"[a-zà-ù0-9]+", testo.lower()) if len(w) > 3 and w not in VUOTE}


def uscite(oggi, orizzonte=60, massimo=20):
    """Radar delle uscite: notizie recenti che citano una data nei prossimi 'orizzonte' giorni."""
    voci = []
    for q, lingua in RICERCHE_USCITE:
        voci += _voci(_url(q, lingua, 30))
    for url in FEED_DIRETTI:
        voci += _voci(url)

    visti, out = set(), []
    for e in voci:
        titolo = _pulisci(e.get("title"))
        if not titolo:
            continue
        testo = f"{titolo} {_pulisci(e.get('summary'))}"
        if not re.search(r"pok[eé]mon|gcc|tcg|espansion|booster|elite trainer", testo, re.I):
            continue
        date = _date(testo, oggi, orizzonte)
        if not date:
            continue
        chiave = (date[0], re.sub(r"\W+", "", titolo.lower())[:40])
        if chiave in visti:
            continue
        visti.add(chiave)
        out.append({"data": date[0].isoformat(), "titolo": titolo, "fonte": _fonte(e), "link": e.get("link", "")})

    # la stessa uscita citata da più fonti = più interesse
    for u in out:
        parole = _parole(u["titolo"])
        u["citazioni"] = sum(1 for v in out if v["data"] == u["data"] and len(parole & _parole(v["titolo"])) >= 2)
    out.sort(key=lambda u: (u["data"], -u["citazioni"]))
    return out[:massimo]


def collega_previsioni(radar, previsioni):
    """Se un'uscita del radar corrisponde a un prodotto su Cardmarket, ne riporta lo stato di mercato."""
    for u in radar:
        pu = _parole(u["titolo"])
        migliore, punti = None, 1
        for p in previsioni:
            comuni = len(pu & _parole(p["nome"]))
            if comuni > punti:
                migliore, punti = p, comuni
        u["mercato"] = migliore["stato"] if migliore else "nessun dato"
        u["prodotto_cardmarket"] = migliore["nome"] if migliore else None
    return radar
