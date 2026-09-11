"""SIM-4 recovery map — how often does the blind pipeline recover the planted node?

Usage (small smoke run):
    python -m sim.recovery --T 300 --noise 0.1 0.3 --keep 1.0 --reps 2 --out out/

Beyond exact/spurious/missed, v1 records:
  * per-axis firing (N, H, M, S) against what was planted — `by_axis` in the
    summary is the honest table: a gate is characterised by its false-positive
    rate on worlds where the axis is absent, not by node-level accuracy;
  * planted vs recovered switch times for M1+H (precision, recall, timing MAE);
  * `s_correct`, the S gate against the generator's process noise.

The grid is a BATCH operation. On the production server, run only with the
explicit approval recorded in the cell state (Modo Celular rule 5). `--jobs N`
forks the grid over processes; seeds are CRC32 of the cell tuple, so the result
does not depend on the number of workers.
"""
from __future__ import annotations
import argparse, csv, itertools, json, os, time, zlib
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from .generators import NODES, generate
from .observe import observe
from .ensemble import generate_ensemble
from .pipeline import identify
from .switching import match_switches
from .density import PASS, FAIL, UNIDENTIFIABLE

AXES = ("N", "H", "M")
SWITCH_TOL = 10          # steps; a recovered switch counts if within +/- this


def run_cell(node, T, noise, keep, nonlinear_h, rep, reps_per_person=1):
    """One cell. `reps_per_person` is the replication factor: 1 reproduces the
    single-trajectory design, where the M axis is `nao identificavel` by
    construction; above 1 the cell becomes WITHIN-PERSON replicates (same A, same
    B, same intervention schedule, different realisation) and the M axis gets a
    real verdict from H3. Everything else is still fitted on one trajectory."""
    seed = zlib.crc32(repr((node, T, noise, keep, nonlinear_h, rep,
                            reps_per_person)).encode()) % (2**31)   # deterministic
    if reps_per_person > 1:
        ens = generate_ensemble(node, n_traj=reps_per_person, mode="within", T=T,
                                seed=seed, meas_noise=noise, keep_frac=keep,
                                nonlinear_h=nonlinear_h)
        traj, obs = generate(node, T=T, seed=seed), ens.obs
    else:
        traj = generate(node, T=T, seed=seed)
        obs = observe(traj, meas_noise=noise, keep_frac=keep, nonlinear_h=nonlinear_h, seed=seed)
    fit = identify(obs, seed=seed)
    planted = set(node.split("+")[1:])                       # axes actually planted
    found = {k for k in AXES if fit.axes.get(k)}
    # an axis the design cannot decide is neither found nor correctly rejected;
    # counting it as "missed" would let an undecidable M look like a clean miss
    undecided = {k for k in AXES if fit.verdicts.get(k) == UNIDENTIFIABLE}
    row = dict(node=node, T=T, noise=noise, keep=keep, nonlinear_h=int(nonlinear_h), rep=rep,
               reps_per_person=reps_per_person,
               selected=fit.node, exact=int(fit.node == node),
               spurious=int(bool(found - planted)),
               missed=int(bool(planted - found - undecided)),
               undecided=int(bool(planted & undecided)),
               s_axis=int(bool(fit.axes.get("S"))),
               n_hardest=fit.hardest.get("N", ""),
               m_verdict=fit.verdicts.get("M", UNIDENTIFIABLE),
               s_correct=int(bool(fit.axes.get("S")) == (traj.truth["process_noise"] > 0)))
    for k in AXES:
        row[f"ax_{k}"] = int(bool(fit.axes.get(k)))
        row[f"vd_{k}"] = fit.verdicts.get(k, "")
    if "switches" in traj.truth:                             # only M1+H plants switches
        m = match_switches(traj.truth["switches"], fit.switches, tol=SWITCH_TOL)
        row.update({f"sw_{k}": v for k, v in m.items()})
    row.update({f"gain_{k}": round(float(v), 4) for k, v in fit.gains.items()})
    return row


