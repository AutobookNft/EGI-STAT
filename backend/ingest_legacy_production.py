#!/usr/bin/env python3
"""ingest_legacy_production.py — Recupero PRODUZIONE STORICA legacy (M-OS3-081 / Asse storico).

Contesto: prima del sistema mission abbiamo prodotto un'enormità di codice. I commit sono la
fonte di verità (le stat mission usano già i commit). Questo script recupera la produzione NON
ancora attribuita a una mission, per repo→organo, e la scrive nella tabella `legacy_production`
dello SQLite serving → la dashboard può mostrare mission + legacy = produzione TOTALE.

Anti-doppio-conteggio: un commit già in `mission_commits` (già contato da una mission) NON viene
ricontato. Produzione legacy organo = tutti i suoi commit MENO quelli già-mission.
Invariante (quadratura): per ogni repo, commit_mission + commit_legacy == commit_git_totali.

NESSUN cambio di policy futura: da ora conta solo il lavoro dentro mission. Questo è SOLO il
record storico del pregresso. Read-only sui repo; scrive solo nello SQLite serving (EGI-STAT).

@author Padmin D. Curtis (CTO-AI) for Fabio Cherici (CEO)
"""
import os, subprocess, sqlite3, sys, glob

HOME = os.path.expanduser("~")
DB = os.path.join(os.path.dirname(__file__), "data", "stats.db")

# Rumore NON-produzione (non codice autorato): version manager, backup, snapshot.
EXCLUDE_SUBSTR = (".nvm", ".backup", "backup-2026", "EGI-HUB-HOME.backup")

def _all_commits(root):
    """Set di TUTTI i commit hash (tutte le branch). Identità precisa del repo."""
    out = subprocess.run(["git", "-C", root, "rev-list", "--all"],
                         capture_output=True, text=True, errors="ignore", timeout=180).stdout
    return frozenset(out.split())

# Soglia di contenimento: due repo sono lo STESSO (clone/worktree, da contare 1 volta) se l'intersezione
# copre ≥90% del più piccolo. I fork divergenti (TOSCA_BANDI da NATAN: condividono solo il seed) NON si fondono.
SAME_REPO_OVERLAP = 0.90

def discover_repos():
    """Repo unici. De-dup SOLO di cloni/worktree (set di commit ~coincidenti, overlap≥90% del più piccolo);
    i fork divergenti restano distinti (prodotti diversi). Rappresentante = più commit, tiebreak nome corto."""
    cand = []
    for gitdir in glob.glob(f"{HOME}/*/.git"):
        root = os.path.dirname(gitdir); name = os.path.basename(root)
        if name.startswith("."): continue
        if any(x in name for x in EXCLUDE_SUBSTR): continue
        s = _all_commits(root)
        if s: cand.append((name, root, s))
    # union-find per overlap
    groups = []  # list[list[(name,root,set)]]
    for item in cand:
        placed = False
        for g in groups:
            rep_set = g[0][2]
            inter = len(item[2] & rep_set)
            if inter and inter >= SAME_REPO_OVERLAP * min(len(item[2]), len(rep_set)):
                g.append(item); placed = True; break
        if not placed:
            groups.append([item])
    out = []
    for members in groups:
        rep = sorted(members, key=lambda m: (-len(m[2]), len(m[0]), m[0]))[0]
        dups = [m[0] for m in members if m[0] != rep[0]]
        if dups:
            print(f"  DEDUP: '{rep[0]}' = anche {dups} (clone/worktree, stessa storia)", file=sys.stderr)
        out.append((rep[0], rep[1]))
    return sorted(out)

def organ_of(repo_name):
    """Organo = nome repo canonicalizzato. Alias noti; 'miscellania-generica' per tooling sciolto."""
    alias = {"Capasso": "pinocapasso", "LeVespe-DOC": "le-vespe-cafe", "DeepDebug-DOC": "DeepDebug"}
    misc = {"book-to-skill", "Padmin_Analyzer", "Olafur"}
    if repo_name in misc:
        return "miscellania-generica"
    return alias.get(repo_name, repo_name)

# Codice NON autorato (dipendenze/generato/minified/lock) — ESCLUSO dal conteggio righe.
# Integrità: contiamo solo ciò che è stato scritto davvero, non node_modules/vendor committati.
VENDOR_SUBSTR = (
    "node_modules/", "/vendor/", "vendor/", "/dist/", "/build/", "/.next/", "/out/",
    "public/build/", "public/dist/", "public/hot", "/storage/framework/", "bootstrap/cache/",
    "/.nuxt/", "/coverage/", "/__pycache__/", "/.venv/", "/venv/", "/site-packages/",
    # M-OS3-081 (audit): dump IDE + dizionari + librerie terze in path non-standard
    ".history/", "/.history/", "cspell", "TCPDF-main/", "/TCPDF", "/tcpdf/",
)
VENDOR_SUFFIX = (
    ".lock", "-lock.json", "package-lock.json", ".min.js", ".min.css", ".map",
    ".bundle.js", ".chunk.js", "composer.lock", "yarn.lock", "pnpm-lock.yaml",
    "Gemfile.lock", "poetry.lock", "go.sum",
)

