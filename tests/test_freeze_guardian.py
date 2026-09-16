"""The freeze guardian: the pre-registration and alpha_frozen.json are bytes, not
intentions. This test recomputes their hashes and compares with standing/freeze.sha256
before any execution. PREREGISTRO_v1 §10.
"""
import hashlib
from pathlib import Path

STANDING = Path(__file__).resolve().parent.parent / "standing"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_hashes():
    """Hashes in freeze.sha256 must match the actual files — no silent edits."""
    freeze = STANDING / "freeze.sha256"
    assert freeze.exists(), "standing/freeze.sha256 not found"
    expected = {}
    for line in freeze.read_text().splitlines():
        if line.strip():
            h, name = line.strip().split(None, 1)
            expected[name.lstrip("*")] = h  # handle binary-mode prefix
    assert expected, "standing/freeze.sha256 is empty: nothing is being guarded"
    for name, want in expected.items():
        path = STANDING / name
        assert path.exists(), f"{name}: listed in freeze.sha256 but not on disk"
        got = _sha256(path)
        assert got == want, f"{name}: expected {want[:16]}... got {got[:16]}..."
