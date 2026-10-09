"""Group world generator for the collective bench (Paper 8).
Split from worlds.py for the 200-line limit.
"""
from __future__ import annotations
import numpy as np

from .worlds import CollectiveWorld, load_policy

__all__ = ["make_G"]

_P = load_policy()


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
