# Bot TCG – report e alert su Telegram

Ogni giorno salva i prezzi di tutto il catalogo Cardmarket di Pokémon, One Piece e Dragon Ball e ti manda gli alert.
Ogni domenica ti manda il report completo in PDF. Costo: 0 €.

Tempo di installazione: circa 30 minuti. Non serve programmare, solo clic e copia-incolla.

---

## 1. Crea il bot Telegram (5 minuti)

1. Su Telegram cerca **@BotFather** e scrivigli `/newbot`.
2. Scegli un nome (es. "TCG Report") e un nome utente che finisca con `bot` (es. `federico_tcg_bot`).
3. BotFather ti risponde con il **token**, una stringa tipo `123456789:ABCdef...`. Copialo da parte.
4. Apri la chat con il tuo nuovo bot e premi **Avvia** (o scrivigli "ciao"). Senza questo passaggio il bot non può scriverti.
5. Ora ti serve il **chat id**, cioè il numero che identifica la tua chat. È il "numero di telefono" a cui il bot manderà i messaggi.
   - Su Telegram cerca **@userinfobot**, aprilo e premi **Avvia**.
   - Ti risponde con alcune righe: quella che inizia con **Id** contiene un numero, per esempio `Id: 123456789`.
   - Quel numero è il tuo chat id. Copialo da parte.

**Se @userinfobot non risponde**, c'è un metodo alternativo dal browser del telefono o del computer:

1. Prendi questo indirizzo: `https://api.telegram.org/botTOKEN/getUpdates`
2. Sostituisci la parola `TOKEN` con il token ricevuto da BotFather, attaccato alla parola `bot`, senza spazi.
   Esempio: se il token è `123456789:ABCdefGHI`, l'indirizzo diventa
   `https://api.telegram.org/bot123456789:ABCdefGHI/getUpdates`
3. Incolla l'indirizzo nella barra del browser e premi invio. Si apre una pagina di solo testo.
4. Cerca la scritta `"chat":{"id":` e il numero che la segue, per esempio `"chat":{"id":123456789`. Quel numero è il chat id.
5. Se la pagina mostra solo `{"ok":true,"result":[]}`, scrivi di nuovo "ciao" al tuo bot e ricarica la pagina.

## 2. Crea il repository su GitHub (10 minuti)

1. Crea un account gratuito su github.com, se non ce l'hai.
2. In alto a destra: **+** → **New repository**.
   - Nome: `tcg-bot`
   - Visibilità: **Public** (così i minuti di esecuzione sono illimitati e Claude può leggere il riepilogo; contiene solo prezzi pubblici, nessun dato personale)
   - Premi **Create repository**.
3. Nella pagina del repository premi **uploading an existing file**.
4. Estrai lo zip sul computer e trascina **tutti i file e le cartelle** (config.py, main.py, requirements.txt, README.md, le cartelle `src` e `data`; la cartella `workflow_da_copiare` non serve caricarla). Premi **Commit changes**.
5. La cartella `.github` spesso è nascosta e non si carica trascinando. Creala a mano:
   - **Add file** → **Create new file**
   - Nel nome scrivi esattamente `.github/workflows/giornaliero.yml`
   - Incolla il contenuto del file `workflow_da_copiare/giornaliero.yml` dello zip, poi **Commit changes**
   - Ripeti per `settimanale.yml` e `setup.yml`

## 3. Inserisci i segreti (3 minuti)

Nel repository: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

| Nome | Valore |
|---|---|
| `TELEGRAM_TOKEN` | il token del punto 1 |
| `TELEGRAM_CHAT_ID` | il chat id del punto 1 |

Poi: **Settings** → **Actions** → **General** → sezione *Workflow permissions* → scegli **Read and write permissions** → **Save**.

## 4. Primo avvio (5 minuti)

1. Apri la scheda **Actions**. Se compare un avviso, premi **I understand my workflows, go ahead and enable them**.
2. A sinistra scegli **Setup** → **Run workflow** → **Run workflow**.
3. Dopo 2-4 minuti ti arriva su Telegram un messaggio con i giochi trovati e qualche prodotto di esempio. Controlla che gli esempi siano del gioco giusto.
4. Poi avvia a mano **Giornaliero** e **Settimanale** una volta, allo stesso modo. Riceverai il primo report di prova.

