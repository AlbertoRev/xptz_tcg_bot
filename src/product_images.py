"""Optional, exact-ID product photographs for the collection focus.

The price-guide catalogue has no image field. A verified product response may
carry one; absent that response, the layout uses a textual product card.
"""
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

from src import rivista

MAX_BYTES = 5_000_000
ALLOWED_HOST = "product-images.s3.cardmarket.com"


def prepara(prodotti):
    """Attach local image names only to products with an exact-ID image URL."""
    for prodotto in prodotti[:4]:
        url = prodotto.get("immagine_prodotto_url")
        if not isinstance(url, str):
            continue
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
            continue
        try:
            response = requests.get(url, timeout=12, stream=True)
            response.raise_for_status()
            if response.url.split("/", 3)[2].lower() != ALLOWED_HOST:
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
        except (OSError, ValueError, requests.RequestException):
            continue
