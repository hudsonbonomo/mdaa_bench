"""Per-run measurements for the standing grid. PREREGISTRO_v1 §6-§7 (+ emendas v1.2, v1.3).

Nothing here executes anything: it reads a `StandingWorld` (including `planted`,
which is ground truth and never reaches a reader) together with the three
`ReadingResult`s and turns them into numbers. The grid loop lives in `bench.py`.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from .pilot_power import (ALPHA, DELTA, STANDING_VALUES, nu_distribution,  # noqa: F401
                          total_variation, tost_rejects)
from .pilot_power_weights import weight_distance  # noqa: F401
from .readers import obs_id
from .worlds import STRATEGY, load_alpha

__all__ = ["confusion", "sstar_proposition", "order_report", "blocking_reason",
           "aged_inside_window", "p2_out_of_scope", "p4_unevaluable", "p4_branch",
           "p4b_current", "tost", "prf"]


def confusion(world, verdicts: dict[str, str]) -> dict[str, int]:
    """nu_attributed x nu_planted, one cell per record. Keys are `planted>ATTRIBUTED`.

    A world without a planted state (B `unlogged`, §6) yields {} and stays out of
    the matrix by construction.
    """
    out: dict[str, int] = {}
    for t, truth in world.planted.items():
        planted = truth.get("planted_state")
        if planted is None:
            return {}
        got = verdicts.get(obs_id(t), "MISSING")
        key = f"{planted}>{got}"
        out[key] = out.get(key, 0) + 1
    return out


def sstar_proposition(status: dict | None) -> dict | None:
    """The proposition about s* carrying the most support — the one the statute
    rule looks at ("nenhuma proposicao elege enquanto a de maior sustentacao
    estiver em B", emenda v1.2)."""
    props = (status or {}).get("byProposition") or []
    mine = [p for p in props if p.get("strategy") == STRATEGY] or props
    if not mine:
        return None
    return max(mine, key=lambda p: len(p.get("status", {}).get("supporting", [])))


def order_report(prop: dict | None) -> dict:
    """Is the order preserved and legible in the parecer? Emenda v1.3: legible
    means every cited observation carries a `seq`, NOT that the seq ranges of
    supporting and contradicting separate cleanly."""
    st = (prop or {}).get("status", {})
    sup = st.get("supporting", []) or []
    con = st.get("contradicting", []) or []
    seqs_s = [o.get("seq") for o in sup]
    seqs_c = [o.get("seq") for o in con]
    legible = bool(sup or con) and all(isinstance(s, int) for s in seqs_s + seqs_c)
    return {"kind": st.get("kind"), "n_supporting": len(sup), "n_contradicting": len(con),
            "supp_seq_min": min(seqs_s) if seqs_s else None,
            "supp_seq_max": max(seqs_s) if seqs_s else None,
            "contra_seq_min": min(seqs_c) if seqs_c else None,
            "contra_seq_max": max(seqs_c) if seqs_c else None,
            "order_legible": legible}


def blocking_reason(result) -> str:
    """Why R_declared did not elect, named from its own status cell (P5, v1.3)."""
    if result.strategy is not None:
        return "elected"
    if not result.verdicts:
        return "no_observation"
    prop = sstar_proposition(result.status)
    if prop is None:
        return "no_proposition"
    if not result.raw.get("appearingIds"):
        return "out_of_scope_or_aged"
    kind = prop.get("status", {}).get("kind")
    return {"B": "B_blocking", "N": "no_evidence"}.get(kind, f"kind_{kind}")


def aged_inside_window(world, verdicts: dict[str, str], policy: str) -> int:
    """Records AGED while still inside the alpha window (age <= warrant_window)."""
    window = load_alpha()["policies"][policy]["warrant_window"]
    now = len(world.observations)
    return sum(1 for o in world.observations
               if (now - o.t) <= window and verdicts.get(obs_id(o.t)) == "AGED")


def p2_out_of_scope(world, verdicts: dict[str, str]) -> tuple[int, int]:
    """B `logged`: hits/total over records whose true condition is not the one in
    force. P2 asks for OUT_OF_SCOPE on those."""
    hits = total = 0
    for t, truth in world.planted.items():
        if truth.get("planted_state") != "out_of_scope":
            continue
        total += 1
        hits += verdicts.get(obs_id(t)) == "OUT_OF_SCOPE"
    return hits, total


def p4_unevaluable(world, verdicts: dict[str, str]) -> dict[str, int]:
    """D: confusion of UNEVALUABLE, attributed against planted, over all records."""
    tp = fp = fn = tn = 0
    for t, truth in world.planted.items():
        want = truth.get("planted_state") == "unevaluable"
        got = verdicts.get(obs_id(t)) == "UNEVALUABLE"
        tp += want and got
        fp += (not want) and got
        fn += want and not got
        tn += (not want) and (not got)
    return {"tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)}


def p4_branch(world, verdicts: dict[str, str]) -> dict:
    """D: what happened to the pre-tau1 block under each reconciliation branch.

    Two readings, both reported, because they come apart when the block is old:

    `returned_ok` is P4's own wording ("apos reconciliacao total todos voltam;
    apos parcial, sem correspondente -> out of scope, nenhum unevaluable"):
    coming back means leaving UNEVALUABLE, and the standing the record then
    carries — APPLICABLE or AGED — is the alpha layer's business, not the
    vocabulary layer's.

    `branch_ok` is the stricter reading, which demands APPLICABLE after a total
    reconciliation. It fails whenever the returned block is older than the alpha
    window (T = 160: the pre-tau1 block sits at age >= 108), which is the
    standing layer working, not the reconciliation failing.
    """
    kind = world.params.get("reconciliation")
    pre = [verdicts.get(obs_id(t)) for t, x in world.planted.items() if x.get("pre_tau1")]
    want = {None: "UNEVALUABLE", "total": "APPLICABLE", "partial": "OUT_OF_SCOPE"}[kind]
    back = {None: {"UNEVALUABLE"}, "total": {"APPLICABLE", "AGED"},
            "partial": {"OUT_OF_SCOPE"}}[kind]
    return {"reconciliation": kind or "none", "n_pre_tau1": len(pre),
            "expected": want, "n_as_expected": sum(1 for v in pre if v == want),
            "n_unevaluable": sum(1 for v in pre if v == "UNEVALUABLE"),
            "n_aged": sum(1 for v in pre if v == "AGED"),
            "returned_ok": bool(pre) and all(v in back for v in pre),
            "branch_ok": bool(pre) and all(v == want for v in pre)}


def p4b_current(world, current) -> dict:
    """P4b mirror-control: R_current leaves every pre-tau1 record out of the tally
    and never brings it back. Rate 1.00 by construction."""
    pre = [current.verdicts.get(obs_id(t))
           for t, x in world.planted.items() if x.get("pre_tau1")]
    return {"n_pre_tau1": len(pre), "n_excluded": sum(1 for v in pre if v == "excluded"),
            "all_excluded": bool(pre) and all(v == "excluded" for v in pre)}


def tost(values, delta: float = DELTA, alpha: float = ALPHA) -> dict:
    """Two one-sided tests of H0: |theta| >= delta. Same decision rule as
    `pilot_power.tost_rejects`, with the p-values kept for the report."""
    x = np.asarray(values, dtype=float)
    n = x.size
    assert n > 1, "TOST needs at least two seeds"
    mean = float(x.mean())
    se = float(x.std(ddof=1) / np.sqrt(n))
    if se == 0.0:
        p_lo = 0.0 if mean > -delta else 1.0
        p_hi = 0.0 if mean < delta else 1.0
    else:
        p_lo = float(stats.t.sf((mean + delta) / se, n - 1))
        p_hi = float(stats.t.cdf((mean - delta) / se, n - 1))
    return {"n": int(n), "mean": mean, "sd": float(x.std(ddof=1)),
            "max": float(x.max()), "delta": delta, "alpha": alpha,
            "p_lower": p_lo, "p_upper": p_hi,
            "equivalent": bool(p_lo < alpha / 2 and p_hi < alpha / 2)}


def prf(tp: int, fp: int, fn: int) -> dict:
    """Precision/recall, with the degenerate case named instead of divided by zero."""
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall}
