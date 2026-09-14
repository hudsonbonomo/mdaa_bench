"""Non-vacuity of the four decision families, measured rather than asserted.

    python scripts/decision_nonvacuity.py [n_seeds]

For each family: the realised share of signature steps, and the error rate of
the policy that COLLAPSES exactly the distinction that family plants
(`epistemic.blind_action`). Both must clear `worlds.NON_VACUITY_FLOOR`; the test
suite asserts it on one seed, this prints the spread over many.

The number this produces goes into PREREGISTRO_v4.md. A family whose blind
policy scores well is a family that measures nothing, and the honest response is
to redesign the family, not to lower the floor.
"""
from __future__ import annotations
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision.eligible import eligible_steps
from decision.epistemic import blind_action, lambda_of
from decision.worlds import FAMILIES, NON_VACUITY_FLOOR, PROP, make_world


def measure(n_seeds=8, T=400):
    out = {}
    for fam in FAMILIES:
        sig, blind = [], []
        for seed in range(n_seeds):
            w = make_world(fam, T=T, seed=seed)
            idx = eligible_steps(w.inp)
            sig.append(np.mean([w.truth["kind"][t] == "sig" for t in idx]))
            blind.append(np.mean([
                blind_action(fam, lambda_of(w.inp.evidence.get(t, ()), PROP, t, w.inp.window),
                             bool(w.inp.pause[t])) != w.truth["optimal"][t] for t in idx]))
        out[fam] = dict(n_seeds=n_seeds, T=T,
                        signature_frac=round(float(np.mean(sig)), 3),
                        blind_error=round(float(np.mean(blind)), 3),
                        blind_error_min=round(float(np.min(blind)), 3),
                        blind_error_max=round(float(np.max(blind)), 3))
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    res = measure(n)
    print(f"floor = {NON_VACUITY_FLOOR}")
    for fam, m in res.items():
        print(f"{fam:12s} sig={m['signature_frac']:.3f}  "
              f"blind_error={m['blind_error']:.3f} "
              f"[{m['blind_error_min']:.3f}, {m['blind_error_max']:.3f}]")
