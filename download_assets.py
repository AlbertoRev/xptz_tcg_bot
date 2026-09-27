"""Prepara il set grafico Pokémon della settimana.

Il bot scarica soltanto gli asset scelti per quel numero della rivista.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import random
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets"

POKEAPI_RAW = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites"
TRAINERCARDS_ITEMS_RAW = "https://raw.githubusercontent.com/jonbarrow/trainercards.studio/master/public/images/items"
TRAINER_ART_POOL = [
    ("may", "May Torchic Pokémon Center Trainer artwork.png"),
    ("brendan", "Ruby Sapphire Brendan.png"),
    ("steven", "Steven Stone M8 JN.png"),
]

WIKIDEX_API="https://www.wikidex.net/api.php"
BALL_ART={"poke-ball":"Poké Ball (Ilustración).png","ultra-ball":"Ultra Ball (Ilustración).png","timer-ball":"Turno Ball (Ilustración).png","nest-ball":"Nido Ball (Ilustración).png","quick-ball":"Veloz Ball (Ilustración).png","dusk-ball":"Ocaso Ball (Ilustración).png","heal-ball":"Sana Ball (Ilustración).png","luxury-ball":"Lujo Ball (Ilustración).png","great-ball":"Super Ball (Ilustración).png","net-ball":"Malla Ball (Ilustración).png"}
ITEM_ART={"bicycle":"Bici acrobática artwork.png","rare-candy":"Caramelo raro (Ilustración).png","exp-share":"Artwork de Repartir Experiencia.png","fresh-water":"Artwork agua fresca.png","old-rod":"Ilustración del tubo pokécubos.png","good-rod":"Kit de Pokécubos ROZA.png"}
TRAINER_WIKIDEX=[("may","Aura ROZA (Ilustración).png"),("brendan","Bruno ROZA (Ilustración).png"),("steven","Máximo (Architraje) Masters EX.png")]

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
POKEMON_IDS = tuple(range(252, 387))  # Hoenn: Treecko (252) → Deoxys (386)

# Pokémon Showdown espone una collezione di trainer sprites con nomi leggibili.
# La usiamo solo per la componente "allenatore", perché il repository sprite di PokéAPI
# espone Pokémon e item ma non una cartella trainer equivalente.
TRAINER_POOL = [
    "ash", "brock", "misty", "cynthia", "red", "blue", "may", "serena",
    "lillie", "leon", "marnie", "iono", "giacomo", "larry", "avery",
    "barry", "bianca",
]

THEMES = ["Tesori di Hoenn", "Rotte di Hoenn", "Mare di Hoenn", "Leggende di Hoenn"]
