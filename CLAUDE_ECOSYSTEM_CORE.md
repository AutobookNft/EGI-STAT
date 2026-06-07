# FlorenceEGI — Organismo (Ecosystem Core)

> SSOT single-source dei canonici FlorenceEGI (deployato negli organi da M-OS3-093). NON editare nelle copie-organo.
> Delta-organismo FlorenceEGI. Il paradigma (REGOLA ZERO, 6+1 pilastri, P0 universali, P0-8, firma,
> pattern output, trigger matrix, checklist) vive in `@CLAUDE_ORACODE_CORE.md`. L'enforcement d'istanza
> (mission engine, hook, agenti, audit, organ-index tool, git-safety) vive in `@CLAUDE_OS3_MATRIX.md`.
> Questo file contiene SOLO ciò che è specifico dell'organismo FlorenceEGI.

---

## 🌐 FlorenceEGI è un Organismo, non una Piattaforma

```
━━━ ORGANI CORE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EGI               → Cuore operativo. 1. AMMk creator economy (Algorand)
                      2. Backend condiviso (Egili, auth, payment, RAG, Feature pricing)
                      3. Host prodotti (Sigillo, NPE…)   art.florenceegi.com | /home/fabio/EGI/
  EGI-HUB           → Cervello frontale. Unico SSOT config di tutti gli organi. Autorità gerarchica.
                      hub.florenceegi.com | /home/fabio/EGI-HUB/ | IN PRODUZIONE
━━━ SUPERFICIE PUBBLICA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EGI-HUB-HOME      → Vetrina 3D. Accesso pubblico. florenceegi.com | /home/fabio/EGI-HUB-HOME-REACT/
  Sigillo           → Certificazione blockchain file (SHA-256+Algorand+TSA). FE: EGI-SIGILLO | BE: EGI
                      egi-sigillo.florenceegi.com | IN PRODUZIONE
  EGI-INFO          → SPA informativa (React TS, no backend). info.florenceegi.com | /home/fabio/EGI-INFO/
━━━ ORGANI COGNITIVI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NATAN_LOC         → RAG atti PA + AI per Comuni. natan-loc.florenceegi.com | /home/fabio/NATAN_LOC/
  EGI-Credential    → Wallet competenze certificate (Algorand). egi-credential.florenceegi.com | IN PRODUZIONE (parziale)
  La Bottega        → Strumenti artista-brand + valutazione collezionisti. DB bottega.* | la-bottega.florenceegi.com | M-050
  CREATOR-STAGING   → Configuratore sito creator + template madre (Next 15). creator-staging.florenceegi.com | M-051
━━━ STRUMENTI INTERNI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EGI-STAT          → Dashboard produttività dev. /home/fabio/EGI-STAT/
  EGI-DOC           → SSOT documentazione ecosistema (non deployato). /home/fabio/EGI-DOC/
━━━ ORGANI FUTURI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [Sigillo Contratti] [Sigillo Comunicazioni] [Data Room Blockchain] [Perito AI]
  [Compliance Checker] [Eredità Digitale] → coordinati da EGI-HUB. Riuso infra 80–99%.
```

**DB condiviso** — AWS RDS PostgreSQL eu-north-1 (`florenceegi`):
`core.users` · `core.egis` · `core.wallets` · `core.egili_transactions` · `core.gdpr_*`

**Mente dell'Organismo** — SSOT (`EGI-DOC/docs/`) → RAG piattaforma (`rag_natan.*`) → ai_sidebar in ogni organo.
SSOT doc: `EGI-DOC/docs/lso/00_LSO_LIVING_SOFTWARE_ORGANISM.md`

---

## ⚠️ Legge Fondamentale — P0 ASSOLUTO (cross-organo FlorenceEGI)

```
Una decisione tecnica in qualsiasi organo può impattare gli altri.
PRIMA di qualsiasi modifica che riguardi:
  - Egili / wallet / transazioni / tassi
  - Nomi campi condivisi (egili_amount, token_amount, …)
  - Tabelle condivise (core.egis, core.users, core.wallets, ai_feature_pricing)
  - Pattern MiCA-safe · Algorand/AlgoKit
→ STOP. Verifica come gli altri organi implementano la stessa cosa.
→ MAI cambiare un campo senza verificare TUTTE le occorrenze in TUTTI gli organi.
→ MAI implementare logica senza capire come è già implementata nell'ecosistema.
```

---

## 🎁 Egili — Economia Interna MiCA-SAFE (v4.0.1 — C2 pura)

