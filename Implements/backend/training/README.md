# Multi-reader RL training / 多读写器强化学习训练

Offline training for the thesis engine's per-reader (K, p\*) controller. The
backend never trains; it only loads policies from the registry
(`app/simulator_thesis/rl/policies/`). Terms: [Docs/VOCABULARY.md](../../../Docs/VOCABULARY.md).

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

| preset | steps | envs | devices / episode | eval grid | eval episodes per cell | time cap | frame cap |
|---|---|---|---|---|---|---|---|
| `smoke` | 1 024 | 1 | 40–120 | mini (1 cell) | 1 | 40 s | 2 000 |
| `small` | 50 000 | 4 | 100–400 | standard (18 cells) | 3 | 600 s | 100 000 |
| `medium` | 250 000 | 8 | 100–1 000 | standard | 5 | 900 s | 150 000 |
| `full` | 1 000 000 | 8 | 100–3 000 | full (60 cells) | 10 | 1 800 s | 300 000 |

The caps apply to training and evaluation episodes alike. They were raised
on 2026-11-12, when the conversion efficiency ξ made devices recharge up to
20× slower: at 120 s / 10 000 frames, 2-reader TDMA and 18-reader FDMA
episodes ended before 99 % identification.

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
rate (`app/simulator_thesis/rl/env.py`).

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
The frontend page `/thesis-simulation/training` lists experiments, curves,
matrices and promotes runs; `/thesis-simulation` runs select a policy by
`policy_id`.

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

## How training works

PS-PPO and MAPPO are trained from scratch in multi-reader deployments. The
single-reader PPO-LSTM of the aperiodic paper is not fine-tuned; it is only
used unchanged by `zero_shot_single`, as the reference.

| approach | network | trained |
|---|---|---|
| `zero_shot_single` | the paper's single-reader RecurrentPPO on every reader, one LSTM state per reader | no |
| PS-PPO | one new MLP shared by all readers (parameter sharing) | yes |
| MAPPO | one shared actor; during training a critic that also sees the global state | yes |
| IPPO | one actor and one critic per reader slot | yes (config only so far) |

One training loop (PS-PPO; `app/simulator_thesis/rl/env.py`):

1. **Reset: sample a deployment.** From the config's `env` block: the number of
   active readers (`readers`, e.g. 1–18) and which of the 18 lattice positions
   they take (`subset`), the start offsets, the resource mode and the subtype
   mix. From the scale: the device count (`n_devices`), the time cap and the
   frame cap. Every episode is a different warehouse (domain randomization).
2. **Step = one frame of one reader.** The engine is event driven: the reader
   with the earliest clock runs next. The environment gives that reader's
   observation to the shared network, the action sets its (K, p\*), the
   engine runs the frame, and the reward is credited to that decision. The
   next step is another reader, with the same network. 18 readers do not need
   18 networks.
3. **Reward** of reader r's frame:

   ```
   local  = ((1 - alpha) * new_ids_r - alpha * collisions_r) / t_frame
   team   = new IDs of all readers since r's previous decision / elapsed time
   reward = (beta * local + (1 - beta) * team) / RATE_SCALE
   ```

   `alpha` is the collision weight of the paper's Eq. (8). `team` rewards
   cooperation instead of grabbing shared resources.
4. **Episode end.** All reachable devices identified, the time cap, the stall
   timeout or `max_frames`. Then back to step 1 with a new deployment, until
   `total_steps` decisions have been made. PPO updates every `n_steps` ×
   `n_envs` decisions.
5. **Evaluation.** The final policy and DFSA run on the same deployments and
   seeds in every cell of the evaluation grid (readers × resource mode ×
   offsets); `t99_vs_dfsa` is the per-cell ratio.

### What `--scale` changes

The scale sets the training budget and the episode size. It does **not**
change which reader configurations are trained on: the reader range,
subsets, offsets and resource modes come from the config file.

| set by the scale | set by the config |
|---|---|
| total steps, parallel envs, PPO rollout / batch / epochs | active readers (`readers`), lattice subset |
| device count range per episode (40–120 up to 100–3000) | start offsets, resource modes, scheme |
| time cap, frame cap | subtype mix, alpha, beta, seeds |
| evaluation grid and episodes per cell | |

`--n-devices LO HI` overrides the device range of any scale. To train on other
reader counts, edit the config's `env.readers` or use another config
(`ps_ppo_fixed2` trains on the 2-reader pair only).

### Policies in the registry

| policy id | what it is |
|---|---|
| `zero_shot_aperiodic_a0p5` | built-in default: the aperiodic paper's single-reader RecurrentPPO (alpha = 0.5) on every reader, no training |
| `zero_shot_single__…` | the same checkpoint, promoted from the `zero_shot_single` experiment so that it carries an evaluation summary |
| `ps_ppo_randomized__…` | PS-PPO trained with randomization over 1–18 readers, offsets and resource modes |
| `mappo__…` | MAPPO with the same randomization |

