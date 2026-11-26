# Vocabulary · 术语表

Abbreviations and terms used in the papers, TR 38.769, the simulators and the multi-reader training code.
本项目（论文、TR 38.769、仿真器与多读写器训练代码）中出现的缩写与术语。

The beginner chapter [96 · acronym table](./en/chapters/96-acronym-table.md) ([中文](./zh/chapters/96-acronym-table.md)) explains the first few in context; this file is the complete list. Formulas: [FORMULAS.md](./FORMULAS.md) · 公式表。

## 3GPP and radio · 3GPP 与无线

| Abbreviation | Full name | 中文 |
| --- | --- | --- |
| 3GPP | 3rd Generation Partnership Project | 第三代合作伙伴计划 |
| TR | Technical Report | 技术报告 |
| TS | Technical Specification | 技术规范 |
| Rel-19 | Release 19 | 第 19 版（3GPP 版本） |
| IoT | Internet of Things | 物联网 |
| A-IoT | Ambient IoT | 环境物联网（无源 / 极低功耗物联网） |
| NR | New Radio | 新空口（5G 无线接口） |
| BS | Base Station | 基站 |
| gNB | Next-generation NodeB | 5G 基站 |
| UE | User Equipment | 用户设备 / 终端 |
| RF | Radio Frequency | 射频 |
| RFID | Radio Frequency Identification | 射频识别 |
| UHF | Ultra High Frequency | 特高频 |
| CW | Continuous Wave | 连续波（载波） |
| R2D | Reader-to-Device | 读写器到设备（下行） |
| D2R | Device-to-Reader | 设备到读写器（上行） |
| SIR | Signal-to-Interference Ratio | 信干比 |
| SINR | Signal-to-Interference-plus-Noise Ratio | 信干噪比 |
| SNR | Signal-to-Noise Ratio | 信噪比 |
| PL | Path Loss | 路径损耗 |
| LOS / NLOS | Line of Sight / Non-Line of Sight | 视距 / 非视距 |
| InF-DH | Indoor Factory, Dense clutter, High base station | 室内工厂（高密度遮挡、高位基站）场景 |
| D1T1 | Deployment 1, Topology 1 (TR 38.769) | 部署 1 拓扑 1（读写器为基站，设备直连） |
| SIC | Self-Interference Cancellation | 自干扰消除 |
| dB / dBm | Decibel / decibel-milliwatt | 分贝 / 毫瓦分贝 |
| FDMA | Frequency-Division Multiple Access | 频分多址 |
| TDMA | Time-Division Multiple Access | 时分多址 |
| LBT | Listen Before Talk | 先听后说 |
| ETSI | European Telecommunications Standards Institute | 欧洲电信标准协会 |
| EN 302 208 | ETSI standard for UHF RFID readers | ETSI UHF RFID 读写器标准 |

## Inventory procedure · 盘点流程

| Abbreviation | Full name | 中文 |
| --- | --- | --- |
| CBRA | Contention-Based Random Access | 基于竞争的随机接入 |
| CFRA | Contention-Free Random Access | 无竞争随机接入 |
| AO | Access Occasion | 接入时机（一次 Msg1 发送机会） |
| Msg1 | Message 1 (random-access preamble / RN16) | 消息 1（随机接入前导） |
| Msg2 | Message 2 (reader acknowledgement) | 消息 2（读写器应答） |
| Msg3 | Message 3 (device ID report) | 消息 3（设备 ID 上报） |
| RN16 | 16-bit Random Number | 16 位随机数 |
| EBI / EI | Early (busy) Indication: one bit per slot after Msg1 saying a response was detected | 早期指示（Msg1 后逐时隙的检测标志位） |
| WUR / WuRx | Wake-Up Receiver | 唤醒接收机 |
| DFSA | Dynamic Framed Slotted ALOHA | 动态帧时隙 ALOHA |
| FSA | Framed Slotted ALOHA | 帧时隙 ALOHA |
| K | Frame size (slots per frame) | 帧长（每帧时隙数） |
| L_s | Number of time slots per frame | 每帧时间时隙数 |
| F / F_r | Frequency subbands (total / granted to reader r) | 频率子带数（总数 / 读写器 r 获得的数） |
| p* | Access probability | 接入概率 |
| N̂ | Estimated backlog | 积压设备数估计 |
| T50 / T99 | Time until 50 % / 99 % of devices are identified | 识别 50% / 99% 设备所需时间 |
| t_wc | Worst-case charging time | 最坏情况充电时间 |
| Ph | Harvested power | 采集功率 |
| EH | Energy Harvesting | 能量采集 |
| Device 1 / 2a / 2b | TR 38.769 device types: 1 = ~1 µW backscatter, no amplifier; 2a = backscatter with energy storage, no amplifier; 2b = with internal signal generation / amplification | TR 38.769 设备类型：1 = 约 1 µW 反向散射、无放大；2a = 带储能的反向散射、无放大；2b = 具备内部信号生成 / 放大 |

