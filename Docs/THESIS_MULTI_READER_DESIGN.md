# Multi-reader thesis extension — design notes · 多读写器论文扩展设计说明

English first, 中文在后。Terms: [VOCABULARY.md](./VOCABULARY.md). Formulas: [FORMULAS.md](./FORMULAS.md).

---

## English

### 1. Scope

The thesis engine (`Implements/backend/app/simulator_thesis`) was extended in three phases, each behind a config block on `POST /sections/{id}/runs` that defaults to the old behaviour:

| Block | Default | What it adds |
| --- | --- | --- |
| `termination` | `oracle` | Reader-side stop rules: `quiet_rounds`, `id_rate`, `energy_bound`, `combined` |
| `resource` | `independent` | Coordination (`shared`, `fdma`, `tdma`, `hybrid`, `lbt`) and inter-reader interference |
| `controller` | `auto` | Per-reader K / p* choice: `fixed`, `dfsa` or a trained RL `policy` from the registry |

With all three defaults the engine is bit-identical to the golden regression (`tests/thesis/test_regression_independent.py`).

### 2. Engine model and the one-sided interference approximation

The engine is discrete-event and sequential: the reader with the earliest clock runs its next whole frame (paging → Msg1 → EI → Msg2 → Msg3), `K = L_s × F_r` slots.

Interference needs concurrency, which a sequential engine does not have. `coordination/coordinator.py` keeps an `ActivityLedger`:

* Every committed frame records when it transmitted modulated R2D, when it radiated CW, and which device uplinks (Msg1/Msg3) used which subband and slot.
* When reader A starts a frame at `t0`, it is checked against all committed frames that overlap it.
* Readers whose clock falls inside A's frame will start during it. Their activity is predicted from their previous frame (paging, then CW).

**Approximation.** The earlier of two overlapping frames never sees the later one. Interference is therefore one-sided: the reader that happens to run first is not hurt by its neighbour's future frame. Making it symmetric would need either a slot-level co-simulation of all readers or roll-back, which is a much larger engine. The bias is the same for every coordination mode, so comparisons between modes are fair. Absolute loss counts in `shared` mode are a lower bound.

Interference tests:

* **R2D (reader → device):** during A's paging and Msg2, the SIR at the device has to exceed `r2d_sir_db` (default 6 dB). The interferers are co-channel readers that are transmitting.
* **D2R (device → reader):** during Msg1/Msg3, the SINR at A's receiver has to exceed `d2r_sinr_db` (default 0.5 dB). The interference sums three terms:
  * other readers' modulated R2D at full power;
  * their CW, reduced by `other_cw_suppression_db` (default 61 dB, TR 38.769 §6.7.5);
  * with `cross_msg1` on, other readers' devices transmitting in the same subband and slot.

  The noise floor is A's own residual self-interference, `P_tx − cancel_depth`.

### 3. Conflict graph: link budget by default

Two readers conflict if one of two things holds:

* **D2R:** either one's CW, after the 61 dB suppression, reaches the other's receiver floor.
* **R2D:** their coverage disks overlap, so they share devices.

Path loss is the InF-DH NLOS model used everywhere else in the engine.

This beats a fixed distance threshold. The coverage radius depends on device type and transmit power, so a single distance would either merge separate halls or miss real conflicts. A distance threshold is still available (`conflict_distance_m`) for experiments.

Finding: with 61 dB suppression the 18-reader TR hall is a single interference domain. Greedy (Welsh–Powell) colouring needs 18 colours, one per reader. So pure FDMA with F = 8 cannot give every reader its own subband, and pure TDMA serialises all 18 readers.

### 4. Coordination modes

| Mode | Grant | Notes |
| --- | --- | --- |
| `independent` | all F subbands, no interference | ideal reference (T_ideal) |
| `shared` | all F subbands, interfering | uncoordinated baseline |
| `fdma` | colour → `F / colours` subbands | `F_r` shrinks, so K shrinks |
| `tdma` | colour → window in a superframe of `colours × tdma_window_s` | serial reference (T_serial) |
| `hybrid` | colours spread over `freq_groups` subband groups, then take turns in time | |
| `lbt` | sense neighbours before a frame, random backoff while one transmits | ETSI dwell rule below |

