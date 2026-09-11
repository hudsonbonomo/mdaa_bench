"""Ensembles of trajectories from one lattice node — the Paper 3 branch.

Findings 2 and 4 of the v1 bench both end in the same place: on a SINGLE
trajectory the M and S axes sit at the edge of identifiability. Replicates are
the way out, and they are also what Paper 3 is about — a density rho(x, t)
flowing, rather than one path.

Two modes, and the distinction is the whole point (Molenaar):

  within   replicates of ONE person: same A, same B, same intervention
           schedule, different realisation. The ensemble is a sample from one
           process, so pooling it estimates that process's density.
  between  different people: each trajectory gets its own A drawn around a
           common mean at a declared dispersion radius. Pooling is legitimate
           only if the spread is small enough that the pooled density still
           describes any individual. When it is not, the pooled density goes
           bimodal and says something true of nobody — which is what H1 tests.

`truth` is recorded on the Ensemble but is NEVER handed to density.py. The
gates receive `obs` and the DESIGN facts an analyst genuinely knows (how many
trajectories, and whether they sampled one person or many) — never A, never the
kernel, never the dispersion radius that produced the data.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import zlib
import numpy as np
from .generators import generate, _stable_matrix
from .observe import observe, Observed

MODES = ("within", "between")
OFFSET_SCALE = 4.0      # set-point separation at spread = 1, in state units


@dataclass
class Ensemble:
    obs: list                       # list[Observed] — all the gates ever see
    mode: str
    n_traj: int
    truth: dict = field(default_factory=dict)     # recovery.py only

    def design(self) -> dict:
        """The facts an analyst has without knowing the generator."""
        return dict(mode=self.mode, n_traj=self.n_traj)


def _cell_seed(*parts) -> int:
    return zlib.crc32(repr(parts).encode()) % (2 ** 31)


def _ball(rng, d: int, radius: float) -> np.ndarray:
    """Uniform draw from the d-ball of the given radius."""
    v = rng.normal(size=d)
    v = v / (np.linalg.norm(v) + 1e-12)
    return v * radius * rng.random() ** (1.0 / d)


def generate_ensemble(node: str, n_traj: int = 30, mode: str = "within", T: int = 400,
                      seed: int = 0, meas_noise: float = 0.05, keep_frac: float = 1.0,
                      nonlinear_h: bool = False, A_radius: float = 0.0,
                      loc_radius: float = 0.0, process_noise: float = 0.15,
                      rho: float = 0.9) -> Ensemble:
    """N trajectories from the SAME node. Seeds are CRC32 of the cell tuple, as
    everywhere else in the bench, so an ensemble is reproducible across processes.

    Between-person dispersion is TWO independent radii, because they do different
    things and v2 welded them to one knob:

      A_radius    how differently people MOVE. A_i = (1-r) A_mean + r A_rand,
                  renormalised to the same spectral radius, so the laws differ but
                  everyone stays stable. On its own this does NOT break pooling:
                  every density stays centred on the same point, and H1 keeps
                  passing at any radius. That is finding 11 of v2.
      loc_radius  where people SIT. Each person draws a set point x* uniformly
                  from the ball of this radius, in state units, and its dynamics
                  run in (x - x*). The constant fed to the generator is solved for,
                  off = (I - A_i) x*, so the set point lands exactly on x*;
                  injecting a constant instead puts it at (I - A_i)^-1 off, which
                  blows up when (I - A_i) is near singular.

    This is the pair Molenaar's objection is actually about, and only the second
    half of it moves the pooled density.
    """
    assert mode in MODES, mode
    d = 2
    base_rng = np.random.default_rng(_cell_seed("ens", node, mode, T, seed,
                                                A_radius, loc_radius))
    A_mean = _stable_matrix(np.random.default_rng(seed), d, rho)

    obs_list, As, stars = [], [], []
    for i in range(n_traj):
        ns = _cell_seed("traj", node, mode, T, seed, i)
        A_i, off, x_star = None, None, np.zeros(d)
        if mode == "between":
            if A_radius > 0:
                A_rand = _stable_matrix(base_rng, d, rho)
                A_i = (1 - A_radius) * A_mean + A_radius * A_rand
                A_i = A_i / max(abs(np.linalg.eigvals(A_i))) * rho
            if loc_radius > 0:
                x_star = _ball(base_rng, d, loc_radius)
                off = (np.eye(d) - (A_mean if A_i is None else A_i)) @ x_star
        traj = generate(node, T=T, d=d, seed=seed, process_noise=process_noise, rho=rho,
                        noise_seed=ns, A_override=A_i, offset=off)
        As.append(traj.truth["A"]); stars.append(x_star)
        obs_list.append(observe(traj, meas_noise=meas_noise, keep_frac=keep_frac,
                                nonlinear_h=nonlinear_h, seed=ns))
    truth = dict(node=node, mode=mode, A_radius=A_radius, loc_radius=loc_radius,
                 A_mean=A_mean, A_per_traj=As, set_points=stars,
                 process_noise=process_noise, meas_noise=meas_noise, T=T)
    return Ensemble(obs=obs_list, mode=mode, n_traj=n_traj, truth=truth)


def pooled_window(obs_list, t0: int, t1: int) -> np.ndarray:
    """Every observation from every trajectory whose time falls in [t0, t1).
    Gaps are simply absent — nothing is interpolated to fill a window."""
    out = [o.y[(o.t >= t0) & (o.t < t1)] for o in obs_list]
    out = [a for a in out if len(a)]
    return np.vstack(out) if out else np.empty((0, obs_list[0].y.shape[1]))


def windows(obs_list, n_windows: int = 6):
    """Equal-width time windows spanning the observed clock."""
    hi = max(int(o.t[-1]) for o in obs_list) + 1
    edges = np.linspace(0, hi, n_windows + 1).astype(int)
    return [(int(a), int(b)) for a, b in zip(edges[:-1], edges[1:]) if b > a]
