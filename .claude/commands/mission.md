# OS3/LSO AGENT HEADER — OPERATIVO

STRUTTURA: 3 agenti — SUPERVISOR (tu), DEV (laravel-specialist / python-rag-specialist / frontend-ts-specialist / node-ts-specialist), AUDIT (os3-audit-specialist).

CONTESTO OBBLIGATORIO ad ogni invocazione di ogni agente: CLAUDE.md del progetto + 00_LSO_LIVING_SOFTWARE_ORGANISM.md + CLAUDE_ECOSYSTEM_CORE.md. Se uno manca → STOP immediato.

FLUSSO per ogni file: SUPERVISOR pianifica → DEV scrive (1 file) → AUDIT valida → PASS: file successivo / WARN: SUPERVISOR decide / BLOCK: DEV riscrive. Eccezioni multi-file solo se atomiche e dichiarate dal SUPERVISOR prima dell'esecuzione.

REGOLE: AUDIT emette sempre PASS / WARN / BLOCK con motivazione e regola OS3 violata. WARN su MiCA-SAFE, valori immutabili o secrets = BLOCK automatico, nessuna eccezione. Loop DEV→AUDIT: max 3 iterazioni, poi ESCALATION a Fabio. Nessuna deduzione senza evidenza — "probabilmente" è vietato senza verifica. No fallback creativi, no naming inventato, no schema DB dedotto.

AUDIT ≠ GATE: AUDIT lavora file per file in sessione, GATE lavora sull'intero diff pre-push. Prima di ogni push: /gate obbligatorio. Dopo ogni task: doc-sync-guardian obbligatorio.

ESCALATION (formato obbligatorio): TASK / FILE / PROBLEMA / REGOLA VIOLATA / COSA MANCA / OPZIONI.

LOG a fine task (SUPERVISOR): TASK / FILE→esito / WARN accettati / ESCALATION / GATE / DOC-SYNC / MISSION REPORT.

LEGGE ASSOLUTA: OS3+LSO vincono sempre. Se conflitto con il task → task sospeso, Fabio informato.

CHECKPOINT OBBLIGATORI (il SUPERVISOR rilegge questo header intero prima di procedere):
- Prima di invocare qualsiasi agente DEV o AUDIT
- Dopo ogni BLOCK ricevuto da AUDIT
- Dopo ogni 3 file completati
- Se il task cambia scope rispetto al piano iniziale

---

# /mission — Avvia Missione Strutturata

Quando ricevi questo comando, applica il seguente protocollo prima di fare qualsiasi altra cosa.

## Fase 0 — Assegnazione Mission ID

PRIMA di qualsiasi altra azione:
1. Leggi `/home/fabio/EGI-DOC/docs/missions/MISSION_REGISTRY.json`
2. Prendi il `counter` corrente come nuovo Mission ID: `M-{counter:03d}`
3. Comunica: "Missione **M-XXX** aperta"
4. NON incrementare il counter ancora — lo farai alla chiusura

## Fase 1 — Raccolta requisiti

Fai queste domande (tutte in una volta, non una alla volta):

1. **Cosa**: Descrivi il comportamento atteso del codice finale in una o due frasi
2. **Layer**: Quale layer è coinvolto? [Python AI / Laravel / Frontend TS / Node.js TS / tutti]
3. **File di riferimento**: Esiste un file simile che posso usare come pattern?
4. **Branch**: Su quale branch lavoriamo? [perfect-with-timeout / develop / main / altro]
5. **Vincoli speciali**: Ci sono limitazioni specifiche per questa missione?

## Fase 2 — Analisi (Plan Mode automatico)

Dopo aver ricevuto le risposte:

1. Leggi i file rilevanti con Read tool
2. Esegui grep per verificare metodi e pattern esistenti
3. Mappa il flow completo: entry point → ogni step → output finale
4. Identifica tutti i file da toccare
5. Identifica i rischi (file > 500 righe, valori immutabili, cross-layer)

## Fase 3 — Piano di implementazione

Prima di scrivere una riga di codice, presenta:

```
PIANO MISSIONE: M-XXX — [titolo]
Branch: [branch]
Layer: [layer/i]

FILE COINVOLTI:
- [file 1] — [tipo modifica: create/modify/read-only]
- [file 2] — [tipo modifica]

SEQUENCE:
1. [step 1]
2. [step 2]
3. [step 3]

RISCHI:
- [rischio se presente]

AGENTE: [laravel-specialist / python-rag-specialist / frontend-ts-specialist / node-ts-specialist]
DOC-SYNC richiesto: [sì/no] — [quale .md aggiornare]

Procedo? (sì/modifica piano)
```

