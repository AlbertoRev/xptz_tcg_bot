"""Check crosswalk integrity before an issue uses the catalogue."""
from collections import Counter
import json

from src.archivio_match import card_name, normalized, read_rows
from src.catalogo_pokemon import DEST


def check(dest=DEST):
    cards = {r["tcgdex_id"]: r for r in read_rows(dest / "carte.jsonl.gz")}
    singles = {r["cardmarket_id"]: r for r in read_rows(dest / "cardmarket_singole.jsonl.gz")}
    links = list(read_rows(dest / "carte_cardmarket_match.jsonl.gz"))
    groups = list(read_rows(dest / "espansioni_candidate.jsonl.gz"))
    set_groups = {r["cardmarket_expansion_id"]: r["tcgdex_set_id"] for r in groups
                  if r["status"] in ("verified", "source_id_linked", "high_confidence_inferred")}
    assert len(links) == len(singles) == len({r["cardmarket_id"] for r in links})
    assert len(groups) == len({r["cardmarket_expansion_id"] for r in groups})
    for link in links:
        original = singles[link["cardmarket_id"]]
        assert link["cardmarket_expansion_id"] == original.get("cardmarket_expansion_id")
        if "tcgdex_id" in link:
            assert link["tcgdex_id"] in cards
            if link["status"] == "source_id_name_set":
                card = cards[link["tcgdex_id"]]
                assert card_name(original["name"]) in {
                    normalized(card.get("name_en")), normalized(card.get("name_it"))}
                assert original["cardmarket_expansion_id"] in set_groups
                assert card["set_id"] == set_groups[original["cardmarket_expansion_id"]]
        for candidate in link.get("candidates", []):
            assert candidate in cards
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    assert sum(manifest["crosswalk"]["card_status"].values()) == len(links)
    return {"singles": len(links), "sets": len(groups),
            "card_status": dict(Counter(r["status"] for r in links))}


if __name__ == "__main__":
    print(json.dumps(check(), ensure_ascii=False, indent=2))
