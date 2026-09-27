# =====================================================================
#  CONFIGURAZIONE DEL BOT - puoi modificare solo i valori qui sotto
# =====================================================================

# Giochi monitorati.
#  - "livello": "principale" = analisi completa ogni settimana
#  - "lingua": lingua su cui investi (usata per le verifiche e i link)
#  - "escludi_nomi": prodotti sigillati con queste parole nel nome vengono esclusi
#  - "riconosci": parole usate per trovare in automatico il gioco su Cardmarket
GIOCHI = {
    "pokemon": {
        "nome": "Pokémon",
        "livello": "principale",
        "lingua": "italian",
        "slug_cardmarket": "Pokemon",
        "riconosci": ["Pikachu", "Charizard", "Mewtwo"],
        "escludi_nomi": ["japanese", "chinese", "korean", "thai", "indonesian"],
    },
}

# Notizie di altri giochi senza prezzi (vuoto = nessuno)
NOTIZIE_EXTRA = {}

# Periodi delle variazioni (giorni)
PERIODI = [7, 30, 90, 180]

# Soglie minime di prezzo (euro) per entrare nel report, così una carta
# da 0,20 € che passa a 0,40 € non finisce tra i "rialzi del 100%".
MIN_PREZZO_REPORT = {"singola": 4, "sigillato": 5}

# Soglie minime per gli alert giornalieri
MIN_PREZZO_ALERT = {"singola": 4, "sigillato": 5}
SOGLIA_ALERT_MOVIMENTO = 0.20      # +/-20% in 7 giorni
SOGLIA_CONFERMA = 0.15             # il giorno prima doveva essere almeno +/-15%
SOGLIA_OCCASIONE = 0.70            # prezzo minimo <= 70% del prezzo di tendenza
SOGLIA_OCCASIONE_MIN = 0.40        # sotto il 40% è quasi sempre un'altra lingua o un prodotto rovinato
MIN_PREZZO_OCCASIONE = {"singola": 20, "sigillato": 5}
# Per le singole il prezzo minimo è spesso di copie rovinate o in altre lingue:
# le occasioni sulle singole sono attive solo con la verifica per lingua (CMAPI_KEY).
OCCASIONI_SINGOLE_SENZA_VERIFICA = False
# True = un prodotto ancora in allerta viene rimandato ogni giorno, con la data della prima segnalazione.
# False = ogni prodotto viene segnalato una volta sola finché resta in allerta.
RIPETI_ALERT_ATTIVI = True
# Alert al giorno: due messaggi separati, uno per il sigillato e uno per le carte singole.
# Priorità sigillato: movimenti di prezzo, poi occasioni, poi prodotti da osservare.
# Priorità singole: movimenti di prezzo confermati, poi slancio delle vendite (stima).
MAX_ALERT_SIGILLATO = 12
MAX_ALERT_SINGOLE = 12
# Slancio singole: media vendite 7 giorni contro media 30 giorni, almeno +/-10%
SOGLIA_SLANCIO = 0.10
# True = se le occasioni vere non bastano a raggiungere il limite, il bot completa con
# prodotti "da osservare": prezzo minimo tra il 70% e l'85% della tendenza (segnale più debole).
RIEMPI_CON_DA_OSSERVARE = True
SOGLIA_DA_OSSERVARE = 0.85

# Previsioni nel report settimanale: prodotti sigillati aggiunti su Cardmarket negli ultimi
# 60 giorni (prevendite e uscite recenti), valutati come caldo / tiepido / freddo.
PREVISIONI_GIORNI = 60
PREVISIONI_MAX_RIGHE = 20
CALDO_VARIAZIONE = 0.10     # prezzo salito almeno del 10% dal primo rilevamento
CALDO_RAPPORTO = 0.85       # oppure in salita e con poche offerte sotto la tendenza
FREDDO_VARIAZIONE = -0.10   # prezzo sceso almeno del 10%
FREDDO_RAPPORTO = 0.70      # oppure molte offerte molto sotto la tendenza

# Quanti prodotti per classifica (rialzi e ribassi)
RIGHE_PER_CLASSIFICA = 5

# Variazioni oltre questo valore sono trattate come probabili errori di dato
VARIAZIONE_MAX_CREDIBILE = 3.0     # +300%

# Prodotti sotto questi prezzi non vengono salvati nello storico (risparmio spazio)
MIN_PREZZO_STORICO = {"singola": 2, "sigillato": 5}

# Verifica prezzi per lingua (livello 2) tramite cardmarketapi.com.
# Funziona solo se imposti il segreto CMAPI_KEY su GitHub (servizio a pagamento).
MAX_VERIFICHE_AL_GIORNO = 8
