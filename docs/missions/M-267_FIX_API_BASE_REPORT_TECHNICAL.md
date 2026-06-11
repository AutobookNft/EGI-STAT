# M-267 — Report Tecnico: fix dashboard vuota (VITE_API_BASE_URL stale)

**Mission:** M-267 | **Data:** 2026-06-11 | **Trigger:** 1 | **Tipo:** fix

## Root cause

`frontend/.env.production` puntava al deploy PRE-M-266
(`egi-stat.13.53.205.215.sslip.io`, host spento): la SPA buildata in M-266
chiamava un'API morta → dashboard vuota su stat.florenceegi.com. Il backend
era sano (endpoint pubblico e API interne rispondevano con dati corretti).
Buco di copertura: nessun test verificava l'env di build produzione.

## Fix

| File | Modifica |
|---|---|
| `frontend/.env.production` | 1 riga: → `https://stat.florenceegi.com` |
| `deploy/pull-frontend.sh` (nuovo) | pull SOLO frontend da S3 su EC2 via SSM (fix rapidi senza full deploy); parametri identici a deploy-stat.sh (P0-12), `--exact-timestamps` |
| `tests/m-267/test_frontend_api_base.sh` | env corretto + bundle senza residui sslip + API hours live con dati — chiude il buco (Circolarità Virtuosa: bug→test) |

## Esecuzione

Rebuild locale → S3 sync (bundle vecchio cancellato) → pull EC2 (CEO).
Verifica live: bundle `index-DYSI_w6s.js`, zero sslip, API 23 progetti,
dashboard piena. Test GREEN completo.

## Audit

PASS — 0 critici, 0 warning, 2 INFO (pull-frontend.sh da committare → fatto
nel commit di chiusura; ROOT hardcoded nel test → accettato, test locale).

## Nota di processo

Il deploy lanciato dal CEO non aveva caricato S3 (run interrotta/profilo);
diagnosi: confronto hash asset live vs locale vs S3. `pull-frontend.sh` nasce
per questo scenario: bundle già su S3, serve solo il pull.
