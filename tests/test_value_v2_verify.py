"""Verification tests for value v2 (P3-v2, addendum SS6).
Applies v2 measure to sizing data from commit b2362a4 and reproduces
the four rates from SS4 table. RED if any check fails.
"""
import json
import pytest
from pathlib import Path

import value.decide as D

SIZING_DIR = Path(__file__).resolve().parent.parent / "value" / "resultados"
CHUNKS = ["sizing_v2_R_200001_200075.json",
          "sizing_v2_R_200076_200150.json",
          "sizing_v2_R_200151_200225.json",
          "sizing_v2_R_200226_200300.json"]

# Expected rates from addendum SS4 table
EXPECTED = {
    ("R", 80): 0.527,
    ("R+", 80): 0.537,
    ("R", 160): 0.540,
    ("R+", 160): 0.527,
}
TOL = 0.001


@pytest.fixture(scope="module")
def all_rows():
    rows = []
    for name in CHUNKS:
        p = SIZING_DIR / name
        if not p.exists():
            pytest.skip(f"sizing data not found: {name}")
        rows.extend(json.loads(p.read_text(encoding="utf-8")))
    return rows


def _cell_rows(all_rows, world, T):
    return [r for r in all_rows if r["world"] == world and r["T"] == T]


def _v2_rate(rows):
    """V2 measure: R_infer_value_elected != R_infer_value_no_pause_elected."""
    n = len(rows)
    changed = sum(1 for r in rows
                  if r.get("R_infer_value_elected")
                  != r.get("R_infer_value_no_pause_elected"))
    return changed / n if n else 0.0


@pytest.mark.parametrize("world,T,expected", [
    ("R", 80, 0.527), ("R+", 80, 0.537),
    ("R", 160, 0.540), ("R+", 160, 0.527),
])
def test_v2_rate_reproduces(all_rows, world, T, expected):
    """Rate from v2 measure matches addendum SS4 within tolerance."""
    rows = _cell_rows(all_rows, world, T)
    assert len(rows) == 300, f"expected 300 rows for {world} T={T}"
    rate = _v2_rate(rows)
    assert abs(rate - expected) <= TOL, (
        f"{world} T={T}: got {rate:.4f}, expected {expected:.3f} "
        f"(diff {abs(rate - expected):.4f} > {TOL})")


@pytest.mark.parametrize("world,T,expected", [
    ("R", 80, 0.527), ("R+", 80, 0.537),
    ("R", 160, 0.540), ("R+", 160, 0.527),
])
def test_p3_v2_passes_sizing(all_rows, world, T, expected):
    """p3_v2 with sizing data matches expected rates."""
    rows = _cell_rows(all_rows, world, T)
    result = D.p3_v2(rows, world, T)
    assert result is not None
    rate = result["rate_infer_value_changes"]
    assert abs(rate - expected) <= TOL, (
        f"{world} T={T}: p3_v2 rate={rate:.4f}, expected {expected:.3f}")


def test_thresholds_match_addendum():
    """TH_P3V2 matches addendum SS4 table (0.35 for all cells)."""
    assert D.TH_P3V2 == 0.35


@pytest.mark.parametrize("world,T", [
    ("R", 80), ("R+", 80), ("R", 160), ("R+", 160),
])
def test_invariance_is_one(all_rows, world, T):
    """R_norm invariance is 1.00 in all cells."""
    rows = _cell_rows(all_rows, world, T)
    rate = sum(1 for r in rows if r.get("P3_invariant") is True) / len(rows)
    assert rate == 1.0, f"{world} T={T}: invariance={rate}"
