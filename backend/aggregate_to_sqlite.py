#!/usr/bin/env python3
"""
aggregate_to_sqlite.py — Aggregatore giornaliero JSON registry → SQLite locale — M-225 (S1)

@package  EGI-STAT/backend (Oracode-STAT)
@author   Padmin D. Curtis (CTO-AI) for Fabio Cherici (CEO)
@version  1.0.0 (Oracode Nexus — Sistema Statistiche)
@date     2026-06-03
@purpose  Terzo strato della catena di verità delle stat Oracode Nexus
          (COMMIT → REGISTRY JSON → SQLite serving → dashboard, vedi
          STATS_SYSTEM_SSOT.md). Legge i MISSION_REGISTRY.json dell'ecosistema
          — scoperti SOLO via indice descrittori ~/oracode-engine/projects.json
          (NO hardcoded EGI-DOC, NO walk del filesystem M-220 deprecato) —
          normalizza i due schemi coesistenti (legacy-IT EGI-DOC + engine-EN
          os3-matrix) riusando ecosystem.normalize_mission, e (ri)popola lo
          SQLite locale gitignored che è la fonte UNICA del serving dashboard.
          Lo SQLite è usa-e-getta: rigenerabile in ogni momento dai JSON in git.
          Idempotente per costruzione (DROP+CREATE full rebuild ad ogni run).
"""
import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone

import ecosystem  # riuso: normalize_mission (2-schemi → canonico), organ_of, projects.json

# ── Costanti ───────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent
DEFAULT_DB = APP_DIR / "data" / "stats.db"
SCHEMA_VERSION = "1.0.0"
AGGREGATOR_VERSION = "1.0.0"

# DDL — schema serving, mirror 1:1 dello stats{} SSOT. DROP+CREATE ⇒ idempotenza
# assoluta: ogni run è funzione PURA dei JSON correnti, nessuna riga stale.
SCHEMA = [
    # 1) missions — una riga per mission completata/closed (canonico normalize_mission).
    """CREATE TABLE missions (
        id                   TEXT PRIMARY KEY,           -- 'M-225' / 'M-OS3-049' (univoco cross-organo)
        organ                TEXT NOT NULL,              -- organo di provenienza (chiave discovery)
        title                TEXT,
        status               TEXT NOT NULL,              -- canonico 'completed'
        mission_type         TEXT,                       -- feature|bugfix|... (default 'feature')
        date_opened          TEXT,                       -- ISO 'YYYY-MM-DD' o NULL
        date_closed          TEXT,                       -- ISO o NULL
        cross_organ          INTEGER NOT NULL DEFAULT 0, -- bool 0/1
        files_modified       INTEGER NOT NULL DEFAULT 0, -- len(files_modified[])
        doc_sync_executed    INTEGER NOT NULL DEFAULT 0, -- bool 0/1
        has_git_stats        INTEGER NOT NULL DEFAULT 0, -- bool: stats{} non vuoto
        total_commits        INTEGER NOT NULL DEFAULT 0,
        weighted_commits     REAL    NOT NULL DEFAULT 0,
        lines_added          INTEGER NOT NULL DEFAULT 0,
        lines_deleted        INTEGER NOT NULL DEFAULT 0,
        lines_net            INTEGER NOT NULL DEFAULT 0,
        lines_touched        INTEGER NOT NULL DEFAULT 0,
        files_touched        INTEGER NOT NULL DEFAULT 0,
        cognitive_load       REAL    NOT NULL DEFAULT 0,
        productivity_index   REAL    NOT NULL DEFAULT 0,
        calculated_at        TEXT,                       -- stats.calculated_at se presente
        registry_path        TEXT NOT NULL               -- realpath del registry sorgente
    )""",
    "CREATE INDEX idx_missions_organ  ON missions(organ)",
    "CREATE INDEX idx_missions_closed ON missions(date_closed)",
    "CREATE INDEX idx_missions_type   ON missions(mission_type)",

    # 2) mission_commits — una riga per commit-hash (indice atomico di ricostruibilità SSOT).
    """CREATE TABLE mission_commits (
        mission_id  TEXT NOT NULL,
        commit_hash TEXT NOT NULL,
        PRIMARY KEY (mission_id, commit_hash),
        FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE
    )""",
    "CREATE INDEX idx_commits_mission ON mission_commits(mission_id)",
    "CREATE INDEX idx_commits_hash    ON mission_commits(commit_hash)",

    # 3) mission_repo_day — una riga per entry stats.by_repo_day[] (traccia giornaliera per-repo).
    """CREATE TABLE mission_repo_day (
        mission_id    TEXT    NOT NULL,
        repo          TEXT    NOT NULL,                  -- 'florenceegi/oracode'
        day           TEXT    NOT NULL,                  -- 'YYYY-MM-DD' (campo 'date' nel JSON)
        commits       INTEGER NOT NULL DEFAULT 0,
        lines_added   INTEGER NOT NULL DEFAULT 0,
        lines_deleted INTEGER NOT NULL DEFAULT 0,
        files_touched INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (mission_id, repo, day),
        FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE
    )""",
    "CREATE INDEX idx_repoday_mission  ON mission_repo_day(mission_id)",
    "CREATE INDEX idx_repoday_repo_day ON mission_repo_day(repo, day)",

    # 4) mission_tags — breakdown tag a livello mission (stats.tags_breakdown{}).
    """CREATE TABLE mission_tags (
        mission_id TEXT    NOT NULL,
        tag        TEXT    NOT NULL,                     -- 'FEAT','FIX','ARCH',...
        count      INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (mission_id, tag),
        FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE
    )""",
    "CREATE INDEX idx_tags_mission ON mission_tags(mission_id)",
    "CREATE INDEX idx_tags_tag     ON mission_tags(tag)",

    # 5) meta — metadati dell'aggregazione (audit del serving rigenerabile).
    """CREATE TABLE meta (
        key   TEXT PRIMARY KEY,
        value TEXT
    )""",
]

