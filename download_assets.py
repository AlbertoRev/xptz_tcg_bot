"
WIKIDEX_API="https://www.wikidex.net/api.php"
BALL_ART={"poke-ball":"Poké Ball (Ilustración).png","ultra-ball":"Ultra Ball (Ilustración).png","timer-ball":"Turno Ball (Ilustración).png","nest-ball":"Nido Ball (Ilustración).png","quick-ball":"Veloz Ball (Ilustración).png","dusk-ball":"Ocaso Ball (Ilustración).png","heal-ball":"Sana Ball (Ilustración).png","luxury-ball":"Lujo Ball (Ilustración).png","great-ball":"Super Ball (Ilustración).png","net-ball":"Malla Ball (Ilustración).png"}
ITEM_ART={"bicycle":"Bici acrobática artwork.png","rare-candy":"Caramelo raro (Ilustración).png","exp-share":"Artwork de Repartir Experiencia.png","fresh-water":"Artwork agua fresca.png","old-rod":"Ilustración del tubo pokécubos.png","good-rod":"Kit de Pokécubos ROZA.png"}
TRAINER_WIKIDEX=[("may","Aura ROZA (Ilustración).png"),("brendan","Bruno ROZA (Ilustración).png"),("steven","Máximo (Architraje) Masters EX.png")]
""Prepara il set grafico Pokémon della settimana.

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


def _download_wikidex(titolo: str, percorso: Path) -> bool:
    try:
        import urllib.parse
        api=WIKIDEX_API+"?"+urllib.parse.urlencode({"action":"query","format":"json","prop":"imageinfo","iiprop":"url","titles":"Archivo:"+titolo})
        req=urllib.request.Request(api,headers={"User-Agent":"Mozilla/5.0 POKEPUTZU-WEEKLY/1.0"})
        with urllib.request.urlopen(req,timeout=30) as r: data=json.loads(r.read().decode("utf-8"))
        page=next(iter(data["query"]["pages"].values())); url=page["imageinfo"][0]["url"]
        return _download(url,percorso)
    except Exception as exc:
        print(f"Artwork WikiDex non disponibile ({titolo}): {exc}"); return False

def _download_mediawiki(titolo: str, percorso: Path) -> bool:
    """Risoluzione via API MediaWiki: evita redirect HTML e recupera il PNG originale."""
    try:
        import urllib.parse
        api="https://archives.bulbagarden.net/w/api.php?"+urllib.parse.urlencode({
            "action":"query","format":"json","prop":"imageinfo","iiprop":"url","titles":"File:"+titolo
        })
        req=urllib.request.Request(api,headers={"User-Agent":"Mozilla/5.0 POKEPUTZU-WEEKLY/1.0"})
        with urllib.request.urlopen(req,timeout=30) as r:
            data=json.loads(r.read().decode("utf-8"))
        page=next(iter(data["query"]["pages"].values()))
        url=page["imageinfo"][0]["url"]
        return _download(url,percorso)
    except Exception as exc:
        print(f"Artwork trainer non disponibile ({titolo}): {exc}")
        return False


