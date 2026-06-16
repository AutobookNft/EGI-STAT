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

# ── Tassonomia status SINGLE-SOURCE (M-OS3-090) ────────────────────────────────
# Verità unica degli status mission: oracode/templates/MISSION_STATUS_TAXONOMY.json.
# LOUD-ON-UNKNOWN: uno status engine non mappato NON viene scartato in silenzio —
# viene registrato in UNKNOWN_STATUSES + segnalato a stderr, così la regressione
# (nuovo status non mappato) si fa SENTIRE invece di sparire dalle stat.
STATUS_TAXONOMY_PATH = "/home/fabio/oracode/templates/MISSION_STATUS_TAXONOMY.json"
UNKNOWN_STATUSES = set()


def _load_status_taxonomy():
    try:
        return json.loads(Path(STATUS_TAXONOMY_PATH).read_text()).get("statuses", {})
    except Exception as e:
        sys.stderr.write(f"⚠⚠ M-OS3-090: MISSION_STATUS_TAXONOMY.json illeggibile ({e}) — fallback minimo\n")
        return {"closed": {"counts_as_production": True},
                "closed_with_debt": {"counts_as_production": True},
                "completed": {"counts_as_production": True}}


STATUS_TAXONOMY = _load_status_taxonomy()


def status_counts_as_production(raw_status):
    """True se lo status conta come produzione. Loud-on-unknown: status non in
    tassonomia → registrato in UNKNOWN_STATUSES + stderr, ritorna False ma MAI in silenzio."""
    if raw_status in STATUS_TAXONOMY:
        return bool(STATUS_TAXONOMY[raw_status].get("counts_as_production"))
    UNKNOWN_STATUSES.add(raw_status)
    sys.stderr.write(
        f"⚠⚠ STATUS SCONOSCIUTO '{raw_status}' — assente da MISSION_STATUS_TAXONOMY.json. "
        f"Mission NON conteggiata finché non lo mappi. AGGIORNA la tassonomia! (M-OS3-090 loud-on-unknown)\n"
    )
    return False


def _is_delivered(m):
    """Regola H3 UNICA condivisa (M-248, decisione CEO 2026-06-08): una mission è
    "delivered" (lavoro consegnato, conta come produzione) sse ha una data di
    chiusura VALIDA — non None, non vuota, non 'pending'. Accetta entrambi gli
    schemi: legacy-IT 'data_chiusura' e engine-EN 'date_close'.

    M-FUC-054 (R1): estratta come funzione condivisa così che `normalize_mission`
    (path prod) e `normalize_open_mission` (feature additiva) NON possano divergere
    sulla definizione di delivered. Refactor neutro: stessa logica già inline in
    normalize_mission, qui resa single-source."""
    date_close_raw = m.get("data_chiusura") or m.get("date_close")
    return date_close_raw not in (None, "", "pending")


def status_is_open(raw_status):
    """True sse lo status indica una mission IN CORSO (WIP): presente in
    STATUS_TAXONOMY con terminal==False AND counts_as_production==False, ESCLUSO
    'perpetual' (registro non chiudibile — non è WIP, decisione M-FUC-054).

    Loud-on-unknown coerente con status_counts_as_production: uno status non in
    tassonomia GRIDA su stderr e ritorna False (mai sparizione silenziosa, M-OS3-090)."""
    if raw_status == "perpetual":
        return False  # registro perpetuo: terminal=false ma NON è WIP — escluso esplicitamente
    if raw_status in STATUS_TAXONOMY:
        spec = STATUS_TAXONOMY[raw_status]
        return (not spec.get("terminal")) and (not spec.get("counts_as_production"))
    UNKNOWN_STATUSES.add(raw_status)
    sys.stderr.write(
        f"⚠⚠ STATUS SCONOSCIUTO '{raw_status}' — assente da MISSION_STATUS_TAXONOMY.json. "
        f"Mission NON classificata come in-corso finché non lo mappi. AGGIORNA la tassonomia! "
        f"(M-OS3-090 loud-on-unknown / M-FUC-054)\n"
    )
    return False


def normalize_open_mission(m):
    """Forma canonica MINIMA di una mission IN CORSO per il cockpit Nexus (M-FUC-054).

    Ritorna {id,title,raw_status,date_opened,mission_type} SOLO se:
      - la mission ha un id;
      - ha uno 'status' (campo engine-EN) con status_is_open(status) True;
      - NON è delivered (not _is_delivered(m)) — partizione mutuamente esclusiva
        con la tabella `missions` (anti-doppio-conteggio H3).
    Altrimenti None. I registry legacy-IT senza 'status' engine → None (coerente:
    non hanno lo status-engine che distingue draft/executing/auditing)."""
    mid = m.get("mission_id") or m.get("id")
    if not mid:
        return None
    status = m.get("status")
    if not status or not status_is_open(status):
        return None
    if _is_delivered(m):
        return None  # delivered → vive in `missions`, MAI in missions_open
    return {
        "id": mid,
        "title": m.get("titolo") or m.get("title") or mid,
        "raw_status": status,
        "date_opened": m.get("data_apertura") or m.get("date_open"),
        "mission_type": m.get("tipo_missione") or m.get("type") or "feature",
    }


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


