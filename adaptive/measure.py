"""Measurement function for the adaptive grid. PREREGISTRO rascunho v0.4 SS3,8.

measure_run(world_name, T, k, seed) -> flat dict of raw numbers, no thresholds.
Every world: five plugin readers' final window and adjustment count.
S and N: R_mix window and trigger count. S: P3 and P3b. K: P5 and cost B.
V: P6 and cost A. R: P7.
"""
from __future__ import annotations

from .worlds import make_world, c1_blocks, load_policy
from .readers import read, read_returns, READERS
from .reader_mix import R_mix
from .replay_check import reproduces, truncated, without_one_return
from . import metrics as M

__all__ = ["measure_run"]

_P = load_policy()
_W0 = int(_P["declared"]["warrant_window"])


def measure_run(world_name: str, T: int, k: int, seed: int) -> dict:
    """Run all readers and measurements for one (world, T, k, seed) cell."""
    w = make_world(world_name, T=T, seed=seed)
    blocks = c1_blocks(w)
    d: dict = {}
    readings_by: dict[str, list] = {}

    # ALL worlds: five plugin readers
    for rdr in READERS:
        rdgs = read_returns(rdr, w, k)
        readings_by[rdr] = rdgs
        d[f"{rdr}_window"] = M.p1_final_window(rdgs)
        d[f"{rdr}_n_adj"] = M.p2_n_adjustments(rdgs)

    # S and N: R_mix
    if world_name in ("S", "N"):
        mix = R_mix(w, k)
        d["R_mix_window"] = mix.get("window", _W0)
        d["R_mix_n_triggers"] = len(mix.get("triggers", []))
        readings_by["R_mix"] = mix

    # S: P3 (R_declared, R_simple, R_mix) and P3b
    if world_name == "S":
        for rdr in ("R_declared", "R_simple"):
            last = readings_by[rdr][-1] if readings_by[rdr] else {}
            adjs = last.get("adjustments", [])
            rep, tot = M.p3_replay_rate(rdr, w, adjs, k)
            d[f"P3_{rdr}_reproduced"] = rep
            d[f"P3_{rdr}_total"] = tot
        mix_data = readings_by.get("R_mix", {})
        triggers = mix_data.get("triggers", [])
        rep, tot = M.p3_replay_rate("R_mix", w, triggers, k)
        d["P3_R_mix_reproduced"] = rep
        d["P3_R_mix_total"] = tot
        # P3b
        last_d = readings_by["R_declared"][-1] if readings_by["R_declared"] else {}
        adjs_d = last_d.get("adjustments", [])
        fail, tot = M.p3b_tampered_rate(w, adjs_d, k)
        d["P3b_failed"] = fail
        d["P3b_total"] = tot

    # K: P5, cost B
    if world_name == "K":
        p5d = M.p5_monotone_conflict_sym(
            readings_by["R_declared"], blocks, w.planted, "R_declared")
        d["P5_R_declared_monotone"] = p5d["monotone"]
        d["P5_R_declared_conflict_first_two"] = p5d[
            "conflict_in_first_two_after_tau"]
        p5s = M.p5_monotone_conflict_sym(
            readings_by["R_sym"], blocks, w.planted, "R_sym")
        d["P5_R_sym_shortened"] = p5s["sym_shortened"]
        d["cost_B_R_declared"] = M.cost_k(
            readings_by["R_declared"], blocks, w.planted)
        d["cost_B_R_fixed"] = M.cost_k(
            readings_by["R_fixed"], blocks, w.planted)

    # V: P6, cost A
    if world_name == "V":
        p6d = M.p6_after_rename(
            readings_by["R_declared"], blocks, w.planted)
        d["P6_R_declared_adj_after_rename"] = p6d["adjustments_after_rename"]
        d["P6_R_declared_suspended_ok"] = p6d["suspended_correct"]
        d["P6_R_declared_all_reason"] = p6d["all_have_reason"]
        p6x = M.p6_after_rename(
            readings_by["R_cross"], blocks, w.planted)
        d["P6_R_cross_adj_after_rename"] = p6x["adjustments_after_rename"]
        d["cost_A_R_cross"] = M.cost_v(readings_by["R_cross"], w.planted)
        d["cost_A_R_declared"] = M.cost_v(
            readings_by["R_declared"], w.planted)

    # R: extra reading and P7
    if world_name == "R":
        rs = w.planted.get("redeclare_seq", T // 2)
        extra = read("R_declared", w, k, now_seq=rs)
        p7 = M.p7_redeclaration(
            extra, readings_by["R_declared"], w.planted)
        d["P7_declared_state_ok"] = p7["declared_state_ok"]
        d["P7_returns_after_redecl"] = p7["returns_after_redecl"]

    return d
