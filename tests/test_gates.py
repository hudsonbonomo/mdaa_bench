"""Gate tests for roadmap cells 1-3 — each one pins down a claim the README makes.

Slower than the smoke tests (EM fits): ~20 s. Run with `-k` to pick one.
"""
import numpy as np
from sim.generators import generate, NODES
from sim.observe import observe
from sim.statespace import to_grid, em_fit
from sim.switching import _viterbi_mindur, match_switches
from sim.pipeline import identify, TOL
from sim.ensemble import generate_ensemble
from sim.density import PASS, FAIL, UNIDENTIFIABLE


# --- cell 1: measurement noise must stop reading as memory -------------------

def test_m_gate_is_not_fooled_by_measurement_noise():
    """v0 finding 1: on a planted-linear world at high measurement noise, the M
    axis fired because AR(1)-on-y is a straw man. AR(6) really does beat AR(1)
    here — the point is that it does NOT beat the state space, so M stays off."""
    beat_ar1 = 0
    for seed in (0, 4):
        tj = generate("M1", T=400, seed=seed)
        fit = identify(observe(tj, meas_noise=0.3, seed=seed), seed=seed, s_null=False, m_null=False)
        assert not fit.axes["M"], (seed, fit.gains)          # the gate holds
        # v2 demoted the AR statistic to a diagnostic; it still shows the illusion
        if fit.gains["M_diag_vs_AR1"] > TOL:
            beat_ar1 += 1
    assert beat_ar1 >= 1, "test is vacuous unless AR(6) beats AR(1) on some seed"


# --- cell 2: regimes, with duration and with timing --------------------------

def test_mindur_decode_emits_no_short_interior_runs():
    """The hard constraint, on a likelihood built to flip every step."""
    rng = np.random.default_rng(0)
    n, D = 300, 25
    logB = np.zeros((n, 2))
    logB[np.arange(n), np.arange(n) % 2] = 5.0               # alternate every step
    logB += 0.01 * rng.normal(size=logB.shape)
    P = np.array([[0.5, 0.5], [0.5, 0.5]])                   # prior offers no stickiness
    z = _viterbi_mindur(logB, P, np.array([0.5, 0.5]), D)
    runs = np.diff(np.flatnonzero(np.r_[1, np.diff(z) != 0, 1]))
    assert all(r >= D for r in runs[:-1]), runs              # trailing run may be cut


def test_h_gate_recovers_planted_switch_times():
    tj = generate("M1+H", T=600, seed=3)
    fit = identify(observe(tj, meas_noise=0.05, seed=3), seed=3, s_null=False, m_null=False)
    assert fit.axes["H"], fit.gains
    m = match_switches(tj.truth["switches"], fit.switches, tol=10)
    assert m["recall"] >= 0.4 and m["precision"] >= 0.5, m
    assert m["mae"] <= 5.0, m                                # timing, not just presence


# --- cell 3: process noise vs measurement noise ------------------------------

def test_statespace_separates_process_from_measurement_noise():
    """The decomposition cell 3 asks for: Q/(Q+R) must be lower on a world with
    no process noise than on the same world with process noise."""
    for seed in (0, 1, 2):
        q = {}
        for pn in (0.0, 0.15):
            tj = generate("M1", T=600, seed=seed, process_noise=pn)
            y, u, mk = to_grid(observe(tj, meas_noise=0.05, seed=seed))
            q[pn] = em_fit(y, u, mk).q_frac
        assert q[0.0] < q[0.15], (seed, q)


def test_s_gate_fires_on_a_stochastic_world():
    tj = generate("M1", T=400, seed=1)
    fit = identify(observe(tj, meas_noise=0.05, seed=1), seed=1, m_null=False)
    assert fit.axes["S"], fit.gains
    assert fit.gains["S"] > fit.gains["S_null_q95"]


def test_s_axis_stays_out_of_the_node_string():
    """S is reported, never composed into the node, so the recovery map keeps
    comparing like with like against v0."""
    tj = generate("M1", T=400, seed=1)
    fit = identify(observe(tj, meas_noise=0.05, seed=1), seed=1, s_null=False, m_null=False)
    assert "S" in fit.axes and "S" not in fit.node


# --- cell "ensemble": the generator bug the Wiener work uncovered -------------

def test_no_generator_diverges():
    """M1+N linearises to (A - alpha e0 e0') far from the origin, not to A, so a
    stable draw of A did not make the node stable: ~18% of seeds ran away to 1e78.
    Silent from v0 to v1 because the 32-cell smoke grid happened to miss it."""
    for node in NODES:
        worst = max(float(np.abs(generate(node, T=600, seed=s).x).max()) for s in range(40))
        assert worst < 1e3, (node, worst)


