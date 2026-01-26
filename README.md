# EGI-STAT - Dashboard di Produttività per Sviluppatori

EGI-STAT è un'applicazione web full-stack progettata per analizzare l'attività dei repository GitHub e trasformarla in metriche di produttività significative. Fornisce una visione chiara del lavoro svolto, classificando i commit e calcolando indici di performance.

![Screenshot del Dashboard](https://i.imgur.com/example.png) <!-- Immagine dimostrativa, da sostituire con uno screenshot reale -->

## Architettura

Il progetto è diviso in due componenti principali:

1.  **Backend (Python & Flask)**: Un'applicazione che si occupa di:
    - Recuperare i dati dei commit da GitHub.
    - Analizzare e classificare ogni commit tramite un sistema di tag personalizzato (`FEAT`, `FIX`, `REFACTOR`, etc.).
    - Calcolare metriche avanzate come l'**Indice di Produttività** e il **Carico Cognitivo**.
    - Salvare i dati aggregati (giornalieri e settimanali) in un database PostgreSQL.
    - Esporre i dati tramite un'API REST.

2.  **Frontend (React & Vite)**: Una single-page application che:
    - Interroga le API del backend per ottenere le statistiche.
    - Visualizza i dati tramite grafici e tabelle interattive, permettendo di filtrare per periodi di tempo.

---

## Componenti Chiave

### Backend

- **API (`api.py`)**: Endpoint Flask che serve i dati statistici aggregati.
- **Motore di Analisi (`core/`)**:
  - `egi_productivity_v7.py`: Il cuore del sistema, orchestra l'analisi.
  - `github_client.py`: Client per l'API di GitHub con un sistema di cache.
  - `tag_system_v2.py`: Definisce le categorie dei commit e i loro pesi.
  - `auto_categorizer.py`: Classifica automaticamente i commit senza tag.
- **Ingestion Dati (`ingest_to_remotedb.py`)**: Script per popolare il database con i dati più recenti da GitHub. Viene eseguito periodicamente tramite `daily_ingest.sh`.
- **Database (`init_remote_db.py`)**: Script per inizializzare lo schema e le tabelle nel database PostgreSQL.

### Frontend

- **App Principale (`src/App.jsx`)**: Componente root che gestisce il layout e il recupero dei dati.
- **Componenti UI (`src/components/`)**:
  - `AdminChart.jsx`: Grafico principale per visualizzare l'andamento della produttività.
  - `DailyStats.jsx`: Componente per mostrare le statistiche dettagliate di un singolo giorno.
- **Configurazione (`vite.config.js`)**: Imposta il server di sviluppo e il proxy per le richieste API al backend.

---

## Setup e Avvio

### Prerequisiti

- Python 3.8+ e pip
- Node.js 18+ e npm
- Un database PostgreSQL in esecuzione
- Un token di accesso personale di GitHub

### 1. Configurazione Backend

1.  **Naviga nella cartella del backend:**

    ```bash
    cd backend
    ```

2.  **Crea e attiva un ambiente virtuale:**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Installa le dipendenze Python:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configura le variabili d'ambiente:**
    Crea un file `.env` nella cartella `backend` e compilalo con le tue credenziali, seguendo l'esempio di `.env.example` (se presente) o usando il seguente template:

    ```env
    # Credenziali Database
    DB_HOST=localhost
    DB_PORT=5432
    DB_DATABASE=nome_db
    DB_USERNAME=utente_db
    DB_PASSWORD=password_db
    DB_SCHEMA=stat

    # Token API GitHub
    GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
    ```

5.  **Inizializza il database:**
    Esegui lo script per creare le tabelle necessarie.
    ```bash
    python init_remote_db.py
    ```

### 2. Configurazione Frontend

1.  **Naviga nella cartella del frontend:**

    ```bash
    cd ../frontend
    ```

2.  **Installa le dipendenze Node.js:**
    ```bash
    npm install
    ```

### 3. Avvio dell'Applicazione

Per far funzionare l'applicazione, entrambi i server (backend e frontend) devono essere in esecuzione contemporaneamente.

1.  **Avvia il server Backend (in un terminale):**

    ```bash
    cd backend
    source .venv/bin/activate
    python api.py
    ```

    Il server sarà in ascolto su `http://127.0.0.1:5000`.

2.  **Avvia il server Frontend (in un altro terminale):**
    ```bash
    cd frontend
    npm run dev
    ```
    L'applicazione sarà accessibile su `http://localhost:5173` (o un'altra porta indicata da Vite).

### 4. Popolamento dei Dati

Per visualizzare le statistiche, è necessario eseguire lo script di "ingestion" per recuperare i dati da GitHub e popolarli nel database.

```bash
cd backend
source .venv/bin/activate
python ingest_to_remotedb.py --days 30 # Analizza gli ultimi 30 giorni
```

Questo comando può essere schedulato (ad esempio con `cron` e lo script `daily_ingest.sh`) per mantenere i dati aggiornati automaticamente.

---

## Comandi Utili

Di seguito una lista di comandi utili per interagire con il sistema di analisi.

### Popolare il Database

Per analizzare i commit e salvare le statistiche nel database, usa lo script `ingest_to_remotedb.py`.

- **Analizzare gli ultimi N giorni:**

  ```bash
  python ingest_to_remotedb.py --days <numero_giorni>
  ```

  Esempio per gli ultimi 7 giorni:

  ```bash
  python ingest_to_remotedb.py --days 7
  ```

- **Analizzare un repository specifico:**
  Puoi limitare l'analisi a un singolo repository tra quelli configurati.
  ```bash
  python ingest_to_remotedb.py --days 30 --repo "AutobookNft/EGI-STAT"
  ```

### Eseguire Report Completi (Output su Terminale o Excel)

Lo script `egi_productivity_v7.py` genera un report dettagliato direttamente nel terminale o, se specificato, in un file Excel. Questo script **non** salva i dati nel database, ma è utile per analisi al volo.

- **Report degli ultimi N giorni sul terminale:**

  ```bash
  python core/egi_productivity_v7.py --days <numero_giorni>
  ```

  Esempio:

  ```bash
  python core/egi_productivity_v7.py --days 15
  ```

- **Esportare il report in formato Excel:**
  Aggiungi il flag `--excel` per creare un file `EGI_Productivity_Report.xlsx`.

  ```bash
  python core/egi_productivity_v7.py --days 30 --excel
  ```

- **Analizzare un solo repository:**
  ```bash
  python core/egi_productivity_v7.py --days 30 --repo "AutobookNft/EGI-STAT"
  ```

**Nota:** Tutti i comandi devono essere eseguiti dalla cartella `backend` con l'ambiente virtuale attivato.