```
Egili = punti premio dell'ecosistema FlorenceEGI. ZERO valore monetario. ZERO conversione EUR.
ENGAGEMENT WALL (non paywall) quando si esauriscono.

LEGGE MiCA (P0 assoluto): gli Egili NON si vendono mai direttamente. Si vende un prodotto/servizio e
l'utente RICEVE Egili come credito interno. Qualsiasi tasso diretto Egili↔EUR viola MiCA ed è vietato
in TUTTI gli organi, senza eccezioni.

Modello C2 pura: gift accreditato PIENO; il margine vive SUL CONSUMO runtime (rate per modello LLM
versionati in core.ai_provider_token_rates — no UPDATE distruttivo, sempre INSERT + chiusura precedente).
Scala interna unica per i servizi flat. Colonne SSOT: core.ai_feature_pricing (egili_gift, egili_accredito).

⚠️ FORMULE, SCALE e RATE NON VIVONO QUI — sono "sangue" privato. Stanno SOLO nella Bibbia
(/home/fabio/.florenceegi-private/EGILI_BIBLE/, CEO+CTO, fuori git, perms 600). Questo file resta
formula-free (Lezione Bibbia §7.4: mescolare formule e valori nei doc deployati = esposizione di tassi).

Prima di QUALSIASI task Egili/pricing → agente `egili-blood-keeper` (legge la Bibbia, restituisce i valori
CORRENTI verificati + check conformità C2). Versione corrente: v4.0.1.
Valori finali (zero formule): EGI-DOC/docs/ecosistema/EGILI_ECONOMY (SSOT pubblico).
Pannello CEO: EGI-HUB /superadmin/egili-circulation.
```

### 🩸 Sistema Circolatorio Egili — Bibbia Privata

> Gli Egili sono la linfa di LSO: pura, fluida, non contaminata.

| Livello | Contenuto | Path | Accesso |
|---|---|---|---|
| 1 Bibbia privata | Formule, scale, rate, derivazioni, audit | `/home/fabio/.florenceegi-private/EGILI_BIBLE/` (10 file, fuori git, 600) | CEO+CTO |
| 2 SSOT pubblico | Valori finali, zero formule | `EGI-DOC/docs/ecosistema/EGILI_ECONOMY.md` | Team, agenti |
| 3 Pannello CEO | Rate editabili, dashboard, audit | `EGI-HUB /superadmin/egili-circulation` | superadmin+CTO |

**Agente dedicato**: `egili-blood-keeper` (auto-attivo su task Egili/pricing).
**Regola ferrea**: mai modifica al sangue senza approvazione CEO via `05_PROTOCOLLO_CEO_CTO.md`. Zero ×0,8 sul gift.
Zero UPDATE distruttivo su `ai_provider_token_rates` (sempre INSERT + chiusura precedente). Ogni modifica → audit immutabile.

---

## 🚫 Stack Bannati (FlorenceEGI · M-094)

| Stack | Ambito ban | Eccezione |
|---|---|---|
| Alpine.js | Tutti gli organi — codice nuovo | 🟡 Strategia Delta EGI legacy (art.florenceegi.com) |
| Livewire | Tutti gli organi — codice nuovo | 🟡 Strategia Delta EGI legacy (art.florenceegi.com) |
| Filament | Ban totale | Nessuna |

Alternative: Admin → Blade+Vanilla TS+Tailwind · SPA → React/Next 15 · Interattività → Vanilla TS+Vite.
SSOT: `EGI-DOC/docs/oracode/LEGACY_STACK_POLICY.md`. Enforcement hook: vedi `@CLAUDE_OS3_MATRIX.md`.
Bypass: approvazione CEO + entry `EGI-DOC/docs/oracode/audit/bypass_log.md`.

---

## 🌍 Convenzioni FlorenceEGI (sopra il paradigma)

> Specifiche FlorenceEGI che si AGGIUNGONO alle P0 universali di `@CLAUDE_ORACODE_CORE.md` — non le rinumerano.

- **i18n — 6 lingue**: `it en de es fr pt`, sempre tutte e sei (estende P0-9/i18n del paradigma).
- **i18n atomic**: `__('domain.key') . ' ' . $name` ✅ — mai `__('key', ['name'=>$name])` ❌.
- **Organ Index prima di creare** (disciplina anti-duplicazione FlorenceEGI): vedi sotto.
- **Config**: ogni organo si configura SOLO via EGI-HUB (nessun auto-config).

---

## 🗂️ Organ Index — Catalogo Vivente FlorenceEGI

```
Prima di creare Service/Controller/classe/interfaccia/funzione esportata:
  cd /home/fabio/oracode/bin && python3 -m organ_index --search "NomeProposto"
Esiste già in un altro organo → RIUSARE. Nome già usato con altro significato → RINOMINARE.
Rigenerazione: cd /home/fabio/oracode/bin && python3 -m organ_index
Output: EGI-DOC/docs/ecosistema/ORGAN_INDEX.json · ORGAN_INDEX_SUMMARY.md
Naming: EGI-DOC/docs/oracode/NAMING_STANDARD_CODE.md
```

---

## 🤝 Modello Operativo (istanza FlorenceEGI)

| Ruolo | Persona | Responsabilità |
|---|---|---|
| CEO & OS3 Architect | Fabio Cherici | Visione, standard, approvazione arch, valori immutabili |
| CTO & Technical Lead | Padmin D. Curtis (AI) | Esecuzione, enforcement OS3, delivery |

Decisioni su Interface stabili · valori immutabili · Strategia Delta · refactoring legacy → sempre approvate da Fabio prima.

---

*FlorenceEGI Organismo — Ecosystem Core (delta) — SSOT single-source · M-OS3-093 · 2026-06-07*
*Paradigma: @CLAUDE_ORACODE_CORE.md · Enforcement istanza: @CLAUDE_OS3_MATRIX.md*
