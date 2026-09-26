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
    "onepiece": {
        "nome": "One Piece",
        "livello": "principale",
        "lingua": "english",
        "slug_cardmarket": "OnePiece",
        "riconosci": ["Luffy", "Roronoa Zoro", "Nami"],
        "escludi_nomi": ["japanese", "chinese", "korean", "(french"],
    },
}

# Notizie di altri giochi senza prezzi (vuoto = nessuno)
NOTIZIE_EXTRA = {}

# Periodi delle variazioni (giorni)
PERIODI = [7, 30, 90, 180]

# Soglie minime di prezzo (euro) per entrare nel report, così una carta
# da 0,20 € che passa a 0,40 € non finisce tra i "rialzi del 100%".
MIN_PREZZO_REPORT = {"singola": 5, "sigillato": 5}

# Soglie minime per gli alert giornalieri
MIN_PREZZO_ALERT = {"singola": 20, "sigillato": 5}
SOGLIA_ALERT_MOVIMENTO = 0.20      # +/-20% in 7 giorni
SOGLIA_CONFERMA = 0.15             # il giorno prima doveva essere almeno +/-15%
SOGLIA_OCCASIONE = 0.70            # prezzo minimo <= 70% del prezzo di tendenza
SOGLIA_OCCASIONE_MIN = 0.40        # sotto il 40% è quasi sempre un'altra lingua o un prodotto rovinato
MIN_PREZZO_OCCASIONE = {"singola": 5, "sigillato": 5}
# Per le singole il prezzo minimo è spesso di copie rovinate o in altre lingue:
# le occasioni sulle singole sono attive solo con la verifica per lingua (CMAPI_KEY).
OCCASIONI_SINGOLE_SENZA_VERIFICA = False
MAX_OCCASIONI_AL_GIORNO = 15        # di cui occasioni sul sigillato
# True = un prodotto ancora in allerta viene rimandato ogni giorno, con la data della prima segnalazione.
# False = ogni prodotto viene segnalato una volta sola finché resta in allerta.
RIPETI_ALERT_ATTIVI = True
MAX_ALERT_AL_GIORNO = 15            # totale alert al giorno (i movimenti di prezzo hanno la precedenza)

# Quanti prodotti per classifica (rialzi e ribassi)
RIGHE_PER_CLASSIFICA = 10

# Variazioni oltre questo valore sono trattate come probabili errori di dato
VARIAZIONE_MAX_CREDIBILE = 3.0     # +300%

# Prodotti sotto questi prezzi non vengono salvati nello storico (risparmio spazio)
MIN_PREZZO_STORICO = {"singola": 2, "sigillato": 5}

# Verifica prezzi per lingua (livello 2) tramite cardmarketapi.com.
# Funziona solo se imposti il segreto CMAPI_KEY su GitHub (servizio a pagamento).
MAX_VERIFICHE_AL_GIORNO = 8