## Multi-reader extension · 多读写器扩展

| Abbreviation | Full name | 中文 |
| --- | --- | --- |
| G | Gain retention, (T_serial − T_policy) / (T_serial − T_ideal) | 增益保持率 |
| Conflict graph | Graph of reader pairs that would break each other's links | 冲突图 |
| Colour | Graph colouring class; same colour = never conflicts | 着色类别（同色互不冲突） |
| Grant | Subbands and time slot a reader may use | 授予资源（子带与时隙） |
| Oracle | Stop rule that knows the ground truth | 全知终止（使用真实值） |
| Quiet rounds | Stop after n frames with no new ID | 连续安静轮数终止 |
| ID rate | Identification rate threshold rule | 识别速率终止 |
| Energy bound | Stop after t_wc without a new ID | 能量上界终止 |
| EWMA | Exponentially Weighted Moving Average | 指数加权移动平均 |
| Pareto front | Rules not beaten on both extra time and missed devices | 帕累托前沿 |
| Replay | Re-running stop rules on a recorded frame history | 回放（在记录的帧历史上重算终止规则） |

## Reinforcement learning · 强化学习

| Abbreviation | Full name | 中文 |
| --- | --- | --- |
| RL | Reinforcement Learning | 强化学习 |
| MDP | Markov Decision Process | 马尔可夫决策过程 |
| POMDP | Partially Observable Markov Decision Process | 部分可观测马尔可夫决策过程 |
| Dec-POMDP | Decentralized POMDP | 分布式部分可观测马尔可夫决策过程 |
| PPO | Proximal Policy Optimization | 近端策略优化 |
| RecurrentPPO | PPO with an LSTM policy | 循环 PPO（带 LSTM 的 PPO） |
| PS-PPO | Parameter-Sharing PPO | 参数共享 PPO |
| MAPPO | Multi-Agent PPO (centralized critic) | 多智能体 PPO（集中式评论家） |
| IPPO | Independent PPO | 独立 PPO |
| CTDE | Centralized Training, Decentralized Execution | 集中训练、分散执行 |
| MARL | Multi-Agent Reinforcement Learning | 多智能体强化学习 |
| GAE | Generalized Advantage Estimation | 广义优势估计 |
| MLP | Multi-Layer Perceptron | 多层感知机 |
| LSTM | Long Short-Term Memory | 长短期记忆网络 |
| Actor / Critic | Policy network / value network | 策略网络 / 价值网络 |
| Episode | One simulated inventory from start to stop | 回合（一次完整盘点） |
| Timestep | One reader frame (one action) | 时间步（一帧 / 一次动作） |
| Rollout | Batch of collected transitions before an update | 采样轨迹批 |
| Zero-shot | Using a policy on a task it was not trained on | 零样本迁移 |
| sb3 | stable-baselines3 | stable-baselines3 强化学习库 |
| α / β | Reward weights (time vs. resource) | 奖励权重（时间 / 资源） |
| SHA-256 | Secure Hash Algorithm 256-bit | 256 位安全哈希（校验策略文件） |

## Software · 软件

| Abbreviation | Full name | 中文 |
| --- | --- | --- |
| API | Application Programming Interface | 应用程序接口 |
| CLI | Command-Line Interface | 命令行接口 |
| CSV | Comma-Separated Values | 逗号分隔值文件 |
| JSON | JavaScript Object Notation | JSON 数据格式 |
| UI | User Interface | 用户界面 |
| CDF | Cumulative Distribution Function | 累积分布函数 |
| p95 | 95th percentile | 第 95 百分位 |
