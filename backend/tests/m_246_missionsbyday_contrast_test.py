"""
@purpose Test red M-246: la prima colonna 'Giorno' della tabella MissionsByDay
         deve avere testo leggibile. Bug: sfondo sticky '#1a1a1a' (scuro) senza
         color esplicito -> testo scuro su scuro = invisibile. Il guard verifica
         che lo stile sticky NON usi piu lo sfondo scuro e dichiari un color.
"""
import os, re
COMP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "..", "frontend", "src", "components", "MissionsByDay.jsx")


def _stick_line():
    src = open(COMP, encoding="utf-8").read()
    m = re.search(r"const stick = \{[^}]*\}", src)
    assert m, "definizione di `stick` non trovata"
    return m.group(0)


def test_stick_has_explicit_color():
    assert "color:" in _stick_line(), "la colonna sticky non dichiara un color -> rischio invisibile"


def test_stick_not_dark_background():
    assert "#1a1a1a" not in _stick_line(), "sfondo sticky scuro #1a1a1a: testo invisibile su card chiara"