DROP_TABLES = [
    "mission_commits", "mission_repo_day", "mission_tags", "meta", "missions",
]


# ── Helpers di tipo (P0-3: parametri/default sempre espliciti, mai nascosti) ──
def _int(v):
    """Cast a int robusto: None/'' → 0, float → troncato. Nessun default nascosto."""
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 0


def _real(v):
    """Cast a float robusto: None/'' → 0.0."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ── Discovery — SOLO indice descrittori projects.json (NO walk, NO hardcoded) ─
def discover_registries_from_index():
    """Ritorna lista ordinata di (realpath_registry, organ).

    Sorgente UNICA: ~/oracode-engine/projects.json → descriptor di ogni
    progetto → registry_path. NESSUN walk del filesystem (M-220 deprecato),
    NESSUN path EGI-DOC hardcoded. Conforme a STATS_SYSTEM_SSOT §Discovery:
    nel caso accoppiato a 1 cliente la discovery degrada all'indice descrittori.

    Dedup per realpath. Salta registry inesistenti o vuoti. Ordine stabile
    (sorted per realpath) ⇒ risoluzione deterministica di eventuali id duplicati.
    """
    seen = set()
    out = []
    for p in ecosystem._paths_from_projects_json():
        rp = os.path.realpath(p)
        if rp in seen or not os.path.isfile(rp):
            continue
        seen.add(rp)
        out.append((rp, ecosystem.organ_of(rp)))
    out.sort(key=lambda t: t[0])
    return out


# ── Schema ───────────────────────────────────────────────────────────────────
def create_schema(conn):
    """Full rebuild: DROP di tutte le tabelle + CREATE. Idempotenza per
    ricostruzione totale — lo SQLite è serving usa-e-getta (SSOT §Ricostruibilità)."""
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF")  # OFF durante DROP per ignorare ordine FK
    for t in DROP_TABLES:
        cur.execute(f"DROP TABLE IF EXISTS {t}")
    for stmt in SCHEMA:
        cur.execute(stmt)
    cur.execute("PRAGMA foreign_keys = ON")
    conn.commit()


# ── Popolamento ───────────────────────────────────────────────────────────────
def insert_mission(conn, organ, registry_path, nm):
    """Inserisce una mission canonica + figli (commits, repo_day, tags).

    Missioni senza stats{}: inserite comunque, metriche a 0, has_git_stats=0,
    zero righe figlie. NON è un errore (le ~108 mission storiche EGI-DOC senza
    commit_hashes restano a 0 finché non gira l'enrich storico — SSOT backlog 6).
    """
    s = nm.get("stats") or {}
    mid = nm["id"]

    # UPSERT (NON 'INSERT OR REPLACE'): REPLACE cancellerebbe la riga padre → il
    # FOREIGN KEY ... ON DELETE CASCADE svuoterebbe mission_commits/repo_day/tags già
    # inseriti dalla copia precedente, distruggendo l'UNIONE (fix audit M-225 P1 v2).
    # ON CONFLICT(id) DO UPDATE aggiorna in-place: nessun CASCADE, i figli si accumulano.
    conn.execute(
        """INSERT INTO missions (
            id, organ, title, status, mission_type, date_opened, date_closed,
            cross_organ, files_modified, doc_sync_executed, has_git_stats,
            total_commits, weighted_commits, lines_added, lines_deleted,
            lines_net, lines_touched, files_touched, cognitive_load,
            productivity_index, calculated_at, registry_path
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            organ=excluded.organ, title=excluded.title, status=excluded.status,
            mission_type=excluded.mission_type, date_opened=excluded.date_opened,
            date_closed=excluded.date_closed, cross_organ=excluded.cross_organ,
            files_modified=excluded.files_modified,
            doc_sync_executed=excluded.doc_sync_executed,
            has_git_stats=excluded.has_git_stats, total_commits=excluded.total_commits,
            weighted_commits=excluded.weighted_commits, lines_added=excluded.lines_added,
            lines_deleted=excluded.lines_deleted, lines_net=excluded.lines_net,
            lines_touched=excluded.lines_touched, files_touched=excluded.files_touched,
            cognitive_load=excluded.cognitive_load,
            productivity_index=excluded.productivity_index,
            calculated_at=excluded.calculated_at, registry_path=excluded.registry_path""",
        (
            mid,
            organ,
            nm.get("title"),
            nm.get("status") or "completed",
            nm.get("mission_type") or "feature",
            nm.get("date_opened"),
            nm.get("date_closed"),
            1 if nm.get("cross_organ") else 0,
            len(nm.get("files_modified") or []),
            1 if nm.get("doc_sync_executed") else 0,
            1 if nm.get("has_git_stats") else 0,
            _int(s.get("total_commits")),
            _real(s.get("weighted_commits")),
            _int(s.get("lines_added")),
            _int(s.get("lines_deleted")),
            _int(s.get("lines_net")),
            _int(s.get("lines_touched")),
            _int(s.get("files_touched")),
            _real(s.get("cognitive_load")),
            _real(s.get("productivity_index")),
            s.get("calculated_at"),
            registry_path,
        ),
    )

    # commit_hashes[] — indice atomico. INSERT OR IGNORE dedup hash ripetuti.
    for h in s.get("commit_hashes") or []:
        if not h:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO mission_commits (mission_id, commit_hash) VALUES (?,?)",
            (mid, str(h)),
        )

    # by_repo_day[] — chiave giorno = 'date' nel JSON (verificato M-001 e M-OS3-049).
    for e in s.get("by_repo_day") or []:
        repo = e.get("repo")
        day = e.get("date") or e.get("day")
        if not repo or not day:
            continue
        conn.execute(
            """INSERT OR REPLACE INTO mission_repo_day (
                mission_id, repo, day, commits, lines_added, lines_deleted, files_touched
            ) VALUES (?,?,?,?,?,?,?)""",
            (
                mid, repo, day,
                _int(e.get("commits")),
                _int(e.get("lines_added")),
                _int(e.get("lines_deleted")),
                _int(e.get("files_touched")),
            ),
        )

    # tags_breakdown{} a livello mission. INSERT OR REPLACE su PK (mission_id, tag).
    for tag, cnt in (s.get("tags_breakdown") or {}).items():
        if not tag:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO mission_tags (mission_id, tag, count) VALUES (?,?,?)",
            (mid, str(tag), _int(cnt)),
        )


def write_meta(conn, registries_count, missions_count, organs, per_organ):
    """Scrive i metadati di audit dell'aggregazione (serving rigenerabile)."""
    rows = {
        "schema_version": SCHEMA_VERSION,
        "aggregator_version": AGGREGATOR_VERSION,
        "aggregated_at": datetime.now(timezone.utc).isoformat(),
        "source": "projects.json (indice descrittori)",
        "registries_count": str(registries_count),
        "missions_count": str(missions_count),
        "organs": ",".join(sorted(organs)),
        "git_enrich": "off",  # S1: stats lette as-is dai registry, nessun git-enrich
    }
    for organ, n in sorted(per_organ.items()):
        rows[f"organ:{organ}"] = str(n)
    for k, v in rows.items():
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (k, v))


# ── Main ──────────────────────────────────────────────────────────────────────
def aggregate(db_path, verbose=False):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)  # crea data/ se assente

    conn = sqlite3.connect(str(db_path))
    try:
        create_schema(conn)

        registries = discover_registries_from_index()
        organs = set()
        per_organ = {}
        n_missions = 0

        # Pass 1: raccogli TUTTE le copie normalizzate per id (multi-registry).
        by_id = {}  # id -> list[(organ, registry_path, nm)]
        for registry_path, organ in registries:
            try:
                reg = json.loads(Path(registry_path).read_text(encoding="utf-8"))
            except Exception as exc:  # registry illeggibile: salta rumorosamente, non crashare
                print(f"  WARN: registry illeggibile {registry_path}: {exc}", file=sys.stderr)
                continue
            for m in reg.get("missions") or []:
                nm = ecosystem.normalize_mission(m)  # None se non completed-con-id
                if nm is None:
                    continue
                by_id.setdefault(nm["id"], []).append((organ, registry_path, nm))

        # Pass 2: MERGE cross-registry SENZA perdita (fix M-225 audit P1).
        # commit_hashes/by_repo_day/tags si UNISCONO (INSERT OR IGNORE / PK composita).
        # La riga scalare 'missions' la vince la copia con PIU commit_hashes (autoritativa:
        # es. M-OS3-* vive in os3-matrix con piu commit) processandola per ULTIMA — cosi
        # INSERT OR REPLACE lascia l'organo+metriche corretti. MAI scartare una copia
        # (ometterne i commit_hashes violerebbe la ricostruibilita — SSOT §commit_hashes).
        # Chiave di ordinamento ESPLICITA (P0-3, niente default impliciti da ordine FS):
        # primaria = #commit_hashes (copia ricca per ultima → vince la riga scalare);
        # tiebreaker dichiarato = nome organo (a parità di ricchezza vince l'organo
        # lessicograficamente maggiore, processato per ultimo — es. 'os3-matrix' > 'oracode',
        # così le missioni engine M-OS3-* restano attribuite a os3-matrix). Deterministico.
        def _sort_key(t):
            organ, _registry, nm = t
            return (len((nm.get("stats") or {}).get("commit_hashes") or []), organ)

        for mid, copies in by_id.items():
            copies_sorted = sorted(copies, key=_sort_key)  # ricca+organo-maggiore per ultima
            for organ, registry_path, nm in copies_sorted:
                insert_mission(conn, organ, registry_path, nm)
            win_organ = copies_sorted[-1][0]
            if len(copies) > 1:
                regs = ", ".join(sorted({o for o, _, _ in copies}))
                print(
                    f"  MERGE: id '{mid}' in {len(copies)} registry ({regs}) -> "
                    f"union commit_hashes, scalare organ='{win_organ}'",
                    file=sys.stderr,
                )
            organs.add(win_organ)
            per_organ[win_organ] = per_organ.get(win_organ, 0) + 1
            n_missions += 1

        write_meta(conn, len(registries), n_missions, organs, per_organ)
        conn.commit()

        if verbose:
            for organ, n in sorted(per_organ.items()):
                print(f"    {organ}: {n} missions")
        print(
            f"  OK: {n_missions} missions da {len(registries)} registries "
            f"({len(organs)} organi) -> {db_path}"
        )
        return 0
    finally:
        conn.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Aggregatore JSON registry -> SQLite locale (Oracode Nexus stat serving)."
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help=f"path SQLite (default: {DEFAULT_DB})")
    parser.add_argument("--verbose", action="store_true", help="dettaglio per-organo")
    args = parser.parse_args(argv)
    return aggregate(args.db, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
