import json

import pytest

pytest.importorskip("stable_baselines3")

from training import evaluate, promote, train  # noqa: E402
from training.scales import PRESETS, resolve_scale  # noqa: E402


def test_scale_resolution():
    assert resolve_scale("small") == PRESETS["small"]
    assert resolve_scale("small:2").total_steps == 2 * PRESETS["small"].total_steps
    assert resolve_scale("0.1").total_steps == PRESETS["full"].total_steps // 10
    with pytest.raises(ValueError):
        resolve_scale("-1")


@pytest.mark.parametrize("config", ["ps_ppo_fixed2", "mappo", "ippo", "zero_shot_single"])
def test_train_evaluate_promote(config, tmp_path, monkeypatch):
    monkeypatch.setattr(train, "run_dir", lambda *a: _rd(tmp_path, *a))
    monkeypatch.setenv("THESIS_POLICY_DIR", str(tmp_path / "registry"))
    rc = train.main(["--config", config, "--scale", "smoke", "--steps", "300", "--n-devices", "20", "40", "--promote"])
    assert rc == 0
    run = next((tmp_path / "out").iterdir())
    meta = json.loads((run / "meta.json").read_text())
    assert meta["status"] == "done"
    assert set(meta["eval_summary"]) == {"policy", "dfsa"}
    assert (run / "eval_matrix.csv").exists() and (run / "plots" / "eval_heatmap.png").exists()
    pid = meta["promoted"]
    from app.thesis_simulator.rl.policy import PolicyController

    ctl = PolicyController.from_registry(pid)
    assert ctl.policy_id == pid
    with pytest.raises(FileExistsError):
        promote.promote(run)


def _rd(tmp_path, experiment, stamp, alpha, beta, seed):
    d = tmp_path / "out" / f"{experiment}_{seed}"
    for sub in ("checkpoints", "plots"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def test_evaluate_cells_are_paired():
    env_cfg = {"n_devices": [20, 30], "t_max_s": 10.0, "stall_timeout_s": 10.0, "max_frames": 300}
    rows = evaluate.evaluate({"dfsa": {"kind": "dfsa"}, "dfsa2": {"kind": "dfsa"}}, "mini", 1, env_cfg)
    a, b = rows
    assert {k: v for k, v in a.items() if k != "candidate"} == {k: v for k, v in b.items() if k != "candidate"}