def test_double_well_is_still_bistable():
    """The stability fix must not flatten the well it was protecting."""
    crossings = 0
    for seed in range(6):
        x0 = generate("M1+N", T=600, seed=seed).x[:, 0]
        crossings += int(np.sum(np.diff(np.sign(x0)) != 0) > 0)
    assert crossings >= 4, crossings


# --- cell "ensemble" step 1: the Wiener null ---------------------------------

def test_wiener_null_blocks_nonlinearity_made_by_the_observation_map():
    """Finding 5: a tanh observation map fabricates N. The linear surrogate is
    blind to it — it asks whether a linear process in y could have done this,
    and the honest answer is no. The Wiener null asks the right question."""
    fired, bound_by_linear = 0, 0
    for seed in range(6):
        tj = generate("M1", T=600, seed=seed)
        fit = identify(observe(tj, meas_noise=0.05, nonlinear_h=True, seed=seed),
                       seed=seed, s_null=False, m_null=False)
        fired += int(bool(fit.axes["N"]))
        bound_by_linear += int(fit.hardest["N"] == "linear")
        assert fit.gains["N_null_q95"] == max(fit.gains["N_null_linear_q95"],
                                              fit.gains["N_null_wiener_q95"],
                                              fit.gains["N_null_switching_q95"])
    assert fired <= 1, f"N fired on {fired}/6 tanh-observed linear worlds"
    # the claim is about the LINEAR null, and it is now stated directly: on a world
    # whose nonlinearity lives in h, the parametric-linear surrogate is the weakest
    # of the three and must never be the one the gate has to clear. Which of the two
    # honest nulls binds is not the point and varies by seed.
    assert bound_by_linear == 0, "the linear null should never be the binding one here"


def test_wiener_null_does_not_cost_power_on_real_nonlinearity():
    fired = 0
    for seed in range(6):
        tj = generate("M1+N", T=600, seed=seed)
        fit = identify(observe(tj, meas_noise=0.05, seed=seed), seed=seed, s_null=False, m_null=False)
        fired += int(bool(fit.axes["N"]))
    assert fired >= 3, f"N only fired on {fired}/6 planted-nonlinear worlds"


# --- cell "boundedness" step 3: the M axis is tri-state ----------------------

def test_m_axis_is_unidentifiable_on_a_single_trajectory():
    """Finding 8 measured the ceiling: the memory kernel beats the best free d+k
    state space by 0-11% even handed the TRUE kernel, against an estimation-noise
    floor of +-0.14. That is not 'no memory', it is 'this design cannot tell', and
    the two must not be the same value — a False here would let the recovery map
    score an undecidable axis as a correct rejection."""
    for node in ("M1+M", "M1"):
        tj = generate(node, T=400, seed=0)
        fit = identify(observe(tj, meas_noise=0.05, seed=0), seed=0,
                       s_null=False, m_null=False)
        assert fit.verdicts["M"] == UNIDENTIFIABLE, (node, fit.verdicts)
        assert fit.axes["M"] is False                      # never composed into the node
        assert "+M" not in fit.node
        assert np.isfinite(fit.gains["M"])                 # still reported as a diagnostic


def test_m_axis_is_decided_over_replicates():
    """Same contest, thirty replicates of one person, and it separates."""
    mem = generate_ensemble("M1+M", n_traj=30, mode="within", T=400, seed=0, meas_noise=0.05)
    mk = generate_ensemble("M1", n_traj=30, mode="within", T=400, seed=0, meas_noise=0.05)
    f_mem = identify(mem.obs, seed=0, s_null=False, m_null=False)
    f_mk = identify(mk.obs, seed=0, s_null=False, m_null=False)
    assert f_mem.verdicts["M"] == PASS, f_mem.notes
    assert f_mk.verdicts["M"] == FAIL, f_mk.notes
    assert f_mem.gains["M_h3"] > f_mk.gains["M_h3"]


def test_too_few_replicates_stay_unidentifiable():
    """The verdict does not improve just because a list was passed."""
    small = generate_ensemble("M1+M", n_traj=4, mode="within", T=300, seed=0, meas_noise=0.05)
    fit = identify(small.obs, seed=0, s_null=False, m_null=False)
    assert fit.verdicts["M"] == UNIDENTIFIABLE, fit.notes
    assert "4 replicates" in " ".join(fit.notes)


def test_other_axes_keep_a_binary_verdict():
    tj = generate("M1", T=400, seed=0)
    fit = identify(observe(tj, meas_noise=0.05, seed=0), seed=0, s_null=False, m_null=False)
    for k in ("N", "H"):
        assert fit.verdicts[k] in (PASS, FAIL)
        assert fit.axes[k] == (fit.verdicts[k] == PASS)


