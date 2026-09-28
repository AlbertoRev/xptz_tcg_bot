"""Resolve editorial card photographs from the local metadata archive."""

from collections import defaultdict
from difflib import SequenceMatcher
import gzip
from io import BytesIO
import json
from pathlib import Path
import re
import unicodedata

import requests
from PIL import Image

from src import rivista

CATALOG = Path(__file__).resolve().parents[1] / "data/catalogo_pokemon/carte.jsonl.gz"
MATCHES = CATALOG.with_name("carte_cardmarket_match.jsonl.gz")


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def query_parts(value):
    raw = str(value or "")
    number = re.search(r"\b(\d{1,3})\s*/\s*\d{1,3}\b", raw)
    name = re.split(r"\s*[\[(]", raw, maxsplit=1)[0]
    return normalize(name), (str(int(number.group(1))) if number else None)


class CardIndex:
    def __init__(self, path=CATALOG):
        self.rows = []
        self.by_id = {}
        self.market_links = {}
        self.by_name = defaultdict(list)
        if not path.is_file():
            return
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if not (row.get("image_it") or row.get("image_en")):
                    continue
                self.rows.append(row)
                self.by_id[row["tcgdex_id"]] = row
                for lang in ("en", "it"):
                    name = normalize(row.get(f"name_{lang}"))
                    if name:
                        self.by_name[name].append(row)
        match_path = path.with_name(MATCHES.name)
        if match_path.is_file():
            with gzip.open(match_path, "rt", encoding="utf-8") as stream:
                for line in stream:
                    match = json.loads(line)
                    self.market_links[match["cardmarket_id"]] = match

    def candidates(self, name, set_name=None, cardmarket_id=None):
        key, number = query_parts(name)
        link = self.market_links.get(cardmarket_id) or {}
        ids = [link["tcgdex_id"]] if link.get("tcgdex_id") else link.get("candidates", [])
        selected = [self.by_id[cid] for cid in ids if cid in self.by_id]
        found = self.by_name.get(key, [])
        if not found:
            # Only candidates with the same first word are eligible. A broad
            # arbitrary nearest string can otherwise display another Pokémon.
            first = key.split(" ")[0] if key else ""
            keys = [k for k in self.by_name if k.startswith(first + " ") or k == first]
            keys.sort(key=lambda k: SequenceMatcher(None, key, k).ratio(), reverse=True)
            found = [r for k in keys[:6] for r in self.by_name[k]]
        if not found:
            return selected
        unique = {r["tcgdex_id"]: r for r in found}
        hint = normalize(set_name)
        def score(row):
            names = [normalize(row.get(f"name_{l}")) for l in ("en", "it")]
            similarity = max(SequenceMatcher(None, key, n).ratio() for n in names)
            number_match = number is not None and number == str(row.get("local_id"))
            set_match = hint and hint in (normalize(row.get("set_name_en")), normalize(row.get("set_name_it")))
            return (bool(set_match), bool(number_match), similarity, bool(row.get("image_it")), row["tcgdex_id"])
        ranked = sorted(unique.values(), key=score, reverse=True)[:8]
        return selected + [r for r in ranked if r["tcgdex_id"] not in ids]


def _save_image(url, target):
    if not url.startswith("https://assets.tcgdex.net/"):
        return False
    try:
        with requests.get(url + "/low.webp", stream=True, timeout=12) as response:
            response.raise_for_status()
            if not response.url.startswith("https://assets.tcgdex.net/"):
                return False
            payload = response.content
            if len(payload) > 3_000_000:
                return False
        with Image.open(BytesIO(payload)) as image:
            image.verify()
        with Image.open(BytesIO(payload)) as image:
            if image.width < 100 or image.height < 100:
                return False
            image.convert("RGB").save(target, "JPEG", quality=88)
        return True
    except (requests.RequestException, OSError, ValueError):
        return False


def prepara(rows):
    """Populate chosen market movements, marking every inferred print uncertain."""
    index = CardIndex()
    if not index.rows:
        print("[card_images] archivio carte assente o senza immagini")
        return
    rivista.ASSET_DIR.mkdir(parents=True, exist_ok=True)
    loaded = 0
    for item in rows:
        if not item.get("nome"):
            continue
        link = index.market_links.get(item.get("id")) or {}
        for card in index.candidates(item["nome"], item.get("set_name"), item.get("id")):
            for lang in ("it", "en"):
                base = card.get(f"image_{lang}")
                if not base:
                    continue
                asset_name = "carta_tcgdex_" + re.sub(r"[^a-zA-Z0-9_-]", "_", card["tcgdex_id"]) + "_" + lang + ".jpg"
                path = rivista.ASSET_DIR / asset_name
                if path.is_file() or _save_image(base, path):
                    item["immagine_carta"] = asset_name
                    item["immagine_carta_riferimento"] = {
                        "nome": card.get(f"name_{lang}") or card.get("name_en"),
                        "set": card.get(f"set_name_{lang}") or card.get("set_name_en") or card["set_id"],
                        "numero": card.get("local_id"), "tcgdex_id": card["tcgdex_id"],
                        "incerto": not (link.get("status") == "verified" and link.get("tcgdex_id") == card["tcgdex_id"]),
                        "match_status": link.get("status", "name_only"),
                    }
                    loaded += 1
                    break
            if item.get("immagine_carta"):
                break
    print(f"[card_images] {loaded}/{len(rows)} immagini editoriali caricate")
