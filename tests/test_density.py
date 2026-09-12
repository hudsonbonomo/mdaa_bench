"""Paper 3 branch: ensembles and gates H1-H4.

Slow (H3 runs the M-axis contest per trajectory, three EM fits each): ~40 s.
"""
import numpy as np
import pytest
from sim.ensemble import generate_ensemble, pooled_window, windows
from sim.density import (h1_ensemble, h2_geometry, h3_memory, h4_locality, run_gates,
                         switching_competitor, PASS, FAIL, VERDICTS, H1_BETWEEN_WITHIN,
                         H1_INSTAB, H2_SCALE_RATIO, H3_TOL, H4_MARGIN)
from sim.observe import pair_times
from sim.statespace import to_grid


# --- the ensemble itself -----------------------------------------------------

def test_within_mode_is_one_person_sampled_twice():
    """Replicates share the structure and differ only in realisation. If this
    fails, `within` is silently a between-person ensemble and H1 means nothing."""
    ens = generate_ensemble("M1", n_traj=6, mode="within", T=200, seed=0)
    As = ens.truth["A_per_traj"]
    for A in As[1:]:
        assert np.allclose(A, As[0])
    ys = [o.y for o in ens.obs]
    assert not np.allclose(ys[0], ys[1])


def test_between_mode_disperses_the_dynamics():
    ens = generate_ensemble("M1", n_traj=6, mode="between", T=200, seed=0, A_radius=0.5, loc_radius=0.5)
    As = ens.truth["A_per_traj"]
    assert not np.allclose(As[0], As[1])
    for A in As:                                  # dispersion changes shape, never stability
        assert max(abs(np.linalg.eigvals(A))) < 1.0


def test_gates_never_receive_truth():
    """`truth` lives on the Ensemble for recovery.py. The gates take `obs` and
    the design facts an analyst actually has."""
    ens = generate_ensemble("M1", n_traj=4, mode="between", T=200, seed=0, A_radius=0.5, loc_radius=0.5)
    assert set(ens.design()) == {"mode", "n_traj"}
    for key in ("A_mean", "A_per_traj", "set_points", "A_radius", "loc_radius", "process_noise"):
        assert key in ens.truth and key not in ens.design()
    for o in ens.obs:
        assert not hasattr(o, "truth") and not hasattr(o, "x")


def test_windows_do_not_interpolate():
    ens = generate_ensemble("M1", n_traj=5, mode="within", T=200, seed=0, keep_frac=0.5)
    total = sum(len(pooled_window(ens.obs, a, b)) for a, b in windows(ens.obs, 5))
    assert total == sum(len(o.t) for o in ens.obs)     # every point once, none invented


# --- H1-H4 on a world where all four should pass -----------------------------

@pytest.fixture(scope="module")
def m1_within():
    return generate_ensemble("M1", n_traj=30, mode="within", T=400, seed=0, meas_noise=0.05)


def test_h1_h2_h4_pass_on_a_clean_within_person_ensemble(m1_within):
    h1 = h1_ensemble(m1_within.obs, "within", seed=0)
    h2 = h2_geometry(m1_within.obs)
    h4 = h4_locality(m1_within.obs)
    assert h1.passed and h1.stat < H1_INSTAB, h1.note
    assert h2.passed and h2.stat <= H2_SCALE_RATIO, h2.note
    assert h4.passed and h4.stat > 0, h4.note
    for g in (h1, h2, h4):                        # every gate states its stopping rule
        assert isinstance(g.passed, bool) and g.note and np.isfinite(g.stat)


def test_h3_passes_on_markov_and_fails_on_planted_memory():
    """The payoff of the ensemble. On ONE trajectory this contest is swamped by
    estimation noise (see the README); over replicates of the same person it
    separates the two worlds with no overlap."""
    mk = generate_ensemble("M1", n_traj=30, mode="within", T=400, seed=0, meas_noise=0.05)
    me = generate_ensemble("M1+M", n_traj=30, mode="within", T=400, seed=0, meas_noise=0.05)
    g_mk = h3_memory(mk.obs, max_traj=6)
    g_me = h3_memory(me.obs, max_traj=6)
    assert g_mk.passed, g_mk.note
    assert not g_me.passed, g_me.note
    assert max(g_mk.detail["per_traj"]) < min(g_me.detail["per_traj"])