# --- cell "lyapunov" step 2: the replication factor in the grid ---------------

def test_reps_per_person_changes_the_M_verdict_and_nothing_else_silently():
    """reps_per_person = 1 must reproduce the single-trajectory design exactly:
    M undecidable. Above MIN_REPLICATES the same cell gets a real verdict."""
    from sim.recovery import run_cell
    solo = run_cell("M1+M", 300, 0.05, 1.0, False, 0, reps_per_person=1)
    many = run_cell("M1+M", 300, 0.05, 1.0, False, 0, reps_per_person=10)
    assert solo["m_verdict"] == UNIDENTIFIABLE
    assert solo["reps_per_person"] == 1 and many["reps_per_person"] == 10
    assert many["m_verdict"] in (PASS, FAIL)          # decided, whichever way
    assert solo["undecided"] == 1 and many["undecided"] == 0


def test_replication_is_within_person():
    """The grid's replicates must share the structure; if they did not, the cell
    would be a between-person ensemble and H3 would mean something else."""
    from sim.ensemble import generate_ensemble
    ens = generate_ensemble("M1+M", n_traj=5, mode="within", T=300, seed=7)
    As = ens.truth["A_per_traj"]
    for A in As[1:]:
        assert np.allclose(A, As[0])


# --- cell "switching null" step 1: the N gate gets a third null --------------

def _n_fires(node, seeds, T=600, noise=0.05):
    fired = 0
    for s in seeds:
        tj = generate(node, T=T, seed=s)
        fit = identify(observe(tj, meas_noise=noise, seed=s), seed=s,
                       s_null=False, m_null=False)
        fired += int(bool(fit.axes.get("N")))
    return fired


def test_switching_null_blocks_N_on_a_two_regime_world():
    """Grid v3's dominant finding: a two-regime world fires N on ~25% of runs.
    Piecewise-linear dynamics are locally nonlinear — each regime has its own
    slope — so a polynomial recovers what one linear map misses. The null asks
    whether a stable linear SWITCHING process could have produced the data."""
    assert _n_fires("M1+H", range(20)) <= 2


def test_switching_null_leaves_real_nonlinearity_detectable():
    """It must not cost the axis its reason to exist."""
    assert _n_fires("M1+N", range(20)) >= 5


def test_N_reports_which_of_the_three_nulls_bound_it():
    tj = generate("M1+H", T=600, seed=0)
    fit = identify(observe(tj, meas_noise=0.05, seed=0), seed=0,
                   s_null=False, m_null=False)
    qs = {k: fit.gains[f"N_null_{k}_q95"] for k in ("linear", "wiener", "switching")}
    assert fit.hardest["N"] in qs
    assert fit.gains["N_null_q95"] == max(qs.values())
    assert qs[fit.hardest["N"]] == max(qs.values())


def test_switching_surrogates_are_stable_switching_processes():
    """A surrogate that diverges is a null of nothing. The fitted pair must admit
    a common quadratic Lyapunov function, or be projected until it does."""
    from sim.statespace import to_grid
    from sim.switching_null import switching_null, project_to_stable, _A_of
    from sim.stability import common_lyapunov
    from sim.pipeline import _gain_fn
    for seed in range(6):
        tj = generate("M1+H", T=600, seed=seed)
        ob = observe(tj, meas_noise=0.05, seed=seed)
        y, u, mk = to_grid(ob)
        kt = int(len(y) * 0.7)
        g, info = switching_null(y, u, mk, kt, _gain_fn(ob, u, mk),
                                 np.random.default_rng(seed), n_surr=5)
        assert info["lyapunov_ok"], (seed, info)
        assert np.all(np.isfinite(g))
        assert 0.0 < info["gamma"] <= 1.0


def test_projection_rescues_an_unstable_pair():
    """Opposite shears have no common P; scaling them down until one exists is
    what keeps a surrogate simulable."""
    from sim.switching_null import project_to_stable, _A_of
    from sim.stability import common_lyapunov
    W = np.zeros((2, 4, 2))                      # Phi = [y(2), u(1), 1]
    W[0][:2] = np.array([[0.9, 0.0], [5.0, 0.9]])
    W[1][:2] = np.array([[0.9, 5.0], [0.0, 0.9]])
    assert common_lyapunov(_A_of(W, 2))[0] is None
    W2, gamma, ok = project_to_stable(W, 2)
    assert ok and gamma < 1.0
    assert common_lyapunov(_A_of(W2, 2))[0] is not None
