"""
@package  EGI-STAT/backend/tests
@author   Padmin D. Curtis (dev-python OS3) for Fabio Cherici (CEO)
@version  1.0.0 (fix extless-shebang code classify)
@date     2026-07-08
@purpose  RED-first (P0-13): gli script eseguibili SENZA estensione (bin/mission,
          bin/deploy-hooks, ~118 nell'ecosistema) portano uno shebang, non
          un'estensione → la whitelist da sola li scartava dal conteggio codice e
          sparivano dalle "righe nette". Qui si verifica l'INVARIANTE: dato
          repo_dir+commit, classify_file legge il blob STORICO (git cat-file, mai
          il working tree — il file può essere stato cancellato/rinominato) e
          classifica "code" i file extension-less con shebang; None senza shebang;
          nessuna regressione su .py/.md; back-compat quando manca repo/commit;
          guard su blob assente (nessuna eccezione propagata). Ultima verifica:
          le 3 copie di classify_file/_shebang_is_code restano IDENTICHE
          (invariante anti-drift — il debito di unificazione è annotato, non qui).
"""
import ast
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import enrich_registry  # import-safe: nessun side-effect (DB) a load

classify_file = enrich_registry.classify_file

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPIES = ("ingest_missions.py", "rebuild_all_daily.py", "enrich_registry.py")


def _run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path):
    """Repo git reale con UN commit: così `git cat-file blob <commit>:<path>`
    legge blob veri. Il test non tocca il working tree del progetto."""
    repo = tmp_path / "repo"
    (repo / "bin").mkdir(parents=True)
    # extension-less CON shebang → deve diventare "code" (il bug da correggere)
    (repo / "bin" / "mission").write_text("#!/usr/bin/env bash\necho hi\n")
    # extension-less SENZA shebang → resta None (comportamento invariato)
    (repo / "bin" / "data").write_text("just some data\nno shebang here\n")
    # .py → code (nessuna regressione whitelist)
    (repo / "app.py").write_text("print('x')\n")
    # .md → doc (nessuna regressione whitelist)
    (repo / "README.md").write_text("# title\n")
    _run(["git", "init"], repo)
    _run(["git", "config", "user.email", "t@t.t"], repo)
    _run(["git", "config", "user.name", "t"], repo)
    _run(["git", "add", "-A"], repo)
    _run(["git", "commit", "-m", "init"], repo)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    return str(repo), commit


def test_extless_with_shebang_is_code(git_repo):
    repo, commit = git_repo
    assert classify_file("bin/mission", repo, commit) == "code"


def test_extless_without_shebang_is_none(git_repo):
    repo, commit = git_repo
    assert classify_file("bin/data", repo, commit) is None


def test_py_still_code_no_regression(git_repo):
    repo, commit = git_repo
    assert classify_file("app.py", repo, commit) == "code"


def test_md_still_doc_no_regression(git_repo):
    repo, commit = git_repo
    assert classify_file("README.md", repo, commit) == "doc"


def test_extless_without_repo_commit_is_none_backcompat():
    # call site senza commit+repo: comportamento invariato (None), niente crash
    assert classify_file("bin/mission") is None


def test_missing_blob_guarded_returns_none(git_repo):
    repo, commit = git_repo
    # path inesistente al commit → git cat-file fallisce → None, nessuna eccezione
    assert classify_file("bin/does-not-exist", repo, commit) is None


def test_always_skip_still_wins(git_repo):
    repo, commit = git_repo
    # vendor/ è ALWAYS_SKIP: skippato PRIMA della logica shebang, anche extless
    assert classify_file("vendor/bin/foo", repo, commit) is None


def _func_sources(path):
    """Estrae il testo sorgente di classify_file e _shebang_is_code da un file."""
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in (
            "classify_file", "_shebang_is_code",
        ):
            out[node.name] = ast.get_source_segment(src, node)
    return out


def test_three_copies_identical():
    # Invariante anti-drift: la fix va applicata IDENTICA alle 3 copie.
    ref = _func_sources(os.path.join(BACKEND_DIR, COPIES[0]))
    assert "classify_file" in ref
    assert "_shebang_is_code" in ref
    for fn in COPIES[1:]:
        other = _func_sources(os.path.join(BACKEND_DIR, fn))
        assert other == ref, f"{fn}: classify_file/_shebang_is_code divergono da {COPIES[0]}"
