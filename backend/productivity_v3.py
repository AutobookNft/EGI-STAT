"""
@package   EGI-STAT/backend
@author    Padmin D. Curtis (CTO-AI) for Fabio Cherici (CEO)
@version   0.1.0 (FlorenceEGI — EGI-STAT, M-243 — PROPOSTA, non in produzione)
@date      2026-06-07
@purpose   Indice di Produttività v3 — proposta grounded sulla skill
           `dev-productivity-metrics` (SPACE/DORA/DevEx + statistica indici
           compositi OECD). Risolve le incoerenze del v2:
             1. throughput-blind (il grafico mostrava AVG per-missione) ->
                qui il valore è THROUGHPUT (somma) E intensità (media), distinti.
             2. cap magico min(|net|,2000) -> sostituito da log1p (coda log-normale,
                rendimenti decrescenti senza costante inventata).
             3. doppia penalizzazione del volume (÷cognitive_load) -> rimossa:
                la complessità è già catturata dal log di righe/file/commit.
             4. pesi impliciti (×10, /10) -> resi ESPLICITI e documentati (P0-3).

           NOTA: modulo di RIFERIMENTO/PROPOSTA. Lo swap nella pipeline di
           produzione (ingest_missions.compute_productivity + endpoint stats_v2)
           cambia la SEMANTICA della metrica => decisione CEO (Trigger Matrix 3).
           Vedi skill chapters/ch06-egistat-applied.md per la giustificazione.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping

# ── Pesi ESPLICITI (P0-3: nessun default nascosto) ────────────────────────────
# Contributo relativo dei tre segnali di OUTPUT al valore di una missione.
# Le righe sono il segnale principale; file e commit aggiungono ampiezza/frammentazione.
# Somma = 1.0 per leggibilità (il valore resta su scala log-unità).
W_LINES = 0.60
W_FILES = 0.25
W_COMMITS = 0.15

# Moltiplicatore di INTENTO/qualità per tag dominante della missione.
# Mappa il "tipo di lavoro" su quanto vale a parità di volume (cfr. DORA: il
# lavoro di refactor/architettura/sicurezza vale più del chore a parità di righe).
# Allineato (ma esplicitato) ai multiplier di classify_day_type del v2.
EFFORT_MULT = {
    "SECURITY": 1.8, "ARCH": 1.6, "REFACTOR": 1.5, "PERF": 1.4,
    "FIX": 1.3, "TEST": 1.2, "FEAT": 1.0, "DEPLOY": 0.8, "DOC": 0.8,
    "I18N": 0.7, "CONFIG": 0.7, "DEBITO": 0.7, "CHORE": 0.6, "WIP": 0.3,
}
DEFAULT_MULT = 1.0


def mission_value(mission: Mapping) -> float:
    """Valore di OUTPUT di una singola missione (scala log-unità, ≥ 0).

    output = Σ peso_i · log1p(segnale_i)   (rendimenti decrescenti, niente cap magico)
    value  = effort_mult · output           (intento/qualità del lavoro)

    Chiavi accettate (mancanti => 0): lines_touched (o lines_added+lines_deleted),
    files, commits, e UNO tra `mult` (moltiplicatore già risolto) oppure
    `dominant_tag` (risolto via EFFORT_MULT).
    """
    lines_touched = mission.get("lines_touched")
    if lines_touched is None:
        lines_touched = (mission.get("lines_added", 0) or 0) + (mission.get("lines_deleted", 0) or 0)
    files = mission.get("files", 0) or 0
    commits = mission.get("commits", 0) or 0

    output = (
        W_LINES * math.log1p(max(0, lines_touched))
        + W_FILES * math.log1p(max(0, files))
        + W_COMMITS * math.log1p(max(0, commits))
    )

    mult = mission.get("mult")
    if mult is None:
        mult = EFFORT_MULT.get(mission.get("dominant_tag"), DEFAULT_MULT)

    return round(output * float(mult), 4)


def weekly_productivity_index(missions: Iterable[Mapping]) -> float:
    """THROUGHPUT settimanale = Σ valore-missione. Risponde a 'quanto abbiamo
    prodotto': scala col volume (159 missioni > 11 missioni), a differenza del v2
    che mostrava la media per-missione (throughput-blind).
    """
    return round(sum(mission_value(m) for m in missions), 2)


def weekly_intensity(missions: Iterable[Mapping]) -> float:
    """INTENSITÀ media per-missione = media valore-missione. Risponde a 'quanto era
    denso/qualificato ogni lavoro': volume-invariante. Metrica COMPLEMENTARE al
    throughput, da mostrare accanto (mai al posto).
    """
    vals = [mission_value(m) for m in missions]
    return round(sum(vals) / len(vals), 2) if vals else 0.0
