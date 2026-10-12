"""Guardian for collective/ freeze. Verifies hashes, completeness,
theta traceability to the preregistro, and positive control.
"""
import re
import shutil
from pathlib import Path

import pytest

from collective.freeze_check import check_freeze, check_plugin
from adaptive.freeze_check import sha256_lf

COLLECTIVE = Path(__file__).resolve().parent.parent / "collective"
TESTS = Path(__file__).resolve().parent


# -- 1. Freeze hash integrity --
def test_check_freeze_passes():
    check_freeze()


# -- 2. Plugin hash integrity (needs MDAA_PLUGIN_DIST) --
_need_plugin = pytest.mark.skipif(
    not __import__("os").environ.get("MDAA_PLUGIN_DIST"),
    reason="MDAA_PLUGIN_DIST not set")


@_need_plugin
def test_check_plugin_passes():
    check_plugin()


# -- 3. Completeness: every relevant file is in freeze.sha256 --
def _freeze_entries() -> dict[str, str]:
    freeze = COLLECTIVE / "freeze.sha256"
    entries: dict[str, str] = {}
    for line in freeze.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        h, name = s.split(None, 1)
        entries[name.lstrip("*")] = h
    return entries


def test_all_collective_files_in_freeze():
    entries = _freeze_entries()
    listed = set(entries.keys())
    expected: set[str] = set()
    for ext in ("*.py", "*.md", "*.json"):
        for p in COLLECTIVE.glob(ext):
            if p.name == "__init__.py":
                continue
            expected.add(p.name)
    expected.add("plugin.sha256")
    for p in TESTS.glob("test_collective_*.py"):
        if p.name == "test_collective_guardian.py":
            continue
        expected.add(f"../tests/{p.name}")
    missing = expected - listed
    extra = listed - expected
    assert not missing, f"Files not in freeze.sha256: {missing}"
    assert not extra, f"Extra entries in freeze.sha256: {extra}"


# -- 4. plugin.sha256 format --
def test_plugin_sha256_format():
    plugin = COLLECTIVE / "plugin.sha256"
    assert plugin.exists()
    lines = plugin.read_text(encoding="utf-8").splitlines()
    comment_lines = [l for l in lines if l.startswith("#")]
    assert len(comment_lines) == 1
    assert "tmulab-mdaa" in comment_lines[0]
    data_lines = [l.strip() for l in lines
                  if l.strip() and not l.startswith("#")]
    names = sorted(l.split(None, 1)[1] for l in data_lines)
    assert names == ["adjustment-cli.js", "adjustment.js",
                     "collective-cli.js", "collective.js",
                     "episode-key.js", "episode-signal.js",
                     "status.js"]


# -- 5. Positive control --
def test_positive_control_changed_file(tmp_path):
    fake = tmp_path / "collective"
    shutil.copytree(COLLECTIVE, fake)
    pre = fake / "PREREGISTRO_v1.md"
    pre.write_bytes(pre.read_bytes() + b"X")
    import collective.freeze_check as fc
    orig = fc.COLLECTIVE
    try:
        fc.COLLECTIVE = fake
        with pytest.raises(RuntimeError, match="hash mismatch"):
            check_freeze()
    finally:
        fc.COLLECTIVE = orig


# -- 6. Theta traceability: per-cell exact match with PREREGISTRO --
def _prereg_text() -> str:
    return (COLLECTIVE / "PREREGISTRO_v1.md").read_text(encoding="utf-8")


def _parse_table_81(text: str) -> dict[tuple, float]:
    """Parse Tabela 8.1 to extract per-cell theta_4 values."""
    result: dict[tuple, float] = {}
    found_header = False
    in_rows = False
    for line in text.splitlines():
        if "Tabela 8.1" in line:
            found_header = True
            continue
        if not found_header:
            continue
        if not line.startswith("|"):
            if in_rows:
                break
            continue
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if cols[0] in ("---", "n"):
            continue
        in_rows = True
        try:
            n = int(cols[0])
            p = float(cols[1].replace(",", "."))
            rho = float(cols[2].replace(",", "."))
            theta = float(cols[5].replace(",", "."))
            result[(n, p, rho)] = theta
        except (ValueError, IndexError):
            continue
    return result


def _parse_main_table(text: str) -> dict[str, float]:
    """Parse the main sizing table (non-G rows) into quantity->theta."""
    result: dict[str, float] = {}
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Quantidade"):
            in_table = True
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if cols[0] == "---":
                continue
            if "tabela 8.1" in cols[-1]:
                continue
            try:
                theta = float(cols[-1].replace(",", "."))
                qty = cols[0]
                cell_desc = cols[1]
                result[f"{qty} | {cell_desc}"] = theta
            except (ValueError, IndexError):
                continue
        elif in_table and not line.startswith("|") and line.strip():
            break
    return result


# -- Q3 thresholds: per-cell from main table --
_Q3_PASS_EXPECTED = {
    (5, 320): 0.95, (5, 640): 1.00,
    (20, 320): 1.00, (20, 640): 1.00,
}
_Q3_WRONG_EXPECTED = {
    (5, 320): 0.95, (5, 640): 1.00,
    (20, 320): 1.00, (20, 640): 1.00,
}
_Q3_REFUSE_EXPECTED = {
    (5, 320): 0.70, (5, 640): 0.70,
    (20, 320): 1.00, (20, 640): 1.00,
}
_Q4_EXPECTED = {
    (10, 0.8, 0.0): 0.85, (10, 0.8, 0.5): 0.80,
    (10, 0.9, 0.0): 0.55, (10, 0.9, 0.5): 0.60,
    (30, 0.8, 0.0): 1.00, (30, 0.8, 0.5): 1.00,
    (30, 0.9, 0.0): 1.00, (30, 0.9, 0.5): 1.00,
}


def test_theta_q1_q2_in_preregistro():
    import collective.decide as D
    assert D.TH_Q1_COUNT == 1.00
    assert D.TH_Q2_POOL == 1.00
    text = _prereg_text()
    assert "1,00" in text


def test_theta_q3_pass_per_cell():
    import collective.decide as D
    assert D.TH_Q3_H1_PASS == _Q3_PASS_EXPECTED


def test_theta_q3_wrong_per_cell():
    import collective.decide as D
    assert D.TH_Q3_H1_WRONG == _Q3_WRONG_EXPECTED


def test_theta_q3_refuse_per_cell():
    import collective.decide as D
    assert D.TH_Q3_H1_REFUSE == _Q3_REFUSE_EXPECTED


def test_theta_q4_per_cell_matches_table_81():
    """Each Q4 cell theta must exactly match Tabela 8.1."""
    import collective.decide as D
    text = _prereg_text()
    parsed = _parse_table_81(text)
    assert parsed, "Could not parse Tabela 8.1"
    assert D.TH_Q4_MEAN_OUTSIDE == parsed, (
        f"decide.py: {D.TH_Q4_MEAN_OUTSIDE}\n"
        f"preregistro: {parsed}")


def test_theta_q4_per_cell_exact():
    import collective.decide as D
    assert D.TH_Q4_MEAN_OUTSIDE == _Q4_EXPECTED
