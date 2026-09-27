import os
import urllib.request

def scarica_immagini_pokemon():
    """Scarica automaticamente tutte le immagini necessarie per il PDF."""
    os.makedirs("assets", exist_ok=True)
    
    # Lista delle immagini da scaricare con relativi link
    immagini = {
        # Pokéball
        "assets/pokeball.png": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Pok%C3%A9ball-encoded.svg/300px-Pok%C3%A9ball-encoded.svg.png",
        "assets/megaball.png": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Great_Ball_Artwork.png/300px-Great_Ball_Artwork.png",
        "assets/ultraball.png": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Ultra_Ball_Artwork.png/300px-Ultra_Ball_Artwork.png",
        "assets/masterball.png": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Master_Ball_Artwork.png/300px-Master_Ball_Artwork.png",
        
        # Pokémon famosi
        "assets/pikachu.png": "https://upload.wikimedia.org/wikipedia/it/1/17/Pikachu.png",
        "assets/charizard.png": "https://upload.wikimedia.org/wikipedia/it/1/13/Charizard.png",
        "assets/blastoise.png": "https://upload.wikimedia.org/wikipedia/it/2/23/Blastoise.png",
        "assets/venusaur.png": "https://upload.wikimedia.org/wikipedia/it/a/a3/Venusaur.png",
        "assets/mewtwo.png": "https://upload.wikimedia.org/wikipedia/it/c/c8/Mewtwo.png",
        "assets/rayquaza.png": "https://upload.wikimedia.org/wikipedia/it/e/e5/Rayquaza.png",
           
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for percorso, url in immagini.items():
        if not os.path.exists(percorso):
            print(f"Scaricamento in corso: {percorso}...")
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req) as response, open(percorso, 'wb') as out_file:
                    out_file.write(response.read())
                print(f"Completato: {percorso}")
            except Exception as e:
                print(f"Errore download {percorso}: {e}")

if __name__ == "__main__":
    scarica_immagini_pokemon()
