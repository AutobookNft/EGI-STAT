@CLAUDE_ECOSYSTEM_CORE.md

# EGI-STAT — Contesto Specifico (Oracode OS3)

> Dashboard produttività sviluppatori FlorenceEGI.
> Analizza attività GitHub, classifica commit per tag OS3, calcola Indice di Produttività.
> Path locale: /home/fabio/EGI-STAT/ | Strumento interno — non deployato pubblicamente

---

## 🌐 Ruolo nell'Organismo

EGI-STAT è uno strumento interno di osservabilità dell'ecosistema FlorenceEGI.
Legge i commit GitHub di tutti gli organi, li classifica per tag OS3 (`[FEAT]`, `[FIX]`, ...),
calcola metriche aggregate (Indice di Produttività, Carico Cognitivo) e le espone via API + dashboard.

Non impatta gli altri organi — è read-only su GitHub, ha il suo DB PostgreSQL separato.

---

## 🏗️ Stack

```
Backend  → Python + Flask + PostgreSQL
           API REST per metriche aggregate (giornaliere e settimanali)
Frontend → React + Vite
           SPA dashboard con grafici e tabelle interattive
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
