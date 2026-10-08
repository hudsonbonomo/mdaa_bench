"""Decision functions, measure_run shape, threshold location. Emendas-3."""
import pathlib, re, pytest
from adaptive import decide as D
from adaptive.measure import measure_run
from adaptive.worlds import WORLDS

_REPO = pathlib.Path(__file__).resolve().parent.parent
PREREG = _REPO / "adaptive" / "PREREGISTRO_v1.md"

_THRESHOLD_MAP = {
    "P1": ["0,90", "1,00"], "P2": ["0,95", "0,60", "0,85"],
    "P3": ["1,00", "0,50"], "P3b": ["1,00"],
    "P4": ["1,00", "0,95"], "P5": ["1,00", "0,95", "0,80"],
    "P6": ["1,00", "0,90"], "P7": ["1,00"],
}

def _get_paragraph(text: str, pred: str) -> str:
    preds = list(_THRESHOLD_MAP.keys())
    idx = preds.index(pred)
    pat = rf"\*\*{re.escape(pred)}\b"
    start = re.search(pat, text)
    assert start, f"**{pred} not found"
    if idx + 1 < len(preds):
        nxt = preds[idx + 1]
        end = re.search(rf"\*\*{re.escape(nxt)}\b", text[start.start()+1:])
        if end:
            return text[start.start():start.start()+1+end.start()]
    return text[start.start():]

@pytest.mark.parametrize("pred,thresholds", list(_THRESHOLD_MAP.items()))
def test_thresholds_in_paragraph(pred, thresholds):
    text = PREREG.read_text(encoding="utf-8")
    para = _get_paragraph(text, pred)
    for th in thresholds:
        assert th in para, f"{th} not in **{pred} paragraph"

def test_no_absolute_paths_in_test_files():
    # Build pattern from parts to avoid self-matching
    pat = re.compile("[A-Z]" + r":\\" + "|" + "/Us" + "ers/" + "|"
                     + "/ho" + "me/")
    for f in sorted((_REPO / "tests").glob("test_adaptive_*.py")):
        assert not pat.findall(f.read_text(encoding="utf-8")), \
            f"{f.name} contains absolute path"

def _row(**kw):
    base = {"R_declared_window": 40, "R_declared_n_adj": 0,
            "R_fixed_window": 40, "R_fixed_n_adj": 0,
            "R_simple_window": 40, "R_simple_n_adj": 0,
            "R_sym_window": 40, "R_sym_n_adj": 0,
            "R_cross_window": 40, "R_cross_n_adj": 0}
    base.update(kw)
    return base

def _rows(n=20, **kw):
    return [_row(**kw) for _ in range(n)]

def test_p1_passes():
    assert D.p1(_rows(R_declared_window=60, R_fixed_window=40),
                "S", 320, 3)["passed"] is True
def test_p1_fails_declared():
    r = D.p1(_rows(R_declared_window=40, R_fixed_window=40), "S", 320, 3)
    assert not r["passed"] and r["failure_class"] == "against_thesis"
def test_p1_not_applicable():
    assert D.p1(_rows(n=1), "N", 320, 3) is None
def test_p2_passes():
    assert D.p2(_rows(R_declared_n_adj=0, R_simple_n_adj=1),
                "N", 640, 3)["passed"] is True
def test_p2_fails_declared():
    r = D.p2(_rows(R_declared_n_adj=1, R_simple_n_adj=1), "N", 640, 3)
    assert not r["passed"] and r["failure_class"] == "against_thesis"
def test_p2_fails_simple():
    r = D.p2(_rows(R_declared_n_adj=0, R_simple_n_adj=0), "N", 320, 3)
    assert not r["passed"] and r["failure_class"] == "instrument_defect"

def test_p3_passes():
    r = D.p3(_rows(P3_R_declared_reproduced=5, P3_R_declared_total=5,
                   P3_R_mix_reproduced=1, P3_R_mix_total=4), "S", 640, 3)
    assert r["passed"] and r["mean_mix"] == 0.25
def test_p3_fails_mix():
    r = D.p3(_rows(P3_R_declared_reproduced=5, P3_R_declared_total=5,
                   P3_R_mix_reproduced=4, P3_R_mix_total=5), "S", 640, 3)
    assert not r["passed"] and r["failure_class"] == "instrument_defect"
def test_p3_fails_declared():
    r = D.p3(_rows(P3_R_declared_reproduced=3, P3_R_declared_total=5,
                   P3_R_mix_reproduced=1, P3_R_mix_total=4), "S", 640, 3)
    assert not r["passed"] and r["failure_class"] == "plugin_defect"
def test_p3_all_empty_instrument_defect():
    r = D.p3(_rows(P3_R_declared_reproduced=0, P3_R_declared_total=0,
                   P3_R_mix_reproduced=0, P3_R_mix_total=0), "S", 640, 3)
    assert not r["passed"] and r["failure_class"] == "instrument_defect"
def test_p3_one_empty_excluded():
    rows = [_row(P3_R_declared_reproduced=5, P3_R_declared_total=5,
                 P3_R_mix_reproduced=1, P3_R_mix_total=4)] * 19
    rows.append(_row(P3_R_declared_reproduced=0, P3_R_declared_total=0,
                     P3_R_mix_reproduced=0, P3_R_mix_total=0))
    r = D.p3(rows, "S", 640, 3)
    assert r["passed"] and r["excluded_declared"] == 1

