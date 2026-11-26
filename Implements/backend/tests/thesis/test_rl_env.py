import numpy as np
import pytest

pytest.importorskip("gymnasium")

from gymnasium.utils.env_checker import check_env  # noqa: E402

from app.simulator_thesis.rl.env import GLOBAL_DIM, MultiReaderInventoryEnv  # noqa: E402
from app.simulator_thesis.rl.features import OBS_DIM, apply_action  # noqa: E402

SPEC = {"n_devices": [30, 60], "readers": [2, 4], "resource_modes": ["independent", "tdma", "fdma"], "offsets": ["none", "random"],
        "subtype_mix": "random", "t_max_s": 20.0, "stall_timeout_s": 20.0, "max_frames": 400}


def _rollout(seed: int, n: int = 60) -> list[tuple]:
    env = MultiReaderInventoryEnv(SPEC)
    obs, info = env.reset(seed=seed)
    env.action_space.seed(seed)
    out = []
    for _ in range(n):
        obs, r, te, tr, info = env.step(env.action_space.sample())
        out.append((round(float(r), 9), info["reader_id"], info.get("k"), float(obs.sum())))
        if te or tr:
            break
    return out


def test_gymnasium_api():
    check_env(MultiReaderInventoryEnv(SPEC), skip_render_check=True)


def test_reset_seed_is_deterministic():
    assert _rollout(5) == _rollout(5)
    assert _rollout(5) != _rollout(6)


def test_episode_ends_with_summary_and_shapes():
    env = MultiReaderInventoryEnv(SPEC)
    obs, _ = env.reset(seed=1)
    assert obs.shape == (OBS_DIM,) and env.global_state().shape == (GLOBAL_DIM,)
    for _ in range(SPEC["max_frames"] + 1):
        obs, r, te, tr, info = env.step(np.zeros(2, dtype=np.float32))
        assert np.all((obs >= 0) & (obs <= 1))
        if te or tr:
            break
    s = info["episode_summary"]
    assert 2 <= s["readers"] <= 4
    assert 0 <= s["identified"] <= s["reachable"] <= s["devices"]
    assert s["resource_efficiency"] is None or 0 <= s["resource_efficiency"] <= 1


def test_homogeneous_mix_is_a_valid_distribution():
    env = MultiReaderInventoryEnv({**SPEC, "subtype_mix": "random"})
    env.reset(seed=0)
    for _ in range(30):
        _, _, info = env.sample_deployment(env.cfg)
        assert abs(sum(info["mix"]) - 1.0) < 1e-9


def test_apply_action_respects_grant_and_bounds():
    for a in ([-1, -1], [1, 1], [0, 0]):
        k, p, m, q = apply_action(np.array(a, dtype=float), 32, 0.5, f_r=4, k_max=512)
        assert k % 4 == 0 and 4 <= k <= 512
        assert 0 < p <= 1
