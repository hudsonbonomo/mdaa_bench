"""Standing worlds — four mechanisms, one observable trajectory.

The decision bench (`decision/`) plants the CORRECT ACTION. This one plants the
STANDING OF THE RECORD: at every observation there is a state of vigencia
(applicable / out_of_scope / aged / unevaluable) that is true by construction,
recorded in `planted` and never handed to a reader. PREREGISTRO_v1 §3.
Generators only: no reader, no runner, no execution. The structural condition of
each world is asserted here, so a world that stopped being the world it claims to
be fails at construction instead of at analysis.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np

__all__ = ["WORLDS", "SIGNALS", "STATES", "STRATEGY", "NOISE_UNCLEAR", "ALPHA_PATH",
           "MAPPED_VALUES", "RECONCILIATIONS", "Observation", "StandingWorld",
           "load_alpha", "make_world", "make_world_a", "make_world_b",
           "make_world_c", "make_world_d"]

WORLDS = ("A", "B", "C", "D")
SIGNALS = ("BETTER", "WORSE", "UNCLEAR")
STATES = ("applicable", "out_of_scope", "aged", "unevaluable")
STRATEGY = "s_star"                 # the target strategy s*
ALPHA_PATH = Path(__file__).resolve().parent / "alpha_frozen.json"
MAPPED_VALUES = ("r0",)             # world D: values a PARTIAL reconciliation carries over
RECONCILIATIONS = ("none", "total", "partial")


def load_alpha(path: Path | str = ALPHA_PATH) -> dict:
    """The frozen policy, as bytes on disk. No generator hardcodes what lives here."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


# PREREGISTRO_v1 §3: UNCLEAR noise is read from the frozen file, never inlined.
NOISE_UNCLEAR = float(load_alpha()["signal_noise_unclear"])


@dataclass(frozen=True)
class Observation:
    strategy: str
    conditions: dict[str, str]
    signal: str                     # BETTER | WORSE | UNCLEAR
    t: int


@dataclass(frozen=True)
class StandingWorld:
    observations: list[Observation]
    vocabulary_events: list[dict]
    planted: dict                   # record index -> ground truth dict
    params: dict


def _draw(rng: np.random.Generator, p_better: float, noise_unclear: float) -> str:
    """One signal. p_unclear is fixed noise; WORSE takes what BETTER leaves."""
    p_worse = 1.0 - p_better - noise_unclear
    assert p_worse >= -1e-12, f"signal mass negative: p_better={p_better}, noise={noise_unclear}"
    return str(rng.choice(SIGNALS, p=[p_better, max(p_worse, 0.0), noise_unclear]))


def make_world_a(T: int, seed: int, noise_unclear: float = NOISE_UNCLEAR,
                 p0: float = 0.80, p1: float = 0.35) -> StandingWorld:
    """A — true aging: fixed logged condition, p(BETTER) decays p0 -> p1 over T."""
    rng = np.random.default_rng(seed)
    p = [p0 + (p1 - p0) * (t / (T - 1)) for t in range(T)] if T > 1 else [p0]
    assert p1 <= p0, f"World A: decay requires p1 <= p0, got p0={p0}, p1={p1}"
    assert all(p[t] >= p[t + 1] for t in range(T - 1)), "World A: monotonicity violated"
    assert p[0] == p0 and p[-1] == p1, f"World A: schedule must run {p0} -> {p1}"
    obs, planted = [], {}
    for t in range(T):
        obs.append(Observation(STRATEGY, {"env": "stable"}, _draw(rng, p[t], noise_unclear), t))
        # aged past the alpha window, applicable inside it: the reader resolves which.
        planted[t] = {"planted_state": "aged_or_applicable", "p_better": p[t]}
    return StandingWorld(obs, [], planted,
                         {"world": "A", "T": T, "seed": seed, "p0": p0, "p1": p1,
                          "noise_unclear": noise_unclear, "p_schedule": p})


