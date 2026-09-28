"""Extract Cardmarket IDs published by TCGdex, preserving source provenance.

The upstream database records IDs inside card variants. These IDs are useful
evidence, but they are not proof of a particular printing or language.
"""
from collections import defaultdict
import argparse
import json
from pathlib import Path
import re
import subprocess

from src.catalogo_pokemon import DEST, write_gzip

SET_ID = re.compile(r'\bid\s*:\s*["\']([^"\']+)')
THIRD_PARTY = re.compile(r'thirdParty\s*:\s*\{[^{}]*?cardmarket\s*:\s*(\d+)', re.S)


def extract(source, dest=DEST):
    source = Path(source)
    if not (source / 'data').is_dir():
        raise ValueError('Manca la directory data del repository TCGdex')
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    cards = defaultdict(set)
    sets = defaultdict(set)
    for section in ('data', 'data-asia'):
        base = source / section
        if not base.exists():
            continue
        set_dirs = {}
        for path in base.rglob('*.ts'):
            if not path.with_suffix('').is_dir():
                continue
            content = path.read_text(encoding='utf-8', errors='replace')
            match = SET_ID.search(content)
            if not match:
                continue
            sid = match.group(1)
            set_dirs[path.with_suffix('')] = sid
            for market_id in set(map(int, THIRD_PARTY.findall(content))):
                sets[market_id].add(sid)
        for path in base.rglob('*.ts'):
            sid = set_dirs.get(path.parent)
            if not sid:
                continue
            cid = f'{sid}-{path.stem}'
            content = path.read_text(encoding='utf-8', errors='replace')
            for market_id in set(map(int, THIRD_PARTY.findall(content))):
                cards[market_id].add(cid)
    if len(cards) < 10000 or len(sets) < 100:
        raise ValueError(f'Sorgente TCGdex incompleta: {len(cards)} prodotti, {len(sets)} set')
    dest.mkdir(parents=True, exist_ok=True)
    write_gzip(dest / 'carte_fonte_tcgdex.jsonl.gz',
               ({'cardmarket_id': pid, 'tcgdex_ids': sorted(ids)} for pid, ids in sorted(cards.items())))
    write_gzip(dest / 'espansioni_fonte_tcgdex.jsonl.gz',
               ({'cardmarket_expansion_id': gid, 'tcgdex_set_ids': sorted(ids)} for gid, ids in sorted(sets.items())))
    (dest / 'fonte_tcgdex.json').write_text(json.dumps({
        'repository': 'https://github.com/tcgdex/cards-database',
        'revision': revision, 'cardmarket_ids': len(cards), 'cardmarket_expansion_ids': len(sets),
        'note': 'ID di origine TCGdex, soggetti a errori e varianti: convalidare nome e set prima di usare una scansione.'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return len(cards), len(sets)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    print(extract(args.source))