def _descriptors_from_projects_json():
    """[(descriptor_dict, descriptor_path)] da projects.json — M-234.

    Gemello di _paths_from_projects_json() ma ritorna il descrittore COMPLETO
    (serve instance_root + repo_map_path + project per l'asse ORE, non solo
    registry_path). Stessa fonte canonica (~/oracode-engine/projects.json).
    """
    out = []
    try:
        pj = json.loads(Path(PROJECTS_JSON).read_text())
    except Exception:
        return out
    for proj in pj.get("projects", []):
        desc = proj.get("descriptor")
        if not desc or not os.path.isfile(desc):
            continue
        try:
            out.append((json.loads(Path(desc).read_text()), desc))
        except Exception:
            continue
    return out


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
    if not mid:
        return None
    # Engine-EN ('status'): passa per la tassonomia single-source → loud-on-unknown
    # (un nuovo status non mappato GRIDA, non sparisce). Legacy-IT ('stato'): vocabolario
    # frozen, conta solo 'completed' (nessun rumore sui legacy aperti).
    # H3 (M-248, regola "delivered", decisione CEO 2026-06-08): una mission con
    # data di chiusura VALIDA conta come prodotta anche se lo status è transitorio
    # (es. 'auditing' = audit di chiusura in corso). date_close valorizzato = lavoro
    # consegnato. La tassonomia resta SSOT del SIGNIFICATO degli status; qui si
    # decide solo l'inclusione nelle statistiche di produzione.
    delivered = _is_delivered(m)  # M-FUC-054 (R1): regola H3 single-source — refactor neutro
    status = m.get("status")
    if status:
        if not status_counts_as_production(status) and not delivered:
            return None
    elif m.get("stato") == "completed":
        pass  # legacy completata ≡ closed
    elif delivered:
        pass  # legacy senza stato ma con data chiusura valida ≡ delivered
    else:
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


# ── Identità canonica di progetto (M-OS3-060) ────────────────────────────────
# Stesso progetto = una sola chiave su entrambi gli assi statistici. I descrittori
# .oracode/project.json dichiarano canonical_name (= nome reale del repo GitHub, il
# leaf) + aliases[]; canonical_of() risolve OGNI alias al canonical_name, e per le
# chiavi non mappate è IDENTITÀ (passthrough). Così Capasso (folder) e pinocapasso
# (repo) collassano in un'unica chiave, senza doppio-conteggio.
_CANONICAL_MAP = None


def _build_canonical_map():
    """alias -> canonical_name dai descrittori di projects.json (M-OS3-060).

    Per ogni descrittore con canonical_name 'cn': map[cn]=cn; per ogni alias a in
    (desc.aliases or []): map[a]=cn. Descrittori senza canonical_name non mappano
    nulla (le loro chiavi restano identità via passthrough di canonical_of)."""
    out = {}
    for desc, _path in _descriptors_from_projects_json():
        cn = desc.get("canonical_name")
        if not cn:
            continue
        out[cn] = cn
        for a in desc.get("aliases") or []:
            out[a] = cn
    return out


def canonical_of(key):
    """Risolve una chiave (organo/progetto) al suo canonical_name.

    Identità (passthrough) per chiavi non mappate: EGI-DOC/os3-matrix/oracode e
    ogni chiave senza alias dichiarato restano invariate. Cache a livello modulo."""
    global _CANONICAL_MAP
    if _CANONICAL_MAP is None:
        _CANONICAL_MAP = _build_canonical_map()
    return _CANONICAL_MAP.get(key, key)


# ── M-252: pattern mission-ID CANONICO (single-source, anti-regex-parziale) ──
# Una mission-id è M- + zero o più segmenti prefisso (OS3, EGI, FUC, DD, NEXUS,
# CAPASSO, FORTINO, LEVESPE, DROP, ...) + un NUMERO finale. I ledger perpetui
# (M-LEDGER-CAPASSO, senza numero finale) NON sono mission e restano esclusi.
# CHIUNQUE deve classificare/contare le mission DEVE usare questo, mai una regex
# ad-hoc (il bug della regex parziale che mancava M-FUC- non si ripete).
import re as _re
MISSION_ID_RE = _re.compile(r"\bM-(?:[A-Za-z0-9]+-)*\d+[a-z]?\b")  # suffisso-lettera incluso (M-160a)


def cites_mission(text: str) -> bool:
    """True se il testo (es. messaggio di commit) cita un id mission canonico."""
    return bool(text and MISSION_ID_RE.search(text))
