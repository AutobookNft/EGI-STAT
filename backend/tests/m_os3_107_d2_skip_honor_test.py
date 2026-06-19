"""
@package  EGI-STAT/backend/tests
@author   Padmin D. Curtis (CTO OS3) for Fabio Cherici (CEO)
@version  1.0.0 (M-OS3-107 D2)
@date     2026-06-19
@purpose  Test RED-first del controllo D2 (skip firmato). Verifica l'INVARIANTE
          FAIL-SAFE: una stat si spegne SOLO con counted=false + skip firmato e
          valido; in ogni altro caso (assenza/malformazione/skip incompleto/
          scadenza auto-revoca) il repo resta CONTATO. È il cardine della
          mission "statistiche a prova di falla": il bug da impedire è lo
          spegnimento SILENZIOSO di un organo. Honor unico in ecosystem.is_counted,
          consumato da aggregatore (produzione) e ingestion.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ecosystem

TODAY = "2026-06-19"


# ── 1. INVARIANTE FAIL-SAFE — assenza / malformazione → CONTATO (rischio #1 CEO) ──
def test_no_stats_block_is_counted():
    assert ecosystem.is_counted({"project": "X"}, TODAY) is True


def test_stats_without_counted_is_counted():
    assert ecosystem.is_counted({"stats": {}}, TODAY) is True


def test_stats_malformed_not_dict_is_counted():
    assert ecosystem.is_counted({"stats": "true"}, TODAY) is True
    assert ecosystem.is_counted({"stats": ["x"]}, TODAY) is True
    assert ecosystem.is_counted({"stats": None}, TODAY) is True


def test_counted_true_explicit_is_counted():
    assert ecosystem.is_counted({"stats": {"counted": True}}, TODAY) is True


# ── 2. SKIP FIRMATO VALIDO permanent → NON contato ──
def test_signed_permanent_skip_is_not_counted():
    d = {"stats": {"counted": False, "skip": {
        "scope": "permanent",
        "reason": "organo doc-only, nessun commit di prodotto",
        "approved_by": "CEO",
        "approved_date": "2026-06-19",
        "mission": "M-OS3-107",
    }}}
    assert ecosystem.is_counted(d, TODAY) is False


# ── 3. SKIP scope=until — auto-revoca alla scadenza ──
def _until_skip(until):
    return {"stats": {"counted": False, "skip": {
        "scope": "until", "until": until,
        "reason": "freeze temporaneo", "approved_by": "CEO",
        "approved_date": "2026-06-01", "mission": "M-OS3-107",
    }}}


def test_until_future_is_not_counted():
    assert ecosystem.is_counted(_until_skip("2026-12-31"), TODAY) is False


def test_until_today_still_not_counted():
    # until == today: ultimo giorno valido, ancora skippato
    assert ecosystem.is_counted(_until_skip(TODAY), TODAY) is False


def test_until_past_auto_revokes_to_counted():
    # SCADUTO → torna CONTATO automaticamente, nessun intervento manuale
    assert ecosystem.is_counted(_until_skip("2026-06-18"), TODAY) is True


def test_until_scope_without_until_date_is_counted():
    # scope=until ma manca 'until' → skip incompleto → fail-safe CONTATO
    d = {"stats": {"counted": False, "skip": {
        "scope": "until", "reason": "x", "approved_by": "CEO",
        "approved_date": "2026-06-01", "mission": "M-OS3-107",
    }}}
    assert ecosystem.is_counted(d, TODAY) is True


# ── 4. SKIP INCOMPLETO / NON FIRMATO → fail-safe CONTATO ──
def test_counted_false_without_skip_is_counted():
    assert ecosystem.is_counted({"stats": {"counted": False}}, TODAY) is True


def test_skip_missing_approved_by_is_counted():
    d = {"stats": {"counted": False, "skip": {
        "scope": "permanent", "reason": "x", "mission": "M-OS3-107",
        "approved_date": "2026-06-19",
    }}}
    assert ecosystem.is_counted(d, TODAY) is True


def test_skip_missing_mission_is_counted():
    d = {"stats": {"counted": False, "skip": {
        "scope": "permanent", "reason": "x", "approved_by": "CEO",
        "approved_date": "2026-06-19",
    }}}
    assert ecosystem.is_counted(d, TODAY) is True


def test_skip_unknown_scope_is_counted():
    d = {"stats": {"counted": False, "skip": {
        "scope": "forever", "reason": "x", "approved_by": "CEO",
        "approved_date": "2026-06-19", "mission": "M-OS3-107",
    }}}
    assert ecosystem.is_counted(d, TODAY) is True


def test_skip_not_dict_is_counted():
    assert ecosystem.is_counted({"stats": {"counted": False, "skip": "yes"}}, TODAY) is True


# ── 5. RETRO-COMPAT — i 22 descrittori reali (nessun blocco stats) restano CONTATI ──
def test_all_real_descriptors_currently_counted():
    descs = ecosystem._descriptors_from_projects_json()
    assert descs, "nessun descrittore trovato in projects.json"
    not_counted = [p for d, p in descs if not ecosystem.is_counted(d, TODAY)]
    assert not not_counted, f"descrittori reali spenti senza skip firmato: {not_counted}"
