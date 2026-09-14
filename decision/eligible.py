"""THE SINGLE ELIGIBILITY PREDICATE of the decision bench.

The dynamics bench paid for this lesson once already (`observe.scorable_steps`,
cell `simetrizar-comparador-e-remedir-poder`): if two models are not scored on
the SAME steps, the comparison is not interpretable, and a null bolted on
afterwards does not repair a comparator that asks two different questions.

Here the risk is worse, because the models differ by construction in WHICH steps
they would like to be judged on. M2 abstains where M1 acts, so letting each
model choose its own denominator would let the abstainer look good by answering
fewer questions — exactly the asymmetry that inflated the M axis under missing
data, in a new costume.

A step is eligible iff
  * `sim.observe.scorable_steps` accepts it — t and t-1 both observed, which is
    what the shared one-step estimator needs to produce a belief at all, and
  * the evidence window fits inside the record (t >= window).

Every model is scored on this index set and no other. The test asserts equality
of INDEX SETS across the three models, not of counts: the same number of steps
drawn from different places would still be three different problems.
"""
from __future__ import annotations
import numpy as np

from sim.observe import scorable_steps
from sim.statespace import to_grid


def eligible_steps(inp) -> np.ndarray:
    _, _, mask = to_grid(inp.obs, t_max=inp.T)
    idx = scorable_steps(mask, np.arange(inp.T))
    return idx[idx >= inp.window]
