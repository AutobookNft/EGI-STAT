@CLAUDE_ORACODE_CORE.md
@CLAUDE_OS3_MATRIX.md
@CLAUDE_ECOSYSTEM_CORE.md

# EGI-STAT — Contesto Specifico (Oracode OS3)

> Dashboard produttività sviluppatori FlorenceEGI.
> Analizza attività GitHub, classifica commit per tag OS3, calcola Indice di Produttività.
> Path locale: /home/fabio/EGI-STAT/ | Deploy: stat.florenceegi.com (M-266)
> Dashboard + API interne dietro BASIC AUTH; UNICO endpoint pubblico:
> /api/public/site-stats (aggregato minimo per fabiocherici.com — MAI nomi progetto)

---

## 🌐 Ruolo nell'Organismo

EGI-STAT è uno strumento interno di osservabilità dell'ecosistema FlorenceEGI.
Legge i commit GitHub di tutti gli organi, li classifica per tag OS3 (`[FEAT]`, `[FIX]`, ...),
calcola metriche aggregate (Indice di Produttività, Carico Cognitivo) e le espone via API + dashboard.

Non impatta gli altri organi — è read-only su GitHub, ha il suo DB separato
(SQLite serving `backend/data/stats.db`, rigenerato dai registry locali; Postgres = legacy).
Sull'EC2 il DB è SHIPPED dalla macchina dev via `deploy/push-stats.sh` (i registry vivono qui).

---

## 🏗️ Stack

```
Backend  → Python + Flask + SQLite serving (stats.db; Postgres legacy)
           API REST per metriche aggregate (giornaliere e settimanali)
           Prod: gunicorn 127.0.0.1:5055 (systemd egi-stat) dietro nginx
Frontend → React + Vite
           SPA dashboard con grafici e tabelle interattive
Privacy  → /api/public/site-stats: SOLO totali aggregati, MAI nomi
           progetto/mission (vincolo M-266); CORS solo fabiocherici.com
```

---

## 🛑 P0 Specifici EGI-STAT

| # | Regola | Enforcement |
|---|--------|-------------|
| P0-STAT-1 | **Read-Only GitHub** | MAI scrivere su repo GitHub tramite EGI-STAT. Solo lettura |
| P0-STAT-2 | **DB separato** | EGI-STAT ha il suo DB — MAI connettere al RDS florenceegi |

---

## 🔍 Audit Oracode

Target ID: **T-006** (interno) | Strumento interno — nessun DOC-SYNC richiesto su EGI-DOC