# Patch proposta — STATS_SYSTEM_SSOT.md (cross-organ, da applicare a mano)

> File bersaglio: `/home/fabio/os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md`
> Modalita: ADDITIVE (nuovo blockquote). Nessuna riga esistente va riscritta o cancellata.
> Motivo no-auto-apply: il file e' fuori da `instance_root` (EGI-STAT) ed e' cross-organo
> (cross-project-guard + scope mission M-251). Applicazione manuale richiesta dal chiamante.

## Discriminazione

- CERCO nel SSOT testo che descriva la PRESERVAZIONE delle tabelle legacy attraverso il rebuild:
  - `grep -ni "preserv\|copy2\|sopravviv\|non gestite\|DROP_TABLES"` sul file → **0 occorrenze**.
  - Il SSOT documenta gia': rebuild ATOMICO con `os.replace` (M-247 / M-OS3-057, righe ~317-338) e
    il "degrado pulito" quando `legacy_production` e' assente (righe ~142, ~211), ma NON l'invariante
    che il rebuild **conserva** le tabelle non-gestite da `aggregate`.
- Concetto NON presente → **ADDITIVE**. Si aggiunge un blockquote, non si modifica nulla.

## Punto di inserimento suggerito

Subito DOPO il blockquote "**Auto-refresh read-time (M-247) — rete di sicurezza ANTI-STALENESS.**"
(termina alla riga ~338, prima del blockquote "⚠️ Observer-effect sul conteggio commit"). E' la
sezione che descrive il rebuild di `aggregate_to_sqlite.py`, quindi e' il contesto naturale.

## Testo da inserire (verbatim)

```markdown
> **Rebuild preserva le tabelle non-gestite da aggregate (M-251) — invariante.** Il rebuild
> atomico (M-247 / M-OS3-057) ricostruisce lo SQLite serving da zero su file temp + `os.replace`.
> Ma `aggregate()` gestisce SOLO le tabelle mission/time (quelle in `DROP_TABLES`): le tabelle
> **non gestite** — `legacy_production` / `legacy_repo_day`, l'**asse storico legacy** popolato
> dall'ingest separato `ingest_legacy_production.py` (vedi §Asse storico legacy) — non sono in
> `DROP_TABLES` e, partendo da un file vuoto, **sparivano** al primo rebuild atomico (regressione
> M-250: righe nette storiche `net_legacy` azzerate, es. EGI ~717k → ~20k). **Fix (M-251):**
> prima del build, se il DB esiste, `aggregate()` ne fa una **COPIA** (`shutil.copy2`) sul file
> temp; `create_schema` droppa/ricrea **solo** le tabelle elencate in `DROP_TABLES`, quindi le
> tabelle legacy **sopravvivono** nella copia; build + `os.replace` atomico restano invariati.
> **Invariante che ne risulta:** *ogni tabella non gestita da `aggregate` persiste attraverso
> ogni rebuild del serving.* Si concilia con il "degrado pulito" gia' documentato (se la tabella
> legacy e' davvero assente le chiavi degradano a zero): ora il rebuild stesso non e' piu' una
> causa di assenza. Re-ingest (`ingest_legacy_production.py`) ripristina i dati persi prima del fix
> (EGI 741k recuperate). Test: `EGI-STAT/backend/tests/m_251_preserve_legacy_test.py` (crea
> `legacy_production`, esegue un rebuild, verifica che tabella e valori sopravvivano; RED prima,
> GREEN dopo).
```

## Verifica post-applicazione (a carico dell'operatore)

Dopo l'inserimento, eseguire sul file:
- `grep -n "M-251" STATS_SYSTEM_SSOT.md` → deve trovare il nuovo blockquote.
- `grep -n "preserv\|copy2\|non gestite" STATS_SYSTEM_SSOT.md` → deve ora trovare l'invariante.
Nessun residuo da aggiornare: e' un'aggiunta, non sostituisce versioni/concetti preesistenti.
