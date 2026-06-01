"""
enrich_by_message.py — Git-stats per missione via grep dell'id nei commit — M-221

@package  EGI-STAT/backend
@author   Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version  1.0.0 (FlorenceEGI — EGI-STAT)
@date     2026-06-01
@purpose  Le missioni degli organi non enrichati (os3-matrix, LeVespe, oracode,
          …) non hanno il blocco `stats` nel registry → PI=0 dopo M-220. Qui le
          enrichiamo attribuendo i commit per **id-missione** (globalmente unico)
          cercato nei messaggi di TUTTI i repo git dell'ecosistema. Un pass
          `git log` per repo (O(repi), non O(missioni×repi)); cross-repo: una
          missione può toccare più repo (es. M-OS3-047 in os3-matrix + oracode).
"""
import os
import re
import sys
import subprocess
from collections import defaultdict

import ecosystem
# Helper condivisi con l'ingest (classify/peso/PI/moltiplicatore-tipo): import a
# livello modulo OK, ingest_missions importa QUESTO modulo lazy → no circolare.
# MISSION_TYPE_MULTIPLIER è identico a quello di enrich_registry (path ricco).
from ingest_missions import (classify_file, parse_tag, TAG_WEIGHTS,
                             compute_productivity, MISSION_TYPE_MULTIPLIER)

def _build_id_re(known_ids):
    """Regex = alternation degli id REALI con word-boundary \\bID\\b. Match esatto
    come l'oracle (git --grep '\\bID\\b'); evita l'over-consumo greedy (es.
    'M-OS3-047-remediation' non deve mangiare l'attribuzione a M-OS3-047). Id più
    lunghi prima (M-094-SUPERVISOR before M-094)."""
    if not known_ids:
        return re.compile(r'(?!x)x')  # non matcha nulla
    alt = "|".join(re.escape(i) for i in sorted(known_ids, key=len, reverse=True))
    return re.compile(r'\b(' + alt + r')\b')


def _git_repos():
    """Tutti i repo git dell'ecosistema dove possono comparire id-missione:
    le dir-progetto dei registry (os3-matrix, oracode, *-DOC) + i repo di codice
    FlorenceEGI (REPO_TO_DIR dell'ingest). Solo quelli con .git."""
    from ingest_missions import REPO_TO_DIR
    roots = set()
    for p in ecosystem._paths_from_projects_json() + ecosystem._paths_from_walk():
        roots.add(ecosystem._project_root(os.path.realpath(p)))
    roots.update(REPO_TO_DIR.values())
    return sorted(r for r in roots if os.path.isdir(os.path.join(r, ".git")))


def _known_id_types():
    """{id: tipo_missione} per tutti gli id reali nei registry. L'autorità:
    attribuiamo solo a id reali (no falsi-positivi del regex). Il tipo serve al
    moltiplicatore PI (P1 audit M-221: PI confrontabile col path ricco)."""
    out = {}
    for missions in ecosystem.discover_registries().values():
        for m in missions:
            mid = m.get("mission_id") or m.get("id")
            if mid:
                out[mid] = m.get("tipo_missione") or m.get("type") or "feature"
    return out


def _scan_repo(repo, id_re, buckets):
    """Un pass git log --all --numstat. Per ogni commit: estrai gli id reali dal
    messaggio (id_re = alternation degli id noti), attribuisci righe/file a
    ciascuno. Dedup commit per hash."""
    cmd = ["git", "-C", repo, "log", "--all",
           "--pretty=format:COMMIT|%H|%s", "--numstat"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=180).stdout
    except Exception as e:
        # P3 audit M-221: non perdere l'attribuzione del repo in silenzio
        print(f"  ⚠️  enrich-by-id: git log fallito su {repo}: {e}", file=sys.stderr)
        return
    cur_ids, cur_hash = [], None
    for line in out.split("\n"):
        if line.startswith("COMMIT|"):
            parts = line.split("|", 2)
            cur_hash = parts[1].strip() if len(parts) > 1 else None
            msg = parts[2] if len(parts) > 2 else ""
            cur_ids = set(id_re.findall(msg))
            if cur_ids and cur_hash:
                tag = parse_tag(msg)
                for mid in cur_ids:
                    b = buckets[mid]
                    if cur_hash not in b["commits"]:
                        b["commits"].add(cur_hash)
                        b["tags"][tag] = b["tags"].get(tag, 0) + 1
            continue
        if not cur_ids or not cur_hash:
            continue
        cols = line.split("\t")
        if len(cols) >= 3 and classify_file(cols[2]) is not None:
            added = int(cols[0]) if cols[0].isdigit() else 0
            deleted = int(cols[1]) if cols[1].isdigit() else 0
            for mid in cur_ids:
                b = buckets[mid]
                b["added"] += added
                b["deleted"] += deleted
                if cols[2]:
                    b["files"].add(cols[2])


def collect_mission_git_stats():
    """Ritorna {mission_id: stats-dict} pronto per mission_stats. Attribuzione
    per id su tutti i repo. PI calcolato con la stessa formula dell'ingest."""
    id_types = _known_id_types()
    id_re = _build_id_re(id_types.keys())
    buckets = defaultdict(lambda: {"commits": set(), "added": 0, "deleted": 0,
                                   "files": set(), "tags": {}})
    for repo in _git_repos():
        _scan_repo(repo, id_re, buckets)

    out = {}
    for mid, b in buckets.items():
        total = len(b["commits"])
        if total == 0:
            continue
        added, deleted = b["added"], b["deleted"]
        net, touched = added - deleted, added + deleted
        files = len(b["files"])
        weighted = sum(c * TAG_WEIGHTS.get(t, 0.5) for t, c in b["tags"].items())
        # P1 audit M-221: moltiplicatore per tipo-missione (come il path ricco),
        # non 1.0 fisso → PI confrontabile cross-organo.
        mult = MISSION_TYPE_MULTIPLIER.get(id_types.get(mid, "feature"), 1.0)
        pi, cl = compute_productivity(total, weighted, net, touched, files, mult)
        out[mid] = {
            "total_commits": total, "weighted_commits": round(weighted, 2),
            "lines_added": added, "lines_deleted": deleted, "lines_net": net,
            "lines_touched": touched, "files_touched": files,
            "cognitive_load": cl, "productivity_index": pi,
            "tags_breakdown": b["tags"],
        }
    return out
