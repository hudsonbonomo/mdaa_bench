"""Integration tests for value bench (Paper 7). Seeds 9001-9004.
Skip without MDAA_PLUGIN_DIST.
"""
import os
import pytest

from value.worlds import make_world, WORLDS
from value.measure import measure_run

pytestmark = pytest.mark.skipif(
    not os.environ.get("MDAA_PLUGIN_DIST"),
    reason="MDAA_PLUGIN_DIST not set: plugin not available")

SEEDS = (9001, 9002, 9003, 9004)
TS = (80, 160)


@pytest.mark.parametrize("T", TS)
@pytest.mark.parametrize("seed", SEEDS[:2])
def test_measure_run_with_plugin(T, seed):
    """measure_run with plugin returns non-None R_norm fields."""
    d = measure_run("P", T, seed, use_plugin=True)
    assert d["R_norm_state"] is not None
    assert d["R_norm_state"] in (
        "SEM_NORMA", "INSUFICIENTE", "JUSTIFICADO",
        "NAO_JUSTIFICADO", "EM_CONFLITO")


@pytest.mark.parametrize("seed", SEEDS[:2])
def test_N0_returns_sem_norma(seed):
    """N0: R_norm must return SEM_NORMA."""
    d = measure_run("N0", 80, seed, use_plugin=True)
    assert d["R_norm_state"] == "SEM_NORMA"


@pytest.mark.parametrize("seed", SEEDS[:2])
def test_X_returns_insuficiente(seed):
    """X (no protocol): R_norm must return INSUFICIENTE."""
    d = measure_run("X", 80, seed, use_plugin=True)
    assert d["R_norm_state"] == "INSUFICIENTE"


@pytest.mark.parametrize("seed", SEEDS[:2])
def test_P3_invariance_R(seed):
    """R: pause invariance holds (P3)."""
    d = measure_run("R", 80, seed, use_plugin=True)
    assert d["P3_invariant"] is True


@pytest.mark.parametrize("seed", SEEDS[:2])
def test_P6_s3_never_elected(seed):
    """P6: s3 (out of gamma) never elected."""
    d = measure_run("P", 80, seed, use_plugin=True)
    assert d["P6_s3_never_elected"] is True
