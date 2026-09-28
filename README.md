# POKèPUTZU WEEKLY

Magazine PDF automatico sul Pokémon GCC. Il bot raccoglie ogni giorno il catalogo e i prezzi Cardmarket per costruire lo storico; la domenica alle 08:30 (Europe/Rome) genera il numero e lo invia su Telegram. Le anteprime del branch `pokeputzu_redesign` inviano un PDF di prova su Telegram senza incrementare il numero. Non sono previsti alert giornalieri.

## Flusso

| Workflow | Compito |
| --- | --- |
| `giornaliero.yml` | Salva i dati Pokémon per lo storico, senza inviare alert |
| `aggiorna_archivio.yml` | Il sabato aggiorna carte, prodotti e collegamenti TCGdex/Cardmarket |
| `settimanale.yml` | Produce il PDF domenicale e lo invia su Telegram |
| `prova_rivista.yml` | Prova il PDF sul branch di sviluppo, carica audit e anteprima su Telegram |

Il PDF ha sette pagine A4: copertina, mercato, novità, analisi, focus collezione, guida mercato e saluto. Il controllo automatico verifica sette pagine e annota se le immagini sono certe, inferite o illustrative. Il logo è in `brand/pokeputzu-weekly-logo.png`.

## Dati e limiti

- [Archivio e correzioni](ARCHIVIO.md): nomi e ID dei prodotti Cardmarket, schede TCGdex in inglese, italiano e giapponese, immagini disponibili e provenienza dei collegamenti.
- Il catalogo pubblico Cardmarket e la sua guida prezzi non certificano la lingua di ogni inserzione. **I prezzi aggregati nel PDF attuale includono più lingue.** L'obiettivo di pubblicare solo prezzi delle versioni italiane richiede offerte filtrate per lingua per tutte le schede mostrate; non presentiamo un prezzo aggregato come se fosse italiano.
- `CMAPI_KEY`, se configurata, consente la verifica opzionale di un piccolo numero di offerte tramite un servizio terzo. Il codice controlla che ID e lingua della risposta concordino. Il magazine nel suo insieme non è ancora alimentato esclusivamente da questa fonte.
- Le foto esatte delle confezioni sono poche. Una foto illustrativa o simile è dichiarata nel PDF e nell'audit; l'archivio dei nomi non prova l'esistenza di una foto corretta.

## Configurazione

I segreti GitHub Actions sono `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` e, facoltativamente, `GEMINI_API_KEY` e `CMAPI_KEY`. Non salvarli nel repository. `GEMINI_API_KEY` dirige l'art direction; senza chiave viene usato un piano locale deterministico. La configurazione editoriale è in `config.py`. Per controllare l'archivio: `python -m src.archivio_check`. Per la prova: `python main.py prova_rivista` (genera localmente senza inviare). Per la produzione: usare il workflow programmato, che registra il numero dopo l'invio riuscito.
