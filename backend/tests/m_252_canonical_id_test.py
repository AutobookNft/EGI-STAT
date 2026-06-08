"""
@purpose Test M-252 anti-drift: il pattern mission-ID canonico (ecosystem.MISSION_ID_RE)
         deve matchare OGNI id mission reale presente nei registry (tutti i prefissi:
         M-, M-OS3-, M-EGI-, M-FUC-, M-DD-, M-NEXUS-, M-CAPASSO-, M-FORTINO-, ...).
         Se compare un prefisso nuovo non coperto, QUESTO test si rompe -> la regex
         parziale fatta a mano non puo' piu' passare inosservata.
"""
import os, sys, re, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ecosystem, aggregate_to_sqlite as agg


def _all_real_ids():
    ids = set()
    for rp, _ in agg.discover_registries_from_index():
        try: d = json.load(open(rp, encoding="utf-8"))
        except Exception: continue
        for m in d.get("missions") or []:
            i = m.get("id") or m.get("mission_id")
            if i: ids.add(i)
    return ids


def test_canonical_matches_every_real_numbered_mission():
    ids = _all_real_ids()
    assert ids, "nessun id trovato nei registry"
    # un id 'mission' ha un NUMERO finale (i ledger perpetui M-LEDGER-X no)
    numbered = [i for i in ids if re.search(r"\d$", i)]
    missed = [i for i in numbered if not ecosystem.MISSION_ID_RE.search(i)]
    assert not missed, f"pattern canonico NON copre questi id reali: {missed}"


def test_cites_mission_helper():
    assert ecosystem.cites_mission("[DOC] M-FUC-014 — bla")
    assert ecosystem.cites_mission("[FIX] M-249 x") and ecosystem.cites_mission("M-OS3-104")
    assert not ecosystem.cites_mission("[DOC] Handoff senza mission")