def _cell(args):
    return run_cell(*args)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--T", type=int, nargs="+", default=[300])
    ap.add_argument("--noise", type=float, nargs="+", default=[0.1, 0.3])
    ap.add_argument("--keep", type=float, nargs="+", default=[1.0])
    ap.add_argument("--nonlinear_h", type=int, nargs="+", default=[0])
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--reps_per_person", type=int, nargs="+", default=[1],
                    help="within-person replicates per cell; >1 gives the M axis a verdict")
    ap.add_argument("--nodes", nargs="+", default=list(NODES))
    ap.add_argument("--jobs", type=int, default=1, help="worker processes (batch runs)")
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    grid = [(n, T, nz, k, bool(nh), r, rp) for n, T, nz, k, nh, r, rp
            in itertools.product(a.nodes, a.T, a.noise, a.keep, a.nonlinear_h,
                                 range(a.reps), a.reps_per_person)]
    print(f"{len(grid)} runs, {a.jobs} job(s)")
    rows = []
    if a.jobs > 1:
        with ProcessPoolExecutor(max_workers=a.jobs) as ex:
            for i, r in enumerate(ex.map(_cell, grid, chunksize=4), 1):
                rows.append(r)
                if i % 50 == 0 or i == len(grid):
                    print(f"  {i}/{len(grid)}  {time.time()-t0:.0f}s")
    else:
        for i, g in enumerate(grid, 1):
            rows.append(run_cell(*g))
            if i % 10 == 0 or i == len(grid):
                print(f"  {i}/{len(grid)}  {time.time()-t0:.0f}s")
    keys = sorted({k for r in rows for k in r},
                  key=lambda k: (k.startswith("sw_"), k.startswith("gain_"), k))
    with open(os.path.join(a.out, "recovery_rows.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, restval=""); w.writeheader(); w.writerows(rows)
    summary = summarize(rows)
    with open(os.path.join(a.out, "recovery_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    plot(rows, a.out)
    plot_observation(rows, a.out)
    plot_recovery_v2(rows, a.out)
    print(json.dumps({k: summary[k] for k in
                      ("by_node", "by_axis", "switch_timing", "m_by_reps_per_person")}, indent=1))


def _mean(xs):
    xs = [x for x in xs if x == x]
    return round(float(np.mean(xs)), 3) if xs else None


def summarize(rows):
    by_node, conf = {}, {}
    for r in rows:
        b = by_node.setdefault(r["node"], dict(n=0, exact=0, spurious=0, missed=0,
                                               undecided=0, s_correct=0))
        b["n"] += 1
        for k in ("exact", "spurious", "missed", "undecided", "s_correct"):
            b[k] += r[k]
        conf[(r["node"], r["selected"])] = conf.get((r["node"], r["selected"]), 0) + 1
    for b in by_node.values():
        for k in ("exact", "spurious", "missed", "undecided", "s_correct"):
            b[k] = round(b[k] / b["n"], 3)

    # per-axis: rate of firing when the axis IS planted (power) and when it is not (false alarm)
    by_axis = {}
    for k in AXES:
        pos = [r[f"ax_{k}"] for r in rows if k in r["node"].split("+")[1:]]
        neg = [r[f"ax_{k}"] for r in rows if k not in r["node"].split("+")[1:]]
        und = [int(r.get(f"vd_{k}", "") == UNIDENTIFIABLE) for r in rows]
        by_axis[k] = dict(n_planted=len(pos), fires_when_planted=_mean(pos),
                          n_absent=len(neg), fires_when_absent=_mean(neg),
                          undecidable=_mean(und))
    s = [r["s_axis"] for r in rows]
    by_axis["S"] = dict(n_planted=len(s), fires_when_planted=_mean(s), n_absent=0,
                        fires_when_absent=None)          # every v0/v1 generator is stochastic

    sw_rows = [r for r in rows if r.get("sw_n_planted", "") != ""]
    switch_timing = dict(
        n=len(sw_rows), tol=SWITCH_TOL,
        recall=_mean([r["sw_recall"] for r in sw_rows]),
        precision=_mean([r["sw_precision"] for r in sw_rows]),
        mae_steps=_mean([r["sw_mae"] for r in sw_rows]),
        planted=_mean([r["sw_n_planted"] for r in sw_rows]),
        recovered=_mean([r["sw_n_recovered"] for r in sw_rows]))
    m_verdicts = {v: sum(1 for r in rows if r.get("m_verdict") == v)
                  for v in (PASS, FAIL, UNIDENTIFIABLE)}
    by_reps = {}
    for rp in sorted({r.get("reps_per_person", 1) for r in rows}):
        sub = [r for r in rows if r.get("reps_per_person", 1) == rp]
        by_reps[str(rp)] = {v: round(sum(1 for r in sub if r["m_verdict"] == v) / len(sub), 3)
                            for v in (PASS, FAIL, UNIDENTIFIABLE)}
    return dict(by_node=by_node, by_axis=by_axis, switch_timing=switch_timing,
                m_verdicts=m_verdicts, m_by_reps_per_person=by_reps,
                confusion={f"{k[0]} -> {k[1]}": v for k, v in sorted(conf.items())})


def plot(rows, out):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    noises = sorted({r["noise"] for r in rows}); Ts = sorted({r["T"] for r in rows})
    fig, axes = plt.subplots(1, len(NODES), figsize=(3.2 * len(NODES), 3.2), dpi=150)
    for ax, node in zip(np.atleast_1d(axes), NODES):
        m = np.full((len(noises), len(Ts)), np.nan)
        for i, nz in enumerate(noises):
            for j, T in enumerate(Ts):
                sel = [r["exact"] for r in rows if r["node"] == node and r["noise"] == nz and r["T"] == T]
                if sel: m[i, j] = np.mean(sel)
        im = ax.imshow(m, vmin=0, vmax=1, cmap="viridis", origin="lower", aspect="auto")
        ax.set_xticks(range(len(Ts))); ax.set_xticklabels(Ts); ax.set_yticks(range(len(noises))); ax.set_yticklabels(noises)
        ax.set_xlabel("T (length)"); ax.set_title(f"planted {node}", fontsize=9)
    np.atleast_1d(axes)[0].set_ylabel("measurement noise")
    fig.colorbar(im, ax=list(np.atleast_1d(axes)), label="exact recovery rate", shrink=0.8)
    fig.suptitle("Recovery map v1 — exact node recovery", fontsize=10)
    fig.savefig(os.path.join(out, "recovery_map.png"), bbox_inches="tight"); fig.savefig(os.path.join(out, "recovery_map.svg"), bbox_inches="tight")


def plot_observation(rows, out):
    """Cell 4: recovery against the OBSERVATION knobs — sampling density and
    observation nonlinearity. Drawn only when the grid actually varied them."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    keeps = sorted({r["keep"] for r in rows}); nhs = sorted({r["nonlinear_h"] for r in rows})
    if len(keeps) < 2 and len(nhs) < 2:
        return
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), dpi=150)
    for ax, (vals, key, xlabel) in zip(axes, [(keeps, "keep", "keep_frac (sampling density)"),
                                              (nhs, "nonlinear_h", "nonlinear h (0 = identity, 1 = tanh)")]):
        for node in NODES:
            ys = [_mean([r["exact"] for r in rows if r["node"] == node and r[key] == v]) for v in vals]
            ax.plot(vals, [y if y is not None else np.nan for y in ys], "o-", label=node)
        ax.set_xlabel(xlabel); ax.set_ylim(-0.05, 1.05); ax.grid(alpha=0.3)
    axes[0].set_ylabel("exact recovery rate"); axes[1].legend(fontsize=8)
    fig.suptitle("Observability: recovery vs sampling and observation nonlinearity", fontsize=10)
    fig.savefig(os.path.join(out, "observability.png"), bbox_inches="tight")
    fig.savefig(os.path.join(out, "observability.svg"), bbox_inches="tight")




def plot_recovery_v2(rows, out):
    """Exact / spurious / missed / UNDECIDED per node, with the third value of the
    M axis drawn rather than folded into 'missed'. An axis the design cannot
    decide is a fourth outcome and the bar chart has to show it, otherwise the map
    reads as if the pipeline had correctly rejected something it never tested."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    keys = ("exact", "spurious", "missed", "undecided")
    colours = ("#2a9d8f", "#e76f51", "#e9c46a", "#8d99ae")
    nodes = [n for n in NODES if any(r["node"] == n for r in rows)]
    vals = {k: [_mean([r[k] for r in rows if r["node"] == n]) or 0.0 for n in nodes]
            for k in keys}
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=150)
    w, xs = 0.2, np.arange(len(nodes))
    for i, (k, c) in enumerate(zip(keys, colours)):
        ax.bar(xs + (i - 1.5) * w, vals[k], w, label=k, color=c)
    ax.set_xticks(xs); ax.set_xticklabels(nodes)
    ax.set_ylim(0, 1.05); ax.set_ylabel("rate"); ax.grid(axis="y", alpha=0.3)
    und = _mean([r["undecided"] for r in rows]) or 0.0
    ax.set_title(f"Recovery map v2 — every cell is a single trajectory, so the M axis is "
                 f"undecidable in {und:.0%} of them", fontsize=9)
    ax.legend(fontsize=8, ncol=4)
    fig.savefig(os.path.join(out, "recovery_map_v2.svg"), bbox_inches="tight")
    fig.savefig(os.path.join(out, "recovery_map_v2.png"), bbox_inches="tight")
    plt.close(fig)


def plot_h3_separation(per_node_gains, out, tol):
    """H3 gains per trajectory, M1 against M1+M, with the decision boundary. This
    is the figure the M axis actually has: the contest that cannot be decided on
    one trajectory, decided over replicates."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=150)
    for i, (node, gains) in enumerate(per_node_gains.items()):
        ax.scatter(np.full(len(gains), i) + np.linspace(-0.12, 0.12, len(gains)),
                   gains, s=26, alpha=0.85,
                   color="#2a9d8f" if "+M" in node else "#8d99ae", label=node)
    ax.axhline(tol, color="#e76f51", lw=1.2, ls="--",
               label=f"H3_TOL = {tol} (above: memory is earned)")
    ax.set_xticks(range(len(per_node_gains))); ax.set_xticklabels(list(per_node_gains))
    ax.set_ylabel("memory-kernel gain per trajectory"); ax.grid(axis="y", alpha=0.3)
    ax.set_title("H3 over replicates of one person — the separation the single\n"
                 "trajectory could not produce", fontsize=9)
    ax.legend(fontsize=8)
    fig.savefig(os.path.join(out, "h3_separation.svg"), bbox_inches="tight")
    fig.savefig(os.path.join(out, "h3_separation.png"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