def _polish_asset(percorso: Path, canvas=512):
    """Porta gli asset piccoli a una resa morbida da illustrazione, senza pixel visibili."""
    try:
        with Image.open(percorso).convert("RGBA") as im:
            bbox=im.getbbox()
            if bbox: im=im.crop(bbox)
            im=im.resize((canvas-80,canvas-80),Image.Resampling.LANCZOS).filter(ImageFilter.SMOOTH_MORE)
            im=im.filter(ImageFilter.UnsharpMask(radius=1.2,percent=115,threshold=3))
            out=Image.new("RGBA",(canvas,canvas),(0,0,0,0)); out.alpha_composite(im,((canvas-im.width)//2,(canvas-im.height)//2))
            out.save(percorso)
    except Exception as exc:
        print(f"Impossibile rifinire {percorso.name}: {exc}")

def _trainer_fallback(percorso: Path, variante=0):
    """Illustrazione originale cel-shaded ad alta risoluzione, usata se il server artwork rifiuta il download."""
    w,h=640,900; im=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA")
    palettes=[((42,92,78,255),(224,91,73,255)),((50,91,126,255),(235,180,75,255)),((88,70,112,255),(79,151,128,255))]
    coat,accent=palettes[variante%len(palettes)]
    # gambe, torso, braccia: forme morbide e contorno scuro
    outline=(38,45,48,255); skin=(230,184,151,255)
    d.rounded_rectangle((245,520,310,825),28,fill=coat,outline=outline,width=8); d.rounded_rectangle((330,520,395,825),28,fill=coat,outline=outline,width=8)
    d.rounded_rectangle((190,285,450,590),70,fill=coat,outline=outline,width=10)
    d.polygon([(205,350),(115,570),(165,600),(255,420)],fill=skin,outline=outline); d.polygon([(435,350),(525,570),(475,600),(385,420)],fill=skin,outline=outline)
    d.ellipse((220,90,420,290),fill=skin,outline=outline,width=10)
    # capelli / cappello / giacca
    d.pieslice((205,55,435,275),180,360,fill=outline)
    d.rounded_rectangle((210,330,430,405),30,fill=accent)
    d.ellipse((260,170,280,190),fill=outline); d.ellipse((360,170,380,190),fill=outline)
    d.arc((285,185,355,235),0,180,fill=(120,72,62,255),width=5)
    # scarpe e Poké Ball alla cintura
    d.rounded_rectangle((225,790,315,855),25,fill=(245,245,238,255),outline=outline,width=8); d.rounded_rectangle((325,790,415,855),25,fill=(245,245,238,255),outline=outline,width=8)
    cx,cy=320,500; d.ellipse((cx-28,cy-28,cx+28,cy+28),fill=(235,75,70,255),outline=outline,width=6); d.rectangle((cx-28,cy-4,cx+28,cy+4),fill=outline); d.ellipse((cx-8,cy-8,cx+8,cy+8),fill=(245,245,238,255),outline=outline,width=4)
    im=im.filter(ImageFilter.GaussianBlur(.35)); im.save(percorso)

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
    mapping=BALL_ART if prefisso=="ball" else ITEM_ART
    slugs=list(mapping); rng.shuffle(slugs)
    for slug in slugs:
        yield f"{prefisso}_{slug}.png", "wikidex:"+mapping[slug], slug

def _candidati_trainer(rng: random.Random):
    candidati=list(TRAINER_WIKIDEX); rng.shuffle(candidati)
    for nome,titolo in candidati:
        yield f"trainer_{nome}.png", "wikidex:"+titolo, nome

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

    # 7 Pokémon grandi: uno diverso per ciascuna pagina della rivista.
    for nome, url in _candidati_pokemon(rng, 10):
        percorso = ASSET_DIR / nome
        if _download(url, percorso):
            manifest["pokemon"].append(nome)
        if len(manifest["pokemon"]) >= 7:
            break

    # 4 Poké Ball illustrate ad alta risoluzione.
    for nome,url,slug in _candidati_item(rng,BALL_POOL,"ball"):
        percorso=ASSET_DIR/nome
        ok=_download_wikidex(url[8:],percorso) if url.startswith("wikidex:") else _download(url,percorso)
        if ok:
            _polish_asset(percorso); manifest["pokeball"].append(nome)
        if len(manifest["pokeball"])>=4: break

    # Strumenti con artwork illustrato.
    for nome,url,slug in _candidati_item(rng,ITEM_POOL,"item"):
        percorso=ASSET_DIR/nome
        ok=_download_wikidex(url[8:],percorso) if url.startswith("wikidex:") else _download(url,percorso)
        if ok:
            _polish_asset(percorso); manifest["oggetti"].append(nome)
        if len(manifest["oggetti"])>=6: break

    # Allenatori Hoenn: artwork ad alta risoluzione, fallback cel-shaded solo se la fonte è indisponibile.
    for nome,url,trainer_nome in _candidati_trainer(rng):
        percorso=ASSET_DIR/nome
        ok=_download_wikidex(url[8:],percorso) if url.startswith("wikidex:") else _download_mediawiki(url,percorso)
        if not ok: _trainer_fallback(percorso,len(manifest["allenatori"]))
        if percorso.exists(): manifest["allenatori"].append(nome)
        if len(manifest["allenatori"])>=3: break

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