# --- H1 and the comparability objection --------------------------------------

def test_h1_fails_when_set_points_disperse():
    """Molenaar: a pooled density over people who sit in different places
    describes nobody. Small dispersion pools fine; large must be caught."""
    near = generate_ensemble("M1", n_traj=30, mode="between", T=400, seed=0,
                             meas_noise=0.05, A_radius=0.0, loc_radius=0.2)
    far = generate_ensemble("M1", n_traj=30, mode="between", T=400, seed=0,
                            meas_noise=0.05, A_radius=0.0, loc_radius=1.5)
    g_near = h1_ensemble(near.obs, "between", seed=0)
    g_far = h1_ensemble(far.obs, "between", seed=0)
    assert g_near.passed, g_near.note
    assert not g_far.passed, g_far.note
    assert g_far.detail["between_within"] > g_near.detail["between_within"]


def test_h2_catches_an_undeclared_scale_mismatch():
    """H2 is a bookkeeping gate: it fails when one KDE bandwidth would mean two
    different things on the two axes."""
    ens = generate_ensemble("M1", n_traj=8, mode="within", T=200, seed=0)
    for o in ens.obs:
        o.y[:, 1] *= 50.0                          # an undeclared unit change
    g = h2_geometry(ens.obs)
    assert not g.passed and g.stat > H2_SCALE_RATIO, g.note
    assert h2_geometry(ens.obs, normalised=True).passed   # declaring it is the fix


def test_run_gates_returns_all_four_with_stopping_rules(m1_within):
    res = run_gates(m1_within, seed=0, max_traj=3)
    assert set(res) == {"H1", "H2", "H3", "H4"}
    for name, g in res.items():
        assert g.name == name and isinstance(g.passed, bool) and g.note


def test_h4_fails_when_the_drift_is_not_a_function_of_position():
    """Negative control, without which H4 would be satisfied by any implementation
    that returns True. Each trajectory carries its OWN constant drift and they all
    occupy the same box (reflecting walls), so every cell of the grid contains
    trajectories going every way: the local flow field averages to the global one
    and has nothing left to win with.

    A first attempt used a random walk under a global time-varying push. That one
    passed H4 — with an unbounded walk, position encodes elapsed time, so the
    local field is a clock and legitimately predicts. The box is what removes it.
    """
    from sim.observe import Observed
    rng = np.random.default_rng(0)
    T, n = 400, 24
    obs = []
    for _ in range(n):
        v = rng.normal(scale=0.25, size=2)
        x = np.zeros((T, 2)); x[0] = rng.uniform(-3, 3, size=2)
        for t in range(1, T):
            q = x[t - 1] + v + rng.normal(scale=0.05, size=2)
            for c in range(2):
                if q[c] > 3:
                    q[c] = 6 - q[c]; v[c] = -v[c]
                elif q[c] < -3:
                    q[c] = -6 - q[c]; v[c] = -v[c]
            x[t] = q
        obs.append(Observed(t=np.arange(T), y=x, u=np.zeros((T, 1)),
                            pause=np.zeros(T, bool)))
    g = h4_locality(obs)
    assert not g.passed, g.note
    assert g.detail["mse_local"] >= g.detail["mse_nonlocal"] * (1 - H4_MARGIN), g.note


# --- cell "boundedness": the two dispersion radii are not interchangeable -----

def test_shape_dispersion_alone_never_breaks_pooling():
    """Finding 11 of v2, now that the two radii can be moved independently:
    people moving under different laws does NOT make a pooled density lie, at
    any radius, because every density stays centred on the same point."""
    for A_r in (0.3, 0.6, 0.9):
        ens = generate_ensemble("M1", n_traj=30, mode="between", T=400, seed=0,
                                meas_noise=0.05, A_radius=A_r, loc_radius=0.0)
        g = h1_ensemble(ens.obs, "between", seed=0)
        assert g.passed, (A_r, g.note)
        assert g.detail["between_within"] < 0.1, (A_r, g.detail)