**LBT dwell rule.** EN 302 208 limits continuous transmission on one channel: after `lbt_max_on_s` (default 4 s) the reader must pause for `lbt_pause_s` (default 0.1 s). The coordinator tracks each reader's burst start and forces the pause. Without it, a reader that won the channel would hold it forever and starve its neighbours.

**Gain retention.** Defined on T99 of the reachable devices:

$$G = \frac{T_\text{serial} - T_\text{policy}}{T_\text{serial} - T_\text{ideal}}$$

G = 1 keeps the whole ideal multi-reader gain; G = 0 is no better than serving conflicting readers one after another. The analysis page warns when the serial reference is less than 5 % slower than the ideal one: G then blows up and means nothing.

### 5. Termination rules and replay

A reader cannot see how many devices are left. All rules use only reader-side observations: frame times and new IDs per frame.

`energy_bound` also uses the worst-case recharge time `T_wc = (E_cap − E_off) / P_h,min + T_on`. The `edge` source takes `P_h,min` at the coverage edge; `actual` takes it from the reader's own devices. `P_h = ξ(P_in)·P_in` as in the aperiodic paper's Eq. (9) and `Sources/`; see [FORMULAS.md § 2](./FORMULAS.md#2-energy--能量). Before 2026-11-12 the engine omitted ξ, so earlier results are not comparable.

**Tail fast-forward.** Once a reader has nothing left (oracle), or keeps paging empty frames under a heuristic rule, the engine advances those empty frames analytically instead of simulating them one by one.

**Replay.** `POST /runs/{id}/termination-replay` scores rules on a finished oracle run's round log without re-simulating. The live engine and the replay share the same pure functions, and a rule never changes the protocol before it fires.

* With a single reader the replay is exact.
* With several readers it is an approximation. A device that its reader would only have found after stopping is counted as missed, although in a live run a neighbouring reader might still have found it. Missed counts are therefore an upper bound.

An oracle run ends at the last identification, which no real reader can know. So the replay extrapolates: a reader whose rule has not fired yet keeps paging empty frames until it does.

### 6. RL controller and training

Step-by-step training loop, what `--scale` changes and the registry policies: [training/README.md › How training works](../Implements/backend/training/README.md#how-training-works).

* **Environment.** `rl/env.py` is `MultiReaderInventoryEnv`; it passes `gymnasium.utils.env_checker.check_env`.
  * One step is one reader frame.
  * The observation is that reader's local features; `global_state` is exposed for centralised critics.
  * The action is (K, p*), bounded by `features.ACTION_SPEC`.
  * Each episode randomises the reader subset, start offsets, resource mode and device mix.
* **Algorithms.** All live in `Implements/backend/training/algos/`.

  | Algorithm | Implementation |
  | --- | --- |
  | PS-PPO | sb3 PPO, MLP, one shared policy for all readers |
  | MAPPO | custom torch: shared actor, centralised critic on `global_state` |
  | IPPO | one actor and one local critic per reader slot |
  | Zero-shot | the aperiodic single-reader RecurrentPPO, one LSTM state per reader |
* **Training scale.** `--scale smoke|small|medium|full`, `preset:factor`, or a float that multiplies `full`.
* **Outputs.** Each run writes `training/outputs/<exp>/<stamp>__a…__b…__s…/` containing:
  * `meta.json`, which records the PID and host, so the API reports a killed run as `interrupted` rather than `running`;
  * `train_metrics.csv`;
  * `checkpoints/final.zip` and `final.json`;
  * `plots/`;
  * `eval_episodes.csv` and `eval_matrix.csv`.
* **Evaluation.** Each cell compares the policy against DFSA on identical deployments (same seed), over readers × devices × resource mode × offsets.
* **Registry.** `python -m training.promote` (or the Training page) copies a run to `rl/policies/<policy_id>.zip` with a SHA-256 json sidecar. A run with `controller.kind = "policy"` refuses a missing file or a hash mismatch with 422 `policy_unavailable`.

### 7. Results so far (small scale; regenerate before quoting)

> **Outdated (2026-11-12).** The tables below were produced before the conversion efficiency ξ was added to the energy model ([FORMULAS.md § 2.1](./FORMULAS.md#21-harvested-power--采能功率)). With ξ, devices recharge up to about 20× slower, and the default time caps (120 s for `small` training and evaluation, 300 s for the sweeps) cut several runs short. The trained policies were trained under the old physics and need retraining. Re-run the sweeps and evaluation with longer caps before quoting any number.

**Resource sweep** (aperiodic, F = 8, 300 devices, 2 seeds, `scripts/thesis/resource/sweep_resource.py`):

| Readers | ideal T99 | serial (TDMA) T99 | FDMA | hybrid | LBT | shared |
| --- | --- | --- | --- | --- | --- | --- |
| 2 (TR pair) | 7.68 s | 21.7 s | 7.59 s, G = 0.94 | 7.59 s, G = 0.94 | 8.57 s, G = 0.87 | 27.6 % identified |
| 18 (TR hall) | 0.69 s | 9.84 s | 141.8 s, G < 0 (worse than serial) | 5.85 s, G = 0.43 | 7.32 s, G = 0.28 | 0 % identified |

* Shared, uncoordinated spectrum collapses even for the TR pair.
* With two readers FDMA (2 colours, 4 subbands each) keeps almost the whole gain, and LBT keeps most of it.
* With 18 readers hybrid FDMA×TDMA keeps the largest share of the gain. FDMA alone with F = 8 and 18 colours leaves most readers without a subband, so the tail is slower than serial; LBT keeps about a quarter of the gain.

**Termination sweep** (aperiodic, 100/300 devices, 2 seeds, quick rule grid; extra time is relative to the oracle stop, so negative means stopping earlier):

| Readers | Rule (Pareto front) | Missed | Extra time |
| --- | --- | --- | --- |
| 1 | quiet_rounds(n=32) | 4.5 % | −3.6 s |
| 1 | id_rate(rounds=50, r_rel=0.01) | 3.0 % | −2.4 s |
| 1 | id_rate(seconds=10, r_rel=0.01) | 1.5 % | +3.7 s |
| 1 | energy_bound(actual, margin=0) | 0 % | +62.8 s |
| 2 | quiet_rounds(n=32) | 3.8 % | −1.6 s |
| 2 | id_rate(rounds=50, r_rel=0.01) | 3.0 % | −0.4 s |
| 2 | id_rate(seconds=10, r_rel=0.01) | 0 % | +6.0 s |

`energy_bound` guarantees no missed device but costs about one t_wc (+54–63 s) of extra paging. `id_rate(seconds=10, r_rel=0.01)` gets close (0–1.5 % missed) for only +4–6 s. Short quiet windows (`quiet_rounds(n ≤ 8)`, `id_rate(rounds=10)`) miss 11–24 %; the missed devices are mostly slow-recharging 2a devices that wake up after the reader has gone quiet.

**Trained policies** (small scale, about 53 k steps, α = β = 0.5, standard evaluation grid with 18 cells):

| Policy | Cells reaching 99 % | Mean identified | Geo-mean T99 / DFSA |
| --- | --- | --- | --- |
| DFSA | 16/18 | 99.2 % | 1.00 |
| PS-PPO randomised | 16/18 | 96.3 % | 0.98 |
| MAPPO | 16/18 | 96.9 % | 0.99 |
| Zero-shot aperiodic RecurrentPPO | 16/18 | 96.2 % | 1.04 |

At small scale the trained policies are on par with DFSA: per-cell T99 ratios range from 0.61 to 1.9, but the geometric mean is about 1, and every policy identifies slightly fewer devices within the evaluation budget. Any RL gain has to come from larger-scale training.

**Estimator fallback (p\*).** `p_star` (`inventory/estimator.py`) has two special cases, as in `Sources/.../grouping_logic.py`:

* No estimate yet (cold start): p\* = `p0_init` (0.1).
* N̂ = 0 after an all-idle frame: p\* = 1. This matches the aperiodic paper's fallback ("ps = 1 to avoid stalling").

An earlier version used 0.1 for both cases. Late-waking devices were then paged at 0.1, which made DFSA and fixed-K about 5× slower in their tails, and it made the RL policies look 2.5× better than DFSA (0.37–0.40). The tables above are from after the fix. The RL policies set p\* themselves and only read the estimator on the first frame, so they did not need retraining.

### 8. How to reproduce

```bash
cd Implements/backend
PYTHONPATH=. .venv/bin/python scripts/thesis/resource/sweep_resource.py --schemes aperiodic --readers 2 18 --f 8 --n 300 --seeds 2
PYTHONPATH=. .venv/bin/python scripts/thesis/termination/sweep_termination.py --schemes aperiodic --readers 1 2 --n 100 300 --seeds 2 --quick
PYTHONPATH=. .venv/bin/python -m training.train --config mappo --scale small --promote
.venv/bin/python -m pytest tests/thesis -q
```

---

## 中文

### 1. 范围

论文仿真引擎分三个阶段扩展。每个阶段对应 `POST /sections/{id}/runs` 中的一个配置块，默认值保持旧行为：

| 配置块 | 默认 | 新增内容 |
| --- | --- | --- |
| `termination` | `oracle` | 读写器侧终止规则：`quiet_rounds`、`id_rate`、`energy_bound`、`combined` |
| `resource` | `independent` | 协调方式（`shared`、`fdma`、`tdma`、`hybrid`、`lbt`）与读写器间干扰 |
| `controller` | `auto` | 每个读写器的 K / p* 选择：`fixed`、`dfsa` 或注册表中训练好的 RL 策略 |

三个配置块都取默认值时，结果与回归基准逐位一致。

### 2. 引擎模型与单向干扰近似

引擎是离散事件、顺序执行的：时钟最早的读写器执行下一整帧，`K = L_s × F_r`。

干扰需要并发，顺序引擎本身没有并发，所以 `coordinator.py` 维护一个活动账本（ActivityLedger）：

* 每个已提交的帧都会记录 R2D 调制发射时段、CW 时段，以及设备上行（Msg1/Msg3）所用的子带与时隙。
* 读写器 A 在 `t0` 开始一帧时，会与所有和它重叠的已提交帧做检查。
* 时钟落在 A 帧内的读写器会在这段时间里启动，它们的活动按其上一帧来预测。

**近似：** 两个重叠帧中，较早的一帧看不到较晚的一帧，因此干扰是单向的。要做成对称，需要所有读写器在时隙级别联合仿真或支持回滚，工作量大得多。这个偏差对所有协调方式都一样，所以模式之间的比较是公平的；`shared` 模式下的绝对损失数是下界。

干扰判定：

* **R2D（读写器 → 设备）：** 寻呼和 Msg2 期间，设备处的 SIR 须高于 `r2d_sir_db`（默认 6 dB）。
* **D2R（设备 → 读写器）：** Msg1/Msg3 期间，A 接收机处的 SINR 须高于 `d2r_sinr_db`（默认 0.5 dB）。干扰由三部分相加：
  * 其他读写器的满功率 R2D；
  * 其他读写器的 CW，扣除 `other_cw_suppression_db`（默认 61 dB，TR 38.769 §6.7.5）；
  * 开启 `cross_msg1` 时，其他读写器的设备在同子带、同时隙的上行。

  底噪为 A 自身的残余自干扰 `P_tx − cancel_depth`。

### 3. 冲突图：默认基于链路预算

满足以下任一条件，两读写器即冲突：

* **D2R：** 任一方的 CW 经 61 dB 抑制后仍达到对方接收底噪；
* **R2D：** 两者覆盖圆重叠，即共享设备。

路径损耗使用 InF-DH NLOS 模型。覆盖半径随设备类型和发射功率变化，单一距离门限要么把不相干的读写器合并，要么漏掉真实冲突，所以默认使用链路预算；距离门限（`conflict_distance_m`）仍保留供实验使用。

发现：61 dB 抑制下，18 读写器的 TR 厂房是一个整体干扰域，贪心着色需要 18 种颜色。因此 F = 8 的纯 FDMA 无法让每个读写器独占子带，纯 TDMA 则把 18 个读写器完全串行化。

### 4. 协调方式

`independent` 是理想参考（T_ideal），`tdma` 是串行参考（T_serial）。各模式的资源分配方式见上方英文表格。

**LBT 驻留规则：** 依据 EN 302 208，连续发射 `lbt_max_on_s`（默认 4 s）后须暂停 `lbt_pause_s`（默认 0.1 s）。没有这条规则，抢到信道的读写器会一直占用，邻居被饿死。

**增益保持率**基于可达设备的 T99：G = (T_serial − T_policy) / (T_serial − T_ideal)。当串行参考比理想参考慢不到 5% 时，G 没有意义，分析页会给出警告。

### 5. 终止规则与回放

读写器看不到剩余设备数，所有规则只使用帧时间和每帧新识别数。

`energy_bound` 还使用最坏充电时间 `T_wc = (E_cap − E_off) / P_h,min + T_on`：`edge` 取覆盖边缘的采能，`actual` 取该读写器自身设备的采能。采能功率为 `P_h = ξ(P_in)·P_in`，与非周期论文式 (9) 和 `Sources/` 一致，见 [FORMULAS.md 第 2 节](./FORMULAS.md#2-energy--能量)。2026-11-12 之前引擎漏乘了 ξ，此前的结果不可比。

**尾部快进：** 读写器没有剩余设备（oracle 模式），或在启发式规则下持续寻呼空帧时，引擎会解析地推进这些空帧，不逐帧仿真。

**回放：** `termination-replay` 在已完成的 oracle 运行的轮次日志上直接评估规则，不需要重新仿真。回放与实时引擎共用同一组纯函数，且规则在触发前不改变协议。

* 单读写器时回放是精确的。
* 多读写器时是近似：读写器停止之后才会识别的设备一律计为漏识，但真实运行中相邻读写器仍可能识别到它，所以漏识数是上界。

oracle 运行在最后一次识别时结束，真实读写器无法知道这一时刻，所以回放会外推：规则尚未触发的读写器继续寻呼空帧，直到规则触发为止。

### 6. 强化学习控制器与训练

逐步的训练流程、`--scale` 改变什么、注册表里的策略：见 [training/README.md › 训练过程](../Implements/backend/training/README.md#训练过程中文)。

* **环境与算法：** 环境为 `MultiReaderInventoryEnv`，一步就是一帧。算法包括 PS-PPO（sb3）、MAPPO（集中式评论家）、IPPO（每个槽位独立的 actor/critic）和零样本（非周期单读写器 RecurrentPPO）。
* **规模与输出：** 用 `--scale` 控制训练规模，输出写到 `training/outputs/`。`meta.json` 记录 PID 和主机名；进程被杀后，API 显示 `interrupted`。
* **评估：** 策略与 DFSA 在相同部署上成对比较。
* **注册表：** 发布后进入 `rl/policies`（带 SHA-256 校验）。运行时若文件缺失或哈希不符，返回 422。

### 7. 当前结果

> **已过时（2026-11-12）。** 下面的结果是在能量模型加入转换效率 ξ 之前得到的（见 [FORMULAS.md 2.1 节](./FORMULAS.md#21-harvested-power--采能功率)）。加入 ξ 后，设备充电最多慢约 20 倍，默认的时间上限（`small` 训练和评估 120 s、扫描 300 s）会让部分运行提前截断。已训练的策略是在旧物理模型下训练的，需要重新训练。引用任何数字之前，请用更长的时间上限重跑扫描和评估。

数值见上方英文表格（小规模实验，引用前请重新生成）。要点：

* 未协调的共享频谱即使只有 TR 两读写器也会崩溃。
* 2 个读写器时，FDMA 几乎保留全部增益（G ≈ 0.94），LBT 保留大部分（G ≈ 0.87）。
* 18 个读写器时，混合 FDMA×TDMA 保留的增益最多（G ≈ 0.43）。单纯 FDMA 在 F = 8、18 种颜色下子带不够，尾部比串行还慢；LBT 约保留四分之一（G ≈ 0.28）。
* `energy_bound` 保证零漏识，但要多寻呼约一个 t_wc（+54–63 s）。`id_rate(seconds=10, r_rel=0.01)` 只多花 4–6 s，漏识 0–1.5%。静默窗口短的规则漏识 11–24%，主要是充电慢的 2a 设备。
* 小规模训练的三种策略与 DFSA 基本持平：T99 几何平均约为 DFSA 的 0.98–1.04 倍，识别比例略低。RL 若要有优势，需要更大规模的训练。

**估计器回退（p\*）。** 与 `Sources/.../grouping_logic.py` 一致，`p_star` 有两种特殊情况：

* 还没有估计（冷启动）：p\* = `p0_init`（0.1）。
* 一帧全空、N̂ = 0：p\* = 1。这与非周期论文的回退一致（“ps = 1 to avoid stalling”）。

旧版本把两种情况都设成 0.1，晚醒的设备只能以 0.1 的概率接入。结果是 DFSA 和固定 K 的尾部慢了约 5 倍，RL 也显得比 DFSA 快 2.5 倍（0.37–0.40）。上面的数字都是修正后的结果。RL 策略自己决定 p\*，只在第一帧读取估计器，所以不需要重新训练。

### 8. 复现

命令见英文第 8 节。
