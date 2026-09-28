"""Create a reviewable Cardmarket→TCGdex crosswalk without guessing variants."""

from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
import re
import unicodedata

from src.catalogo_pokemon import DEST, write_gzip

SET_MIN_SHARED = 20
SET_MIN_COVERAGE = .60
SET_MIN_MARGIN = 1.25


def normalized(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join(re.findall(r"[a-z0-9]+", "".join(ch for ch in value if not unicodedata.combining(ch))))


def card_name(value):
    # Cardmarket often appends attack names in square brackets.
    return normalized(re.split(r"\s*\[", value or "", maxsplit=1)[0])


def read_rows(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def optional_index(path, key):
    return {row[key]: row for row in read_rows(path)} if path.is_file() else {}


def build(dest=DEST):
    cards = list(read_rows(dest / "carte.jsonl.gz"))
    products = list(read_rows(dest / "cardmarket_singole.jsonl.gz"))
    manual_cards = json.loads((dest / "carte_verificate.json").read_text(encoding="utf-8"))
    manual_sets = json.loads((dest / "espansioni_verificate.json").read_text(encoding="utf-8"))
    source_cards = optional_index(dest / "carte_fonte_tcgdex.jsonl.gz", "cardmarket_id")
    source_sets = optional_index(dest / "espansioni_fonte_tcgdex.jsonl.gz", "cardmarket_expansion_id")
    by_id = {c["tcgdex_id"]: c for c in cards}
    label_by_set = {c["set_id"]: c.get("set_name_en") for c in cards if c.get("set_name_en")}
    groups = defaultdict(list)
    names_by_set = defaultdict(lambda: defaultdict(list))
    for card in cards:
        for lang in ("en", "it"):
            key = normalized(card.get(f"name_{lang}"))
            if key:
                names_by_set[card["set_id"]][key].append(card)
    set_names = {sid: set(names) for sid, names in names_by_set.items()}
    inverse = defaultdict(set)
    for sid, names in set_names.items():
        for key in names:
            inverse[key].add(sid)
    for product in products:
        groups[product.get("cardmarket_expansion_id")].append(product)

    crosswalk = []
    chosen_sets = {}
    for gid, rows in sorted(groups.items(), key=lambda pair: str(pair[0])):
        names = {card_name(row["name"]) for row in rows}
        names.discard("")
        scores = Counter()
        for name in sorted(names):
            candidate_sets = inverse.get(name, ())
            weight = 1 / math.sqrt(len(candidate_sets) or 1)
            for sid in sorted(candidate_sets):
                scores[sid] += weight
        top = scores.most_common(2)
        manual_sid = manual_sets.get(str(gid))
        source_sids = source_sets.get(gid, {}).get("tcgdex_set_ids", [])
        source_sid = source_sids[0] if len(source_sids) == 1 and source_sids[0] in set_names else None
        if not top and not manual_sid and not source_sid:
            crosswalk.append({"cardmarket_expansion_id": gid, "status": "unmatched", "products": len(rows)})
            continue
        sid, score = top[0] if top else (manual_sid or source_sid, 0)
        if manual_sid or source_sid:
            sid = manual_sid or source_sid
            if sid not in set_names:
                raise ValueError(f"Set verificato assente da TCGdex: {gid} → {sid}")
        shared = len(names & set_names[sid])
        coverage = shared / max(1, min(len(names), len(set_names[sid])))
        margin = score / (top[1][1] if len(top) > 1 else .001)
        if manual_sid:
            status = "verified"
        elif source_sid:
            status = "source_id_linked"
        elif shared >= SET_MIN_SHARED and coverage >= SET_MIN_COVERAGE and margin >= SET_MIN_MARGIN:
            status = "high_confidence_inferred"
        else:
            status = "review"
        if status != "review":
            chosen_sets[gid] = (sid, status)
        crosswalk.append({"cardmarket_expansion_id": gid, "tcgdex_set_id": sid,
                          "set_name_en": label_by_set.get(sid),
                          "status": status, "products": len(rows), "shared_names": shared,
                          "coverage": round(coverage, 3), "margin": round(margin, 3),
                          "alternative_set_id": top[1][0] if len(top) > 1 else None})

    matches = []
    counts = Counter()
    for p in products:
        pid = p["cardmarket_id"]
        gid = p.get("cardmarket_expansion_id")
        key = card_name(p["name"])
        base = {"cardmarket_id": pid, "cardmarket_expansion_id": gid}
        if str(pid) in manual_cards:
            cid = manual_cards[str(pid)]
            if cid not in by_id:
                raise ValueError(f"Carta verificata assente da TCGdex: {pid} → {cid}")
            base.update(tcgdex_id=cid, status="verified")
        elif pid in source_cards:
            ids = source_cards[pid]["tcgdex_ids"]
            valid = [cid for cid in ids if cid in by_id]
            exact = [cid for cid in valid if key in
                     {normalized(by_id[cid].get("name_en")), normalized(by_id[cid].get("name_it"))}]
            sid = chosen_sets.get(gid, (None, None))[0]
            aligned = [cid for cid in exact if by_id[cid]["set_id"] == sid]
            if len(aligned) == 1:
                base.update(tcgdex_id=aligned[0], status="source_id_name_set")
            elif len(exact) == 1 and sid is None:
                base.update(tcgdex_id=exact[0], status="source_id_name_only")
            else:
                base.update(status="source_conflict", candidates=valid[:4])
        elif gid in chosen_sets:
            sid, set_status = chosen_sets[gid]
            candidates = {c["tcgdex_id"]: c for c in names_by_set[sid].get(key, ())}
            if len(candidates) == 1:
                base.update(tcgdex_id=next(iter(candidates)), status="high_confidence_inferred" if set_status != "verified" else "set_verified_name_unique")
            elif candidates:
                base.update(status="ambiguous", candidates=sorted(candidates)[:4])
            else:
                base.update(status="unmatched")
        else:
            base.update(status="review")
        counts[base["status"]] += 1
        matches.append(base)

    write_gzip(dest / "espansioni_candidate.jsonl.gz", crosswalk)
    write_gzip(dest / "carte_cardmarket_match.jsonl.gz", matches)
    manifest_path = dest / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["crosswalk"] = {"set_status": dict(Counter(r["status"] for r in crosswalk)),
                             "card_status": dict(counts), "method": "unique name inside conservatively matched expansion; inferred mappings are not manual verifications"}
    provenance = dest / "fonte_tcgdex.json"
    if provenance.is_file():
        manifest["crosswalk"]["source_revision"] = json.loads(provenance.read_text(encoding="utf-8"))["revision"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest["crosswalk"]


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
