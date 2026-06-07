# OS3 Matrix — Enforcement (istanza FlorenceEGI)

> SSOT single-source dei canonici FlorenceEGI (deployato negli organi da M-OS3-093). NON editare nelle copie-organo.
> Profilo enforcement PER-ISTANZA: descrive quali hook/agenti/gate del Matrix sono attivi e rilevanti
> per FlorenceEGI (organismo multi-organo Laravel/React + RAG). Il paradigma vive in `@CLAUDE_ORACODE_CORE.md`,
> l'organismo in `@CLAUDE_ECOSYSTEM_CORE.md`. Questo file = lo strato di esecuzione.

## Cos'è OS3 Matrix
Lo strato di enforcement commerciale di Oracode (privato, Florence EGI S.R.L.): hook PreToolUse/PostToolUse,
gate validator, mission engine, DOC-SYNC v2, agenti specializzati. Trasforma le regole P0 del paradigma da
"disciplina" a "enforcement automatico". Per FlorenceEGI è attivo nella forma più completa (istanza di riferimento).

## STATO ENFORCEMENT (FlorenceEGI — 2026-06-07)
Multi-organo (12 organi, DB condiviso), enforcement PRODUCTION su mission-engine, DOC-SYNC, git-safety,
provenance Ultra, compliance MiCA/GDPR. Hook globali in `~/.claude/hooks/`, agenti in `~/.claude/agents/`.

## Hook presenti (per funzione — campione rilevante FlorenceEGI)
- **Mission engine**: `mission-state-guard` (blocca Write senza mission focalizzata), `mission-read-tracker`, `mission-report-guard`, `mission-stats-guard`, `mission-timeout-checker`, `os3-mission-reinject`, `state-file-write-guard`, `spawn-fingerprint-logger`.
- **Audit/Gate**: `os3-preflight-guard`, `os3-audit-on-complete`, `os3-audit-static`, `os3-deep-audit`, `oracode-lint-gate`, `oracode-lint-guard`, `test-quality-gate`, `coverage-check-precheck`.
- **DOC-SYNC / SSOT**: `doc-sync-v2-guard`, `ssot-living-check`, `ssot-reflex-guard`, `trigger-matrix-classifier`.
- **Provenance Ultra (P0-2/P0-4/P0-5)**: `uem-provenance-guard`, `uem-code-validation-guard`, `ulm-provenance-guard`, `utm-key-atomicity-guard`, `p04-method-guard`.
- **Sicurezza/segreti**: `env-guard`, `gitleaks-precommit`, `install-gitleaks-hooks`, `db-prod-guard` (M-OS3-087: blocca distruttivo verso DB prod), `hardcoded-strings-guard`, `immutable-values-guard`.
- **Compliance dominio**: `mica-guard`, `seo-public-content-guard`, `web-quality-gate-guard`.
- **Stack/codice**: `check-no-legacy-stack` (Alpine/Livewire/Filament ban), `legacy-guard`, `organ-index-guard`, `organ-index-ts-guard`.
- **Git/FS safety**: `git-main-guard`, `rm-guard`, `cross-project-guard`, `deploy-pipeline-guard`.
- **Altro**: `package-reality-check`, `m094-supervisor-reminder`.

## Gate Validator
`os3-gate` (agente) + `os3-preflight-guard` (hook): validazione pre-push su organi critici. Skill `/gate`.

## Mission Registry Enforcement
Engine `bin/mission`: FASE 0 (prenota ID) → executing (test-file gate) → auditing (os3-audit-specialist) →
closed/closed_with_debt (report-pair + doc-sync-v2). Registry: `EGI-DOC/docs/missions/MISSION_REGISTRY.json`.
Edit fuori mission focalizzata → bloccati da `mission-state-guard`.

## DOC-SYNC v2 Runtime
Agente `doc-sync-v2` a chiusura mission: analisi diff → SSOT impattati (registry watches + RAG) →
patch additivo/sostitutivo → re-index RAG → audit trail. L'operatore NON aggiorna i SSOT a mano durante la mission.

## Agenti Specializzati (~/.claude/agents/)
- **Oracode/LSO**: `oracode-specialist`, `oracode-alignment-interpreter`, `organ-gap-scout`, `os3-audit-specialist`, `os3-gate`, `ssot-living-agent`, `doc-sync-v2`, `skill-dryrun-guardian`.
- **Dominio FlorenceEGI**: `egili-blood-keeper` (sangue Egili), `m093-remediation-tracker`, `corporate-finance-specialist`.
- **Coder specialist**: `node-ts-specialist` (+ laravel/python/frontend specialist a livello organo).
- **Ingegneri-design**: `engineer-architecture`, `engineer-product`, `engineer-recsys`, `engineer-social-graph`, `engineer-trust-safety`, `engineer-evaluator`, `engineer-meta`.
- **DeepDebug** (read-only): `deepdebug-memory`, `deepdebug-concurrency`, `deepdebug-perf`, `deepdebug-reverse-security`, `deepdebug-ai-driven`.
- Protocollo spawn: `AGENT_EPISTEMOLOGY_PROTOCOL.md` (UNCERTAINTY FLAGS obbligatori).

## Organ Index
Tool `python3 -m organ_index` (in `oracode/bin`). Hook `organ-index-guard`/`organ-index-ts-guard` su creazione classi.
Catalogo organi: vedi `@CLAUDE_ECOSYSTEM_CORE.md`.

## Git Safety — Enforcement
`git-main-guard` (push sicuro, no force su main), `rm-guard` (riferimenti attivi), `gitleaks-precommit` (segreti).
Soglie R1-R4: vedi paradigma `@CLAUDE_ORACODE_CORE.md`.

## Protocollo Epistemologico — Enforcement
`spawn-fingerprint-logger` traccia gli spawn agente; ogni report agente termina con `## UNCERTAINTY FLAGS`.
*(Nota: bug noto fingerprint-logger mis-correla mission-ID dal prompt → workaround `--bypass-fingerprint` documentato.)*

---
*Profilo enforcement FlorenceEGI — SSOT single-source · M-OS3-093 · 2026-06-07*
*Paradigma: @CLAUDE_ORACODE_CORE.md · Organismo: @CLAUDE_ECOSYSTEM_CORE.md*