## Fase 4 — Esecuzione

Solo dopo approvazione esplicita:
- Un file per volta
- Firma OS3.0 su ogni file
- Verifica che il file non superi 500 righe (300 per Node.js TS)
- npm run build se tocca frontend

## Fase 5 — Chiusura operativa

```
MISSIONE COMPLETATA: M-XXX — [titolo]

FILE CREATI/MODIFICATI:
- [lista]

NEXT STEPS:
- [ ] npm run build (se frontend)
- [ ] sudo supervisorctl restart [servizio] (se Python/Node)
- [ ] php artisan config:cache (se config Laravel)
- [ ] DOC-SYNC: aggiornare [file.md]
- [ ] Commit: [TAG] [descrizione]
```

## Fase 6 — Report e Registrazione (OBBLIGATORIA — P0)

**La missione NON è chiusa finché questa fase non è completata.**

### 6a. Compilare Mission Report

Usare i template in `/home/fabio/EGI-DOC/docs/missions/`:
1. **Report tecnico**: `M-XXX_[NOME].md` (da `TEMPLATE_REPORT_TECNICO.md`)
2. **Report esteso**: `M-XXX_[NOME]_FULL.md` (da `TEMPLATE_REPORT_ESTESO.md`)

Il report esteso DEVE includere:
- Sezione 5 (Trasformazione portata nell'organismo)
- Sezione 6 (Memoria narrativa — lesson learned, pattern riusabile, followup)
- Sezione 7 (Audit — se eseguito, con finding aperti)

### 6b. Aggiornare MISSION_REGISTRY.json

```json
{
  "mission_id": "M-XXX",
  "titolo": "...",
  "data_apertura": "YYYY-MM-DD",
  "data_chiusura": "YYYY-MM-DD",
  "stato": "completed | suspended | blocked",
  "tipo_missione": "feature | bugfix | refactor | docsync | audit | lso-evolution",
  "organi_coinvolti": ["..."],
  "cross_organo": true | false,
  "report_tecnico": "missions/M-XXX_[NOME].md",
  "report_esteso": "missions/M-XXX_[NOME]_FULL.md",
  "doc_sync_executed": true | false,
  "doc_verified": false,
  "doc_verified_date": null,
  "files_modified": ["path/relativo/file1.php", "path/relativo/file2.py"]
}
```

**Campi propriocettivi (OBBLIGATORI da M-025):**
- `doc_sync_executed`: il SUPERVISOR dichiara se ha eseguito DOC-SYNC durante la missione
- `doc_verified`: sempre `false` alla chiusura — sarà `true` quando l'SSOT Living Agent verificherà
- `doc_verified_date`: sempre `null` alla chiusura
- `files_modified`: lista ESPLICITA di tutti i file di codebase creati o modificati (path relativi al repo)

Incrementare il `counter` nel registry.

### 6c. Calcolare e scrivere le stats della missione

```bash
cd /home/fabio/EGI-STAT/backend && ./.venv/bin/python enrich_registry.py --force
```

Questo calcola da git log: commits, lines +/-, net, files, weighted commits, cognitive load, productivity index, commit_hashes. Scrive tutto nel campo `stats` della missione nel MISSION_REGISTRY.json.

**OBBLIGATORIO** — una missione senza stats è incompleta.

### 6d. Commit e push EGI-DOC

```bash
git add docs/missions/M-XXX_*.md docs/missions/MISSION_REGISTRY.json
git commit -m "[DOC] Mission report M-XXX — [titolo breve]"
git push origin main
```

### 6e. LOG SUPERVISOR finale

```
LOG SUPERVISOR — M-XXX
TASK: [titolo]
FILE → esito: [lista con PASS/WARN/BLOCK]
WARN accettati: [lista]
WARN aperti (Tipo 2): [lista — richiedono approvazione Fabio]
ESCALATION: [nessuna / lista]
AUDIT: [link report]
GATE: [eseguito/non eseguito]
DOC-SYNC: [file aggiornati]
MISSION REPORT: M-XXX registrato in MISSION_REGISTRY.json
```

**Se la Fase 6 non viene completata, la missione risulta NON CHIUSA nel registry.**

## Ripresa Missione

Per riprendere una missione sospesa o in corso:
1. L'utente dice: "riprendi missione M-XXX"
2. Leggi `MISSION_REGISTRY.json` → trova M-XXX
3. Leggi il report esteso (`report_esteso`) per contesto completo
4. Riparti dalla fase dove era rimasta (WARN aperti, followup suggeriti)