Da quel momento è tutto automatico:
- **ogni giorno alle 06:00** salva i prezzi e manda gli alert, se ce ne sono;
- **ogni domenica alle 08:30** manda il report con il PDF.

Se qualcosa va storto ricevi un messaggio su Telegram con l'invito a controllare la scheda Actions.

## 5. Analisi settimanale di Claude (5 minuti)

Da una conversazione con Claude, chiedi di creare un'attività pianificata incollando questo testo
(sostituisci `NOMEUTENTE` con il tuo nome utente GitHub):

```
Crea un'attività pianificata ogni domenica alle 10:00 con queste istruzioni:

Leggi il file con i dati del mercato carte collezionabili:
https://raw.githubusercontent.com/NOMEUTENTE/tcg-bot/main/data/riepilogo/ultimo.json

Poi cerca sul web le notizie degli ultimi 7 giorni su: uscite e ristampe Pokémon GCC in italiano,
One Piece Card Game in inglese, Dragon Ball Super Card Game Fusion World, carte Naruto Kayou.

Scrivi in italiano, al massimo una pagina:
1. Sintesi in 5 righe.
2. Cosa faresti con 200 euro questa settimana (anche "niente"), con una motivazione breve.
3. Trend a breve e a lungo termine, ognuno con incertezza bassa, media o alta e il motivo.
4. Uscite e notizie rilevanti, ognuna con il link alla fonte.
5. Rischi: ristampe, cali, segnali di bolla.

Regole: usa solo i numeri presenti nel file, senza ricalcolarli né inventarne altri.
Se una data di uscita non ha una fonte ufficiale scrivi "non confermata".
Se "giorni_storico" è sotto 30, dillo all'inizio e sii prudente.
Non dare certezze: è un supporto alle decisioni, non una consulenza finanziaria.
```

## Cosa trovi nel report

- Nuovi prodotti sigillati aggiunti su Cardmarket (spesso sono le prossime uscite in prevendita).
- Rialzi e ribassi a 7, 30, 90 e 180 giorni per sigillato e singole, con incertezza.
- Occasioni sul sigillato: prezzo minimo molto sotto la tendenza, da verificare nella tua lingua.
- Notizie della settimana con link.
- Dragon Ball: prezzi la prima domenica del mese; Naruto: solo notizie.

## Limiti da conoscere

- I prezzi Cardmarket gratuiti sono **medie di tutte le lingue**. Per il prezzo delle copie in italiano apri il link del prodotto e filtra la lingua.
- Il sigillato non ha medie di vendita nei file Cardmarket: le sue variazioni partono dallo storico del bot (7 giorni dopo l'avvio per il 7g, 30 per il 30g, e così via).
- Per le singole ci sono stime dal primo giorno a 7 e 30 giorni, segnate con un asterisco.
- Le carte gradate non sono ancora incluse.

## Modifiche

Tutte le soglie (prezzi minimi, percentuali degli alert, numero di righe) sono in `config.py`, con una spiegazione accanto a ogni valore.
Per modificarlo: apri il file su GitHub → icona della matita → cambia il valore → **Commit changes**.

## Verifica automatica per lingua (opzionale, a pagamento)

Se un giorno vuoi il prezzo reale delle copie in italiano calcolato in automatico, crea una chiave su cardmarketapi.com
e aggiungila come segreto `CMAPI_KEY`. Il bot la usa da solo, al massimo 8 verifiche al giorno.
Senza chiave tutto funziona lo stesso, con la verifica manuale tramite i link.

## Immagini decorative della rivista

La rivista prepara automaticamente un **kit grafico diverso ogni settimana** nella cartella `assets/` prima di creare il PDF. Il kit contiene Pokémon, Poké Ball, strumenti e sprite di allenatori; non devi caricare immagini a mano su GitHub e la cartella resta esclusa dal repository.

Pokémon, Poké Ball e strumenti vengono scelti dagli sprite pubblici di PokéAPI. Per la categoria allenatori viene usato il repository di sprite di Pokémon Showdown, perché il repository sprite di PokéAPI non espone una collezione trainer equivalente. Il PDF continua a essere generato anche se una singola immagine non è disponibile.
