"""Collective worlds -- O, Pn, G generators for Paper 8.
Pop worlds (Pc, Pl, Pw) live in worlds_pop.py for the 200-line limit.
Parameters from policy_frozen.json. Each generator asserts what it plants.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np

__all__ = [
    "WORLDS", "CollectiveWorld", "load_policy", "make_world",
    "make_O", "make_Pn", "make_G",
]

WORLDS = ("O", "Pn", "Pc", "Pl", "Pw", "G")
POLICY_PATH = Path(__file__).resolve().parent / "policy_frozen.json"


def load_policy(path: Path | str = POLICY_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


_P = load_policy()


@dataclass(frozen=True)
class CollectiveWorld:
    observations: list[dict]
    declarations: list[dict]
    vocabulary_events: list[dict]
    condition: dict[str, str]
    members: list[dict] | None          # G world only
    group_input: dict | None            # G world only
    person_worlds: list | None          # Pop worlds: per-person adaptive worlds
    planted: dict
    params: dict


def _obs(seq, signal, key, cond, observer="obs-0", episode_id=None):
    o: dict = {
        "seq": seq, "signal": signal,
        "conditions": {key: cond},
        "strategy": ["s*"], "id": f"obs-{seq}",
        "journeyId": "bench", "note": "",
        "provenance": {"kind": "PERSON", "observer": observer},
    }
    if episode_id is not None:
        o["episodeId"] = episode_id
    return o


# ── O: observers ──────────────────────────────────────────────
def make_O(k: int, seed: int) -> CollectiveWorld:
    """O -- k duplicate BETTER reports per episode of s1, one WORSE episode.
    Includes inversion case: per episode s1 wins, per observation s2 would win.
    """
    rng = np.random.default_rng(seed)
    pol = _P["O"]
    inv = pol["inversion"]
    n_eps = pol["episodes"]
    obs: list[dict] = []
    seq = 0

    # Main episodes: each has k BETTER reports, same episodeId
    for ep in range(n_eps):
        eid = f"ep-s1-{ep}"
        for r in range(k):
            obs.append(_obs(seq, "BETTER", "modo", "c1",
                            observer=f"obs-{r}", episode_id=eid))
            seq += 1

    # One WORSE episode from another observer
    obs.append(_obs(seq, "WORSE", "modo", "c1",
                    observer="obs-worse", episode_id="ep-s1-worse"))
    seq += 1

    # Inversion case: s2 has fewer episodes but many reports each
    s1_inv_eps = inv["s1_episodes"]
    s2_inv_eps = inv["s2_episodes"]
    s2_reps = inv["s2_reports_each"]
    inv_obs: list[dict] = []
    inv_seq = seq
    for ep in range(s1_inv_eps):
        eid = f"ep-inv-s1-{ep}"
        inv_obs.append(_obs(inv_seq, "BETTER", "modo", "c1",
                            observer="obs-inv-0", episode_id=eid))
        inv_seq += 1
    for ep in range(s2_inv_eps):
        eid = f"ep-inv-s2-{ep}"
        for r in range(s2_reps):
            inv_obs.append(_obs(inv_seq, "BETTER", "modo", "c1",
                                observer=f"obs-inv-s2-{r}", episode_id=eid))
            inv_seq += 1

    obs.extend(inv_obs)

    # Assertions
    episode_ids_s1 = {o["episodeId"] for o in obs
                      if o["episodeId"] and o["episodeId"].startswith("ep-s1-")}
    assert len(episode_ids_s1) == n_eps + 1  # n_eps BETTER + 1 WORSE

    # Inversion: per observation s2 has more, per episode s1 has more
    inv_s1_obs = [o for o in inv_obs if "inv-s1" in o["episodeId"]]
    inv_s2_obs = [o for o in inv_obs if "inv-s2" in o["episodeId"]]
    assert len(inv_s2_obs) > len(inv_s1_obs), \
        "inversion: s2 must have more observations than s1"
    inv_s1_episodes = {o["episodeId"] for o in inv_s1_obs}
    inv_s2_episodes = {o["episodeId"] for o in inv_s2_obs}
    assert len(inv_s1_episodes) > len(inv_s2_episodes), \
        "inversion: s1 must have more episodes than s2"

    w = CollectiveWorld(
        obs, [{"seq": 0, "window": 40, "by": "person"}], [],
        {"modo": "c1"}, None, None, None,
        {"world": "O", "planted": "statute_B", "k": k,
         "n_episodes": n_eps,
         "inversion": {"s1_episodes": s1_inv_eps,
                       "s2_episodes": s2_inv_eps,
                       "s2_reports_each": s2_reps}},
        {"world": "O", "k": k, "seed": seed})
    return w


# ── Pn: person new ───────────────────────────────────────────
def make_Pn(n: int, seed: int) -> CollectiveWorld:
    """Pn -- person has no records. Population of n people has records."""
    rng = np.random.default_rng(seed)
    pol = _P["Pn"]
    rpp = pol["records_per_person"]
    p_s1, p_s2 = pol["p_s1"], pol["p_s2"]

    pop_obs: list[dict] = []
    repertoire = {"s1", "s2"}
    seq = 0
    for person in range(n):
        for t in range(rpp):
            strat = str(rng.choice(["s1", "s2"]))
            p = p_s1 if strat == "s1" else p_s2
            sig = "BETTER" if rng.random() < p else "WORSE"
            o = _obs(seq, sig, "modo", "c1", observer=f"person-{person}")
            o["strategy"] = [strat]
            o["personRef"] = f"person-{person}"
            pop_obs.append(o)
            seq += 1

    # The target person has NO observations
    person_obs: list[dict] = []

    w = CollectiveWorld(
        person_obs, [{"seq": 0, "window": 40, "by": "person"}], [],
        {"modo": "c1"}, None, None, None,
        {"world": "Pn", "planted": "no_evidence",
         "repertoire": sorted(repertoire), "n_population": n,
         "population_obs": pop_obs},
        {"world": "Pn", "n": n, "seed": seed})
    assert len(w.observations) == 0, "Pn: person must have no records"
    assert len(pop_obs) == n * rpp
    return w


# ── G: group ─────────────────────────────────────────────────
def make_G(n: int, m: int, p: float, rho: float,
           seed: int) -> CollectiveWorld:
    """G -- group world with n members, m actions, correlation rho."""
    rng = np.random.default_rng(seed)
    pol = _P["G"]
    show_rate = pol["show_reasons_rate"]
    status_quo = pol["status_quo"]
    actions = [f"a{i}" for i in range(m)]
    assert status_quo in actions, f"status_quo {status_quo} not in actions"

    members = []
    for mi in range(n):
        show = bool(rng.random() < show_rate)
        gamma: dict = {}
        for a in actions:
            auth = bool(rng.random() < p) if rho == 0.0 else None
            feas = bool(rng.random() < 0.95)
            safe = bool(rng.random() < 0.95)
            epi = bool(rng.random() < 0.95)
            gamma[a] = {"auth": auth, "feas": feas, "safe": safe, "epi": epi}

        # With correlation rho, draw common factor per action
        if rho > 0:
            for a in actions:
                common = bool(rng.random() < p)
                if rng.random() < rho:
                    gamma[a]["auth"] = common
                else:
                    gamma[a]["auth"] = bool(rng.random() < p)

        # Blockers get random component
        for a in actions:
            if not gamma[a]["auth"]:
                comp = rng.choice(["feas", "auth", "safe", "epi"])
                gamma[a][comp] = False

        members.append({
            "memberRef": f"m{mi}",
            "released": True,
            "showReasons": show,
            "gamma": gamma,
        })

    group_input = {
        "actions": actions,
        "statusQuo": status_quo,
        "members": members,
    }

    # Compute planted admissible set
    admissible = []
    for a in actions:
        ok = all(
            members[mi]["gamma"][a]["auth"]
            and members[mi]["gamma"][a]["feas"]
            and members[mi]["gamma"][a]["safe"]
            and members[mi]["gamma"][a]["epi"]
            for mi in range(n))
        if ok:
            admissible.append(a)

    w = CollectiveWorld(
        [], [], [], {}, members, group_input, None,
        {"world": "G", "planted": "intersection",
         "admissible": sorted(admissible),
         "status_quo": status_quo,
         "n_members": n, "m_actions": m},
        {"world": "G", "n": n, "m": m, "p": p, "rho": rho, "seed": seed})
    return w


# ── Dispatch ─────────────────────────────────────────────────
from .worlds_pop import make_Pc, make_Pl, make_Pw  # noqa: E402

_DISPATCH = {
    "O": lambda seed, **kw: make_O(k=kw.get("k", 2), seed=seed),
    "Pn": lambda seed, **kw: make_Pn(n=kw.get("n", 5), seed=seed),
    "G": lambda seed, **kw: make_G(
        n=kw.get("n", 5), m=kw.get("m", 5),
        p=kw.get("p", 0.8), rho=kw.get("rho", 0.0), seed=seed),
    "Pc": lambda seed, **kw: make_Pc(
        n=kw.get("n", 5), T=kw.get("T", 320), seed=seed),
    "Pl": lambda seed, **kw: make_Pl(
        n=kw.get("n", 5), T=kw.get("T", 320), seed=seed),
    "Pw": lambda seed, **kw: make_Pw(
        n=kw.get("n", 5), T=kw.get("T", 320), seed=seed),
}


def make_world(name: str, seed: int, **kw) -> CollectiveWorld:
    assert name in WORLDS, f"unknown world {name!r}"
    return _DISPATCH[name](seed=seed, **kw)
