# Archivio Pokémon per POKèPUTZU WEEKLY

La base conserva l'identità Cardmarket di ogni prodotto e le carte TCGdex con
set, numero e URL della scansione. `data/catalogo_pokemon/manifest.json`
riporta quantità, data e provenienza. L'archivio copre i cataloghi disponibili
al momento dell'ultimo aggiornamento, non le uscite future.

| File | Contenuto |
| --- | --- |
| `cardmarket_singole.jsonl.gz` | ID e nome dei prodotti carta Cardmarket |
| `cardmarket_altri.jsonl.gz` | ID e nome dei prodotti non singoli |
| `carte.jsonl.gz` | Carte TCGdex, nome, set, numero e URL scansione |
| `espansioni_candidate.jsonl.gz` | Possibili collegamenti tra espansioni |
| `carte_cardmarket_match.jsonl.gz` | Stato del collegamento per ogni carta Cardmarket |
| `carte_verificate.json`, `espansioni_verificate.json` | Correzioni umane persistenti, chiave ID Cardmarket, valore ID TCGdex |
| `foto_prodotti.json` | Foto di confezioni con ID Cardmarket controllato |

`verified` indica un abbinamento controllato e inserito nel registro manuale;
`high_confidence_inferred` indica nome univoco entro un'espansione collegata
con criteri conservativi; `ambiguous`, `review` e `unmatched` richiedono
revisione. Un nome uguale non identifica necessariamente la lingua, variante,
tiratura o la foto corretta. La scansione inferita è segnata con `≈` nel PDF.
Una foto simile è indicata come tale nella didascalia e nel file di audit.

Per correggere definitivamente un abbinamento, inserire un ID Cardmarket e
un ID TCGdex nel relativo JSON di verifica, controllando set, numero, lingua
e variante sulla scheda originale. Dopo la modifica, eseguire:

```sh
python -m src.archivio_match
python -m src.archivio_check
```

L'aggiornamento settimanale del sabato importa le nuove uscite e ricalcola
gli abbinamenti; la rivista usa l'ultima base conservata. Il workflow di prova
genera il PDF e un file `*_image_audit.json` con le corrispondenze effettive.
Nessuna importazione di massa da Pokécardex è prevista senza un canale
autorizzato per i suoi dati e immagini.
