"""Archivio di metadati Pokémon TCG da TCGdex e Cardmarket.

Non accoppia automaticamente l'ID di una carta TCGdex a un prodotto
Cardmarket: un nome ripetuto può indicare stampe e lingue diverse.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "catalogo_pokemon"
SOURCES = {
    "carte_en": "https://api.tcgdex.net/v2/en/cards",
    "carte_it": "https://api.tcgdex.net/v2/it/cards",
    "carte_ja": "https://api.tcgdex.net/v2/ja/cards",
    "set_en": "https://api.tcgdex.net/v2/en/sets",
    "set_it": "https://api.tcgdex.net/v2/it/sets",
    "set_ja": "https://api.tcgdex.net/v2/ja/sets",
    "cardmarket_singole": "https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json",
    "cardmarket_altri": "https://downloads.s3.cardmarket.com/productCatalog/productList/products_nonsingles_6.json",
}


def fetch_json(url: str):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "POKEPUTZU-WEEKLY/catalogue/1.0"}), timeout=240) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, ValueError):
            if attempt == 2:
                raise
            time.sleep(8 * (attempt + 1))


def card_rows(en, it, sets_en=(), sets_it=(), ja=(), sets_ja=()):
    """Merge by exact TCGdex ID, retaining cards unique to either language."""
    index = {}
    for lang, cards in (("en", en), ("it", it), ("ja", ja)):
        if not isinstance(cards, list):
            raise ValueError(f"TCGdex {lang}: expected card list")
        for card in cards:
            cid = card.get("id")
            if not isinstance(cid, str) or not card.get("name"):
                continue
            row = index.setdefault(cid, {"tcgdex_id": cid, "set_id": cid.rsplit("-", 1)[0],
                                         "local_id": str(card.get("localId", ""))})
            row[f"name_{lang}"] = card["name"]
            image = card.get("image")
            if isinstance(image, str) and image.startswith("https://assets.tcgdex.net/"):
                row[f"image_{lang}"] = image  # base URL; append /high.webp on demand
    for lang, sets in (("en", sets_en), ("it", sets_it), ("ja", sets_ja)):
        if not isinstance(sets, (list, tuple)):
            raise ValueError(f"TCGdex {lang}: expected set list")
        names = {s["id"]: s["name"] for s in sets if s.get("id") and s.get("name")}
        for row in index.values():
            if row["set_id"] in names:
                row[f"set_name_{lang}"] = names[row["set_id"]]
    return sorted(index.values(), key=lambda r: r["tcgdex_id"])


def market_rows(payload, kind):
    products = payload.get("products") if isinstance(payload, dict) else None
    if not isinstance(products, list):
        raise ValueError(f"Cardmarket {kind}: expected products list")
    rows = {}
    for product in products:
        pid = product.get("idProduct")
        name = product.get("name")
        if pid is None or not isinstance(name, str) or not name.strip():
            continue
        rows[int(pid)] = {"cardmarket_id": int(pid), "name": name.strip(),
                          "category": product.get("categoryName") or "",
                          "added": (product.get("dateAdded") or "")[:10],
                          "catalog_group": kind,
                          "image_status": "da_verificare"}
        if product.get("idExpansion") not in (None, ""):
            try:
                rows[int(pid)]["cardmarket_expansion_id"] = int(product["idExpansion"])
            except (ValueError, TypeError):
                pass
    return sorted(rows.values(), key=lambda r: r["cardmarket_id"])


def write_gzip(path, rows):
    # Stable gzip metadata makes unchanged catalogues easy to compare in git.
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as zipped:
            for row in rows:
                zipped.write((json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
    temporary.replace(path)


def build(dest=DEST):
    raw = {key: fetch_json(url) for key, url in SOURCES.items()}
    cards = card_rows(raw["carte_en"], raw["carte_it"], raw["set_en"], raw["set_it"],
                      raw["carte_ja"], raw["set_ja"])
    singles = market_rows(raw["cardmarket_singole"], "singles")
    others = market_rows(raw["cardmarket_altri"], "nonsingles")
    curated_file = dest / "foto_prodotti.json"
    if curated_file.is_file():
        curated = json.loads(curated_file.read_text(encoding="utf-8"))
        for row in others:
            image = curated.get(str(row["cardmarket_id"]))
            if image and image["name"] == row["name"]:
                row.update(image_status="verified_title_and_id", image_url=image["image_url"],
                           image_source=image["source"])
    # Guard against a transient empty response overwriting a usable archive.
    if len(cards) < 1000 or len(singles) < 1000 or len(others) < 100:
        raise ValueError(f"Catalogo sospettosamente incompleto: {len(cards)} / {len(singles)} / {len(others)}")
    dest.mkdir(parents=True, exist_ok=True)
    write_gzip(dest / "carte.jsonl.gz", cards)
    write_gzip(dest / "cardmarket_singole.jsonl.gz", singles)
    write_gzip(dest / "cardmarket_altri.jsonl.gz", others)
    summary = {
        "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": SOURCES,
        "counts": {"tcgdex_cards": len(cards), "tcgdex_name_en": sum("name_en" in c for c in cards),
                   "tcgdex_name_it": sum("name_it" in c for c in cards),
                   "tcgdex_name_ja": sum("name_ja" in c for c in cards),
                   "tcgdex_image_en": sum("image_en" in c for c in cards),
                   "tcgdex_image_it": sum("image_it" in c for c in cards),
                   "tcgdex_image_ja": sum("image_ja" in c for c in cards),
                   "tcgdex_set_name_en": sum("set_name_en" in c for c in cards),
                   "tcgdex_set_name_it": sum("set_name_it" in c for c in cards),
                   "tcgdex_set_name_ja": sum("set_name_ja" in c for c in cards),
                   "cardmarket_singles": len(singles), "cardmarket_nonsingles": len(others)},
        "notes": ["TCGdex e Cardmarket non sono collegati automaticamente per nome.",
                  "Le immagini delle carte sono URL di base; la disponibilità del file non è verificata per ogni carta.",
                  "Cardmarket nonsingles include anche accessori; non equivale a soli prodotti sigillati.",
                  "I nomi del catalogo non provano lingua, stato di uscita o corrispondenza della confezione."],
    }
    summary["counts"]["product_photos_curated"] = sum(r["image_status"] == "verified_title_and_id" for r in others)
    (dest / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEST)
    args = parser.parse_args()
    print(json.dumps(build(args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
