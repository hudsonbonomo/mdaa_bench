"""Verification tests for collective v2 (Q3-v2, addendum SS6).
Applies v2 measure to sizing folds from commit b2362a4 and reproduces
the rates and block costs from SS4 table. RED if any check fails.
"""
import json
import glob
import pytest
from pathlib import Path

import collective.decide as D
from collective.controls import _collect_returns

SIZING_DIR = Path(__file__).resolve().parent.parent / "collective" / "resultados"
FOLDS_PW = SIZING_DIR / "folds_Pw"
FOLDS_PC = SIZING_DIR / "folds_Pc"
PW_CHUNKS = ["sizing_v2_Pw_300001_300075.json",
             "sizing_v2_Pw_300076_300150.json",
             "sizing_v2_Pw_300151_300225.json",
             "sizing_v2_Pw_300226_300300.json"]

# Expected from addendum SS4 table
EXPECTED_GATE = {(5, 320): 0.987, (5, 640): 1.00,
                 (20, 320): 1.00, (20, 640): 1.00}
EXPECTED_BORROW = {(5, 320): 0.987, (5, 640): 0.993,
                   (20, 320): 1.00, (20, 640): 1.00}
EXPECTED_PC_OWN = {5: 6.46, 20: 6.42}
EXPECTED_PC_POOL = {5: 4.09, 20: 4.00}
TOL = 0.01
BL = 5  # block_length from adaptive policy


@pytest.fixture(scope="module")
def pw_rows():
    rows = []
    for name in PW_CHUNKS:
        p = SIZING_DIR / name
        if not p.exists():
            pytest.skip(f"sizing data not found: {name}")
        rows.extend(json.loads(p.read_text(encoding="utf-8")))
    return rows


def _pw_cell(pw_rows, n, T):
    return [r for r in pw_rows if r.get("n") == n and r.get("T") == T]


def _seq_to_block(s):
    if s < BL:
        return 0
    return (s - BL) // (2 * BL) + 1


@pytest.mark.parametrize("n,T", [(5, 320), (5, 640), (20, 320), (20, 640)])
def test_gate_rate(pw_rows, n, T):
    """Gate pass rate matches addendum SS4."""
    rows = _pw_cell(pw_rows, n, T)
    assert len(rows) == 300
    rate = sum(1 for r in rows if r.get("H1_passed")) / len(rows)
    exp = EXPECTED_GATE[(n, T)]
    assert abs(rate - exp) <= TOL, (
        f"Pw n={n} T={T}: gate={rate:.4f}, expected {exp}")


@pytest.mark.parametrize("n,T", [(5, 320), (5, 640), (20, 320), (20, 640)])
def test_borrow_error_rate(pw_rows, n, T):
    """Borrowing error rate matches addendum SS4."""
    rows = _pw_cell(pw_rows, n, T)
    rate = sum(1 for r in rows if r.get("borrow_error")) / len(rows)
    exp = EXPECTED_BORROW[(n, T)]
    assert abs(rate - exp) <= TOL, (
        f"Pw n={n} T={T}: borrow={rate:.4f}, expected {exp}")


def test_thresholds_match_addendum():
    """Q3-v2 thresholds match addendum SS4 table."""
    assert D.TH_Q3V2_PASS == {
        (5, 320): 0.95, (5, 640): 1.00,
        (20, 320): 1.00, (20, 640): 1.00}
    assert D.TH_Q3V2_BORROW == {
        (5, 320): 0.95, (5, 640): 0.95,
        (20, 320): 1.00, (20, 640): 1.00}


def _compute_pc_costs(n):
    """Compute R_own and R_pool block costs from saved folds."""
    folds_dir = FOLDS_PC
    pattern = str(folds_dir / f"folds_n{n}_T*_s*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        return None, None
    own_blocks, pool_blocks = [], []
    for path in files:
        fdata = json.loads(Path(path).read_text(encoding="utf-8"))
        pf = fdata["folds"]
        # R_own: per person, first fold where window >= 50
        for person_folds in pf:
            for fi, f in enumerate(person_folds):
                if isinstance(f, dict) and f.get("window", 0) >= 50:
                    own_blocks.append(fi)
                    break
        # R_pool: find block of return that pushed window to 50
        returns = _collect_returns(pf)
        run, threshold = 0, 3
        for r in returns:
            kind = r["kind"]
            if kind == "COUNTED":
                run += 1
            elif kind in ("CONFLICT", "CONTRADICTED"):
                run = 0
            if run >= threshold:
                pool_blocks.append(_seq_to_block(r["seq"]))
                break
    own_mean = sum(own_blocks) / len(own_blocks) if own_blocks else None
    pool_mean = sum(pool_blocks) / len(pool_blocks) if pool_blocks else None
    return own_mean, pool_mean


@pytest.mark.parametrize("n,exp_own,exp_pool", [
    (5, 6.46, 4.09), (20, 6.42, 4.00)])
def test_pc_cost_blocks(n, exp_own, exp_pool):
    """Pc cost of refusal in blocks matches addendum SS4."""
    own, pool = _compute_pc_costs(n)
    if own is None:
        pytest.skip(f"Pc folds for n={n} not found")
    assert abs(own - exp_own) <= TOL, (
        f"Pc n={n}: R_own={own:.2f}, expected {exp_own}")
    assert abs(pool - exp_pool) <= TOL, (
        f"Pc n={n}: R_pool={pool:.2f}, expected {exp_pool}")
