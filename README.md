# Redazione CF/IBAN da PDF — Web App

App Streamlit per omissare automaticamente Codice Fiscale e IBAN da un PDF.
Motore già testato: stessa logica dello script Colab, con la differenza che
qui lavora su file caricati via browser invece che su file locali.

## Deploy gratuito su Streamlit Community Cloud

1. Crea un repository GitHub (anche privato) e caricaci questi 2 file:
   - `app.py`
   - `requirements.txt`

2. Vai su https://share.streamlit.io e accedi con il tuo account GitHub.

3. Clicca "New app", seleziona il repository, il branch e il file `app.py`.

4. Clicca "Deploy". Dopo qualche minuto avrai un URL pubblico tipo:
   `https://tuonome-redazione.streamlit.app`

5. Ogni volta che aggiorni `app.py` su GitHub, l'app si ridistribuisce
   automaticamente.

## Esecuzione in locale (per provarla prima di pubblicarla)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Si apre su http://localhost:8501

## Note

- L'app non salva permanentemente i file caricati: vengono processati
  in memoria e scartati alla fine della sessione. Restano comunque
  temporaneamente sul server che ospita l'app durante l'elaborazione —
  vedi l'avviso privacy mostrato nell'interfaccia.
- Per documenti scansionati (immagine, non testo selezionabile) serve
  prima un passaggio di OCR: questa versione lavora solo su PDF con
  testo estraibile.
- Se vuoi restringere l'accesso (es. solo al tuo ente), Streamlit
  Community Cloud supporta anche apps private con autenticazione via
  Google/e-mail nelle impostazioni dell'app.
