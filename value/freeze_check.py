"""Freeze-check for value/. Imports sha256_lf and _parse_manifest from
adaptive.freeze_check and checks value/ files and plugin files.
Plugin files: value-cli.js, judgment.js, norm.js, standing-cli.js, status.js.
"""
from __future__ import annotations

import os
from pathlib import Path

from adaptive.freeze_check import sha256_lf, _parse_manifest

__all__ = ["check_freeze", "check_plugin"]

VALUE = Path(__file__).resolve().parent


def check_freeze() -> None:
    """Verify every file listed in ``value/freeze.sha256``."""
    freeze = VALUE / "freeze.sha256"
    if not freeze.exists():
        raise RuntimeError(
            "value/freeze.sha256 not found: freeze commit not done")
    expected = _parse_manifest(freeze)
    if not expected:
        raise RuntimeError("value/freeze.sha256 is empty")
    for name, want in expected.items():
        p = VALUE / name
        if not p.exists():
            raise RuntimeError(
                f"{name}: listed in freeze.sha256 but not on disk")
        got = sha256_lf(p)
        if got != want:
            raise RuntimeError(
                f"{name}: hash mismatch (expected {want[:16]}... "
                f"got {got[:16]}...)")


def check_plugin() -> None:
    """Verify plugin files listed in ``value/plugin.sha256``."""
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError("MDAA_PLUGIN_DIST not set")
    manifest = VALUE / "plugin.sha256"
    if not manifest.exists():
        raise RuntimeError("value/plugin.sha256 not found")
    expected = _parse_manifest(manifest)
    if not expected:
        raise RuntimeError("value/plugin.sha256 has no file entries")
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
