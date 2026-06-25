"""
@package  EGI-STAT/backend/tests
@author   Padmin D. Curtis (CTO OS3) for Fabio Cherici (CEO)
@version  1.0.0 (M-STAT-002 — drift producer ship-with-push)
@date     2026-06-25
@purpose  Il producer genera drift.json (esito ssot-index-check sul laptop) che il
          cockpit serve (gemello M-NEXUS-009). Verifica: rc=0 → has_drift False;
          rc!=0 → has_drift True; check irraggiungibile (rc None) → has_drift True
          (conservativo, MAI falso-verde). Shape: has_drift/returncode/raw/generated_at.
"""
import json

import produce_drift


class _Fake:
    def __init__(self, rc, out="", err=""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


def test_clean_rc0(tmp_path, monkeypatch):
    monkeypatch.setattr(produce_drift, "_RUN", lambda *a, **k: _Fake(0, "OK: indice coerente"))
    out = tmp_path / "drift.json"
    d = produce_drift.produce(str(out))
    assert d["has_drift"] is False
    assert d["returncode"] == 0
    assert "coerente" in d["raw"]
    assert d["generated_at"]
    assert json.loads(out.read_text())["has_drift"] is False


def test_drift_rc2(tmp_path, monkeypatch):
    monkeypatch.setattr(produce_drift, "_RUN", lambda *a, **k: _Fake(2, "DRIFT: 1 incoerenze"))
    d = produce_drift.produce(str(tmp_path / "drift.json"))
    assert d["has_drift"] is True
    assert d["returncode"] == 2


def test_unreachable_is_conservative_drift(tmp_path, monkeypatch):
    def _boom(*a, **k):
        raise FileNotFoundError("ssot-index-check assente")
    monkeypatch.setattr(produce_drift, "_RUN", _boom)
    d = produce_drift.produce(str(tmp_path / "drift.json"))
    assert d["has_drift"] is True  # rc None → conservativo, mai falso-verde
    assert d["returncode"] is None
    assert "assente" in d["raw"]