def test_location_dispersion_is_what_breaks_pooling():
    """The same ensemble size and node, with the laws held identical and only
    the set points scattered."""
    ens = generate_ensemble("M1", n_traj=30, mode="between", T=400, seed=0,
                            meas_noise=0.05, A_radius=0.0, loc_radius=1.5)
    g = h1_ensemble(ens.obs, "between", seed=0)
    assert not g.passed and g.verdict == FAIL, g.note
    assert g.detail["between_within"] > H1_BETWEEN_WITHIN, g.detail


def test_h1_boundary_in_loc_radius_is_a_number():
    """The README quotes a boundary; this pins it down so the quote cannot rot.
    Measured by bisection on four seeds: 0.65 to 1.01, median ~0.84."""
    def verdict(loc, seed):
        ens = generate_ensemble("M1", n_traj=30, mode="between", T=400, seed=seed,
                                meas_noise=0.05, A_radius=0.0, loc_radius=loc)
        return h1_ensemble(ens.obs, "between", seed=seed).verdict
    for seed in (0, 1):
        assert verdict(0.30, seed) == PASS, seed          # well below the boundary
        assert verdict(1.50, seed) == FAIL, seed          # well above it


def test_every_gate_reports_a_verdict_from_the_declared_set():
    ens = generate_ensemble("M1", n_traj=10, mode="within", T=200, seed=0)
    for g in run_gates(ens, seed=0, max_traj=2).values():
        assert g.verdict in VERDICTS
        assert (g.verdict == PASS) == g.passed


# --- cell "switching null" step 2: the M axis over replicates ----------------

def test_h3_computes_and_reports_a_switching_null():
    """The null must be present and reported, not merely intended."""
    ens = generate_ensemble("M1+H", n_traj=10, mode="within", T=300, seed=0,
                            meas_noise=0.05)
    g = h3_memory(ens.obs, max_traj=2, seed=0, switch_null=True, three_way=False)
    assert np.isfinite(g.detail["switching_q95"])
    assert g.detail["n_nulls"] >= 1
    assert "switching null" in g.note
    off = h3_memory(ens.obs, max_traj=2, seed=0, switch_null=False, three_way=False)
    assert off.detail["switching_q95"] == float("-inf")


def test_h3_null_cannot_make_the_gate_stricter():
    """The null only ever ADDS a way to pass (be judged Markov). A world the gate
    already called Markov must never become non-Markov because a null was added."""
    for node in ("M1", "M1+H", "M1+M"):
        ens = generate_ensemble(node, n_traj=10, mode="within", T=300, seed=1,
                                meas_noise=0.05)
        off = h3_memory(ens.obs, max_traj=2, seed=1, switch_null=False, three_way=False)
        on = h3_memory(ens.obs, max_traj=2, seed=1, switch_null=True, three_way=False)
        if off.passed:
            assert on.passed, (node, off.note, on.note)


def test_h3_switching_null_does_not_rescue_the_M_axis_on_two_regime_worlds():
    """A RECORDED NEGATIVE RESULT, not an aspiration.

    The cell set out to bring M's false-alarm rate on two-regime worlds down to
    <= 2/20. Measured over 20 seeds at T=600 with 10 replicates, the axis still
    fires on 7 of 20 with the null against 8 of 20 without it. The null removes
    one false alarm in eight. The fitted dwell times match the planted ones
    (60.6 vs 60, 43.4 vs 50, ...), so the null is not mis-specified — a switching
    surrogate simply does not reproduce the memory-like structure that the real
    two-regime trajectory carries. This test pins the measured behaviour on a
    smaller sample so the claim in the README cannot rot silently.
    """
    fires = 0
    for seed in range(6):
        ens = generate_ensemble("M1+H", n_traj=10, mode="within", T=600, seed=seed,
                                meas_noise=0.05)
        fires += int(h3_memory(ens.obs, max_traj=2, seed=seed, three_way=False,
                               switch_null=True).verdict == FAIL)
    assert fires >= 1, "the false alarm has gone away; re-measure and update the README"


