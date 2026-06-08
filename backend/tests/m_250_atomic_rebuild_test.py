"""
@purpose Test M-250: il rebuild del serving deve essere ATOMICO. Con DB stale +
         richieste concorrenti, prima il DROP+CREATE non-atomico esponeva un DB a
         meta ricostruzione (mission=0) -> dashboard rotta. Verifica che durante
         un rebuild un lettore concorrente non veda MAI 0 missioni se ce ne sono.
"""
import os, sys, sqlite3, threading, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aggregate_to_sqlite as agg


def test_rebuild_is_atomic(tmp_path):
    db = str(tmp_path / "s.db")
    agg.aggregate(db)  # primo build completo
    base = sqlite3.connect(db).execute("SELECT COUNT(*) FROM missions").fetchone()[0]
    assert base > 0, "fixture senza missioni"

    seen_zero = []
    stop = threading.Event()

    def reader():
        while not stop.is_set():
            try:
                n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM missions").fetchone()[0]
                if n == 0:
                    seen_zero.append(1)
            except sqlite3.OperationalError:
                pass  # 'no such table' durante un DROP non-atomico = fallimento
            except Exception:
                seen_zero.append(1)

    t = threading.Thread(target=reader); t.start()
    for _ in range(3):
        agg.aggregate(db)  # rebuild ripetuti mentre il reader legge
    stop.set(); t.join()
    assert not seen_zero, f"lettore concorrente ha visto DB vuoto/rotto {len(seen_zero)} volte (rebuild non atomico)"
