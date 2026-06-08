"""
@purpose Test M-249: le risposte API /api devono avere Cache-Control no-store,
         altrimenti il browser ricicla stat vecchie e la dashboard sembra rotta.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api


def test_api_responses_no_store():
    c = api.app.test_client()
    r = c.get("/api/v2/stats/weekly?limit=1")
    cc = r.headers.get("Cache-Control", "")
    assert "no-store" in cc, f"Cache-Control manca no-store: {cc!r}"
