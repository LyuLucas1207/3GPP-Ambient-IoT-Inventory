# Recurrent PPO for the aperiodic-paging paper

| File | Role |
|---|---|
| `transforms.py` | observation scaling and the action transform. Training and inference share this one definition. |
| `env.py` | Gymnasium env; one step = one CBRA round of the proposed aperiodic protocol |
| `train.py` | sb3-contrib `RecurrentPPO` with the Table III settings, plus checkpoint and metadata writer |
| `evaluate.py` | runs a checkpoint through the same `run_batch` as every baseline |
| `checkpoint.py` | checkpoint paths, SHA-256 verification, `/ppo/status` payload |
| `../controllers/recurrent_ppo.py` | inference adapter: observation + LSTM state → `(L, p)` and `(m, q)` |

## Train

```bash
cd Implements
python backend/scripts/aperiodic/train_ppo/train_ppo.py --steps 1000000 --seed 42            # paper setting, alpha = 0.5
python backend/scripts/aperiodic/train_ppo/train_ppo.py --steps 1000000 --seed 42 --alpha 0  # Table VI sweep: 0, 0.25, 0.75
```

Each run writes `checkpoints/recurrent_ppo_alpha_<a>.zip` plus a `.json`
sidecar. The sidecar records steps, seed, config hash, package versions, git
commit, SHA-256, the transforms, and the full training config. The API
verifies the SHA-256 before every load. `fully_trained` is false below
1,000,000 steps, and the UI and API then warn that the results do not
reproduce the paper's policy.

## Exactly what is implemented

* **State** (Eq. 5): `[S1, S2a, S2b, I, C, L_prev, p_prev]` of the previous
  round. Counts are divided by `L_prev·F`, `L_prev` by `L_max`, and `p` is
  unchanged. The scaling is invertible, so no information is lost. C2,
  backlog, energies and availability are never observed.
* **Action**: the policy emits `a ∈ [-1, 1]²`. The mapping is log-uniform to
  `m ∈ [0.25, 10]` and `q ∈ [0.1, 10]` (the paper fixes only the ranges). The
  environment then applies `L = max(1, min(ceil(m·L_prev), 83))` and
  `p = clip(q·p_prev, 1e-4, 1)`.
* **Reward** (Eq. 8): `((1−α)·(S1+S2a+S2b)·t_S − α·C2·t_C)/T_round`, computed
  by the engine. C2 counts physically multi-occupied AOs that contain a
  type-2a/2b device; it is a training signal only.
* **Episodes** (Sec. V-A3), all multi-source:
  * `N_tot ~ U{100..15000}`
  * homogeneous (one random type) or heterogeneous, with probability 0.5 each
  * `L_1 ~ U{1,2,4,8,16,32}` and `p_1 ~ U(0,1]`
  * a fresh layout, channel and initial availability per episode
  * Round 1 is played with `(L_1, p_1)`, and the agent acts from round 2 on.
* **Network**: separate actor and critic `LSTM(1×128)`, each followed by
  `MLP(128, 128, ReLU)` (`shared_lstm=False, enable_critic_lstm=True`).
  Hidden states reset at episode starts.
* **Table III**: lr 3e-4, γ 0.9, λ 0.95, clip 0.2, entropy 0.01, vf 0.02,
  grad-norm 0.5, 2048 steps/rollout, minibatch 256, 10 epochs.
* **Value normalisation**: `VecNormalize(norm_obs=False, norm_reward=True)`.
  This SB3 mechanism keeps value targets O(1) and affects training only.
* **Inference**: deterministic (mean action). The same seeds as the
  baselines are used, via `run_batch`.
