"""Prepara il set grafico Pokémon della settimana.

Il bot scarica soltanto gli asset scelti per quel numero della rivista, così ogni
settimana la grafica cambia senza dover salvare le immagini nel repository.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import random
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets"

POKEAPI_RAW = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites"
SHOWDOWN_TRAINER_RAW = "https://play.pokemonshowdown.com/sprites/trainers"

# Poké Ball e varianti: tutte arrivano dagli sprite item di PokéAPI.
BALL_POOL = [
    "poke-ball", "great-ball", "ultra-ball", "master-ball", "premier-ball", "luxury-ball",
    "heal-ball", "dusk-ball", "quick-ball", "timer-ball", "net-ball", "nest-ball",
    "repeat-ball", "dive-ball", "dream-ball", "beast-ball",
]

# Oggetti riconoscibili del mondo Pokémon, tutti sotto sprites/items di PokéAPI.
ITEM_POOL = [
    "potion", "super-potion", "hyper-potion", "max-potion", "full-restore", "revive", "max-revive",
    "antidote", "paralyze-heal", "awakening", "burn-heal", "ice-heal", "full-heal",
    "escape-rope", "repel", "super-repel", "max-repel", "rare-candy", "nugget", "big-nugget",
    "pearl", "big-pearl", "star-piece", "stardust", "honey", "bicycle", "old-rod", "good-rod",
    "super-rod", "exp-share", "lucky-egg", "amulet-coin", "soothe-bell", "quick-claw", "leftovers",
    "focus-band", "focus-sash", "choice-band", "choice-scarf", "choice-specs", "muscle-band",
    "wise-glasses",
]

# La pagina di PokéAPI indica che la National Dex corrente contiene 1025 Pokémon.
POKEMON_IDS = tuple(range(1, 1026))

# Pokémon Showdown espone una collezione di trainer sprites con nomi leggibili.
# La usiamo solo per la componente "allenatore", perché il repository sprite di PokéAPI
# espone Pokémon e item ma non una cartella trainer equivalente.
TRAINER_POOL = [
    "ash", "brock", "misty", "cynthia", "red", "blue", "may", "serena",
    "lillie", "leon", "marnie", "iono", "giacomo", "larry", "avery",
    "barry", "bianca",
]

THEMES = [
    "Avventura di Kanto", "Ragazzi di Johto", "Tesori di Hoenn", "Sinnoh Expedition",
    "Unima in viaggio", "Kalos Style", "Alola al tramonto", "Galar League", "Tesori di Paldea",
    "Notte Misteriosa", "Palestra Elettrica", "Cascata Acquatica", "Sentiero Selvaggio",
    "Cima Ghiacciata", "Zona Vulcanica", "Foresta Incantata",
]


def _seed(numero: int, data: str) -> int:
    raw = f"il-collezionista|{data}|{numero}".encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:16], 16)


def _download(url: str, percorso: Path) -> bool:
    """Scarica un singolo PNG in modo atomico. Ritorna True se disponibile."""
    if percorso.exists() and percorso.stat().st_size > 100:
        return True

    temporaneo = percorso.with_suffix(percorso.suffix + ".part")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Il-Collezionista/2.0)"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response, open(temporaneo, "wb") as out_file:
            blob = response.read()
            if not blob:
                raise ValueError("file vuoto")
            out_file.write(blob)
        # Evita di salvare HTML/altro contenuto come se fosse un PNG.
        with Image.open(temporaneo) as img:
            img.verify()
        os.replace(temporaneo, percorso)
        print(f"Asset pronto: {percorso.name}")
        return True
    except Exception as exc:
        try:
            temporaneo.unlink(missing_ok=True)
        except OSError:
            pass
        print(f"Asset non disponibile ({url}): {exc}")
        return False


def _candidati_pokemon(rng: random.Random, quanti: int):
    ids = list(POKEMON_IDS)
    rng.shuffle(ids)
    # Di tanto in tanto pesca anche un shiny per rendere davvero variabile il kit.
    for poke_id in ids:
        shiny = rng.random() < 0.16
        variante = "shiny" if shiny else "normale"
        nome = f"pokemon_{poke_id}_{variante}.png"
        base = f"{POKEAPI_RAW}/pokemon/other/official-artwork"
        if shiny:
            url = f"{base}/shiny/{poke_id}.png"
        else:
            url = f"{base}/{poke_id}.png"
        yield nome, url
        quanti -= 1
        if quanti <= 0:
            break


def _candidati_item(rng: random.Random, piscina, prefisso: str):
    slugs = list(piscina)
    rng.shuffle(slugs)
    for slug in slugs:
        nome = f"{prefisso}_{slug}.png"
        url = f"{POKEAPI_RAW}/items/{slug}.png"
        yield nome, url, slug


def _candidati_trainer(rng: random.Random):
    nomi = list(TRAINER_POOL)
    rng.shuffle(nomi)
    for nome in nomi:
        yield f"trainer_{nome}.png", f"{SHOWDOWN_TRAINER_RAW}/{nome}.png", nome


def scarica_immagini_pokemon(numero: int = 1, data: str | None = None):
    """Costruisce e scarica il kit grafico della settimana.

    Il risultato viene passato a rivista.py: contiene i file effettivamente scaricati,
    il tema della settimana e l'ordine con cui usarli nel PDF.
    """
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    data = data or dt.date.today().isoformat()
    rng = random.Random(_seed(numero, data))

    manifest = {
        "numero": numero,
        "data": data,
        "tema": THEMES[rng.randrange(len(THEMES))],
        "pokemon": [],
        "pokeball": [],
        "oggetti": [],
        "allenatori": [],
    }

    # 6 Pokémon grandi: copertina, bordi, separatori e retro.
    for nome, url in _candidati_pokemon(rng, 10):
        percorso = ASSET_DIR / nome
        if _download(url, percorso):
            manifest["pokemon"].append(nome)
        if len(manifest["pokemon"]) >= 6:
            break

    # 4 Poké Ball diverse a settimana.
    for nome, url, slug in _candidati_item(rng, BALL_POOL, "ball"):
        percorso = ASSET_DIR / nome
        if _download(url, percorso):
            manifest["pokeball"].append(nome)
        if len(manifest["pokeball"]) >= 4:
            break

    # 6 strumenti diversi a settimana.
    for nome, url, slug in _candidati_item(rng, ITEM_POOL, "item"):
        percorso = ASSET_DIR / nome
        if _download(url, percorso):
            manifest["oggetti"].append(nome)
        if len(manifest["oggetti"]) >= 6:
            break

    # 3 trainer sprites: se un nome non è disponibile, si passa al successivo.
    for nome, url, trainer_nome in _candidati_trainer(rng):
        percorso = ASSET_DIR / nome
        if _download(url, percorso):
            manifest["allenatori"].append(nome)
        if len(manifest["allenatori"]) >= 3:
            break

    # Il manifest è utile per debuggare un run di GitHub Actions e resta in assets/,
    # già esclusa dal repository tramite .gitignore.
    try:
        (ASSET_DIR / "settimana.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        print(f"Impossibile salvare il manifest: {exc}")

    print(
        f"Kit Pokémon n.{numero}: {manifest['tema']} | "
        f"{len(manifest['pokemon'])} Pokémon, {len(manifest['pokeball'])} Ball, "
        f"{len(manifest['oggetti'])} oggetti, {len(manifest['allenatori'])} allenatori"
    )
    return manifest


if __name__ == "__main__":
    scarica_immagini_pokemon()
