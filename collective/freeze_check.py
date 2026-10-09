"""Freeze-check for collective/. Imports sha256_lf and _parse_manifest
from adaptive.freeze_check. Checks collective/ files and plugin files.
Plugin files: collective-cli.js, collective.js, episode-key.js,
episode-signal.js, status.js, adjustment-cli.js, adjustment.js.
"""
from __future__ import annotations

import os
from pathlib import Path

from adaptive.freeze_check import sha256_lf, _parse_manifest

__all__ = ["check_freeze", "check_plugin"]

COLLECTIVE = Path(__file__).resolve().parent


def check_freeze() -> None:
    """Verify every file listed in ``collective/freeze.sha256``."""
    freeze = COLLECTIVE / "freeze.sha256"
    if not freeze.exists():
        raise RuntimeError(
            "collective/freeze.sha256 not found: freeze commit not done")
    expected = _parse_manifest(freeze)
    if not expected:
        raise RuntimeError("collective/freeze.sha256 is empty")
    for name, want in expected.items():
        p = COLLECTIVE / name
        if not p.exists():
            raise RuntimeError(
                f"{name}: listed in freeze.sha256 but not on disk")
        got = sha256_lf(p)
        if got != want:
            raise RuntimeError(
                f"{name}: hash mismatch (expected {want[:16]}... "
                f"got {got[:16]}...)")


def check_plugin() -> None:
    """Verify plugin files listed in ``collective/plugin.sha256``."""
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError("MDAA_PLUGIN_DIST not set")
    manifest = COLLECTIVE / "plugin.sha256"
    if not manifest.exists():
        raise RuntimeError("collective/plugin.sha256 not found")
    expected = _parse_manifest(manifest)
    if not expected:
        raise RuntimeError("collective/plugin.sha256 has no file entries")
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