def make_world_b(T: int, seed: int, logged: bool, noise_unclear: float = NOISE_UNCLEAR,
                 p_c1: float = 0.80, p_c2: float = 0.35) -> StandingWorld:
    """B — condition swap: c1/c2 alternate in blocks of T/4; `unlogged` records all as c1."""
    assert T % 4 == 0, f"World B: T must be divisible by 4, got {T}"
    rng = np.random.default_rng(seed)
    block = T // 4
    true_cond = [("c1", "c2", "c1", "c2")[t // block] for t in range(T)]
    blocks = [true_cond[i * block:(i + 1) * block] for i in range(4)]
    assert len(blocks) == 4 and all(len(b) == block for b in blocks), \
        f"World B: expected 4 blocks of {block}, got {[len(b) for b in blocks]}"
    assert [b[0] for b in blocks] == ["c1", "c2", "c1", "c2"] and \
        all(len(set(b)) == 1 for b in blocks), "World B: block alternation violated"
    current = true_cond[-1]         # the condition in force when the record is read
    obs, planted = [], {}
    for t in range(T):
        c = true_cond[t]
        p_better = p_c1 if c == "c1" else p_c2
        recorded = c if logged else "c1"
        obs.append(Observation(STRATEGY, {"env": recorded}, _draw(rng, p_better, noise_unclear), t))
        state = ("applicable" if c == current else "out_of_scope") if logged else None
        planted[t] = {"planted_state": state, "true_condition": c, "logged": logged}
    assert len(obs) == T, f"World B: expected {T} observations, got {len(obs)}"
    seen = [o.conditions["env"] for o in obs]
    assert (seen == true_cond) if logged else (set(seen) == {"c1"}), \
        "World B: the `logged` factor must decide what the record shows"
    return StandingWorld(obs, [], planted,
                         {"world": "B", "T": T, "seed": seed, "logged": logged,
                          "block": block, "p_c1": p_c1, "p_c2": p_c2,
                          "current_condition": current, "noise_unclear": noise_unclear,
                          "indeterminate_by_construction": not logged})


def make_world_c(T: int, seed: int, noise_unclear: float = NOISE_UNCLEAR,
                 p0: float = 0.80, p_c: float = 0.25) -> StandingWorld:
    """C — the person forgot: one step drop at tau = T/2, no ramp. Nothing is aged."""
    rng = np.random.default_rng(seed)
    tau = T // 2
    p = [p0 if t < tau else p_c for t in range(T)]
    assert p[tau - 1] == p0 and p[tau] == p_c, f"World C: no step at tau={tau}"
    assert all(p[t] == p0 for t in range(tau)) and all(p[t] == p_c for t in range(tau, T)), \
        "World C: ramp detected, the drop must be a single discontinuity"
    obs, planted = [], {}
    for t in range(T):
        obs.append(Observation(STRATEGY, {"env": "stable"}, _draw(rng, p[t], noise_unclear), t))
        # applicable by merit of the world: the correct reading is statute B with order.
        planted[t] = {"planted_state": "applicable", "correct_reading": "B_with_order",
                      "phase": "pre_tau" if t < tau else "post_tau"}
    return StandingWorld(obs, [], planted,
                         {"world": "C", "T": T, "seed": seed, "tau": tau, "p0": p0,
                          "p_c": p_c, "noise_unclear": noise_unclear, "p_schedule": p})


def make_world_d(T: int, seed: int, noise_unclear: float = NOISE_UNCLEAR,
                 p0: float = 0.80, force_reconciliation: str | None = None) -> StandingWorld:
    """D — vocabulary change: c1 renamed c1_prime at T/3, maybe reconciled at 2T/3.

    The signal does not move (p0 throughout): this world tests the vocabulary, not
    the trajectory. `regime` carries the values a PARTIAL reconciliation fails to map.
    `force_reconciliation` pins the branch — None draws it (1/2 event, then 1/2 total
    / 1/2 partial, PREREGISTRO_v1 §3); "none"|"total"|"partial" fix it. Both draws are
    consumed either way, so a seed's observation stream does not move when pinned.
    """
    assert force_reconciliation is None or force_reconciliation in RECONCILIATIONS, \
        f"World D: force_reconciliation must be None or one of {RECONCILIATIONS}"
    rng = np.random.default_rng(seed)
    tau1, tau2 = T // 3, 2 * T // 3
    events = [{"type": "rename", "t": tau1, "from": "c1", "to": "c1_prime"}]
    drawn_event, drawn_kind = rng.random() < 0.5, rng.random() < 0.5
    if force_reconciliation is None:
        kind = ("total" if drawn_kind else "partial") if drawn_event else None
    else:
        kind = None if force_reconciliation == "none" else force_reconciliation
    if kind is not None:
        events.append({"type": "reconciliation", "t": tau2, "kind": kind})
    renames = [e for e in events if e["type"] == "rename"]
    recons = [e for e in events if e["type"] == "reconciliation"]
    assert len(renames) == 1 and renames[0]["t"] == tau1, \
        f"World D: expected exactly one rename at {tau1}, got {renames}"
    assert len(recons) <= 1 and all(e["t"] == tau2 for e in recons), \
        f"World D: at most one reconciliation at {tau2}, got {recons}"
    obs, planted = [], {}
    for t in range(T):
        regime = str(rng.choice(("r0", "r1")))
        label = "c1" if t < tau1 else "c1_prime"
        obs.append(Observation(STRATEGY, {"env": label, "regime": regime},
                               _draw(rng, p0, noise_unclear), t))
        if t < tau1:
            if kind == "total":
                final = "applicable"
            elif kind == "partial":
                final = "applicable" if regime in MAPPED_VALUES else "out_of_scope"
            else:
                final = "unevaluable"
            planted[t] = {"planted_state": final, "pre_tau1": True,
                          "state_between_tau1_tau2": "unevaluable", "regime": regime}
        else:
            planted[t] = {"planted_state": "applicable", "pre_tau1": False,
                          "state_between_tau1_tau2": "applicable", "regime": regime}
    labels = [o.conditions["env"] for o in obs]
    switches = [t for t in range(1, T) if labels[t] != labels[t - 1]]
    assert switches == [tau1], f"World D: label must change exactly once at {tau1}, got {switches}"
    pre = [planted[t]["planted_state"] for t in range(tau1)]
    if kind == "partial":
        assert "unevaluable" not in pre, "World D: a partial reconciliation leaves no unevaluable"
    elif kind is None:
        assert set(pre) <= {"unevaluable"}, "World D: without an event pre-tau1 stays unevaluable"
    return StandingWorld(obs, events, planted,
                         {"world": "D", "T": T, "seed": seed, "tau1": tau1, "tau2": tau2,
                          "p0": p0, "noise_unclear": noise_unclear,
                          "reconciliation": kind, "forced": force_reconciliation,
                          "mapped_values": list(MAPPED_VALUES)})


_DISPATCH = {"A": make_world_a, "B": make_world_b, "C": make_world_c, "D": make_world_d}


def make_world(world: str, **kwargs) -> StandingWorld:
    """Route to the generator of `world`. Keyword arguments are the generator's own."""
    assert world in WORLDS, f"unknown world {world!r}, expected one of {WORLDS}"
    return _DISPATCH[world](**kwargs)
