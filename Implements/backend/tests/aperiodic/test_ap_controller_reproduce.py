import numpy as np

from app.aperiodic_simulator.reproduction import controller_reproduce as cr
from app.aperiodic_simulator.rl import checkpoint as ck
from app.aperiodic_simulator.core.states import HarvestingScenario


def test_methods_share_seeds_and_differ_only_in_controller():
    a = cr.method_batch("pfsa_L8", HarvestingScenario.MULTI_SOURCE, 400, 2, 7, 1, t_curve=1.0)
    b = cr.method_batch("cmebe", HarvestingScenario.MULTI_SOURCE, 400, 2, 7, 1, t_curve=1.0)
    assert [m["n_eff"] for m in a.episodes] == [m["n_eff"] for m in b.episodes]
    assert a.cfg.controller.value == "pfsa_pze" and a.cfg.L_fixed == 8
    assert b.cfg.controller.value == "cmebe" and b.cfg.L_initial == 1


def test_figure7_reports_missing_rl_instead_of_substituting(tmp_path, monkeypatch):
    monkeypatch.setattr(ck, "CHECKPOINT_DIR", tmp_path)
    d = cr.figure7(2, 0, 1, n_tot=500, progress=lambda s: None)
    curves = d["panels"]["multi_source"]["curves"]
    assert set(curves) == {"dfsa_schoute", "cmebe"}
    assert "recurrent_ppo" in d["unavailable"]
    assert d["checkpoints"]["0.5"]["available"] is False
    for c in curves.values():
        assert c["reference"]["paper_T"]["T50"] > 0
        assert np.all(np.diff(c["curve_mean"]) >= -1e-9)


def test_table_v_rows_compare_against_paper_values(tmp_path, monkeypatch):
    monkeypatch.setattr(ck, "CHECKPOINT_DIR", tmp_path)
    monkeypatch.setattr(cr, "table5", lambda: [{"scenario": "multi_source", "n_tot": 300, "recurrent_ppo": 5.0, "pfsa_L1": 9.0, "pfsa_L8": 6.0, "pfsa_L32": 7.0}])
    rows = cr.table_v(2, 0, 1, progress=lambda s: None)
    by = {r["method"]: r for r in rows}
    assert by["recurrent_ppo"]["available"] is False
    for L in (1, 8, 32):
        r = by[f"pfsa_L{L}"]
        assert r["available"] and r["sim_s"] > 0 and r["paper_s"] == {1: 9.0, 8: 6.0, 32: 7.0}[L]
        assert r["rel_err_pct"] == (r["sim_s"] - r["paper_s"]) / r["paper_s"] * 100


def test_cached_result_with_more_episodes_is_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "results_dir", lambda: tmp_path)
    data = {"figure": "tables", "episodes": 100, "table_v": [], "table_vi": []}
    assert cr.write_outputs(data, plot=False)
    assert cr.write_outputs({**data, "episodes": 5}, plot=False) == []
    assert cr.cached_episodes(tmp_path / "tables" / "tables.json") == 100
