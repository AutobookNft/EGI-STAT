# M-266 — Report Tecnico: stat.florenceegi.com + endpoint pubblico site-stats

**Mission:** M-266 | **Data:** 2026-06-11 | **Trigger:** 2
**Deploy:** eseguito dal CEO (approvazione esplicita in chat) — STAT_DEPLOY_OK
**Test:** GREEN locale + live (401 protetti, 200 pubblico, CORS ok)

## Scope

EGI-STAT (strumento interno, prima solo locale) deployato su
stat.florenceegi.com per alimentare il widget "cantiere aperto" della nuova
pagina /softwarehouse di fabiocherici.com (vincolo CEO: dati live dal giorno 1).
Protezione: TUTTO dietro basic auth tranne UN endpoint aggregato.

## Architettura

```
fabiocherici.com (statico, browser visitatore)
   └─ GET https://stat.florenceegi.com/api/public/site-stats   ← unico pubblico
        nginx: auth off SOLO su /api/public/, limit_req 10r/m, noindex
        flask: CORS solo https://fabiocherici.com, cache 60s (solo su 200)
        gunicorn 127.0.0.1:5055 (systemd egi-stat, user forge)
        SQLite stats.db — SHIPPED dalla macchina dev (push-stats.sh):
        i registry sorgente vivono in locale, l'EC2 serve il DB com'è
        (_ensure_fresh è best-effort: senza registry serve il DB esistente)
```

## Payload pubblico (privacy by design — MAI nomi progetto)

`hours_total, hours_last_7_days, hours_note ("manual + commit-estimate"),
projects_total, projects_active_30d, last_activity, lines_net_total,
generated_at` — al deploy: 2.243,7h / 179,4h / 23 / 21 / 2.595.750 righe.

## File

| File | Ruolo |
|---|---|
| `backend/public_stats.py` | site_stats() su pattern stats_v2 (M-234/M-OS3-086) |
| `backend/api.py` | route /api/public/site-stats + after_request split (public: cache 60s su 200 + CORS; resto: no-store) |
| `deploy/nginx/stat.florenceegi.com.conf` | basic auth globale, /api/public/ libero rate-limited, /health ALB |
| `deploy/systemd/egi-stat.service` | gunicorn 2 worker |
| `deploy/deploy-stat.sh` | full deploy (pattern tmp-le-vespe; hash apr1 -stdin, mai plaintext) |
| `deploy/push-stats.sh` | refresh solo stats.db ("live": da lanciare post-sessione o cron locale) |
| `tests/m-266/test_public_site_stats.sh` | acceptance locale (shape+plausibilità+anti-lista-progetti) + live (401/200/CORS) |

DNS: record A-alias creato via procedura SSOT (EGI-DOC
docs/aws/ROUTE53_SUBDOMAIN_PROCEDURE.md aggiornato e pushato).

## Audit

PASS — 0 critici. R1 (errore generico su endpoint pubblico + no-cache su 5xx)
e R2 (CLAUDE.md drift) ASSORBITI nel repo; **R1 va in produzione al prossimo
lancio di deploy-stat.sh da parte del CEO** (il classifier limita 1 approvazione
= 1 lancio). R3 (CORS(app) wildcard interno) e R4 (default_type /health,
hardening systemd) registrati come debito P2.

## Debiti

- [PENDING-DEPLOY] R1 fix committato ma non ancora sull'EC2 → prossimo deploy
- [P2] R3 CORS(app) globale da restringere; R4 systemd hardening
- [OPS] push-stats.sh in cron locale per "live" senza intervento manuale
