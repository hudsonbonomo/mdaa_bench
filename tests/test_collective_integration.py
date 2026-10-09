"""Integration tests for collective bench (Paper 8). Seeds 9001-9004.
Skip without MDAA_PLUGIN_DIST.
"""
import os
import pytest

from collective.worlds import make_world
from collective.measure import measure_run

pytestmark = pytest.mark.skipif(
    not os.environ.get("MDAA_PLUGIN_DIST"),
    reason="MDAA_PLUGIN_DIST not set: plugin not available")

SEEDS = (9001, 9002, 9003, 9004)


@pytest.mark.parametrize("seed", SEEDS[:2])
def test_measure_O_with_plugin(seed):
    d = measure_run("O", seed, use_plugin=True, k=2)
    assert d["world"] == "O"
    assert "Q1_statute_dup" in d


@pytest.mark.parametrize("seed", SEEDS[:2])
def test_measure_Pn_with_plugin(seed):
    d = measure_run("Pn", seed, use_plugin=True, n=5)
    assert d["world"] == "Pn"


@pytest.mark.parametrize("seed", SEEDS[:2])
def test_measure_G_with_plugin(seed):
    d = measure_run("G", seed, use_plugin=True, n=5, m=5, p=0.8, rho=0.0)
    assert d["world"] == "G"
    assert "Q4_R_mean_chosen" in d
