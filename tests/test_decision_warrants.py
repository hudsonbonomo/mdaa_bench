"""chi is declared, frozen, and load-bearing.

Three things have to be true or the warrant layer proves nothing: the file
cannot change between definition and evaluation without a test failing; the
rules actually bite (a mutated chi changes the verdict); and the pre-registration
carries the same hash the code verifies.
"""
import pathlib
import shutil

import pytest
import yaml

from decision import worlds as W
from decision.epistemic import lambda_of
from decision.warrant import (CHI_PATH, FREEZE_PATH, Chi, FrozenChiViolation, chi_hash,
                              frozen_hash, load_chi, remedy, warranted)
from decision.worlds import CONDITIONS, PROP, SUBJECT, Evidence, PauseRecord, Scope

AP, NAO = CONDITIONS
ROOT = pathlib.Path(__file__).resolve().parents[1]


def ev(c, v, t=5, prov="post"):
    return Evidence(Scope(SUBJECT, PROP, c, t), v, prov)


def lam(items, t=5, window=1):
    return lambda_of(items, PROP, t, window)


def test_the_frozen_hash_matches_the_file_on_disk():
    assert chi_hash() == frozen_hash()
    assert load_chi().sha256 == frozen_hash()


def test_a_changed_chi_is_refused(tmp_path):
    """The vulnerability the paper declares (D8), turned into an invariant."""
    copy = tmp_path / "warrants.yaml"
    shutil.copy(CHI_PATH, copy)
    copy.write_text(copy.read_text(encoding="utf-8") + "\n# tuned after seeing the result\n",
                    encoding="utf-8")
    with pytest.raises(FrozenChiViolation):
        load_chi(copy)
    assert load_chi(copy, verify=False).version == 1      # readable, just not trusted


def test_the_pre_registration_carries_the_same_hash():
    doc = ROOT / "PREREGISTRO_v4.md"
    if not doc.exists():
        pytest.skip("PREREGISTRO_v4.md not generated yet")
    assert chi_hash() in doc.read_text(encoding="utf-8")


def _without_provenance(text):
    return [ln for ln in text.splitlines() if not ln.startswith("**Proveniência:**")]


def test_the_pre_registration_is_regenerated_from_the_code():
    """A GUARD WITH A FIXED POINT, unlike `tests/test_prereg.py`.

    That one compares the whole document, including a provenance line that reads
    `git rev-parse HEAD`, so it can only be green in the instant before a commit:
    regenerating and committing moves HEAD and makes the document stale again.
    Here the provenance line is excluded from the comparison — it is the only
    part that cannot have a fixed point — and everything the code introspects is
    still compared exactly. The file on disk is restored either way, so running
    the suite never edits a pre-registration."""
    import subprocess
    import sys
    doc = ROOT / "PREREGISTRO_v4.md"
    if not doc.exists():
        pytest.skip("PREREGISTRO_v4.md not generated yet")
    before = doc.read_bytes()
    try:
        r = subprocess.run([sys.executable, "make_prereg_decision.py"], cwd=ROOT,
                           capture_output=True, text=True, timeout=600)
        assert r.returncode == 0, r.stderr
        now = doc.read_text(encoding="utf-8")
    finally:
        doc.write_bytes(before)
    assert _without_provenance(now) == _without_provenance(before.decode("utf-8")), (
        "PREREGISTRO_v4.md is stale - run `python make_prereg_decision.py`")


def test_chi_sets_the_admissibility_window_the_world_uses():
    assert load_chi().window == W.WINDOW


def test_act_needs_a_decided_reading_a_support_and_no_pause():
    chi = load_chi()
    decided = lam((ev(NAO, 1), ev(NAO, 1)))
    assert warranted(chi, "ACT", decided, (), SUBJECT, 5).ok
    assert warranted(chi, "ACT", lam(()), (), SUBJECT, 5).reason == "no_support"
    assert warranted(chi, "ACT", lam((ev(NAO, 1), ev(NAO, -1))), (), SUBJECT, 5).reason == "conflict"
    assert warranted(chi, "ACT", lam((ev(AP, 1), ev(NAO, -1))), (), SUBJECT, 5).reason == "cross_scope"
    spont = lam((ev(NAO, 1, prov="spont"), ev(NAO, 1, prov="spont")))
    assert warranted(chi, "ACT", spont, (), SUBJECT, 5).reason == "provenance"
    p = (PauseRecord(SUBJECT, "ACT", 0, 10),)
    assert warranted(chi, "ACT", decided, p, SUBJECT, 5).reason == "pause"


def test_a_pause_suspends_intervening_and_not_looking():
    """No action other than ACT can ever be denied FOR the pause. Some are still
    denied for want of support, which is a different clause."""
    chi = load_chi()
    p = (PauseRecord(SUBJECT, "ACT", 0, 10),)
    states = (lam(()), lam((ev(NAO, 1),)), lam((ev(NAO, 1), ev(NAO, -1))),
              lam((ev(AP, 1), ev(NAO, -1))))
    for a in ("OBSERVE", "PROBE", "COMPARE", "WAIT"):
        for state in states:
            assert warranted(chi, a, state, p, SUBJECT, 5).reason != "pause", (a, state)
    assert warranted(chi, "WAIT", lam(()), p, SUBJECT, 5).ok


def test_a_pause_for_another_subject_or_another_class_does_not_bind():
    chi = load_chi()
    decided = lam((ev(NAO, 1), ev(NAO, 1)))
    for p in (PauseRecord("S2", "ACT", 0, 10), PauseRecord(SUBJECT, "PROBE", 0, 10),
              PauseRecord(SUBJECT, "ACT", 20, 30)):
        assert warranted(chi, "ACT", decided, (p,), SUBJECT, 5).ok, p


def test_every_denial_has_a_remedy_and_none_of_them_is_act():
    chi = load_chi()
    for reason in ("no_support", "conflict", "cross_scope", "provenance", "pause"):
        r = remedy(chi, "ACT", reason)
        assert r in W.ACTIONS and r != "ACT", (reason, r)


def test_every_rule_names_the_external_criterion_that_judges_it():
    chi = load_chi()
    for name, rule in chi.actions.items():
        assert rule["warrant_claim"].strip(), name
        assert rule["external_criterion"], name
        assert all(isinstance(c, str) for c in rule["external_criterion"]), name


def test_the_rules_are_not_decorative(tmp_path):
    """Mutation: drop the provenance requirement from a COPY of chi and the same
    world state becomes warranted. If it did not, the clause was scenery."""
    raw = yaml.safe_load(CHI_PATH.read_text(encoding="utf-8"))
    raw["actions"]["ACT"]["provenance"]["required"] = None
    copy = tmp_path / "warrants.yaml"
    copy.write_text(yaml.safe_dump(raw), encoding="utf-8")
    loose = load_chi(copy, verify=False)
    spont = lam((ev(NAO, 1, prov="spont"), ev(NAO, 1, prov="spont")))
    assert warranted(load_chi(), "ACT", spont, (), SUBJECT, 5).reason == "provenance"
    assert warranted(loose, "ACT", spont, (), SUBJECT, 5).ok
