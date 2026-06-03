-- drop_stat_schema.sql — DISMISSIONE Postgres stat.* (M-227 / S3)
-- ⚠️ GATED — NON eseguire autonomamente. Richiede:
--   1. Decisione CEO: "mission-scoped sufficiente" (vedi POSTGRES_DECOMMISSION_ANALYSIS.md).
--   2. Backup/snapshot RDS confermato.
--   3. DailyStats.jsx + endpoint v1 daily_detail rimossi/migrati PRIMA (altrimenti la tab si rompe).
-- Irreversibile (oltre al backup). La pipeline serving gira gia su SQLite locale (S1/S2).
--
-- Esecuzione (assistita, con CEO):
--   psql "$DATABASE_URL" -f drop_stat_schema.sql
--
-- @author Padmin D. Curtis (CTO-AI) for Fabio Cherici (CEO)

-- Verifica preliminare (read-only) — quante righe si perdono:
-- SELECT 'daily_stats' t, count(*) FROM stat.daily_stats
-- UNION ALL SELECT 'weekly_stats', count(*) FROM stat.weekly_stats
-- UNION ALL SELECT 'mission_stats', count(*) FROM stat.mission_stats
-- UNION ALL SELECT 'commits', count(*) FROM stat.commits;

-- DROP (de-commentare SOLO dopo i 3 prerequisiti sopra):
-- DROP SCHEMA stat CASCADE;
