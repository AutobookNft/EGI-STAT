#!/usr/bin/env python3
"""
@package  EGI-STAT/backend
@author   Padmin D. Curtis (Supervisor-CTO, AI Partner OS3.0) for Fabio Cherici
@version  1.0.0 (FlorenceEGI — EGI-STAT, M-FUC-057)
@date     2026-06-16
@purpose  Copertura repo (ship-with-push): scansiona i repo git sotto la working-root
  (DOVE i repo VIVONO: il laptop), li confronta con l'indice di discovery
  ~/oracode-engine/projects.json + i descrittori .oracode/project.json, e produce
  coverage.json. Spedito al cockpit dal push (push-stats-nexus.sh). La scansione NON
  può girare sul server (i repo laptop-only non ci sono) → si calcola alla fonte.

  Classi:
   - instrumented:        repo git CON .oracode/project.json E presente in projects.json
   - orphan_descriptor:   repo git CON descrittore ma NON in projects.json (entra alla
                          prossima open via registerProject — finché no, invisibile alle stat)
   - uninstrumented:      repo git SENZA .oracode/project.json (fuori dalle stat del tutto)
   - index_pollution:     voci di projects.json con root inesistente o sotto /tmp (residui test)
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone

BASE = os.environ.get("COVERAGE_SCAN_ROOT", os.path.expanduser("~"))
PROJECTS_JSON = os.path.expanduser("~/oracode-engine/projects.json")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "coverage.json")


def _load_index_roots() -> dict[str, str]:
    """root(realpath) -> name dalle voci di projects.json."""
    try:
        idx = json.loads(open(PROJECTS_JSON, encoding="utf-8").read())
    except Exception:
        return {}
    out = {}
    for p in idx.get("projects") or []:
        root = p.get("root")
        if root:
            out[os.path.realpath(root)] = p.get("name") or os.path.basename(root)
    return out


def scan() -> dict:
    index_roots = _load_index_roots()
    instrumented, orphan_descriptor, uninstrumented = [], [], []

    for entry in sorted(os.listdir(BASE)):
        if entry.startswith("."):
            continue  # salta dir nascoste (.nvm, .cache, …) — non sono organi
        d = os.path.join(BASE, entry)
        if not os.path.isdir(d) or not os.path.isdir(os.path.join(d, ".git")):
            continue
        has_desc = os.path.isfile(os.path.join(d, ".oracode", "project.json"))
        in_index = os.path.realpath(d) in index_roots
        if has_desc and in_index:
            instrumented.append(entry)
        elif has_desc and not in_index:
            orphan_descriptor.append(entry)
        else:
            uninstrumented.append(entry)

    # pollution: voci in projects.json con root assente o sotto /tmp
    pollution = []
    for root, name in index_roots.items():
        if root.startswith("/tmp") or not os.path.isdir(root):
            pollution.append({"name": name, "root": root,
                              "reason": "root sotto /tmp" if root.startswith("/tmp") else "root inesistente"})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_root": BASE,
        "counts": {
            "instrumented": len(instrumented),
            "orphan_descriptor": len(orphan_descriptor),
            "uninstrumented": len(uninstrumented),
            "index_pollution": len(pollution),
        },
        "instrumented": instrumented,
        "orphan_descriptor": orphan_descriptor,
        "uninstrumented": uninstrumented,
        "index_pollution": pollution,
    }


def check(data: dict) -> tuple[int, list[str]]:
    """Gate D6 (M-OS3-107): BLOCK se la copertura ha falle che nascondono repo
    alle stat. exit 2 quando esiste index_pollution (residui /tmp o root
    inesistenti) o orphan_descriptor (repo con descrittore fuori da
    projects.json → invisibile alle stat finché non si apre una mission).
    Decisione CEO 2026-06-19: orphan = BLOCK, non solo classificato. exit 0 solo
    se entrambe le classi sono vuote."""
    lines: list[str] = []
    for p in data.get("index_pollution") or []:
        lines.append(f"  index_pollution: {p.get('name')} — {p.get('root')} ({p.get('reason')})")
    for o in data.get("orphan_descriptor") or []:
        lines.append(f"  orphan_descriptor: {o} (descrittore presente ma fuori da projects.json)")
    return (2 if lines else 0), lines


def main(argv: list[str]) -> int:
    data = scan()
    if "--check" in argv:
        code, lines = check(data)
        if code:
            print("✗ coverage --check: FALLE di copertura (repo nascosti alle stat):",
                  file=sys.stderr)
            for l in lines:
                print(l, file=sys.stderr)
        else:
            print("✓ coverage --check: nessuna falla (0 pollution, 0 orphan).",
                  file=sys.stderr)
        return code
    if "--print" in argv:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, OUT)
    print(f"coverage.json scritto: {OUT} "
          f"(uninstrumented={data['counts']['uninstrumented']}, "
          f"orphan={data['counts']['orphan_descriptor']}, "
          f"pollution={data['counts']['index_pollution']})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
