"""
@package  EGI-STAT/backend/tests
@author   Padmin D. Curtis (CTO OS3) for Fabio Cherici (CEO)
@version  1.0.0 (M-OS3-107 D6)
@date     2026-06-19
@purpose  Test RED-first del controllo D6: il gate coverage_scan --check deve
          USCIRE ≠0 quando esistono index_pollution (residui /tmp o root
          inesistenti) o orphan_descriptor (repo con descrittore fuori da
          projects.json). Decisione CEO: orphan = BLOCK (non tollerato), non
          solo classificato. Test sulla funzione pura check(data) con dati
          sintetici (non accoppiato al projects.json live, mutabile).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import coverage_scan


def _data(pollution=None, orphan=None):
    return {
        "counts": {"instrumented": 1, "orphan_descriptor": len(orphan or []),
                   "uninstrumented": 0, "index_pollution": len(pollution or [])},
        "instrumented": ["EGI"],
        "orphan_descriptor": orphan or [],
        "uninstrumented": [],
        "index_pollution": pollution or [],
    }


def test_clean_passes_exit_zero():
    code, lines = coverage_scan.check(_data())
    assert code == 0


def test_pollution_blocks_exit_nonzero():
    code, lines = coverage_scan.check(_data(
        pollution=[{"name": "TESTPROJ", "root": "/tmp/x/proj", "reason": "root sotto /tmp"}]))
    assert code != 0
    assert any("TESTPROJ" in l or "/tmp/x/proj" in l for l in lines)


def test_orphan_blocks_exit_nonzero():
    code, lines = coverage_scan.check(_data(orphan=["nexus-cockpit"]))
    assert code != 0
    assert any("nexus-cockpit" in l for l in lines)


def test_both_block_and_report_each():
    code, lines = coverage_scan.check(_data(
        pollution=[{"name": "TESTPROJ", "root": "/tmp/x/proj", "reason": "root sotto /tmp"}],
        orphan=["nexus-cockpit"]))
    assert code != 0
    blob = "\n".join(lines)
    assert "TESTPROJ" in blob and "nexus-cockpit" in blob


def test_check_argv_clean_returns_zero(monkeypatch):
    # main(['--check']) usa scan() reale: dopo la remediation (TESTPROJ rimossi +
    # nexus-cockpit registrato) lo stato live deve essere PULITO → exit 0.
    monkeypatch.setattr(coverage_scan, "scan", lambda: _data())
    assert coverage_scan.main(["--check"]) == 0


def test_check_argv_dirty_returns_nonzero(monkeypatch):
    monkeypatch.setattr(coverage_scan, "scan", lambda: _data(orphan=["x"]))
    assert coverage_scan.main(["--check"]) != 0
