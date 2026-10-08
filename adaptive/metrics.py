"""Per-prediction measurements for the adaptive grid. PREREGISTRO v0.3 §8.

Input: readings per block from read_returns (or R_mix triggers), blocks, and
planted. A return WAS READ in a block when lastReturn.seq == last round of the
block. Output: raw numbers, no thresholds.
"""
from __future__ import annotations
from .worlds import load_policy
from .replay_check import reproduces, truncated, without_one_return

__all__ = ["p1_final_window", "p2_n_adjustments", "p3_replay_rate",
           "p3b_tampered_rate", "p5_monotone_conflict_sym",
           "p6_after_rename", "p7_redeclaration", "cost_k", "cost_v"]

_P = load_policy()
_W0 = int(_P["declared"]["warrant_window"])
_STEP = int(_P["rule"]["step"])


def p1_final_window(readings: list[dict]) -> int:
    """P1: window of the last reading."""
    if not readings:
        return _W0
    return int(readings[-1].get("window", _W0))


def p2_n_adjustments(readings: list[dict]) -> int:
    """P2/P4: number of adjustments in last reading.
    For R_mix: number of triggers (len of triggers list)."""
    if not readings:
        return 0
    last = readings[-1]
    return len(last.get("adjustments", []))


def p3_replay_rate(reader: str, world, adjustments: list[dict],
                   k: int, rule: dict | None = None) -> tuple[int, int]:
    """P3: (reproduced, total) over non-truncated adjustments."""
    non_trunc = [a for a in adjustments if not truncated(a, rule)]
    if not non_trunc:
        return (0, 0)
    ok = sum(1 for a in non_trunc
             if reproduces(reader, world, a, k))
    return (ok, len(non_trunc))


def p3b_tampered_rate(world, adjustments: list[dict],
                      k: int) -> tuple[int, int]:
    """P3b: (failed, total) with one return removed, over R_declared adjs."""
    if not adjustments:
        return (0, 0)
    failed = 0
    for a in adjustments:
        tampered = without_one_return(a)
        if not reproduces("R_declared", world, tampered, k):
            failed += 1
    return (failed, len(adjustments))


def p5_monotone_conflict_sym(readings: list[dict], blocks, planted,
                             reader: str) -> dict:
    """P5: (i) window never decreases between consecutive readings;
    (ii) among the first two blocks with first_round >= tau, some was read
    as CONFLICT; (iii) for R_sym: some reading after tau has window smaller
    than previous."""
    tau = planted.get("tau", 0)
    # (i) monotone
    monotone = True
    for i in range(1, len(readings)):
        if readings[i].get("window", 0) < readings[i - 1].get("window", 0):
            monotone = False
            break
    # (ii) first two blocks with first_round >= tau have CONFLICT
    conflict_in_first_two = False
    count = 0
    for i, (a, last) in enumerate(blocks):
        if a >= tau and i < len(readings):
            lr = readings[i].get("lastReturn")
            if lr and lr.get("seq") == last and lr.get("kind") == "CONFLICT":
                conflict_in_first_two = True
            count += 1
            if count >= 2:
                break
    # (iii) R_sym: some reading after tau with smaller window
    sym_shortened = False
    if reader == "R_sym":
        for i in range(1, len(readings)):
            bi_start = blocks[i][0] if i < len(blocks) else 0
            if bi_start >= tau:
                if readings[i].get("window", 0) < \
                        readings[i - 1].get("window", 0):
                    sym_shortened = True
                    break
    return {"monotone": monotone,
            "conflict_in_first_two_after_tau": conflict_in_first_two,
            "sym_shortened": sym_shortened}


def p6_after_rename(readings: list[dict], blocks, planted) -> dict:
    """P6: (i) adjustments with seq > first_rename; (ii) every reading
    between rename and reconciliation: SUSPENDED, window==W0, reason starts
    with 'a condition key was renamed'; (iii) every reading has reason."""
    fr = planted.get("first_rename", float("inf"))
    pairs = planted.get("rename_recon_pairs", [])
    # (i) count only from LAST reading (each reading carries all prior adj)
    adj_after = 0
    last_rdg = readings[-1] if readings else {}
    for a in last_rdg.get("adjustments", []):
        if a.get("seq", 0) > fr:
            adj_after += 1
    # (ii) readings whose nowSeq is between rename and reconciliation
    suspended_ok = True
    for i, rdg in enumerate(readings):
        ns = blocks[i][1] + 1 if i < len(blocks) else 0
        for ren, rec in pairs:
            if ren <= ns < rec:
                if rdg.get("state") != "SUSPENDED":
                    suspended_ok = False
                if rdg.get("window") != _W0:
                    suspended_ok = False
                if not rdg.get("reason", "").startswith(
                        "a condition key was renamed"):
                    suspended_ok = False
    # (iii)
    all_have_reason = all(bool(r.get("reason")) for r in readings)
    return {"adjustments_after_rename": adj_after,
            "suspended_correct": suspended_ok,
            "all_have_reason": all_have_reason}


def p7_redeclaration(extra_reading: dict, readings: list[dict],
                     planted) -> dict:
    """P7: extra reading at nowSeq=redeclare_seq: DECLARED, W0, run==0;
    first adjustment with seq > redeclare_seq: all named returns have
    fromSeq >= redeclare_seq."""
    rs = planted.get("redeclare_seq", 0)
    decl_ok = (extra_reading.get("state") == "DECLARED" and
               extra_reading.get("window") == _W0 and
               extra_reading.get("run", -1) == 0)
    returns_ok = True
    last_rdg = readings[-1] if readings else {}
    for a in last_rdg.get("adjustments", []):
        if a.get("seq", 0) > rs:
            for ret in a.get("returns", []):
                if ret.get("fromSeq", 0) < rs:
                    returns_ok = False
            break
    return {"declared_state_ok": decl_ok, "returns_after_redecl": returns_ok}


def cost_k(readings: list[dict], blocks, planted) -> int:
    """Cost K: B = number of blocks with first_round >= tau read as CONFLICT.
    For R_declared and R_fixed."""
    tau = planted.get("tau", 0)
    b = 0
    for i, (a, last) in enumerate(blocks):
        if a >= tau and i < len(readings):
            lr = readings[i].get("lastReturn")
            if lr and lr.get("seq") == last and lr.get("kind") == "CONFLICT":
                b += 1
    return b


def cost_v(readings: list[dict], planted) -> int:
    """Cost V: A = number of adjustments with seq > first_rename.
    For R_cross and R_declared."""
    fr = planted.get("first_rename", float("inf"))
    last_rdg = readings[-1] if readings else {}
    a = 0
    for adj in last_rdg.get("adjustments", []):
        if adj.get("seq", 0) > fr:
            a += 1
    return a
