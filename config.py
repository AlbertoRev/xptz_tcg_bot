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

# Periodi delle variazioni (giorni)
PERIODI = [7, 30, 90, 180]

# Soglie minime di prezzo (euro) per entrare nel report, così una carta
# da 0,20 € che passa a 0,40 € non finisce tra i "rialzi del 100%".
MIN_PREZZO_REPORT = {"singola": 4, "sigillato": 5}

# La rivista non invia alert giornalieri. Le occasioni sulle singole
# richiedono una verifica della lingua prima di entrare nel magazine.
SOGLIA_OCCASIONE = 0.70
SOGLIA_OCCASIONE_MIN = 0.40
MIN_PREZZO_OCCASIONE = {"singola": 20, "sigillato": 5}
OCCASIONI_SINGOLE_SENZA_VERIFICA = False

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
