"""Smoke tests: generators produce what they claim; pipeline runs blind; truth never leaks."""
import numpy as np
from sim.generators import generate, NODES
from sim.observe import observe, regular_pairs
from sim.pipeline import identify


def test_generators_shapes_and_truth():
    for node in NODES:
        tr = generate(node, T=120, seed=1)
        assert tr.x.shape == (120, 2) and tr.u.shape == (120, 1)
        assert tr.truth["node"] == node
        assert not tr.u[tr.pause].any()                     # u_ped = 0 inside the pause
    h = generate("M1+H", T=400, seed=3)
    assert len(h.truth["switches"]) >= 1                     # at least one planted switch


def test_observation_never_returns_state():
    tr = generate("M1", T=100, seed=2)
    obs = observe(tr, meas_noise=0.2, keep_frac=0.7, seed=2)
    assert not hasattr(obs, "x") and len(obs.t) < 100
    y0, y1, u = regular_pairs(obs)
    assert len(y0) == len(y1) == len(u)


def test_pipeline_runs_and_recovers_linear_at_low_noise():
    tr = generate("M1", T=400, seed=5)
    fit = identify(observe(tr, meas_noise=0.05, seed=5), seed=5, s_null=False, m_null=False)
    assert fit.node in ("M1", "M1+M")                        # no spurious N or H on a linear world
    assert not fit.axes["N"] and not fit.axes["H"]


def test_pipeline_detects_planted_nonlinearity():
    tr = generate("M1+N", T=600, seed=7)
    fit = identify(observe(tr, meas_noise=0.05, seed=7), seed=7, s_null=False, m_null=False)
    assert fit.axes["N"], fit.gains
