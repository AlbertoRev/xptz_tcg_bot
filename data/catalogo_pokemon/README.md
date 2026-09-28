# Archivio Pokémon TCG

Questo archivio distingue tre elenchi, senza attribuire a una carta TCGdex un ID Cardmarket per semplice somiglianza del nome:

| File | Identificatore | Contenuto |
| --- | --- | --- |
| `carte.jsonl.gz` | `tcgdex_id` | ID e nome EN/IT del set, numero locale, nomi EN/IT e URL di base delle immagini disponibili |
| `cardmarket_singole.jsonl.gz` | `cardmarket_id` | Nomi, categorie e ID espansione delle singole nel catalogo ufficiale Cardmarket |
| `cardmarket_altri.jsonl.gz` | `cardmarket_id` | Prodotti non singoli Cardmarket, inclusi sigillati e accessori |
| `foto_prodotti.json` | `cardmarket_id` | Foto delle confezioni controllate manualmente con fonte e nome esatto |
| `manifest.json` | — | Data, fonti, conteggi e limiti dei dati |

I file sono JSON Lines compressi con gzip: ogni riga decompressa è un oggetto JSON. Per le carte, un URL `image_it` o `image_en` è **un riferimento**, non la conferma che l'immagine sia scaricabile. Per l'immagine WebP ad alta risoluzione si aggiunge `/high.webp` all'URL di base; il programma editoriale deve verificare la risposta prima di usarla. Il file Cardmarket non contiene le fotografie delle confezioni: `image_status: da_verificare` indica che serve una fonte fotografica abbinata all'esatto prodotto e formato.

Il PDF sceglie una scansione per nome e, quando presenti, numero e set; indica sempre il set della scansione perché il catalogo gratuito Cardmarket non fornisce una corrispondenza verificata fra gli ID Cardmarket e TCGdex. Per le confezioni usa prima la foto associata all'ID preciso, poi la foto più simile fra quelle disponibili in `foto_prodotti.json`, accompagnata dalla dicitura **foto simile** e dal nome della confezione mostrata. Quando un'immagine remota non è raggiungibile, usa un'illustrazione tematica dichiarata come tale: nessun riquadro numerato vuoto.

Per aggiornare i file: `python -m src.catalogo_pokemon`, poi `python -m src.archivio_fonte_tcgdex /percorso/al/repository/tcgdex` e `python -m src.archivio_match`. La prova della rivista su `pokeputzu_redesign` aggiorna le liste API e conserva l'archivio come artefatto GitHub Actions. Le immagini non sono salvate nel repository. Gli ID di origine TCGdex sono controllati con nome e set prima dell'uso.

Fonti: [TCGdex REST API](https://tcgdex.dev/rest/cards), [TCGdex assets](https://tcgdex.dev/assets), [Cardmarket Product Catalog](https://www.cardmarket.com/en/Magic/Data). Pokécardex può servire per controlli manuali, ma non è una sorgente automatica dell'archivio.