def _is_vendored(path):
    p = path.strip()
    # rinominati: "old => new" o "{a => b}/c" → valuta la parte dopo '=>' se presente
    if "=>" in p:
        p = p.split("=>")[-1].strip().rstrip("}").strip()
    if any(s in p for s in VENDOR_SUBSTR): return True
    if any(p.endswith(s) for s in VENDOR_SUFFIX): return True
    return False

def commit_numstat(root):
    """dict hash -> (added, deleted, files) per OGNI commit non-merge, SOLO file autorati
    (esclusi node_modules/vendor/dist/build/lock/minified). Righe vendored NON contate."""
    out = subprocess.run(
        ["git", "-C", root, "log", "--all", "--no-merges", "--numstat", "--pretty=format:@%H"],
        capture_output=True, text=True, errors="ignore", timeout=600).stdout
    res = {}; cur = None; a = d = f = 0
    for line in out.splitlines():
        if line.startswith("@"):
            if cur is not None: res[cur] = (a, d, f)
            cur = line[1:].strip(); a = d = f = 0
        elif line.strip():
            p = line.split("\t")
            if len(p) == 3 and not _is_vendored(p[2]):
                a += int(p[0]) if p[0].isdigit() else 0
                d += int(p[1]) if p[1].isdigit() else 0
                f += 1
    if cur is not None: res[cur] = (a, d, f)
    return res

def main():
    if not os.path.isfile(DB):
        print(f"✗ SQLite assente: {DB} — esegui prima aggregate_to_sqlite.py", file=sys.stderr); sys.exit(2)
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    mission_hashes = {r[0] for r in conn.execute("SELECT commit_hash FROM mission_commits")}
    print(f"commit già-mission (anti-doppio): {len(mission_hashes)}")

    conn.execute("DROP TABLE IF EXISTS legacy_production")
    conn.execute("""CREATE TABLE legacy_production (
        organ TEXT PRIMARY KEY, repos TEXT, commits INTEGER, lines_added INTEGER,
        lines_deleted INTEGER, lines_net INTEGER, files_touched INTEGER, computed_at TEXT)""")

    by_organ = {}; quad = []
    for name, root in discover_repos():
        ns = commit_numstat(root)
        total_c = len(ns); leg_c = leg_a = leg_d = leg_f = 0; miss_c = 0
        for h, (a, d, f) in ns.items():
            if h in mission_hashes: miss_c += 1
            else: leg_c += 1; leg_a += a; leg_d += d; leg_f += f
        org = organ_of(name)
        o = by_organ.setdefault(org, {"repos": set(), "c": 0, "a": 0, "d": 0, "f": 0})
        o["repos"].add(name); o["c"] += leg_c; o["a"] += leg_a; o["d"] += leg_d; o["f"] += leg_f
        quad.append((name, total_c, miss_c, leg_c))

    for org, o in sorted(by_organ.items()):
        conn.execute(
            "INSERT INTO legacy_production (organ,repos,commits,lines_added,lines_deleted,lines_net,files_touched,computed_at) VALUES (?,?,?,?,?,?,?,datetime('now'))",
            (org, ",".join(sorted(o["repos"])), o["c"], o["a"], o["d"], o["a"]-o["d"], o["f"]))
    conn.commit()

    print("\n=== PRODUZIONE LEGACY per organo (commit non-mission) ===")
    print(f"{'ORGANO':24} {'COMMIT':>7} {'RIGHE_ADD':>12} {'RIGHE_NET':>12}")
    ta = tc = 0
    for r in conn.execute("SELECT * FROM legacy_production ORDER BY lines_added DESC"):
        print(f"{r['organ']:24} {r['commits']:>7} {r['lines_added']:>12} {r['lines_net']:>12}")
        ta += r["lines_added"]; tc += r["commits"]
    print(f"{'TOTALE LEGACY':24} {tc:>7} {ta:>12}")

    print("\n=== QUADRATURA per repo (mission + legacy == git) ===")
    bad = 0
    for name, total, miss, leg in sorted(quad):
        ok = (miss + leg == total)
        if not ok: bad += 1
        if total > 100 or not ok:
            print(f"  {name:24} git={total:5} mission={miss:4} legacy={leg:5} {'OK' if ok else '✗MISMATCH'}")
    print(f"\nquadratura: {'TUTTO OK' if bad==0 else str(bad)+' MISMATCH'}")
    conn.close()

if __name__ == "__main__":
    main()
