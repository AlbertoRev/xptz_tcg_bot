# Archivio Pokémon TCG

Questo archivio distingue tre elenchi, senza attribuire a una carta TCGdex un ID Cardmarket per semplice somiglianza del nome:

| File | Identificatore | Contenuto |
| --- | --- | --- |
| `carte.jsonl.gz` | `tcgdex_id` | ID del set, numero locale, nomi EN/IT e URL di base delle immagini disponibili |
| `cardmarket_singole.jsonl.gz` | `cardmarket_id` | Nomi e categorie delle singole nel catalogo ufficiale Cardmarket |
| `cardmarket_altri.jsonl.gz` | `cardmarket_id` | Prodotti non singoli Cardmarket, inclusi sigillati e accessori |
| `manifest.json` | — | Data, fonti, conteggi e limiti dei dati |

I file sono JSON Lines compressi con gzip: ogni riga decompressa è un oggetto JSON. Per le carte, un URL `image_it` o `image_en` è **un riferimento**, non la conferma che l'immagine sia scaricabile. Per l'immagine WebP ad alta risoluzione si aggiunge `/high.webp` all'URL di base; il programma editoriale deve verificare la risposta prima di usarla. Il file Cardmarket non contiene le fotografie delle confezioni: `image_status: da_verificare` indica che serve una fonte fotografica abbinata all'esatto prodotto e formato.

Per aggiornare i file: `python -m src.catalogo_pokemon`. La prova della rivista su `pokeputzu_redesign` esegue questo aggiornamento, conserva i file nel branch e carica l'archivio come artifact GitHub Actions. Le immagini non sono salvate nel repository.

Fonti: [TCGdex REST API](https://tcgdex.dev/rest/cards), [TCGdex assets](https://tcgdex.dev/assets), [Cardmarket Product Catalog](https://www.cardmarket.com/en/Magic/Data). Pokécardex può servire per controlli manuali, ma non è una sorgente automatica dell'archivio.
