"""
@purpose Test red M-243: il nuovo Indice di Produttivita (v3) deve essere
         THROUGHPUT-aware (somma del valore prodotto), non una media per-missione
         throughput-blind. Cattura l'incoerenza: settimana con 159 missioni e
         volume 4x deve avere PI piu alto di una settimana con 11 missioni.
         Importa la funzione che sara implementata in productivity_v3.py.
"""
import importlib
import pytest


def _load():
    return importlib.import_module("productivity_v3")


def test_module_exists():
    mod = _load()
    assert hasattr(mod, "weekly_productivity_index")


def test_throughput_monotonic():
    """Doppio del lavoro identico -> indice strettamente maggiore (non uguale)."""
    mod = _load()
    one = [{"weighted": 5.0, "lines_net": 200, "lines_touched": 400,
            "files": 5, "commits": 3, "mult": 1.0}]
    two = one * 2
    assert mod.weekly_productivity_index(two) > mod.weekly_productivity_index(one)
