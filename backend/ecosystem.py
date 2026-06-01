"""
ecosystem.py — Discovery multi-registry + normalizzazione missioni — M-220

@package  EGI-STAT/backend
@author   Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version  1.0.0 (FlorenceEGI — EGI-STAT)
@date     2026-06-01
@purpose  Dopo il decoupling Oracode Nexus, le missioni vivono in registry
          per-organo (non più solo EGI-DOC). Questo modulo scopre TUTTI i
          MISSION_REGISTRY.json dell'ecosistema e normalizza i due schemi
          coesistenti (legacy-IT di EGI-DOC + engine-EN dell'engine os3-matrix)
          a un dizionario canonico, così che l'ingest conti ogni organo.
"""
import os
import sys
import json
from pathlib import Path

# Root da spazzare. Poli vive in /tmp/oracode (fuori HOME). Tutti i repo contano
# (decisione CEO 2026-06-01: archive e simulazioni inclusi — sono produzione).
SCAN_ROOTS = ["/home/fabio", "/tmp/oracode"]
PROJECTS_JSON = "/home/fabio/oracode-engine/projects.json"
PRUNE_DIRS = {"node_modules", ".git", "vendor", ".next", "dist", "build", "__pycache__"}


def _project_root(registry_path):
    """dir-progetto = parent di docs/ (.../EGI-DOC/docs/missions/REG.json → .../EGI-DOC)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(registry_path))))


def organ_of(registry_path):
    """organ = basename della dir-progetto. .../EGI-DOC/... → 'EGI-DOC'."""
    return os.path.basename(_project_root(registry_path))


def _paths_from_projects_json():
    """Censimento engine: include progetti fuori dai root di scan (es. Poli in
    /tmp/oracode). Fonte canonica, ma non esaustiva (non tutti i progetti sono
    engine-registered)."""
    paths = []
    try:
        pj = json.loads(Path(PROJECTS_JSON).read_text())
    except Exception:
        return paths
    for proj in pj.get("projects", []):
        desc = proj.get("descriptor")
        if not desc or not os.path.isfile(desc):
            continue
        try:
            rp = json.loads(Path(desc).read_text()).get("registry_path")
        except Exception:
            rp = None
        if rp:
            paths.append(rp)
    return paths


def _paths_from_walk():
    """Sweep filesystem con pruning: cattura i registry non engine-registered
    (fabiocherici, ORACODE-DOC, archive). os.walk pruned — glob ricorsivo
    impallava su node_modules."""
    paths = []
    for base in SCAN_ROOTS:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in PRUNE_DIRS]
            if os.path.basename(root) == "missions" and "MISSION_REGISTRY.json" in files:
                paths.append(os.path.join(root, "MISSION_REGISTRY.json"))
    return paths


def discover_registries():
    """UNION(projects.json, walk(SCAN_ROOTS)) dedup per realpath.
    Ritorna {organ: [missions...]}. Esclude registry vuoti (template).

    Collisione basename (es. due `*-DOC` omonimi in path diversi): NON
    sovrascrive muto (P2 audit M-220). Disambigua con chiave parent/basename
    per ENTRAMBI e logga un warning su stderr."""
    seen = set()
    by_organ = {}     # organ -> (realpath, missions)
    for p in _paths_from_projects_json() + _paths_from_walk():
        rp = os.path.realpath(p)
        if rp in seen or not os.path.isfile(rp):
            continue
        seen.add(rp)
        try:
            reg = json.loads(Path(rp).read_text())
        except Exception:
            continue
        missions = reg.get("missions") or []
        if not missions:
            continue
        organ = organ_of(rp)
        if organ in by_organ and by_organ[organ][0] != rp:
            # collisione: disambigua entrambi con il segmento padre
            prev_rp, prev_missions = by_organ.pop(organ)
            print(f"  ⚠️  collisione organo '{organ}' — disambiguo per path "
                  f"({prev_rp} vs {rp})", file=sys.stderr)
            by_organ[_disambig(prev_rp)] = (prev_rp, prev_missions)
            by_organ[_disambig(rp)] = (rp, missions)
        else:
            by_organ[organ] = (rp, missions)
    return {organ: m for organ, (_, m) in by_organ.items()}


def _disambig(registry_path):
    """Chiave organo a 2 segmenti: <parent>/<project-dir> (anti-collisione)."""
    root = _project_root(registry_path)
    return os.path.basename(os.path.dirname(root)) + "/" + os.path.basename(root)


def normalize_mission(m):
    """Mappa entrambi gli schemi a un canonico. Ritorna None se non è una
    missione completata-con-id (da saltare).

    legacy-IT (EGI-DOC):  mission_id / stato==completed / titolo /
                          data_apertura / data_chiusura / tipo_missione /
                          organi_coinvolti / cross_organo / files_modified /
                          doc_sync_executed / stats{}
    engine-EN (os3-matrix engine): id / status==closed / title /
                          date_open / date_close / trigger_matrix  (no stats)
    """
    mid = m.get("mission_id") or m.get("id")
    completed = (m.get("stato") == "completed") or (m.get("status") == "closed")
    if not mid or not completed:
        return None

    title = m.get("titolo") or m.get("title") or mid
    stats = m.get("stats") or {}
    return {
        "id": mid,
        "title": title,
        "status": "completed",  # canonico (closed engine ≡ completed)
        "date_opened": m.get("data_apertura") or m.get("date_open"),
        "date_closed": m.get("data_chiusura") or m.get("date_close"),
        "mission_type": m.get("tipo_missione") or m.get("type") or "feature",
        "organs": m.get("organi_coinvolti") or m.get("organs") or [],
        "cross_organ": bool(m.get("cross_organo") or m.get("cross_organ") or False),
        "files_modified": m.get("files_modified") or [],
        "doc_sync_executed": bool(m.get("doc_sync_executed", False)),
        # stats: ricche solo per i registry già enrichati (EGI-DOC). Altrove 0
        # finché non gira l'enrich per-organo (follow-up M-220 fase 2).
        "stats": stats,
        "has_git_stats": bool(stats),
    }
