"""Adaptive worlds -- five mechanisms planted for policy adjustment testing.
PREREGISTRO rascunho v0.3 §4. Generators assert structural conditions on
planted values. Parameters from policy_frozen.json.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import math
import numpy as np

__all__ = ["WORLDS", "SIGNALS", "AdaptiveWorld", "load_policy",
           "make_world", "make_world_s", "make_world_n", "make_world_k",
           "make_world_v", "make_world_r", "c1_blocks", "condition_at"]
WORLDS = ("S", "N", "K", "V", "R")
SIGNALS = ("BETTER", "WORSE", "UNCLEAR")
POLICY_PATH = Path(__file__).resolve().parent / "policy_frozen.json"

def load_policy(path: Path | str = POLICY_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

_P = load_policy()
_L = int(_P["stream"]["block_length"])
_KEY, _STRATEGY = str(_P["stream"]["key"]), str(_P["stream"]["strategy"])
_TARGET, _W0 = str(_P["stream"]["target"]), int(_P["declared"]["warrant_window"])

@dataclass(frozen=True)
class AdaptiveWorld:
    observations: list[dict]
    declarations: list[dict]
    vocabulary_events: list[dict]
    condition: dict[str, str]
    planted: dict
    params: dict

def _draw(rng: np.random.Generator, p_better: float) -> str:
    assert 1.0 - p_better >= -1e-12
    return str(rng.choice(["BETTER", "WORSE"],
               p=[p_better, max(1.0 - p_better, 0.0)]))

def _obs(t: int, signal: str, key: str, cond: str) -> dict:
    return {"seq": t, "signal": signal, "conditions": {key: cond},
            "strategy": [_STRATEGY], "id": f"obs-{t}",
            "journeyId": "bench", "note": "",
            "provenance": {"kind": "PERSON"}}

def _sched(T: int) -> list[str]:
    return [_TARGET if (t // _L) % 2 == 0 else "c2" for t in range(T)]

def _gen_obs(T, seed, sched, p_fn):
    rng = np.random.default_rng(seed)
    return [_obs(t, _draw(rng, p_fn(t) if sched[t] == _TARGET else 0.5),
                 _KEY, sched[t]) for t in range(T)], rng

# c1_blocks and condition_at live in world_utils.py (200-line split).
def c1_blocks(world: AdaptiveWorld) -> list[tuple[int, int]]:
    from .world_utils import c1_blocks as _c1b
    return _c1b(world)

def condition_at(world: AdaptiveWorld, seq: int) -> dict:
    from .world_utils import condition_at as _ca
    return _ca(world, seq)

def _assert_block_integrity(world: AdaptiveWorld) -> None:
    from .world_utils import assert_block_integrity
    assert_block_integrity(world)

def make_world_s(T: int, seed: int) -> AdaptiveWorld:
    """S -- short ruler, stable world. p(BETTER|c1)=p constant."""
    p = float(_P["worlds"]["S"]["p"])
    sc = _sched(T)
    obs, _ = _gen_obs(T, seed, sc, lambda t: p)
    w = AdaptiveWorld(obs, [{"seq": 0, "window": _W0, "by": "person"}],
                      [], {_KEY: _TARGET},
                      {"world": "S", "planted": "extending_is_correct"},
                      {"world": "S", "T": T, "seed": seed, "p": p})
    assert w.planted["planted"] == "extending_is_correct"
    _assert_block_integrity(w)
    return w

def make_world_n(T: int, seed: int) -> AdaptiveWorld:
    """N -- right ruler, isolated disagreement. p alternates hi/lo."""
    p_hi = float(_P["worlds"]["N"]["p_hi"])
    p_lo = float(_P["worlds"]["N"]["p_lo"])
    regime = int(_P["worlds"]["N"]["regime_rounds"])
    bpr = regime // (2 * _L)
    assert bpr * (2 * _L) == regime, "regime must be multiple of 2*L"
    sc = _sched(T)
    c1_count, obs_list, p_schedule = 0, [], []
    rng = np.random.default_rng(seed)
    for t in range(T):
        if t == 0 and sc[t] == _TARGET:
            c1_count = 1
        elif t > 0 and t % _L == 0 and sc[t] == _TARGET and sc[t-1] != _TARGET:
            c1_count += 1
        ridx = (c1_count - 1) // bpr if c1_count > 0 else 0
        p_t = p_hi if ridx % 2 == 0 else p_lo
        if sc[t] == _TARGET and (t % _L == 0) and (t == 0 or sc[t-1] != _TARGET):
            p_schedule.append(p_t)
        obs_list.append(_obs(t, _draw(rng, p_t if sc[t] == _TARGET else 0.5),
                             _KEY, sc[t]))
    for j in range(len(p_schedule)):
        expected = p_hi if math.floor(j / 4) % 2 == 0 else p_lo
        assert p_schedule[j] == expected, \
            f"N: block {j} planted p={p_schedule[j]}, expected {expected}"
    w = AdaptiveWorld(obs_list, [{"seq": 0, "window": _W0, "by": "person"}],
                      [], {_KEY: _TARGET},
                      {"world": "N", "planted": "shell_from_previous_regime",
                       "p_schedule": p_schedule},
                      {"world": "N", "T": T, "seed": seed, "p_hi": p_hi,
                       "p_lo": p_lo, "regime": regime, "blocks_per_regime": bpr})
    _assert_block_integrity(w)
    return w

def make_world_k(T: int, seed: int) -> AdaptiveWorld:
    """K -- person changes once. p=p_before until tau=T/2, then p_after."""
    pb = float(_P["worlds"]["K"]["p_before"])
    pa = float(_P["worlds"]["K"]["p_after"])
    tau = T // 2
    sc = _sched(T)
    obs, _ = _gen_obs(T, seed, sc, lambda t: pb if t < tau else pa)
    assert tau == T // 2, "K: tau must be T/2"
    w = AdaptiveWorld(obs, [{"seq": 0, "window": _W0, "by": "person"}],
                      [], {_KEY: _TARGET},
                      {"world": "K", "planted": "type1_after_tau", "tau": tau},
                      {"world": "K", "T": T, "seed": seed, "tau": tau,
                       "p_before": pb, "p_after": pa})
    _assert_block_integrity(w)
    return w

def make_world_v(T: int, seed: int) -> AdaptiveWorld:
    """V -- vocabulary rename and reconciliation. p constant, key changes."""
    p = float(_P["worlds"]["V"]["p"])
    fr = int(_P["worlds"]["V"]["first_rename"])
    re = int(_P["worlds"]["V"]["rename_every"])
    ra = int(_P["worlds"]["V"]["reconcile_after"])
    sc = _sched(T)
    renames, recons = [], []
    t_r = fr
    while t_r < T:
        renames.append(t_r)
        if t_r + ra < T: recons.append(t_r + ra)
        t_r += re
    kn = [_KEY] + [f"{_KEY}_{i + 2}" for i in range(len(renames))]
    events = []
    for i, tr in enumerate(renames):
        events.append({"kind": "KEY_RENAMED", "seq": tr,
                       "from": kn[i], "to": kn[i + 1]})
    for i, tc in enumerate(recons):
        events.append({"kind": "RECONCILED", "seq": tc,
                       "oldKey": kn[i], "newKey": kn[i + 1]})
    events.sort(key=lambda e: e["seq"])
    rng = np.random.default_rng(seed)
    obs, ki = [], 0
    for t in range(T):
        if t in renames: ki = renames.index(t) + 1
        obs.append(_obs(t, _draw(rng, p if sc[t] == _TARGET else 0.5),
                        kn[ki], sc[t]))
    gr = [e["seq"] for e in events if e["kind"] == "KEY_RENAMED"]
    gc = [e["seq"] for e in events if e["kind"] == "RECONCILED"]
    assert gr == renames, f"V: rename schedule {gr} != {renames}"
    assert gc == recons, f"V: reconciliation {gc} != {recons}"
    pairs = list(zip(renames, recons[:len(renames)]))
    w = AdaptiveWorld(obs, [{"seq": 0, "window": _W0, "by": "person"}],
                      events, {kn[ki]: _TARGET},
                      {"world": "V", "planted": "suspended_between_rename_recon",
                       "renames": renames, "reconciliations": recons,
                       "key_names": kn, "first_rename": fr,
                       "rename_recon_pairs": pairs},
                      {"world": "V", "T": T, "seed": seed, "p": p,
                       "first_rename": fr, "rename_every": re,
                       "reconcile_after": ra, "n_renames": len(renames)})
    _assert_block_integrity(w)
    return w

def make_world_r(T: int, seed: int) -> AdaptiveWorld:
    """R -- redeclaration. Like S; person redeclares W=W0 at T/2."""
    p = float(_P["worlds"]["R"]["p"])
    rw = int(_P["worlds"]["R"]["redeclare_window"])
    tau = T // 2
    sc = _sched(T)
    obs, _ = _gen_obs(T, seed, sc, lambda t: p)
    decl = [{"seq": 0, "window": _W0, "by": "person"},
            {"seq": tau, "window": rw, "by": "person"}]
    assert len(decl) == 2 and decl[1]["by"] == "person", \
        "R: single redeclaration act with person provenance"
    w = AdaptiveWorld(obs, decl, [], {_KEY: _TARGET},
                      {"world": "R", "planted": "redeclaration_resets",
                       "tau": tau, "redeclare_seq": tau},
                      {"world": "R", "T": T, "seed": seed, "p": p,
                       "tau": tau, "redeclare_window": rw})
    _assert_block_integrity(w)
    return w

_DISPATCH = {"S": make_world_s, "N": make_world_n, "K": make_world_k,
             "V": make_world_v, "R": make_world_r}

def make_world(name: str, T: int, seed: int) -> AdaptiveWorld:
    assert name in WORLDS, f"unknown world {name!r}"
    return _DISPATCH[name](T=T, seed=seed)