def test_p3b_passes():
    assert D.p3b(_rows(P3b_failed=5, P3b_total=5),
                 "S", 640, 3)["passed"] is True
def test_p3b_fails():
    r = D.p3b(_rows(P3b_failed=3, P3b_total=5), "S", 640, 3)
    assert not r["passed"] and r["failure_class"] == "instrument_defect"
def test_p3b_all_empty():
    r = D.p3b(_rows(P3b_failed=0, P3b_total=0), "S", 640, 3)
    assert not r["passed"] and r["failure_class"] == "instrument_defect"

def test_p4_simple_passes():
    r = D.p4(_rows(P3_R_simple_reproduced=3, P3_R_simple_total=3),
             "S", 640, 3)
    assert r["passed"] and r["side"] == "R_simple"
def test_p4_simple_fails():
    r = D.p4(_rows(P3_R_simple_reproduced=1, P3_R_simple_total=3),
             "S", 640, 3)
    assert not r["passed"] and r["failure_class"] == "against_thesis"
def test_p4_simple_all_empty():
    r = D.p4(_rows(P3_R_simple_reproduced=0, P3_R_simple_total=0),
             "S", 640, 3)
    assert not r["passed"] and r["failure_class"] == "instrument_defect"
def test_p4_mix_passes():
    r = D.p4(_rows(R_mix_n_triggers=0), "N", 320, 3)
    assert r["passed"] and r["side"] == "R_mix"
def test_p4_mix_fails():
    r = D.p4(_rows(R_mix_n_triggers=1), "N", 320, 3)
    assert not r["passed"] and r["failure_class"] == "against_thesis"

def test_p5_passes():
    r = D.p5(_rows(P5_R_declared_monotone=True,
                   P5_R_declared_conflict_first_two=True,
                   P5_R_sym_shortened=True), "K", 320, 3)
    assert r["passed"] is True
def test_p5_fails_monotone():
    r = D.p5(_rows(P5_R_declared_monotone=False,
                   P5_R_declared_conflict_first_two=True,
                   P5_R_sym_shortened=True), "K", 320, 3)
    assert not r["passed"] and r["failure_class"] == "against_thesis"
def test_p5_fails_sym():
    r = D.p5(_rows(P5_R_declared_monotone=True,
                   P5_R_declared_conflict_first_two=True,
                   P5_R_sym_shortened=False), "K", 320, 3)
    assert not r["passed"] and r["failure_class"] == "instrument_defect"

def test_p6_passes():
    r = D.p6(_rows(P6_R_declared_adj_after_rename=0,
                   P6_R_declared_suspended_ok=True,
                   P6_R_declared_all_reason=True,
                   P6_R_cross_adj_after_rename=1), "V", 320, 3)
    assert r["passed"] is True
def test_p6_fails_declared():
    r = D.p6(_rows(P6_R_declared_adj_after_rename=1,
                   P6_R_declared_suspended_ok=True, P6_R_declared_all_reason=True,
                   P6_R_cross_adj_after_rename=1), "V", 320, 3)
    assert not r["passed"] and r["failure_class"] == "plugin_defect"
def test_p6_fails_cross():
    r = D.p6(_rows(P6_R_declared_adj_after_rename=0,
                   P6_R_declared_suspended_ok=True, P6_R_declared_all_reason=True,
                   P6_R_cross_adj_after_rename=0), "V", 320, 3)
    assert not r["passed"] and r["failure_class"] == "instrument_defect"

def test_p7_passes():
    r = D.p7(_rows(P7_declared_state_ok=True, P7_returns_after_redecl=True),
             "R", 320, 3)
    assert r["passed"] is True
def test_p7_fails():
    r = D.p7(_rows(P7_declared_state_ok=False, P7_returns_after_redecl=True),
             "R", 320, 3)
    assert not r["passed"] and r["failure_class"] == "plugin_defect"

_BASE = {f"{r}_{s}" for r in ("R_declared", "R_fixed", "R_simple",
         "R_sym", "R_cross") for s in ("window", "n_adj")}
_EXTRA = {
    "S": {"R_mix_window", "R_mix_n_triggers", "P3_R_declared_reproduced",
          "P3_R_declared_total", "P3_R_simple_reproduced",
          "P3_R_simple_total", "P3_R_mix_reproduced", "P3_R_mix_total",
          "P3b_failed", "P3b_total"},
    "N": {"R_mix_window", "R_mix_n_triggers"},
    "K": {"P5_R_declared_monotone", "P5_R_declared_conflict_first_two",
          "P5_R_sym_shortened", "cost_B_R_declared", "cost_B_R_fixed"},
    "V": {"P6_R_declared_adj_after_rename", "P6_R_declared_suspended_ok",
          "P6_R_declared_all_reason", "P6_R_cross_adj_after_rename",
          "cost_A_R_cross", "cost_A_R_declared"},
    "R": {"P7_declared_state_ok", "P7_returns_after_redecl"}}

@pytest.mark.parametrize("world_name", WORLDS)
def test_measure_run_keys(world_name):
    d = measure_run(world_name, T=320, k=3, seed=7001)
    missing = (_BASE | _EXTRA[world_name]) - set(d.keys())
    assert not missing, f"missing keys for {world_name}: {missing}"
