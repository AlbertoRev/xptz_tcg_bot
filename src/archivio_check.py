"""Check crosswalk integrity before an issue uses the catalogue."""
from collections import Counter
import json

from src.archivio_match import read_rows
from src.catalogo_pokemon import DEST


def check(dest=DEST):
    cards = {r["tcgdex_id"]: r for r in read_rows(dest / "carte.jsonl.gz")}
    singles = {r["cardmarket_id"]: r for r in read_rows(dest / "cardmarket_singole.jsonl.gz")}
    links = list(read_rows(dest / "carte_cardmarket_match.jsonl.gz"))
    groups = list(read_rows(dest / "espansioni_candidate.jsonl.gz"))
    assert len(links) == len(singles) == len({r["cardmarket_id"] for r in links})
    assert len(groups) == len({r["cardmarket_expansion_id"] for r in groups})
    for link in links:
        original = singles[link["cardmarket_id"]]
        assert link["cardmarket_expansion_id"] == original.get("cardmarket_expansion_id")
        if "tcgdex_id" in link:
            assert link["tcgdex_id"] in cards
        for candidate in link.get("candidates", []):
            assert candidate in cards
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    assert sum(manifest["crosswalk"]["card_status"].values()) == len(links)
    return {"singles": len(links), "sets": len(groups),
            "card_status": dict(Counter(r["status"] for r in links))}


if __name__ == "__main__":
    print(json.dumps(check(), ensure_ascii=False, indent=2))
