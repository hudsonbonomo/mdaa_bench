"""Guardian for adaptive/ freeze. Verifies hashes, completeness, and
positive control (a changed file must be caught). Pattern from
tests/test_freeze_guardian.py.
"""
import shutil
from pathlib import Path

import pytest

from adaptive.freeze_check import check_freeze, sha256_lf

ADAPTIVE = Path(__file__).resolve().parent.parent / "adaptive"
TESTS = Path(__file__).resolve().parent


def test_check_freeze_passes():
    """All hashes in freeze.sha256 match the actual files."""
    check_freeze()


def _freeze_entries() -> dict[str, str]:
    freeze = ADAPTIVE / "freeze.sha256"
    entries: dict[str, str] = {}
    for line in freeze.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        h, name = stripped.split(None, 1)
        entries[name.lstrip("*")] = h
    return entries


def test_all_adaptive_files_in_freeze():
    """Every adaptive/*.py, *.md, *.json, plugin.sha256 and every
    tests/test_adaptive_*.py (except this guardian) must be listed."""
    entries = _freeze_entries()
    listed = set(entries.keys())

    expected: set[str] = set()
    for ext in ("*.py", "*.md", "*.json"):
        for p in ADAPTIVE.glob(ext):
            if p.name == "__init__.py":
                continue
            expected.add(p.name)
    expected.add("plugin.sha256")

    for p in TESTS.glob("test_adaptive_*.py"):
        if p.name == "test_adaptive_guardian.py":
            continue
        expected.add(f"../tests/{p.name}")

    missing = expected - listed
    extra = listed - expected
    assert not missing, f"Files not in freeze.sha256: {missing}"
    assert not extra, f"Extra entries in freeze.sha256: {extra}"


def test_plugin_sha256_format():
    """plugin.sha256 has the commit line and the three expected files."""
    plugin = ADAPTIVE / "plugin.sha256"
    assert plugin.exists()
    lines = plugin.read_text(encoding="utf-8").splitlines()
    comment_lines = [l for l in lines if l.startswith("#")]
    assert len(comment_lines) == 1
    assert "tmulab-mdaa" in comment_lines[0]
    commit_hash = comment_lines[0].split()[-1]
    assert len(commit_hash) == 40, "commit hash must be 40 hex chars"

    data_lines = [l.strip() for l in lines
                  if l.strip() and not l.startswith("#")]
    names = [l.split(None, 1)[1] for l in data_lines]
    assert sorted(names) == ["adjustment-cli.js", "adjustment.js",
                              "standing.js"]


def test_positive_control_changed_file(tmp_path):
    """Changing one byte of PREREGISTRO_v1.md must make check_freeze raise."""
    fake_adaptive = tmp_path / "adaptive"
    shutil.copytree(ADAPTIVE, fake_adaptive)

    pre = fake_adaptive / "PREREGISTRO_v1.md"
    original = pre.read_bytes()
    pre.write_bytes(original + b"X")

    import adaptive.freeze_check as fc
    orig_adaptive = fc.ADAPTIVE
    try:
        fc.ADAPTIVE = fake_adaptive
        with pytest.raises(RuntimeError, match="hash mismatch"):
            check_freeze()
    finally:
        fc.ADAPTIVE = orig_adaptive
