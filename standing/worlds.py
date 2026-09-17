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
           "MAPPED_VALUES", "RECONCILIATIONS", "KEY_OLD", "KEY_NEW", "COND_VALUE",
           "Observation", "StandingWorld", "load_alpha", "make_world", "make_world_a",
           "make_world_b", "make_world_c", "make_world_d"]

WORLDS = ("A", "B", "C", "D")
SIGNALS = ("BETTER", "WORSE", "UNCLEAR")
STATES = ("applicable", "out_of_scope", "aged", "unevaluable")
STRATEGY = "s_star"                 # the target strategy s*
ALPHA_PATH = Path(__file__).resolve().parent / "alpha_frozen.json"
KEY_OLD, KEY_NEW, COND_VALUE = "c1", "c1_prime", "stable"   # world D: the KEY renamed at tau1 (§3)
MAPPED_VALUES = ("legacy",)         # world D: values a PARTIAL reconciliation carries over
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
    """D — vocabulary change: the KEY c1 is renamed c1_prime at tau1 = T/3 (same values,
    §3), maybe reconciled at tau2 = 2T/3; events use the plugin's VocabularyEvent fields.
    The signal does not move (p0 throughout). The condition is FIXED, so a TOTAL
    reconciliation brings every pre-tau1 record back, while a PARTIAL one — covering only
    MAPPED_VALUES, which the recorded value is not among — leaves them `out_of_scope` and
    never `unevaluable`. `force_reconciliation` pins the branch; both draws are consumed
    either way, so a seed's stream does not move when the branch is pinned.
    """
    assert (force_reconciliation is None or force_reconciliation in RECONCILIATIONS) \
        and COND_VALUE not in MAPPED_VALUES, \
        f"World D: force_reconciliation in {RECONCILIATIONS}; {COND_VALUE!r} has no correspondent"
    rng = np.random.default_rng(seed)
    tau1, tau2 = T // 3, 2 * T // 3
    events = [{"kind": "KEY_RENAMED", "seq": tau1, "from": KEY_OLD, "to": KEY_NEW}]
    drawn_event, drawn_kind = rng.random() < 0.5, rng.random() < 0.5
    drawn = ("total" if drawn_kind else "partial") if drawn_event else None
    kind = drawn if force_reconciliation is None else \
        (None if force_reconciliation == "none" else force_reconciliation)
    vmap = {"valueMap": {v: v for v in MAPPED_VALUES}} if kind == "partial" else {}
    if kind is not None:    # a valueMap covering only MAPPED_VALUES is PARTIAL; absent is TOTAL
        events.append({"kind": "RECONCILED", "seq": tau2,
                       "oldKey": KEY_OLD, "newKey": KEY_NEW, **vmap})
    renames = [e for e in events if e["kind"] == "KEY_RENAMED"]
    recons = [e for e in events if e["kind"] == "RECONCILED"]
    assert len(renames) == 1 and renames[0] == {"kind": "KEY_RENAMED", "seq": tau1,
                                                "from": KEY_OLD, "to": KEY_NEW}, \
        f"World D: expected exactly one rename at {tau1}, VocabularyEvent-shaped, got {renames}"
    assert len(recons) <= 1 and all(e["seq"] == tau2 for e in recons) and \
        all(set(e) <= {"kind", "seq", "oldKey", "newKey", "valueMap"} for e in recons) and \
        (kind == "partial") == any("valueMap" in e for e in recons), \
        f"World D: at most one reconciliation at {tau2}, VocabularyEvent-shaped, got {recons}"
    mapped = COND_VALUE in MAPPED_VALUES
    pre_final = {"total": "applicable",
                 "partial": "applicable" if mapped else "out_of_scope"}.get(kind, "unevaluable")
    obs, planted = [], {}
    for t in range(T):
        key, early = (KEY_OLD, True) if t < tau1 else (KEY_NEW, False)
        obs.append(Observation(STRATEGY, {key: COND_VALUE}, _draw(rng, p0, noise_unclear), t))
        planted[t] = {"planted_state": pre_final if early else "applicable",
                      "pre_tau1": early, "key": key, "value": COND_VALUE,
                      "state_between_tau1_tau2": "unevaluable" if early else "applicable",
                      "value_mapped": mapped if early else True}
    keys = [next(iter(o.conditions)) for o in obs]
    switches = [t for t in range(1, T) if keys[t] != keys[t - 1]]
    assert switches == [tau1] and set(keys[:tau1]) == {KEY_OLD} and set(keys[tau1:]) == {KEY_NEW} \
        and {v for o in obs for v in o.conditions.values()} == {COND_VALUE}, \
        f"World D: only the KEY moves, {KEY_OLD} -> {KEY_NEW}, once at {tau1}; got {switches}"
    pre = {planted[t]["planted_state"] for t in range(tau1)}
    want = {None: {"unevaluable"}, "total": {"applicable"},
            "partial": {"applicable", "out_of_scope"}}[kind]
    assert pre <= want, f"World D: pre-tau1 under reconciliation={kind} must be {want}, got {pre}"
    return StandingWorld(obs, events, planted,
                         {"world": "D", "T": T, "seed": seed, "tau1": tau1, "tau2": tau2,
                          "p0": p0, "noise_unclear": noise_unclear, "reconciliation": kind,
                          "forced": force_reconciliation, "key_old": KEY_OLD, "key_new": KEY_NEW,
                          "cond_value": COND_VALUE, "mapped_values": list(MAPPED_VALUES)})


_DISPATCH = {"A": make_world_a, "B": make_world_b, "C": make_world_c, "D": make_world_d}


def make_world(world: str, **kwargs) -> StandingWorld:
    """Route to the generator of `world`. Keyword arguments are the generator's own."""
    assert world in WORLDS, f"unknown world {world!r}, expected one of {WORLDS}"
    return _DISPATCH[world](**kwargs)
