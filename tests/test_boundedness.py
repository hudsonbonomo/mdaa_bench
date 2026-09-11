"""Boundedness as a generator invariant.

Two generator defects reached v2 without a single test noticing:

  M1+N  linearised to (A - alpha e0 e0') far from the origin, not to A, so a
        stable draw of A did not make the node stable. 11 of 60 seeds ran away
        to 1e78. Caught in cell `ensemble-e-gates-h1-h4`, by accident, while
        debugging something else.
  M1+M  had a fixed kernel mass of 0.55 against rho(0.5A) = 0.45, which puts
        z = 1 on the characteristic polynomial EXACTLY whenever 0.5A has a real
        dominant eigenvalue: 60 of 200 seeds were integrated random walks rather
        than the stationary decaying-kernel memory the node advertises. Caught
        here, by looking, which is the point of this file.

Neither defect is visible in a 32-cell smoke grid. Both are visible in one sweep
over seeds. So the sweep runs as a test, on every node and every ensemble mode,
at the two process-noise levels the grid actually uses.

The magnitude check (max |x| <= 50) catches runaway. It does NOT catch a unit
root — a random walk at T = 800 rarely exceeds 50 — so the STRUCTURAL condition
of each node is asserted separately. That pair is the invariant.
"""
import numpy as np
import pytest
from sim.generators import generate, NODES, _companion_rho
from sim.ensemble import generate_ensemble, MODES
from sim.stability import common_lyapunov, certifies

N_SEEDS = 120
T = 800
PROCESS_NOISE = (0.0, 0.15)      # the two extremes the grid uses
MAX_ABS = 50.0
RHO = 0.9


def _worst(node, pn, seeds=range(N_SEEDS)):
    worst, arg = 0.0, None
    for s in seeds:
        x = generate(node, T=T, seed=s, process_noise=pn).x
        assert np.all(np.isfinite(x)), f"{node} seed={s} pn={pn}: NaN or inf"
        m = float(np.abs(x).max())
        if m > worst:
            worst, arg = m, s
    return worst, arg


@pytest.mark.parametrize("node", NODES)
@pytest.mark.parametrize("pn", PROCESS_NOISE)
def test_single_trajectories_stay_bounded(node, pn):
    worst, seed = _worst(node, pn)
    assert worst <= MAX_ABS, f"{node} pn={pn}: max|x| = {worst:.3g} at seed {seed}"


@pytest.mark.parametrize("mode", MODES)
def test_ensembles_stay_bounded(mode):
    """Ensembles re-draw A per trajectory in `between` mode and move the fixed
    point, both of which can break a boundedness argument made for `generate`."""
    for node in NODES:
        for pn in PROCESS_NOISE:
            ens = generate_ensemble(node, n_traj=12, mode=mode, T=T, seed=0,
                                    meas_noise=0.0, process_noise=pn,
                                    A_radius=0.8 if mode == "between" else 0.0,
                                    loc_radius=0.8 if mode == "between" else 0.0)
            for i, o in enumerate(ens.obs):
                assert np.all(np.isfinite(o.y)), f"{node}/{mode} traj {i}: NaN or inf"
                # the set point is deliberately displaced in `between` mode, so the
                # bound is around it, not around zero
                centre = np.median(o.y, axis=0)
                dev = float(np.abs(o.y - centre).max())
                assert dev <= MAX_ABS, f"{node}/{mode} pn={pn} traj {i}: dev = {dev:.3g}"


def test_structural_condition_per_node():
    """max|x| is a symptom test; these are the conditions themselves, one per
    node, the same ones written above each node body in generators.py."""
    d, alpha = 2, 0.45
    for s in range(N_SEEDS):
        m1 = generate("M1", T=60, seed=s).truth
        assert max(abs(np.linalg.eigvals(m1["A"]))) < 1.0

        n = generate("M1+N", T=60, seed=s).truth          # far field, not A
        assert max(abs(np.linalg.eigvals(n["A_far"]))) < 1.0

        h = generate("M1+H", T=60, seed=s).truth          # both modes, slow switching
        assert max(abs(np.linalg.eigvals(h["A"]))) < 1.0
        assert max(abs(np.linalg.eigvals(h["A2"]))) < 1.0

        m = generate("M1+M", T=60, seed=s).truth          # AR(p) companion
        assert m["companion_rho"] < 1.0
        assert _companion_rho(m["A"] * 0.5, m["kernel"], d) == pytest.approx(
            m["companion_rho"], abs=1e-9)


def test_m1m_has_no_unit_root_on_any_seed():
    """The defect this file was written to catch, stated as its own test: the
    old fixed mass of 0.55 gave rho == 1.0000 on 30% of seeds."""
    worst = max(generate("M1+M", T=60, seed=s).truth["companion_rho"] for s in range(N_SEEDS))
    assert worst <= RHO + 1e-6, f"companion radius reached {worst:.6f}"


def test_m1m_kernel_still_decays():
    """Solving for the mass must not change the shape the node is named after."""
    k = generate("M1+M", T=60, seed=0).truth["kernel"]
    assert np.all(np.diff(k) < 0), k
    assert k[0] / k[-1] > 50, "the kernel should span orders of magnitude"


# --- cell "lyapunov": the switched node gets a real invariant -----------------

def test_every_generated_hybrid_carries_a_verified_common_lyapunov_P():
    """M1+H's old condition was rho(A) < 1 and rho(A2) < 1 separately, which does
    not certify anything under switching. Now the generator redraws A2 until a
    COMMON P exists, and the P it stores is re-checked here against both LMIs —
    the search is not allowed to be its own witness."""
    redraws = []
    for s in range(200):
        t = generate("M1+H", T=60, seed=s).truth
        P = t["lyapunov_P"]
        assert P is not None, s
        assert np.linalg.eigvalsh(P).min() > 0, (s, P)
        for A in (t["A"], t["A2"]):
            assert np.linalg.eigvalsh(A.T @ P @ A - P).max() < 0, (s, A)
        assert certifies(P, (t["A"], t["A2"])), s
        redraws.append(t["n_redraws"])
    assert max(redraws) < 50, "redraw budget nearly exhausted"


def test_a_pair_without_a_common_P_is_rejected():
    """Opposite shears: both stable at rho = 0.9, but their product has spectral
    radius 26.6, so no common P can exist and none must be reported."""
    A1 = np.array([[0.9, 5.0], [0.0, 0.9]])
    A2 = np.array([[0.9, 0.0], [5.0, 0.9]])
    assert max(abs(np.linalg.eigvals(A1))) < 1 and max(abs(np.linalg.eigvals(A2))) < 1
    assert max(abs(np.linalg.eigvals(A1 @ A2))) > 1        # switching diverges
    P, margin = common_lyapunov((A1, A2))
    assert P is None and margin > 0, (P, margin)
    assert not certifies(P, (A1, A2))


def test_common_lyapunov_agrees_with_itself_on_a_trivially_feasible_pair():
    """Two contractions sharing P = I: the solver must find something, and what it
    finds must certify."""
    A1 = np.diag([0.5, 0.8]); A2 = np.diag([0.7, 0.3])
    P, margin = common_lyapunov((A1, A2))
    assert P is not None and margin < 0
    assert certifies(P, (A1, A2))


def test_common_lyapunov_refuses_dimensions_it_cannot_solve():
    with pytest.raises(NotImplementedError):
        common_lyapunov((np.eye(3) * 0.5, np.eye(3) * 0.4))
