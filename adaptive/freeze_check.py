"""Freeze-check for adaptive/. Recomputes SHA-256 hashes and refuses to
run if any file diverges from the manifest. Line endings are normalised
to LF so hashes are identical on Windows and Linux.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

__all__ = ["sha256_lf", "check_freeze", "check_plugin"]

ADAPTIVE = Path(__file__).resolve().parent


def sha256_lf(path: Path) -> str:
    """SHA-256 of *path* with CRLF replaced by LF."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _parse_manifest(path: Path) -> dict[str, str]:
    """Parse a ``<hash>  <name>`` manifest, skipping comment lines."""
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        h, name = stripped.split(None, 1)
        entries[name.lstrip("*")] = h
    return entries


def check_freeze() -> None:
    """Verify every file listed in ``adaptive/freeze.sha256``."""
    freeze = ADAPTIVE / "freeze.sha256"
    if not freeze.exists():
        raise RuntimeError(
            "adaptive/freeze.sha256 not found: freeze commit not done")
    expected = _parse_manifest(freeze)
    if not expected:
        raise RuntimeError("adaptive/freeze.sha256 is empty")
    for name, want in expected.items():
        p = ADAPTIVE / name
        if not p.exists():
            raise RuntimeError(
                f"{name}: listed in freeze.sha256 but not on disk")
        got = sha256_lf(p)
        if got != want:
            raise RuntimeError(
                f"{name}: hash mismatch (expected {want[:16]}... "
                f"got {got[:16]}...)")


def check_plugin() -> None:
    """Verify every file listed in ``adaptive/plugin.sha256``."""
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError("MDAA_PLUGIN_DIST not set")
    manifest = ADAPTIVE / "plugin.sha256"
    if not manifest.exists():
        raise RuntimeError("adaptive/plugin.sha256 not found")
    expected = _parse_manifest(manifest)
    if not expected:
        raise RuntimeError("adaptive/plugin.sha256 has no file entries")
    for name, want in expected.items():
        p = Path(dist) / name
        if not p.exists():
            raise RuntimeError(
                f"{name}: listed in plugin.sha256 but not in "
                f"MDAA_PLUGIN_DIST ({dist})")
        got = sha256_lf(p)
        if got != want:
            raise RuntimeError(
                f"{name}: plugin hash mismatch (expected {want[:16]}... "
                f"got {got[:16]}...)")
