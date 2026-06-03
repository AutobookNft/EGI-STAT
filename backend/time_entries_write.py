"""
time_entries_write.py — Append validato + atomico di una voce ore manuale — M-237

@package  EGI-STAT/backend (Oracode-STAT)
@author   Padmin D. Curtis (CTO-AI) for Fabio Cherici (CEO)
@version  1.0.0 (Oracode Nexus — Sistema Statistiche, asse ORE)
@date     2026-06-03
@purpose  Lato-scrittura dell'asse ORE (M-234 era sola lettura). Il modale
          "Aggiungi tempo" della dashboard POSTa una voce; questo modulo la
          VALIDA (Sicurezza Proattiva, Pilastro 6 + REGOLA ZERO: niente
          deduzioni di project/path) e la appende in modo ATOMICO al
          TIME_ENTRIES.json dell'ISTANZA del progetto. Il project deve essere
          WHITELISTED (solo nomi presenti in ~/oracode-engine/projects.json):
          questo risolve il path dell'istanza dalla fonte canonica e chiude
          ogni path traversal. Scrittura tmp+os.replace (atomica, no shell,
          niente injection: json.dump, mai os.system/string interpolation).
"""
import os
import re
import json
import tempfile
from pathlib import Path

import ecosystem  # _descriptors_from_projects_json — fonte canonica whitelist
from datetime import date as _date  # M-237 audit P2: validazione data reale

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class TimeEntryError(ValueError):
    """Validazione fallita -> il chiamante traduce in HTTP 400 (UEM-first lato API)."""


def _known_projects():
    """{input_accettato: instance_root} dai SOLI descrittori di projects.json.

    Whitelist canonica (M-237): un project non presente qui NON e scrivibile.
    Dedup per realpath (FlorenceEGI compare 2 volte in projects.json). Le chiavi
    accettate sono: il campo 'project' del descrittore (fallback basename) E —
    M-OS3-060 — il canonical_name e ogni alias dichiarato. Così un alias e un
    input valido (l'anti-traversal resta: solo chiavi note), ma in scrittura il
    project memorizzato e SEMPRE il canonical (vedi validate_payload).
    """
    out = {}
    seen = set()
    for desc, _path in ecosystem._descriptors_from_projects_json():
        root = desc.get("instance_root")
        if not root:
            continue
        rp = os.path.realpath(root)
        if rp in seen:
            continue
        seen.add(rp)
        names = {desc.get("project") or os.path.basename(rp)}
        cn = desc.get("canonical_name")
        if cn:
            names.add(cn)
        for a in desc.get("aliases") or []:
            names.add(a)
        for name in names:
            if name:
                out[name] = rp
    return out


def validate_payload(payload):
    """Valida e normalizza il payload del POST. Solleva TimeEntryError se invalido.

    Ritorna (project_name, instance_root, entry_dict) pronto per l'append.
    Regole (P0-3 espliciti, niente default nascosti):
      - project: str non vuota, DEVE essere whitelisted (else 400, anti-traversal).
      - date:    str 'YYYY-MM-DD' (ISO date).
      - minutes: int > 0 (rifiuta 0, negativi, float, stringhe non-intere, bool).
      - description: str non vuota dopo strip.
    """
    if not isinstance(payload, dict):
        raise TimeEntryError("payload must be a JSON object")

    project = payload.get("project")
    if not isinstance(project, str) or not project.strip():
        raise TimeEntryError("project required")
    project = project.strip()

    known = _known_projects()
    if project not in known:
        # NON-FOUND != NOT-EXIST: qui e voluto — solo progetti noti sono scrivibili.
        raise TimeEntryError(f"unknown project: {project}")
    instance_root = known[project]
    # M-OS3-060: normalizza al canonical_name (un alias NON crea una nuova chiave).
    # Identità per chiavi non mappate (passthrough). L'anti-traversal e gia passato.
    project = ecosystem.canonical_of(project)

    date = payload.get("date")
    # Validazione data REALE (M-237 audit P2): non solo il formato (_DATE_RE escludeva già
    # forme non-YYYY-MM-DD) ma anche la VALIDITÀ del calendario — date impossibili come
    # 2026-13-99 sono rifiutate (data-quality: non devono entrare nelle aggregazioni ore).
    if not isinstance(date, str) or not _DATE_RE.match(date):
        raise TimeEntryError("date required (YYYY-MM-DD)")
    try:
        _date.fromisoformat(date)
    except ValueError:
        raise TimeEntryError("date non valida (giorno/mese inesistente)")

    minutes = payload.get("minutes")
    # bool e sottoclasse di int: escludila ESPLICITAMENTE (True/False non sono minuti).
    if isinstance(minutes, bool) or not isinstance(minutes, int):
        raise TimeEntryError("minutes must be an integer")
    if minutes <= 0:
        raise TimeEntryError("minutes must be > 0")

    description = payload.get("description")
    if not isinstance(description, str) or not description.strip():
        raise TimeEntryError("description required")
    description = description.strip()

    entry = {
        "ledger_mission": f"M-LEDGER-{project.upper()}",
        "project": project,
        "date": date,
        "source": "manual",
        "description": description,
        "minutes": minutes,
    }
    return project, instance_root, entry


def append_entry(instance_root, entry):
    """Append ATOMICO di `entry` al TIME_ENTRIES.json dell'istanza.

    Read-modify-write su file temporaneo nella STESSA dir + os.replace (rename
    atomico same-filesystem): un lettore concorrente (aggregate) vede sempre il
    file vecchio-completo o il nuovo-completo, mai uno parziale. Crea
    docs/missions/ e il file (schema {entries:[]}) se assenti. Nessuna shell,
    nessuna interpolazione: solo json.load/json.dump. Ritorna il path scritto.
    """
    te_dir = Path(instance_root) / "docs" / "missions"
    te_dir.mkdir(parents=True, exist_ok=True)
    te_path = te_dir / "TIME_ENTRIES.json"

    if te_path.is_file():
        try:
            data = json.loads(te_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise TimeEntryError(f"TIME_ENTRIES.json illeggibile: {exc}")
        if not isinstance(data, dict):
            data = {"entries": []}
    else:
        data = {"entries": []}

    entries = data.get("entries")
    if not isinstance(entries, list):
        entries = []
    entries.append(entry)
    data["entries"] = entries

    # tmp nella stessa dir -> os.replace e atomico (stesso filesystem).
    fd, tmp_name = tempfile.mkstemp(dir=str(te_dir), prefix=".time_entries.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, str(te_path))
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise
    return str(te_path)
