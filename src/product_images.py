"""Photographs of real products, matched to Cardmarket catalogue IDs.

Cardmarket's public price-guide catalogue contains names and IDs but no
photographs. An editorially checked source list supplies known sealed products;
an exact-ID response from the optional price verifier covers further items.
"""
from io import BytesIO
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
from urllib.parse import urlparse

import requests
from PIL import Image

from src import rivista

MAX_BYTES = 5_000_000

# Product title and package photograph were checked together on each source
# page. Keep the Cardmarket ID in the key so variants cannot share artwork.
# Add new entries after checking the physical package and its language/format.
PHOTO_FILE = Path(__file__).resolve().parents[1] / "data/catalogo_pokemon/foto_prodotti.json"


def curated():
    data = json.loads(PHOTO_FILE.read_text(encoding="utf-8"))
    return {int(cid): (entry["name"], entry["image_url"], entry["source"])
            for cid, entry in data.items()}
ALLOWED_HOSTS = {"product-images.s3.cardmarket.com", "images.tcggo.com",
                 "insogames.com", "rogerz.dk", "pokestorelb.com"}


def _download(url, name):
    if not isinstance(url, str):
        return None
    path = rivista.ASSET_DIR / name
    if path.is_file():
        return name
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        return None
    try:
        with requests.get(url, timeout=15, stream=True) as response:
            response.raise_for_status()
            if urlparse(response.url).hostname not in ALLOWED_HOSTS:
                return None
            data = bytearray()
            for chunk in response.iter_content(64 * 1024):
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    return None
        with Image.open(BytesIO(data)) as im:
            im.verify()
        with Image.open(BytesIO(data)) as im:
            if im.width < 100 or im.height < 100:
                return None
            im = im.convert("RGB")
            im.thumbnail((900, 900))
            path.parent.mkdir(parents=True, exist_ok=True)
            im.save(path, "JPEG", quality=88)
        return name
    except (OSError, ValueError, requests.RequestException):
        return None


def _similarity(name, candidate):
    def words(value):
        return re.findall(r"[a-z0-9]+", value.casefold())
    a, b = words(name), words(candidate)
    shared = len(set(a) & set(b)) / max(len(set(a) | set(b)), 1)
    # Keep booster, box, deck and collection formats in the comparison.
    return .7 * SequenceMatcher(None, " ".join(a), " ".join(b)).ratio() + .3 * shared


def prepara(prodotti):
    """Use exact-ID photos first, then label the closest available photo."""
    loaded = 0
    cache = {}
    known = curated()
    for prodotto in prodotti[:4]:
        entry = known.get(prodotto.get("id"))
        exact = entry if entry and prodotto.get("nome") == entry[0] else None
        photo = None
        if exact:
            photo = _download(exact[1], f"prodotto_cardmarket_{int(prodotto['id'])}.jpg")
            source = exact[2]
        else:
            photo = _download(prodotto.get("immagine_prodotto_url"),
                              f"prodotto_cardmarket_{int(prodotto['id'])}.jpg")
            source = "Cardmarket"
        if photo:
            prodotto["immagine_prodotto"] = photo
            prodotto["fonte_immagine"] = source
            prodotto["immagine_approssimata"] = False
            loaded += 1
            continue
        for cid, candidate in known.items():
            if cid not in cache:
                cache[cid] = _download(candidate[1], f"prodotto_cardmarket_{cid}.jpg")
        ranked = sorted(((_similarity(prodotto.get("nome", ""), c[0]), cid, c)
                         for cid, c in known.items() if cache[cid]), reverse=True)
        if not ranked:
            print(f"[product_images] nessuna fotografia disponibile per ID {prodotto.get('id')}")
            continue
        _, cid, closest = ranked[0]
        prodotto["immagine_prodotto"] = cache[cid]
        prodotto["fonte_immagine"] = closest[2]
        prodotto["immagine_approssimata"] = True
        prodotto["immagine_riferimento"] = closest[0]
        print(f"[product_images] ID {prodotto.get('id')}: foto simile {cid} ({closest[0]})")
        loaded += 1
    print(f"[product_images] {loaded}/{min(4, len(prodotti))} immagini di prodotto caricate")
