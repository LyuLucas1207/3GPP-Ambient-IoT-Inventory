# Multi-reader RL training / 多读写器强化学习训练

Offline training for the thesis engine's per-reader (K, p\*) controller. The
backend never trains; it only loads policies from the registry
(`app/thesis_simulator/rl/policies/`). Terms: [Docs/VOCABULARY.md](../../../Docs/VOCABULARY.md).

后端不训练，只从策略注册表加载。流程：`train` → `outputs/` → `promote` → 注册表 → 前端 / API 用 `policy_id` 选择。

## Quick start

```bash
cd Implements/backend
.venv/bin/python -m training.train --config ps_ppo_randomized --scale smoke     # seconds, checks the pipeline
.venv/bin/python -m training.train --config ps_ppo_randomized --scale small --promote
.venv/bin/python -m training.train --config mappo --scale 0.25 --seeds 0 1 2 --jobs 3
.venv/bin/python -m training.evaluate --runs training/outputs/ps_ppo_randomized/<run> training/outputs/ps_ppo_fixed2/<run> --grid full
.venv/bin/python -m training.promote training/outputs/mappo/<run> --policy-id mappo_v1
```

Or `scripts/menu.sh` → `thesis` → *train (multi-reader)* / *evaluate policies* / *promote policy*.

## Scale

| preset | steps | envs | devices / episode | eval grid | eval episodes per cell |
|---|---|---|---|---|---|
| `smoke` | 1 024 | 1 | 40–120 | mini (1 cell) | 1 |
| `small` | 50 000 | 4 | 100–400 | standard (18 cells) | 3 |
| `medium` | 250 000 | 8 | 100–1 000 | standard | 5 |
| `full` | 1 000 000 | 8 | 100–3 000 | full (60 cells) | 10 |

`--scale small:3` triples `small`. A bare number multiplies `full`
(`--scale 0.1` = 100 000 steps). Factors scale steps and (when ≥ 1) evaluation
episodes. `--steps`, `--n-envs`, `--n-devices LO HI`, `--eval-episodes` and
`--eval-grid` override single values.

## Configs (`configs/*.json`)

| config | algorithm | training deployments |
|---|---|---|
| `ps_ppo_fixed2` | PS-PPO (stable-baselines3) | TR D1T1-A2 pair only, independent resources |
| `ps_ppo_fixed18_hybrid` | PS-PPO | full 18-reader hall, hybrid TDMA+FDMA only |
| `ps_ppo_randomized` | PS-PPO | 1–18 random readers, offsets, resource policies, subtype mixes |
| `mappo` | MAPPO (shared actor, centralized critic) | as `ps_ppo_randomized` |
| `ippo` | IPPO (one actor + local critic per reader slot) | as `ps_ppo_randomized` |
| `zero_shot_single` | none: aperiodic single-reader RecurrentPPO on every reader | evaluation only |

`alphas`, `betas` and `seeds` are lists: every combination is one job
(`--jobs N` runs N in parallel). `alpha` weights collisions against new IDs
in the local reward, `beta` weights the reader's own rate against the team
rate (`app/thesis_simulator/rl/env.py`).

The two `fixed` configs are the "retrain per configuration" references:
compare them with `ps_ppo_randomized` in one `evaluate.py` call.

## Outputs

```
outputs/<experiment>/<UTC stamp>__a<alpha>__b<beta>__s<seed>/
  meta.json              status, timings, sidecar fields, evaluation summary
  checkpoints/final.zip  the policy (zero_shot_single has none: it points at the aperiodic zip)
  checkpoints/final.json registry sidecar: algo, alpha, beta, seed, scale, configs, specs, versions, SHA-256
  train_metrics.csv      one row per training episode: return, identified fraction, T99, mean ID time, resource efficiency
  eval_matrix.csv        mean per test cell (readers x resource policy x offsets), policy vs DFSA, T99 ratio
  eval_episodes.csv      every evaluation episode
  plots/learning_curve.png, plots/eval_heatmap.png
  tb/                    TensorBoard logs, only if tensorboard is installed
outputs/_eval/<stamp>/   standalone evaluate.py results
```

`outputs/` is git-ignored. In Docker (prod compose) it and the registry are
bind-mounted, so new runs and promoted policies appear without a rebuild.
The frontend page `/thesis/training` lists experiments, curves, matrices and
promotes runs; `/thesis` runs select a policy by `policy_id`.

## What is learned

One decision per frame of the reader whose clock is earliest. Observation
(41 values, `rl/features.py`): the last 4 frames of that reader (success,
collision and empty fractions, new IDs and joiners per resource, log K, p\*,
frame duration) plus its context (active readers, neighbours in the conflict
graph, colour, subband share, start offset, position, time since the last new
ID, frames run). Device counts, energies and availability are never observed.
Action: two values in [-1, 1] mapped to
multipliers of the previous K (rounded to the reader's subband grant) and p\*,
as in the aperiodic paper. The first frame of each reader uses the DFSA
cold start.
