# Formulas · 公式表

The formulas the thesis engine (`Implements/backend/app/thesis_simulator`) actually computes. Each formula is written in LaTeX (rendered by the Markdown preview: Ctrl+Shift+V) and followed by a table of its variables and the code location. Terms: [VOCABULARY.md](./VOCABULARY.md). Design and results: [THESIS_MULTI_READER_DESIGN.md](./THESIS_MULTI_READER_DESIGN.md).

论文仿真引擎（`Implements/backend/app/thesis_simulator`）实际计算的公式。公式用 LaTeX 书写（用 Markdown 预览查看：Ctrl+Shift+V），每个公式下面是变量表和代码位置。术语见 [VOCABULARY.md](./VOCABULARY.md)，设计与结果见 [THESIS_MULTI_READER_DESIGN.md](./THESIS_MULTI_READER_DESIGN.md)。

Code paths are relative to `Implements/backend/app/thesis_simulator/`. 代码路径均相对于该目录。

**Contents · 目录**

1. [Radio link · 无线链路](#1-radio-link--无线链路)
2. [Energy · 能量](#2-energy--能量)
3. [Frame and random access · 帧与随机接入](#3-frame-and-random-access--帧与随机接入)
4. [Estimator and controllers · 估计器与控制器](#4-estimator-and-controllers--估计器与控制器)
5. [Coordination and interference · 协调与干扰](#5-coordination-and-interference--协调与干扰)
6. [Termination · 终止规则](#6-termination--终止规则)
7. [RL controller · 强化学习控制器](#7-rl-controller--强化学习控制器)
8. [Metrics · 评价指标](#8-metrics--评价指标)

---

## 1. Radio link · 无线链路

### 1.1 Path loss · 路径损耗

$$
\begin{aligned}
PL_{\mathrm{LOS}} &= 31.84 + 21.5\log_{10} d + 19\log_{10} f_c \\
PL_{\mathrm{NLOS}} &= \max\!\left(PL_{\mathrm{LOS}},\; 33.63 + 21.9\log_{10} d + 20\log_{10} f_c\right) \\
d &= \sqrt{d_{xy}^2 + (h_{\mathrm{BS}} - h_{\mathrm{dev}})^2}
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| PL_LOS | Line-of-sight path loss (TR 38.901 InF) | 视距路径损耗 | dB |
| PL_NLOS | Non-line-of-sight path loss, used everywhere in the engine | 非视距路径损耗，全引擎统一使用 | dB |
| d | 3D distance reader ↔ device | 读写器与设备的三维距离 | m |
| d_xy | Horizontal distance | 水平距离 | m |
| f_c | Carrier frequency | 载波频率 | 0.9 GHz |
| h_BS | Reader (base station) height | 读写器（基站）高度 | 8 m |
| h_dev | Device height | 设备高度 | 1.5 m |

Code: `physics.pl_los`, `physics.pl_nlos`

### 1.2 Incident power at the device · 设备入射功率

$$
P_{\mathrm{in}} = P_{\mathrm{tx}} + G_{\mathrm{tx}} - PL_{\mathrm{NLOS}} - L_{\mathrm{dev}} - L_{\mathrm{obj}} - L_{\mathrm{extra}} \quad [\mathrm{dBm}]
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| P_in | CW power arriving at the device | 到达设备的载波功率 | dBm |
| P_tx | Reader transmit power | 读写器发射功率 | 33 dBm |
| G_tx | Reader antenna gain | 读写器天线增益 | 6 dBi |
| L_dev | Fixed device-side loss | 设备侧固定损耗 | 7 dB |
| L_obj | Object (body) loss | 物体遮挡损耗 | 0.9 dB |
| L_extra | Extra attenuation set per reader | 每个读写器额外设定的衰减 | 0 dB |

Code: `physics.incident_pin_dbm`, `inventory/energy.compute_reader_contribution`

### 1.3 Reader sensitivity · 读写器灵敏度

$$
P_{\mathrm{req}} = P_{\mathrm{tx}} - CD + SNR_{\mathrm{req}} \quad [\mathrm{dBm}]
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| P_req | Weakest uplink signal the reader can decode | 读写器能解码的最弱上行信号 | dBm |
| CD | Self-interference cancellation depth (own CW leak) | 自干扰消除深度（自身载波泄漏） | 140 dB |
| SNR_req | Required SNR | 所需信噪比 | 0.5 dB |

Code: `physics.reader_required_level_dbm`

### 1.4 Coverage radius · 覆盖半径

$$
\begin{aligned}
MPL_{\mathrm{R2D}} &= P_{\mathrm{tx}} + G_{\mathrm{tx}} - L_{\mathrm{obj}} - L_{\mathrm{dev}} - L_{\mathrm{extra}} - S_{\mathrm{rx}} \\
MPL_{\mathrm{D2R}}^{\mathrm{bs}} &= \tfrac{1}{2}\left(P_{\mathrm{tx}} + G_{\mathrm{bs}} - L_{\mathrm{dev}} - L_{\mathrm{extra}} - P_{\mathrm{req}}\right) && \text{backscatter: Device 1, 2a} \\
MPL_{\mathrm{D2R}}^{\mathrm{act}} &= P_{\mathrm{act}} - L_{\mathrm{dev}} - L_{\mathrm{extra}} - P_{\mathrm{req}} && \text{active: Device 2b} \\
PL_{\mathrm{NLOS}}(R_{\mathrm{R2D}}) &= MPL_{\mathrm{R2D}}, \qquad PL_{\mathrm{NLOS}}(R_{\mathrm{D2R}}) = MPL_{\mathrm{D2R}} \\
R &= \min\left(R_{\mathrm{R2D}},\; R_{\mathrm{D2R}}\right)
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| MPL | Maximum path loss a link can tolerate | 链路能承受的最大路径损耗 | dB |
| S_rx | Device receiver sensitivity | 设备接收灵敏度 | Device 1 / 2a / 2b: −36 / −40 / −70 dBm |
| G_bs | Backscatter gain minus loss | 反向散射增益减损耗 | 2a: +10 − 6 dB; Device 1: −6 dB |
| P_act | Active transmit power of Device 2b | Device 2b 主动发射功率 | dBm |
| ½ | Backscatter travels the path twice | 反向散射信号往返两次路径 | — |
| R | Coverage radius: the shorter of downlink and uplink | 覆盖半径：取下行和上行中较短的一个 | m |

Code: `physics.range_from_sensitivity_m`, `physics.d2r_backscatter_range_m`, `physics.d2r_active_range_m`, `physics.effective_coverage_m`

---

## 2. Energy · 能量

### 2.1 Harvested power · 采能功率

$$
\begin{aligned}
P_{\mathrm{in}}^{\mathrm{tot}} &= \sum_r P_{\mathrm{in},r} \quad [\mathrm{W}] \\
P_h &= \xi\!\left(P_{\mathrm{in}}^{\mathrm{tot}}\right) \cdot P_{\mathrm{in}}^{\mathrm{tot}} \\
\xi(p) &= \begin{cases} (p + 41)/100, & p \le -10\ \mathrm{dBm} \\ (-2p + 11)/100, & p > -10\ \mathrm{dBm} \end{cases} \qquad \xi \in [0, 1]
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| P_in,r | Incident CW power from reader r | 读写器 r 的入射载波功率 | W |
| P_in_tot | Total incident CW power from all readers | 所有读写器的总入射载波功率 | W |
| P_h | Power the device harvests while OFF | 设备关机时采集的功率 | W |
| ξ | RF-to-DC conversion efficiency (aperiodic paper Eq. 9) | 射频-直流转换效率（非周期论文式 9） | ξ(−36 dBm) = 0.05 |
| p | P_in_tot expressed in dBm | 以 dBm 表示的总入射功率 | dBm |

ξ is applied to the total, as in `Sources/` multi-source mode. ξ 作用在总功率上，与 `Sources/` 多源模式一致。

Code: `inventory/energy.harvested_power_w`, `app/common/rf.py`

### 2.2 ON / OFF cycle · 开机 / 关机循环

$$
\begin{aligned}
\text{ON:}\quad & \frac{dE}{dt} = -P_{\mathrm{on}} && \text{for up to } T_{\mathrm{on}} \text{ or until } E = E_{\mathrm{off}} \;\to\; \text{OFF} \\
\text{OFF:}\quad & \frac{dE}{dt} = +P_h && \text{until } E = E_{\mathrm{cap}} \;\to\; \text{ON for } T_{\mathrm{on}} \\
\text{join:}\quad & E \ge E_{\mathrm{off}} + E_{\mathrm{rx}}(\text{frame})
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| E | Energy stored in the device | 设备储存的能量 | J |
| P_on | Power drawn while listening | 监听时的功耗 | 1 µW |
| T_on | Listening window after waking up | 醒来后的监听时长 | 100 ms (DCM: 12 ms) |
| E_cap | Turn-on threshold (capacitor full) | 开机门限（电容充满） | Device 1: 5 µJ; 2a / 2b: 25 µJ |
| E_off | Turn-off threshold | 关机门限 | Device 1: 2.5 µJ; 2a / 2b: 12.5 µJ |
| E_rx(frame) | Energy needed to receive this frame | 接收这一帧所需的能量 | J |

Code: `inventory/energy.advance_availability`, `inventory/frame.py`, `inventory/episode._per_subtype_energy`

### 2.3 Worst-case recharge time · 最坏充电时间 T_wc

$$
\begin{aligned}
T_{\mathrm{wc}} &= \max_{i\ \in\ \text{covered}} \left[\frac{E_{\mathrm{cap},i} - E_{\mathrm{off},i}}{P_{h,i}} + T_{\mathrm{on},i}\right] \\
\text{edge:}\quad P_{h,i} &= \xi(P_{\mathrm{in}})\,P_{\mathrm{in}}, \quad P_{\mathrm{in}} \text{ at the coverage edge } R_i \text{ (this reader only)} \\
\text{actual:}\quad P_{h,i} &= \text{the device's real harvested power (oracle)} \\
T_{\mathrm{on},i} &= \max\left(T_{\mathrm{on}}^{\mathrm{default}},\, T_{\mathrm{on}}^{\mathrm{DCM}}\right) = 100\ \mathrm{ms}
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| T_wc | Longest time any covered device needs to recharge and listen again | 覆盖范围内设备重新充满并监听所需的最长时间 | s |
| E_cap,i − E_off,i | Energy to recover from OFF | 从关机恢复需要补充的能量 | J |
| P_h,i | Harvested power assumed for device i | 设备 i 的采能功率 | W |
| R_i | Coverage radius of device i's type | 设备 i 所属类型的覆盖半径 | m |

Values for one default reader (33 dBm, 6 dBi) · 默认单读写器的取值:

| Device · 设备 | Coverage radius · 覆盖半径 | P_in at edge · 边缘入射功率 | ξ | T_wc |
| --- | --- | --- | --- | --- |
| Device 1 | 23.9 m | −32.1 dBm | 0.089 | 46 s |
| Device 2a | 41.4 m | −37.1 dBm | 0.039 | 1 685 s |
| Device 2b | 136.7 m | −48.4 dBm | 0 | ∞ |

ξ = 0 below −41 dBm, i.e. beyond 62.5 m from one reader. Device 2b transmits actively, so its coverage (136.7 m) reaches far past that: a 2b device at its edge harvests nothing from this reader alone, and the `edge` bound is infinite whenever a reader covers a 2b device. ξ 在 −41 dBm 以下为 0，即距单个读写器 62.5 m 以外。Device 2b 主动发射，覆盖半径 136.7 m 远超这个距离：边缘的 2b 设备仅靠本读写器采不到能量，所以只要覆盖内有 2b，`edge` 上界就是无穷大。

> **Known inconsistency (open).** These values use the device catalog (`catalog.py`), as scenes built in the UI do. Scenes without device parameters (`synthetic_scene`, used by training, sweeps and tests) fall back to a backscatter 2b in `episode._build_world`, with 23.9 m coverage and T_wc ≈ 232 s.
>
> **已知不一致（未修正）。** 上表按设备目录（`catalog.py`）计算，与 UI 中建的场景一致。没有设备参数的场景（`synthetic_scene`，用于训练、扫描和测试）在 `episode._build_world` 中把 2b 默认当作反向散射，覆盖 23.9 m，T_wc 约 232 s。

Code: `inventory/termination.worst_case_recharge_s`, `inventory/episode._assign_recharge_bounds`

> **History.** Before 2026-11-12 the thesis engine used P_h = P_in without ξ, unlike the paper and `Sources/`, so devices recharged about 1/ξ times too fast (about 20× at −36 dBm). Results produced before that date are not comparable.
>
> **历史说明。** 2026-11-12 之前，论文引擎直接用 P_h = P_in，没有乘 ξ，与论文和 `Sources/` 不一致，设备充电快了约 1/ξ 倍（−36 dBm 时约 20 倍）。该日期之前的结果不可比。

---

## 3. Frame and random access · 帧与随机接入

### 3.1 Msg1 resources · Msg1 资源数

$$
K = L_s \times F_r, \qquad K' = \left\lceil \frac{K}{F} \right\rceil \times F_r
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| K | Msg1 resources in the frame | 本帧的 Msg1 资源数 | — |
| L_s | Msg1 length in time slots | Msg1 的时隙长度 | — |
| F | Subbands of the carrier | 载波的子带总数 | 8 |
| F_r | Subbands granted to this reader | 分配给该读写器的子带数 | F in `independent` |

Code: `inventory/controller._scale_to_grant`

### 3.2 Device access · 设备接入

$$
\begin{aligned}
&\text{device } i \text{ joins if } u_i < p^*, \quad u_i \sim \mathcal{U}(0, 1) \\
&\text{slot of device } i \sim \mathcal{U}\{1, \dots, K\} \\
&S,\ C,\ E = \#\text{slots with exactly } 1,\ \ge 2,\ 0 \text{ devices}
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| p* | Access probability broadcast in the page | 寻呼中广播的接入概率 | 0–1 |
| u_i | The device's own random draw | 设备自己的随机数 | — |
| S | Success slots | 成功时隙数 | — |
| C | Collision slots | 碰撞时隙数 | — |
| E | Empty slots | 空闲时隙数 | — |

Code: `inventory/frame.py`, `inventory/aloha.py`

### 3.3 Frame duration · 帧时长

$$
T_{\mathrm{frame}} = T_{\mathrm{pg}} + \left\lceil \frac{K}{F_r} \right\rceil T_{\mathrm{M1}} + T_{\mathrm{EBI}}(K) + S_{\mathrm{M2}}\,T_{\mathrm{M2}} + \left\lceil \frac{S_{\mathrm{M2}}}{F_r} \right\rceil T_{\mathrm{M3}}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| T_pg | Paging message duration | 寻呼消息时长 | s |
| T_M1, T_M2, T_M3 | Msg1 / Msg2 / Msg3 durations | Msg1 / Msg2 / Msg3 时长 | s |
| T_EBI(K) | Early (busy) indication after Msg1 | Msg1 之后的早期指示 | s |
| S_M2 | Msg2 transmissions (aperiodic: S) | Msg2 次数（非周期：等于 S） | — |

Code: `inventory/frame.py`

---

## 4. Estimator and controllers · 估计器与控制器

### 4.1 Backlog estimate · 剩余设备估计

$$
\begin{aligned}
\hat N &= \begin{cases} -\dfrac{K}{p}\,\ln\dfrac{E}{K}, & E > 0 \quad \text{(empty-slot inversion)} \\[2mm] \dfrac{S + 2.39\,C}{p}, & E = 0,\ C > 0 \quad \text{(Schoute)} \\[2mm] \dfrac{S}{p}, & \text{otherwise} \end{cases} \\[2mm]
\tilde N &= \max\!\left(0,\ \operatorname{round}(\hat N - S)\right)
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| N̂ | Estimated devices that competed in this frame | 估计本帧参与竞争的设备数 | — |
| Ñ | Estimated devices left for the next frame of this group | 该组下一帧剩余的设备数 | — |
| p | p* used in this frame | 本帧使用的 p* | — |
| 2.39 | Schoute's collision constant | Schoute 碰撞常数 | — |

Code: `inventory/estimator.update`

### 4.2 Access probability · 接入概率

$$
p^* = \begin{cases} p_0 = 0.1, & \text{no estimate yet (cold start)} \\ 1, & \tilde N = 0 \ \text{(all-idle frame)} \\ \min\!\left(1,\ K / \tilde N\right), & \text{otherwise} \end{cases}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| p_0 | Cold-start probability | 冷启动概率 | 0.1 |

Code: `inventory/estimator.p_star`

### 4.3 DFSA frame size · DFSA 帧大小

$$
K = \operatorname{clip}\!\left(2\tilde N,\ 16,\ K_{\max}\right), \qquad K_0 = \max(8,\ k_{\mathrm{initial}})
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| K_max | Largest frame | 最大帧大小 | 668 |
| K_0 | First-frame size | 第一帧大小 | from `k_initial` |

Code: `inventory/controller.DfsaController`

---

## 5. Coordination and interference · 协调与干扰

### 5.1 Conflict graph · 冲突图

$$
\begin{aligned}
P_{ab} &= P_{\mathrm{tx}} + G_{\mathrm{tx}} - PL_{\mathrm{NLOS}}(d_{ab}) && \text{CW of reader } b \text{ at reader } a \ [\mathrm{dBm}] \\
a \leftrightarrow b \text{ conflict} &\iff P_{ab} - S_{\mathrm{cw}} \ge P_{\mathrm{tx}} - CD \ \ \lor\ \ d_{ab} < R_a + R_b
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| d_ab | Distance between readers a and b | 读写器 a、b 之间的距离 | m |
| S_cw | Suppression of another reader's CW (TR 38.769 §6.7.5) | 对其他读写器载波的抑制 | 61 dB |
| P_tx − CD | Reader's self-interference floor | 读写器自干扰底噪 | dBm |
| R_a, R_b | Coverage radii | 覆盖半径 | m |

Code: `coordination/coordinator._link_budget_conflicts`

### 5.2 Resource modes · 资源分配方式

$$
\begin{aligned}
\text{FDMA:}\quad & g = \min(\text{colours}, F), \quad \text{colour } c \text{ gets } \{ s : s \bmod g = c \bmod g \}, \quad F_r \approx F / g \\
\text{TDMA:}\quad & \text{superframe} = \text{colours} \times T_{\mathrm{win}}, \quad \text{colour } c \text{ starts frames only in window } c \\
\text{Hybrid:}\quad & g = \text{freq\_groups}, \quad \text{colours sharing a group take turns in time} \\
\text{LBT:}\quad & \text{sense before each frame, back off if busy}; \quad \text{on} \le 4\ \mathrm{s},\ \text{then pause} \ge 0.1\ \mathrm{s}
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| colours | Colours of the conflict graph (Welsh–Powell) | 冲突图着色数 | — |
| g | Frequency groups | 频率组数 | FDMA: min(colours, F); hybrid: 2 |
| T_win | TDMA window per colour | 每种颜色的 TDMA 时间窗 | 0.5 s |

Code: `coordination/coordinator._assign`, `coordination/coordinator.time_slot`, `coordination/spec.py`

### 5.3 Decoding tests · 解码判断

$$
\begin{aligned}
\text{D2R (Msg1, Msg3):}\quad & SINR = P_{\mathrm{sig}} - 10\log_{10}\!\left(P_{\mathrm{floor}} + I\right) \ge 0.5\ \mathrm{dB} \\
\text{R2D (paging, Msg2):}\quad & SIR \ge 6\ \mathrm{dB}
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| P_sig | Wanted signal at the receiver | 接收端的有用信号 | dBm |
| P_floor | Reader self-interference floor (P_tx − CD) | 读写器自干扰底噪 | W |
| I | Interference from other readers and their devices | 来自其他读写器及其设备的干扰 | W |

Code: `coordination/coordinator.sinr_db`, `coordination/spec.py`

---

## 6. Termination · 终止规则

### 6.1 Quiet rounds · 静默轮数

$$
\text{stop if } n_{\mathrm{quiet}} \ge n
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| n_quiet | Consecutive frames without a new ID | 连续没有新 ID 的帧数 | — |
| n | Threshold | 阈值 | default 10 |

### 6.2 Identification rate · 识别速率

$$
\begin{aligned}
r &= \frac{\text{new IDs in the window}}{t_{\mathrm{end}} - t_{\mathrm{start}}}, \qquad
EWMA_t = \alpha \frac{\text{new IDs}}{T_{\mathrm{frame}}} + (1 - \alpha)\, EWMA_{t-1} \\
r_{\mathrm{peak}} &= \max_{\text{so far}} r \\
\text{stop if } & \ r < r_{\min} \ \lor\ r < r_{\mathrm{rel}} \cdot r_{\mathrm{peak}} \quad (\text{after } min\_frames \text{ frames since the first ID}) \\
\text{no ID yet: } & \ \text{stop after } 4 \max(1, min\_frames) \text{ frames}
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| window | Last N frames, last N seconds, or EWMA | 最近 N 帧、最近 N 秒，或指数平均 | default 20 frames |
| α | EWMA weight | 指数平均权重 | 0.1 |
| r_min | Absolute threshold | 绝对阈值 | IDs/s, off by default |
| r_rel | Relative threshold (fraction of the peak) | 相对阈值（峰值的比例） | 0.01 |
| min_frames | Frames after the first ID before the rule may fire | 第一次识别后至少要跑的帧数 | 5 |

### 6.3 Energy bound · 能量上界

$$
\begin{aligned}
&\text{stop if } \ t - t_{\mathrm{last\,ID}} \ge \min\!\left(T_{\mathrm{wc}} \cdot (1 + margin),\ T_{\mathrm{max\,wait}}\right) \\
&\text{edge: } R_i \leftarrow \min(R_i,\ R_{\mathrm{cap}}) \text{ in } T_{\mathrm{wc}} \ (\S\ 2.3)
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| t_last_ID | Time of the last new ID | 最后一次识别到新设备的时间 | s |
| T_wc | Worst-case recharge time (§ 2.3) | 最坏充电时间（见 2.3 节） | s |
| margin | Safety factor | 安全余量 | default 0 |
| R_cap | `edge_cap_m`: farthest distance assumed for the worst case | 计算最坏情况时假设的最远距离 | UI default 41.4 m (Device 2a coverage); off = each type's radius |
| T_max wait | `max_wait_s`: upper bound on the wait | 等待时间上限 | off by default |

Without `edge_cap_m`, a reader covering an active Device 2b gets T_wc = ∞ (§ 2.3) and the rule never fires. 不设 `edge_cap_m` 时，覆盖内有主动式 Device 2b 的读写器 T_wc = ∞（见 2.3 节），规则永远不会触发。

`combined` = `all` or `any` of sub-rules. Code: `inventory/termination.py`

---

## 7. RL controller · 强化学习控制器

### 7.1 Action mapping · 动作映射

$$
\begin{aligned}
m &= \exp\!\left(\ln 0.25 + \frac{a_0 + 1}{2}\left(\ln 10 - \ln 0.25\right)\right), && m \in [0.25, 10] \\
q &= \exp\!\left(\ln 0.1 + \frac{a_1 + 1}{2}\left(\ln 10 - \ln 0.1\right)\right), && q \in [0.1, 10] \\
L &= \operatorname{clip}\!\left(\lceil m\, L_{\mathrm{prev}} \rceil,\ 1,\ \lceil K_{\max} / F_r \rceil\right), \qquad K = L \times F_r \\
p &= \operatorname{clip}\!\left(q\, p_{\mathrm{prev}},\ p_{\mathrm{floor}},\ 1\right)
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| a_0, a_1 | Network outputs | 网络输出 | [−1, 1] |
| m, q | Multipliers of L and p (log-uniform) | L 和 p 的倍数（对数均匀） | — |
| L_prev, p_prev | Previous frame's L and p | 上一帧的 L 和 p | — |
| p_floor | Lowest allowed p | p 的下限 | — |

Code: `rl/features.apply_action`, `aperiodic_simulator/rl/transforms.py`

### 7.2 Reward · 奖励

$$
\begin{aligned}
local &= \frac{(1 - \alpha)\, new_r - \alpha\, C_r}{T_{\mathrm{frame}}} \\
team &= \frac{\text{new IDs of all readers since } r\text{'s previous decision}}{\text{elapsed time}} \\
reward &= \frac{\beta \cdot local + (1 - \beta) \cdot team}{100}
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| new_r | New IDs in reader r's frame | 读写器 r 本帧的新识别数 | — |
| C_r | Collision slots in that frame | 本帧的碰撞时隙数 | — |
| α | Collision weight (paper Eq. 8) | 碰撞权重（论文式 8） | 0.5 |
| β | Own frame vs. whole team | 自己与全体的权重 | 0.5 |
| 100 | Scale that keeps rewards around 1 | 缩放常数，使奖励约为 1 | — |

Code: `rl/env.py`

---

## 8. Metrics · 评价指标

### 8.1 Completion · 完成度

$$
\begin{aligned}
N_{\mathrm{reach}} &= N - N_{\mathrm{unreachable}}, \qquad \text{identified fraction} = N_{\mathrm{id}} / N_{\mathrm{reach}} \\
T_{99} &= \text{time of the } \lceil 0.99\, N_{\mathrm{reach}} \rceil\text{-th identification}, \qquad T_{\mathrm{mean}} = \text{mean identification time} \\
RE &= \frac{\sum S}{\sum K}
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| N | All devices | 设备总数 | — |
| N_unreachable | Devices outside every reader's coverage | 不在任何读写器覆盖内的设备 | — |
| N_id | Identified devices | 已识别设备数 | — |
| RE | Resource efficiency: successful Msg1 resources per resource | 资源效率：成功 Msg1 资源占全部资源的比例 | 0–1 |

Code: `rl/env.outcome`, `analysis.py`

### 8.2 Comparisons · 对比指标

$$
\rho = \frac{T_{99}(\text{policy})}{T_{99}(\text{DFSA})}, \qquad
\bar\rho = \exp\!\left(\operatorname{mean} \ln \rho\right), \qquad
G = \frac{T_{\mathrm{serial}} - T_{\mathrm{policy}}}{T_{\mathrm{serial}} - T_{\mathrm{ideal}}}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| ρ | Policy time relative to DFSA (< 1 = faster) | 策略相对 DFSA 的时间（< 1 表示更快） | — |
| T_serial | One reader on the air at a time | 每次只有一个读写器发射 | s |
| T_ideal | Independent resources, no interference | 资源独立、无干扰 | s |
| G | 1 = ideal, 0 = serial, < 0 = worse than serial | 1 = 理想，0 = 串行，< 0 = 比串行还差 | — |

Code: `training/evaluate.py`, `scripts/thesis/resource/sweep_resource.py`

### 8.3 Per-device metrics · 逐设备指标

$$
\begin{aligned}
\text{readers in range} &= \sum_r \mathbb{1}\!\left[d_{i,r} \le R_{i,r}\right] \\
\text{CBRA failures} &= \text{joined attempts (paged + Msg1) that did not end identified} \\
\text{reader changes} &= \text{joins at a different reader after going OFF} \\
\text{failure} \to \text{page} &= \text{time from a failed attempt to the next paging acquisition}
\end{aligned}
$$

| Symbol · 符号 | Meaning | 含义 | Value · 取值 |
| --- | --- | --- | --- |
| 1[·] | 1 if true, else 0 | 条件成立为 1，否则为 0 | — |
| d_i,r | Distance device i ↔ reader r | 设备 i 与读写器 r 的距离 | m |
| R_i,r | Reader r's coverage radius for device i's type | 读写器 r 对设备 i 类型的覆盖半径 | m |

Code: `inventory/metrics.py`
