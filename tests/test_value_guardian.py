"""Guardian for value/ freeze. Verifies hashes, completeness, theta
traceability to the preregistro, and positive control.
"""
import re
import shutil
from pathlib import Path

import pytest

from value.freeze_check import check_freeze, check_plugin
from adaptive.freeze_check import sha256_lf

VALUE = Path(__file__).resolve().parent.parent / "value"
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
    freeze = VALUE / "freeze.sha256"
    entries: dict[str, str] = {}
    for line in freeze.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        h, name = s.split(None, 1)
        entries[name.lstrip("*")] = h
    return entries


def test_all_value_files_in_freeze():
    entries = _freeze_entries()
    listed = set(entries.keys())
    expected: set[str] = set()
    for ext in ("*.py", "*.md", "*.json"):
        for p in VALUE.glob(ext):
            if p.name == "__init__.py":
                continue
            expected.add(p.name)
    expected.add("plugin.sha256")
    for p in TESTS.glob("test_value_*.py"):
        if p.name == "test_value_guardian.py":
            continue
        expected.add(f"../tests/{p.name}")
    missing = expected - listed
    extra = listed - expected
    assert not missing, f"Files not in freeze.sha256: {missing}"
    assert not extra, f"Extra entries in freeze.sha256: {extra}"


# -- 4. plugin.sha256 format --
def test_plugin_sha256_format():
    plugin = VALUE / "plugin.sha256"
    assert plugin.exists()
    lines = plugin.read_text(encoding="utf-8").splitlines()
    comment_lines = [l for l in lines if l.startswith("#")]
    assert len(comment_lines) == 1
    assert "tmulab-mdaa" in comment_lines[0]
    data_lines = [l.strip() for l in lines
                  if l.strip() and not l.startswith("#")]
    names = sorted(l.split(None, 1)[1] for l in data_lines)
    assert names == ["judgment.js", "norm.js", "standing-cli.js",
                     "status.js", "value-cli.js"]


# -- 5. Positive control --
def test_positive_control_changed_file(tmp_path):
    fake_value = tmp_path / "value"
    shutil.copytree(VALUE, fake_value)
    pre = fake_value / "PREREGISTRO_v1.md"
    pre.write_bytes(pre.read_bytes() + b"X")
    import value.freeze_check as fc
    orig = fc.VALUE
    try:
        fc.VALUE = fake_value
        with pytest.raises(RuntimeError, match="hash mismatch"):
            check_freeze()
    finally:
        fc.VALUE = orig


# -- 6. Theta traceability: each TH_ in decide.py appears in PREREGISTRO --
def _prereg_text() -> str:
    return (VALUE / "PREREGISTRO_v1.md").read_text(encoding="utf-8")


_THETA_MAP = [
    # (variable_name, section_marker, expected_value_text)
    ("TH_P2_T80", "P2", "0,80"),
    ("TH_P2_T160", "P2", "0,95"),
    ("TH_P2_REWARD", "P2", "1,00"),
    ("TH_P3_R", "P3", "0,20"),
    ("TH_P3_RPLUS", "P3", "0,25"),
    ("TH_P4_CONFLICT", "P4", "1,00"),
    ("TH_P4_ELECT_T80", "P4", "0,85"),
    ("TH_P4_ELECT_T160", "P4", "0,95"),
    ("TH_P5_X_NAIVE_T80", "P5", "0,85"),
    ("TH_P5_X_NAIVE_T160", "P5", "0,95"),
    ("TH_P5_XP_T80", "P5", "0,70"),
    ("TH_P5_XP_T160", "P5", "0,90"),
]


@pytest.mark.parametrize("var,section,text", _THETA_MAP,
                         ids=[t[0] for t in _THETA_MAP])
def test_theta_in_preregistro(var, section, text):
    """Each threshold in decide.py must appear in the preregistro."""
    import value.decide as D
    val = getattr(D, var)
    assert val is not None, f"{var} is None"
    prereg = _prereg_text()
    # Find the prediction paragraph (** P<n> ...)
    pattern = rf"\*\*{section}\b.*?\*\*"
    match = re.search(pattern, prereg)
    assert match, f"Section {section} not found in preregistro"
    # Find the value text in the section onwards
    start = match.start()
    rest = prereg[start:]
    assert text in rest, (
        f"{var}={val}: expected '{text}' in {section} section")
