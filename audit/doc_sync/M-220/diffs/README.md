diff --git a/README.md b/README.md
index 45e9dd8..d680544 100644
--- a/README.md
+++ b/README.md
@@ -13,6 +13,7 @@ Il progetto è diviso in due componenti principali:
     - Analizzare e classificare ogni commit tramite un sistema di tag personalizzato (`FEAT`, `FIX`, `REFACTOR`, etc.).
     - Calcolare metriche avanzate come l'**Indice di Produttività** e il **Carico Cognitivo**.
     - Salvare i dati aggregati (giornalieri e settimanali) in un database PostgreSQL.
+    - Aggregare le **missioni Oracode** di *tutti* gli organi dell'ecosistema (tabella `mission_stats`), taggando ogni riga con l'organo di provenienza (vedi `backend/MULTI_REGISTRY.md`, M-220).
     - Esporre i dati tramite un'API REST.
 
 2.  **Frontend (React & Vite)**: Una single-page application che:
@@ -32,6 +33,7 @@ Il progetto è diviso in due componenti principali:
   - `tag_system_v2.py`: Definisce le categorie dei commit e i loro pesi.
   - `auto_categorizer.py`: Classifica automaticamente i commit senza tag.
 - **Ingestion Dati (`ingest_to_remotedb.py`)**: Script per popolare il database con i dati più recenti da GitHub. Viene eseguito periodicamente tramite `daily_ingest.sh`.
+- **Ingestion Missioni (`ingest_missions.py`)**: Sincronizza la tabella `mission_stats` dai `MISSION_REGISTRY.json` di tutti gli organi. Multi-registry da M-220: la discovery dei registry e la normalizzazione dei due schemi coesistenti (legacy-IT + engine-EN) vivono in `ecosystem.py`; la migrazione idempotente dello schema (`organ` + PK composta) in `migrate_mission_stats_organ.py`. Dettaglio completo in `backend/MULTI_REGISTRY.md`.
 - **Database (`init_remote_db.py`)**: Script per inizializzare lo schema e le tabelle nel database PostgreSQL.
 
 ### Frontend
