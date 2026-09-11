"""The pre-registration must not rot.

`make_prereg.py` reads the constants out of the modules, so the document cannot
disagree with the code as long as it is regenerated. This checks the file on
disk is the file the current code produces, and that the numbers a reader would
act on actually appear in it.
"""
import pathlib
import subprocess
import sys

import pytest
from sim import pipeline as P, density as D, generators as G

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "PREREGISTRO_v1.md"


def test_document_is_regenerated_from_the_code():
    before = DOC.read_text(encoding="utf-8")
    r = subprocess.run([sys.executable, "make_prereg.py"], cwd=ROOT,
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr
    assert DOC.read_text(encoding="utf-8") == before, (
        "PREREGISTRO_v1.md is stale — run `python make_prereg.py`")


@pytest.mark.parametrize("value", [P.TOL, P.NULL_Q, P.N_SURR, P.MIN_SEG, P.MIN_REPLICATES,
                                   P.S_QFRAC, D.H1_INSTAB, D.H1_BETWEEN_WITHIN,
                                   D.H3_TOL, D.H4_MARGIN])
def test_every_declared_tolerance_appears(value):
    assert str(value) in DOC.read_text(encoding="utf-8"), value


def test_it_names_the_boundedness_condition_of_every_node():
    text = DOC.read_text(encoding="utf-8")
    for node in G.NODES:
        assert f"| `{node}` |" in text, node
    assert "rho(A - alpha e0 e0')" in text          # the M1+N condition, in full
    assert "companion" in text                      # the M1+M one


def test_it_says_what_the_design_cannot_decide():
    text = DOC.read_text(encoding="utf-8")
    assert D.UNIDENTIFIABLE in text
    assert "não roda" in text or "nao roda" in text  # the grid is conditional