The id suffix is `a<alpha>__b<beta>__s<seed>__<UTC stamp>`. The promoted runs
are `small` scale (about 53 k steps, 5 % of the paper budget). The
`…__20261112T173120` runs are trained with ξ and the 600 s cap; their T99 is
slower than DFSA (geometric mean: MAPPO 1.36, PS-PPO 1.44, zero-shot 1.29), so
`small` is not enough training.

## 训练过程（中文）

PS-PPO 和 MAPPO 都是在多读写器部署中**从零训练**的。非周期论文的单读写器 PPO-LSTM 没有被继续训练，只在 `zero_shot_single` 中原样使用，作为对照。

| 方案 | 网络 | 是否训练 |
|---|---|---|
| `zero_shot_single` | 论文的单读写器 RecurrentPPO，放到每个读写器上，每个读写器有自己的 LSTM 状态 | 否 |
| PS-PPO | 一个新的 MLP，所有读写器共用（参数共享） | 是 |
| MAPPO | 共用一个演员网络；训练时另有一个能看到全局状态的评论家 | 是 |
| IPPO | 每个读写器槽位各有一个演员和一个评论家 | 是（目前只有配置） |

一次训练循环（PS-PPO，`app/simulator_thesis/rl/env.py`）：

1. **重置：随机生成一个部署。** 从配置的 `env` 中取：活跃读写器数量（`readers`，例如 1–18）和它们占 18 个格点中的哪些位置（`subset`）、启动偏移、资源模式、设备类型比例。从 scale 中取：设备数量（`n_devices`）、时间上限、帧数上限。每一局都是一个不同的仓库（域随机化）。
2. **一步 = 一个读写器的一帧。** 引擎是事件驱动的，时钟最早的读写器先跑。环境把这个读写器的观测交给共享网络，动作决定它这一帧的 (K, p\*)，引擎跑完这一帧，奖励记在这次决策上。下一步换另一个读写器，用的还是同一个网络。18 个读写器不需要 18 个网络。
3. **奖励**（读写器 r 的一帧）：local 看它自己的新识别数和碰撞数，team 看所有读写器的总识别速度，reward = β·local + (1−β)·team。α 是论文第 (8) 式的碰撞权重；team 项鼓励读写器互相配合，而不是抢共享资源。
4. **一局结束：** 可达设备全部识别完、时间上限、停滞超时或 `max_frames`。然后回到第 1 步生成新部署，直到决策总数达到 `total_steps`。每 `n_steps` × `n_envs` 次决策做一次 PPO 更新。
5. **评估：** 最终策略和 DFSA 在评估网格的每个场景（读写器数 × 资源模式 × 偏移）上用相同的部署和种子运行；`t99_vs_dfsa` 是每个场景的比值。

### `--scale` 改变什么

scale 决定训练预算和每局的规模，**不改变**训练用的读写器配置。读写器范围、位置子集、偏移和资源模式都来自配置文件。

| 由 scale 决定 | 由配置文件决定 |
|---|---|
| 总步数、并行环境数、PPO 的 rollout / batch / epochs | 活跃读写器数量（`readers`）、格点子集 |
| 每局设备数量范围（从 40–120 到 100–3000） | 启动偏移、资源模式、寻呼方案 |
| 时间上限、帧数上限 | 设备类型比例、alpha、beta、种子 |
| 评估网格、每个场景的评估局数 | |

`--n-devices LO HI` 可以覆盖任何 scale 的设备范围。想换读写器数量训练，就改配置的 `env.readers`，或者用其他配置（`ps_ppo_fixed2` 只在 2 个读写器上训练）。

### 注册表里的策略

| 策略 id | 含义 |
|---|---|
| `zero_shot_aperiodic_a0p5` | 内置默认：非周期论文的单读写器 RecurrentPPO（α = 0.5）放到每个读写器上，不训练 |
| `zero_shot_single__…` | 同一个模型文件，从 `zero_shot_single` 实验发布而来，所以带有评估摘要 |
| `ps_ppo_randomized__…` | PS-PPO，在 1–18 个读写器、偏移和资源模式上随机化训练 |
| `mappo__…` | MAPPO，随机化方式相同 |

id 后缀是 `a<alpha>__b<beta>__s<seed>__<UTC 时间戳>`。已发布的运行都是 `small` 规模（约 5.3 万步，相当于论文预算的 5%）。`…__20261112T173120` 是加入 ξ、时间上限 600 s 后重新训练的版本，T99 比 DFSA 慢（几何平均：MAPPO 1.36、PS-PPO 1.44、零样本 1.29），说明 `small` 的训练量不够。
