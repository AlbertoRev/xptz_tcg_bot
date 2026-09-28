"""Photographs of real products, matched to Cardmarket catalogue IDs.

Cardmarket's public price-guide catalogue contains names and IDs but no
photographs. An editorially checked source list supplies known sealed products;
an exact-ID response from the optional price verifier covers further items.
"""
from io import BytesIO
from urllib.parse import urlparse

import requests
from PIL import Image

from src import rivista

MAX_BYTES = 5_000_000

# Product title and package photograph were checked together on each source
# page. Keep the Cardmarket ID in the key so variants cannot share artwork.
# Add new entries after checking the physical package and its language/format.
CURATED = {
    357064: ("Celestial Storm Booster",
             "https://images.tcggo.com/tcggo/storage/21877/conversions/celestial-storm-booster-large.webp",
             "TCGGO"),
    664333: ("Pokémon GO Pin Collection—Bulbasaur",
             "https://insogames.com/cdn/shop/products/PIN-POGO-BULB_530x%402x.jpg?v=1664928562",
             "INSOGAMES"),
    468319: ("VMAX Rising Booster Box",
             "https://rogerz.dk/cdn/shop/files/vmaxrising_600x600.png?v=1690486597",
             "Rogerz"),
    698560: ("Ampharos ex Battle Deck",
             "https://pokestorelb.com/cdn/shop/files/P8887_699-85230_01.jpg?v=1757684914&width=1445",
             "Pokéstore LB"),
}
ALLOWED_HOSTS = {"product-images.s3.cardmarket.com", "images.tcggo.com",
                 "insogames.com", "rogerz.dk", "pokestorelb.com"}


def prepara(prodotti):
    """Attach images only when the exact product ID and title are known."""
    loaded = 0
    for prodotto in prodotti[:4]:
        entry = CURATED.get(prodotto.get("id"))
        if entry and prodotto.get("nome") == entry[0]:
            url, source = entry[1:]
        else:
            url, source = prodotto.get("immagine_prodotto_url"), "Cardmarket"
        if not isinstance(url, str):
            continue
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            continue
        try:
            with requests.get(url, timeout=15, stream=True) as response:
                response.raise_for_status()
                if urlparse(response.url).hostname not in ALLOWED_HOSTS:
                    continue
                data = bytearray()
                for chunk in response.iter_content(64 * 1024):
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        break
            if len(data) > MAX_BYTES:
                continue
            with Image.open(BytesIO(data)) as im:
                im.verify()
            with Image.open(BytesIO(data)) as im:
                if im.width < 100 or im.height < 100:
                    continue
                im = im.convert("RGB")
                im.thumbnail((900, 900))
                name = f"prodotto_cardmarket_{int(prodotto['id'])}.jpg"
                path = rivista.ASSET_DIR / name
                path.parent.mkdir(parents=True, exist_ok=True)
                im.save(path, "JPEG", quality=88)
                prodotto["immagine_prodotto"] = name
                prodotto["fonte_immagine"] = source
                loaded += 1
        except (OSError, ValueError, requests.RequestException) as exc:
            print(f"[product_images] immagine non disponibile per ID {prodotto.get('id')}: {type(exc).__name__}")
            continue
    print(f"[product_images] {loaded}/{min(4, len(prodotti))} immagini di prodotto caricate")