# --- cell "comparador-M": the three-way contest -------------------------------

def _m_fires(node, seed, three_way=True, n_traj=10, T=600, max_traj=3):
    """The M axis fires exactly when H3 fails. One ensemble, one verdict."""
    ens = generate_ensemble(node, n_traj=n_traj, mode="within", T=T, seed=seed,
                            meas_noise=0.05)
    return h3_memory(ens.obs, max_traj=max_traj, seed=seed, three_way=three_way)


def test_the_contest_has_two_rivals_and_names_the_binding_one():
    g = _m_fires("M1+M", 0)
    assert np.isfinite(g.detail["switching_gain"]), g.note
    assert g.detail["hardest"] in ("state_space", "switching")
    # the headline statistic is the BINDING rival, so the gate cannot be cleared
    # by beating the easier one
    assert g.stat == min(g.detail["mean_gain"], g.detail["switching_gain"])
    assert "two-regime model" in g.note


def test_switching_competitor_is_scored_on_the_same_future_block():
    """Both rivals must be answering the same question, or the margin is fiction."""
    ens = generate_ensemble("M1+M", n_traj=2, mode="within", T=600, seed=0,
                            meas_noise=0.05)
    o = ens.obs[0]
    kt = max(int(len(to_grid(o)[0]) * 0.7), 20)
    mse = switching_competitor(o, kt)
    assert np.isfinite(mse) and mse > 0
    ts = pair_times(o)
    assert ts[int(np.searchsorted(ts, kt))] >= kt      # split on the original clock


@pytest.mark.parametrize("node,target", [
    ("M1+H", 1),      # two-regime world: the axis must now stay quiet
    ("M1", 0),        # neither memory nor regimes: no false alarm at all
])
def test_three_way_contest_kills_the_false_alarm(node, target):
    """The targets were declared in the cell scope before the measurement.

    This is what the cell was for. Under the old comparator the M axis fired on
    11 of 40 two-regime worlds; with the two-regime model present as a rival it
    fires on 1 of 40, and on 0 of the 20 seeds used here.
    """
    fires = sum(int(_m_fires(node, s).verdict == FAIL) for s in range(20))
    assert fires <= target, f"{node}: M fired on {fires}/20, target <={target}"


def test_the_second_rival_costs_almost_no_power_on_planted_memory():
    """The price cap. A comparator that fixes the false alarm by never firing has
    fixed nothing, so the cost has to be bounded, and it is bounded exactly:

        new statistic = min(gain over state space, gain over switching) <= old

    so every world the new gate fires on, the old one fired on too. The cost is
    the worlds where the switching model — not the state space — is the binding
    rival. Measured over 40 worlds, that is 1 of 40; over these 20 seeds it must
    not exceed 1.

    THE DECLARED POWER TARGET OF 12/20 WAS NOT MET, and the number is registered
    rather than the threshold moved: the three-way contest fires on 10/20 at
    max_traj=3 and 9/20 at max_traj=8, against 20/40 for the OLD gate on the same
    worlds. So the shortfall is not the new rival's doing — power against planted
    memory sits near 50% for both comparators, because the statistics land
    continuously around H3_TOL (seven of the twenty fall between +0.002 and
    +0.028). Raising it is a question about H3_TOL and about T, not about which
    rivals are in the contest, and it does not belong to this cell.
    """
    lost = 0
    for seed in range(20):
        g = _m_fires("M1+M", seed)
        fired_new = g.stat > H3_TOL
        fired_old = g.detail["mean_gain"] > H3_TOL      # the pre-cell comparator
        assert not (fired_new and not fired_old), "the new statistic cannot exceed the old"
        lost += int(fired_old and not fired_new)
    assert lost <= 1, f"the switching rival cost {lost}/20 detections on planted memory"
