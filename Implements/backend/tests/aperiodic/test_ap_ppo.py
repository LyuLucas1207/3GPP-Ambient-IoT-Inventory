import json
import math

import numpy as np
import pytest

from app.aperiodic_simulator.core.config import EpisodeConfig
from app.aperiodic_simulator.rl import checkpoint as ck
from app.aperiodic_simulator.rl.env import AperiodicInventoryEnv
from app.aperiodic_simulator.rl.transforms import (
    M_RANGE,
    OBS_DIM,
    Q_RANGE,
    action_to_multipliers,
    apply_action,
    normalize_observation,
)
from app.aperiodic_simulator.core.timing import collision_time_equivalent_s, success_time_equivalent_s


def test_action_transform_ranges_and_log_center():
    assert action_to_multipliers([-1, -1]) == pytest.approx((M_RANGE[0], Q_RANGE[0]))
    assert action_to_multipliers([1, 1]) == pytest.approx((M_RANGE[1], Q_RANGE[1]))
    m, q = action_to_multipliers([0, 0])
    assert m == pytest.approx(math.sqrt(0.25 * 10)) and q == pytest.approx(1.0)
    assert action_to_multipliers([5, -5]) == pytest.approx((10.0, 0.1))  # out-of-box actions are clipped


def test_environment_rules_cannot_be_bypassed():
    assert apply_action(10.0, 10.0, 40, 0.5, 83, 1e-4) == (83, 1.0)
    assert apply_action(0.25, 0.1, 1, 1e-4, 83, 1e-4) == (1, 1e-4)
    assert apply_action(1.01, 1.0, 16, 0.3, 83, 1e-4)[0] == math.ceil(1.01 * 16)


def test_observation_is_eq5_without_c2():
    obs = {"S1": 3, "S2a": 1, "S2b": 0, "I": 50, "C": 10, "L": 8, "p": 0.4, "decoded": 4}
    x = normalize_observation(obs, F=8, L_max=83)
    assert x.shape == (OBS_DIM,)
    assert x.tolist() == pytest.approx([3 / 64, 1 / 64, 0, 50 / 64, 10 / 64, 8 / 83, 0.4])


def test_env_reward_matches_eq8_and_hides_c2():
    env = AperiodicInventoryEnv(alpha=0.5, fixed={"n_tot": 800, "L_initial": 2, "p_initial": 1.0, "seed": 5, "type_mix": "mixed"})
    obs, _ = env.reset(seed=0)
    assert obs.shape == (OBS_DIM,) and env.observation_space.contains(obs)
    s = env.system
    for _ in range(5):
        obs, r, term, trunc, info = env.step(np.array([0.3, 0.0], dtype=np.float32))
        t0, t1, _, _, S = env.ep.history[-1][:5]
        expected = (0.5 * S * success_time_equivalent_s(s) - 0.5 * info["C2"] * collision_time_equivalent_s(s)) / (t1 - t0)
        assert r == pytest.approx(expected)
        assert info["C2"] >= 0 and len(obs) == 7
        if term or trunc:
            break


def test_env_training_distribution_samples():
    env = AperiodicInventoryEnv()
    env.reset(seed=0)
    seen_mix, seen_L, ps, ns = set(), set(), [], []
    for _ in range(60):
        cfg = env.sample_config()
        seen_mix.add(cfg.type_mix)
        seen_L.add(cfg.L_initial)
        ps.append(cfg.p_initial)
        ns.append(cfg.n_tot)
    assert seen_mix == {"mixed", "1", "2a", "2b"}
    assert seen_L <= {1, 2, 4, 8, 16, 32} and len(seen_L) >= 4
    assert all(0 < p <= 1 for p in ps) and all(100 <= n <= 15000 for n in ns)
    assert env.ep is not None and env.scenario.value == "multi_source"


@pytest.fixture(scope="module")
def tiny_model():
    from sb3_contrib import RecurrentPPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    from app.aperiodic_simulator.rl.train import policy_kwargs

    venv = DummyVecEnv([lambda: AperiodicInventoryEnv(n_range=(100, 400))])
    model = RecurrentPPO("MlpLstmPolicy", venv, n_steps=64, batch_size=32, n_epochs=1, policy_kwargs=policy_kwargs(), seed=0, device="cpu")
    model.learn(64)
    return model


def test_architecture_separate_actor_critic_lstm(tiny_model):
    pol = tiny_model.policy
    assert pol.lstm_actor.hidden_size == 128 and pol.lstm_actor.num_layers == 1
    assert pol.lstm_critic is not None and pol.lstm_critic is not pol.lstm_actor
    pi = [m for m in pol.mlp_extractor.policy_net if hasattr(m, "out_features")]
    vf = [m for m in pol.mlp_extractor.value_net if hasattr(m, "out_features")]
    assert [m.out_features for m in pi] == [128, 128] and [m.out_features for m in vf] == [128, 128]
    assert pol.action_space.shape == (2,)


def test_checkpoint_roundtrip_and_controller(tiny_model, tmp_path, monkeypatch):
    from app.aperiodic_simulator.controllers import recurrent_ppo as rp
    from app.aperiodic_simulator.core.runner import run_episode
    from app.aperiodic_simulator.core.states import ControllerName

    monkeypatch.setattr(ck, "CHECKPOINT_DIR", tmp_path)
    with pytest.raises(ck.CheckpointMissing):
        rp.ppo_controller_factory(0.5)
    zp = ck.checkpoint_path(0.5)
    tiny_model.save(zp)
    meta = {"alpha": 0.5, "seed": 0, "training_steps": 64, "architecture": "test", "trained_scenario": "multi_source", "sha256": ck.sha256_file(zp)}
    ck.meta_path(0.5).write_text(json.dumps(meta))
    st = ck.ppo_status_payload()
    assert st["available"] and st["fully_trained"] is False and st["training_steps"] == 64

    factory = rp.ppo_controller_factory(0.5)
    cfg = EpisodeConfig(n_tot=300, seed=2, controller=ControllerName.RECURRENT_PPO, L_initial=1, L_fixed=1, t_max_s=60.0)
    ctrl = factory(cfg)
    res = run_episode(cfg, controller=ctrl)
    hist = res.controller_history
    assert hist[0]["m"] is None and all(h["m"] is not None for h in hist[1:])
    for prev, cur in zip(hist, hist[1:]):
        L_exp, p_exp = apply_action(cur["m"], cur["q"], prev["L"], prev["p"], ctrl.L_max, ctrl.p_floor)
        assert (cur["L"], cur["p"]) == (L_exp, pytest.approx(p_exp))
    assert ctrl.state is not None  # recurrent state carried across rounds
    ctrl.reset(1, 1.0)
    assert ctrl.state is None and ctrl.episode_start.all()

    rp._MODELS.clear()  # force a fresh load from the saved zip
    again = run_episode(cfg, controller=rp.ppo_controller_factory(0.5)(cfg)).controller_history
    assert [(h["L"], h["p"]) for h in again] == [(h["L"], h["p"]) for h in hist]

    zp.write_bytes(zp.read_bytes() + b"tamper")
    with pytest.raises(ck.CheckpointMissing):
        rp.ppo_controller_factory(0.5)


def test_api_refuses_ppo_without_checkpoint(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(ck, "CHECKPOINT_DIR", tmp_path)
    client = TestClient(app)
    body = {"num_devices": 200, "ppo_enabled": True, "controller": "recurrent_ppo", "L_mode": "adaptive", "max_time_s": 30}
    res = client.post("/api/aperiodic-simulator/simulate", json=body)
    assert res.status_code == 409
    assert "train_ppo/train_ppo.py" in res.json()["detail"]
