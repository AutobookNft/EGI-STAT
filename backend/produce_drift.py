#!/usr/bin/env python3
"""
@package  EGI-STAT/backend
@author   Padmin D. Curtis (CTO-AI) for Fabio Cherici (CEO)
@version  1.0.0 (M-STAT-002)
@date     2026-06-25
@purpose  Producer di drift.json per il cockpit Nexus (ship-with-push, gemello di
          M-NEXUS-009). Esegue `ssot-index-check` SUL LAPTOP (dove indice e
          registry_path esistono con i path reali /home/fabio/...) e ne serializza
          l'esito; il file viene spedito al box dal push-stats-nexus.sh, e il
          cockpit lo SERVE soltanto (un check live sul box sarebbe falso: là manca
          projects.json e i path sono del laptop). Conservativo: check
          irraggiungibile → has_drift True (mai falso-verde, REGOLA ZERO).
"""
import json
import os
import subprocess  # nosec B404 — lista-argomenti, shell=False
import sys
from datetime import datetime, timezone

# Iniettabile nei test (monkeypatch).
_RUN = subprocess.run

CHECK_BIN = os.getenv(
    "ORACODE_SSOT_INDEX_CHECK_BIN", "/home/fabio/os3-matrix/bin/ssot-index-check"
)


def produce(out_path: str) -> dict:
    """Esegue ssot-index-check e scrive drift.json in out_path. Ritorna il dict."""
    try:
        p = _RUN([CHECK_BIN], capture_output=True, text=True, timeout=60)  # nosec B603
        rc = p.returncode
        raw = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
    except Exception as exc:  # noqa: BLE001 — check irraggiungibile
        rc = None
        raw = f"ssot-index-check non eseguibile: {exc}"
    data = {
        "has_drift": rc != 0,  # rc None (irraggiungibile) → True (conservativo)
        "returncode": rc,
        "raw": raw.strip(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "drift.json"
    )
    d = produce(out)
    print(f"drift.json: has_drift={d['has_drift']} rc={d['returncode']} -> {out}")
