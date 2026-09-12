"""Redraw the v4 grid's figures from its CSV, without re-running the grid.

The grid is expensive and pre-registered; its rows are the artefact. A figure
that has to be corrected — as the recovery map did, since its caption described
the v2 design — is redrawn from those rows and nothing else.

    python scripts/replot_v4.py [out_v4]
"""
from __future__ import annotations
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.recovery import plot_recovery_v4

NUM = ("exact", "spurious", "missed", "undecided", "s_correct", "T", "noise", "keep",
       "rep", "reps_per_person", "ax_N", "ax_H", "ax_M", "s_axis")


def load(path):
    rows = []
    for r in csv.DictReader(open(os.path.join(path, "recovery_rows.csv"),
                                 encoding="utf-8")):
        out = dict(r)
        for k in NUM:
            if k in out and out[k] != "":
                try:
                    out[k] = float(out[k]) if "." in out[k] else int(out[k])
                except ValueError:
                    out[k] = {"True": 1, "False": 0}.get(out[k], out[k])
        rows.append(out)
    return rows


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "out_v4"
    rows = load(path)
    plot_recovery_v4(rows, path)
    solo = sum(1 for r in rows if int(r["reps_per_person"]) == 1)
    print(f"{len(rows)} linhas de {path}; {solo} de trajetoria unica, "
          f"{len(rows) - solo} com replicas")
    print(f"{path}/recovery_map_v4.svg + .png")


if __name__ == "__main__":
    main()
