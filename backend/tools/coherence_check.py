#!/usr/bin/env python3
"""
@package   EGI-STAT/backend/tools
@author    Padmin D. Curtis (CTO-AI) for Fabio Cherici (CEO)
@version   1.0.0 (FlorenceEGI — EGI-STAT, M-248)
@date      2026-06-08
@purpose   PROVA RIPRODUCIBILE di coerenza statistiche (deliverable CEO P0).
           Confronta, su TUTTI i progetti, le mission PRODUTTIVE reali nei
           registry (via la stessa normalizzazione + clustering anti-collisione
           dell'aggregatore) con le righe effettive nello stats.db.
           Exit 0 = zero discrepanze; exit != 0 = numero di discrepanze, con
           elenco. Ripetibile: `python3 backend/tools/coherence_check.py`.

           Copre H1 (collisione id) + H3 (regola delivered): il numero atteso è
           il numero di CLUSTER-identità (mission reali distinte), non di id.
           NOTA: la coerenza commit (git-vs-registry) dipende dal fix observer-
           effect in os3-matrix/bin/mission (H4) — qui si verifica conteggio
           mission stat-vs-registry, la metrica che il CEO vede come "ne vedo meno".
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aggregate_to_sqlite as agg
import ecosystem

DB = os.getenv("STATS_DB_PATH",
               os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "stats.db"))


def expected_rows_from_registries():
    """Mission reali distinte attese = somma dei cluster-identità per id, su tutti i
    registry. Replica la logica di Pass2 (normalize_mission + _cluster_by_identity)."""
    by_id = {}
    per_registry = {}
    for rp, organ in agg.discover_registries_from_index():
        try:
            data = json.loads(open(rp, encoding="utf-8").read())
        except Exception as exc:
            print(f"  WARN registry illeggibile {rp}: {exc}", file=sys.stderr)
            continue
        n = 0
        for m in data.get("missions") or []:
            nm = ecosystem.normalize_mission(m)
            if nm is None:
                continue
            by_id.setdefault(nm["id"], []).append((organ, rp, nm))
            n += 1
        per_registry[organ] = per_registry.get(organ, 0) + n

    clusters = 0
    for mid, copies in by_id.items():
        clusters += len(agg._cluster_by_identity(copies))
    return clusters, per_registry


def main():
    if not os.path.isfile(DB):
        print(f"FAIL: stats.db assente: {DB}", file=sys.stderr)
        return 2

    expected, _per_reg = expected_rows_from_registries()

    conn = sqlite3.connect(DB)
    db_rows = conn.execute("SELECT COUNT(*) FROM missions").fetchone()[0]
    # coerenza interna: ogni riga child punta a una mission esistente (FK logica)
    orphan_tags = conn.execute(
        "SELECT COUNT(*) FROM mission_tags t LEFT JOIN missions m "
        "ON t.mission_organ=m.organ AND t.mission_id=m.id WHERE m.id IS NULL"
    ).fetchone()[0]
    # invariante H6: nessuna riga che il serving filtrerebbe fuori
    unclosed = conn.execute(
        "SELECT COUNT(*) FROM missions WHERE NOT "
        "(date_closed IS NOT NULL AND date_closed!='' AND date_closed!='pending')"
    ).fetchone()[0]
    conn.close()

    discrepancies = 0
    print("=" * 60)
    print("COHERENCE CHECK — stat-vs-registry (M-248)")
    print("=" * 60)
    print(f"  mission reali nei registry (cluster-identità): {expected}")
    print(f"  righe in stats.db (missions):                  {db_rows}")
    if expected != db_rows:
        discrepancies += abs(expected - db_rows)
        print(f"  ✗ DISCREPANZA conteggio: {expected} vs {db_rows} (delta {expected-db_rows})")
    else:
        print(f"  ✓ conteggio coerente")
    print(f"  righe child orfane (mission_tags):             {orphan_tags}")
    if orphan_tags:
        discrepancies += orphan_tags
        print("  ✗ child orfani presenti")
    print(f"  righe non-chiuse in missions (invariante H6):  {unclosed}")
    if unclosed:
        discrepancies += unclosed
        print("  ✗ violazione invariante chiuso")
    print("-" * 60)
    if discrepancies == 0:
        print(f"COHERENCE: registries={expected} db={db_rows} drift=0  → OK")
        return 0
    print(f"COHERENCE: {discrepancies} discrepanze  → FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
