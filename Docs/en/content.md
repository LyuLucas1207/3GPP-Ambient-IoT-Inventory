# Ambient IoT 入门指南 · 目录

> 第一次进入无线通信 / IoT / 3GPP / Ambient IoT 的 **research-fit test** 学习笔记。
>
> 目标：从零建立词汇与系统直觉，最终理解并复现论文 **Figure 5(b)**。

## 怎么用

1. **一个 chapter = 一个 `.md` 文件**（点击下方链接即可跳转）。
2. **文件夹只用来分组**：`chapters/` 放正文，`figures/` 放逐图精读——不是“一章一文件夹”。
3. 每章顶部/底部都有：**返回目录**、**上一章**、**下一章**。
4. 章节编号 **0–97** 与讲义小节一一对应（另有 Preface）。

## 相关材料

- 论文 PDF：[`../Papers/`](../Papers/)
- 简历等文件：[`../Files/`](../Files/)
- 完整单文件备份：[`ambient_iot_beginner_guide.md`](./ambient_iot_beginner_guide.md)
- **真实世界故事（快速直觉）**：[`story.md`](./story.md)
- **逐图精读轨道**：[`figures/README.md`](./figures/README.md)

---

## 章节目录

### 定位与故事

- [**Story · 把论文放回真实世界**](./story.md) ← 推荐先读：工厂盘点 / 没电 / 拥塞 / RF 充电
- [Preface · 研究适配度测试（Preface）](./chapters/00-research-fit.md)
- [0. 仓库故事与 Inventory](./chapters/00-warehouse-story.md)

### 基础概念：IoT / 标准 / 设备

- [1. IoT](./chapters/01-iot.md)
- [2. A-IoT（含手机对比）](./chapters/02-a-iot.md)
- [3. batteryless + 电容水杯类比](./chapters/03-batteryless.md)
- [4. Energy Harvesting / RF / 天线链路](./chapters/04-energy-harvesting.md)
- [5. Reader（BS / UE）](./chapters/05-reader.md)
- [6. BS + 工厂场景 120m×60m](./chapters/06-bs.md)
- [7. UE](./chapters/07-ue.md)
- [8. 3GPP（Samsung / Apple 例子）](./chapters/08-3gpp.md)
- [9. Release 18 / 19](./chapters/09-release-18-19.md)
- [10. TR 38.769](./chapters/10-tr-38-769.md)
- [11. Device 1 / Device 2](./chapters/11-device-1-2.md)

### 物理层直觉：CW / Backscatter / RFID / NR

- [12. CW](./chapters/12-cw.md)
- [13. Carrier](./chapters/13-carrier.md)
- [14. Backscatter（镜子 / 手电筒）](./chapters/14-backscatter.md)
- [15. RFID](./chapters/15-rfid.md)
- [16. UHF](./chapters/16-uhf.md)
- [17. A-IoT vs RFID](./chapters/17-aiot-vs-rfid.md)
- [18. NR](./chapters/18-nr.md)
- [19. R2D / D2R](./chapters/19-r2d-d2r.md)

### Inventory 与随机接入

- [20. Paging](./chapters/20-paging.md)
- [21. Random Access](./chapters/21-random-access.md)
- [22. CBRA](./chapters/22-cbra.md)
- [23. CFRA](./chapters/23-cfra.md)
- [24. Contention（厕所类比）](./chapters/24-contention.md)
- [25. AO](./chapters/25-ao.md)
- [26. 时频资源](./chapters/26-time-frequency-resources.md)
- [27. FDMA](./chapters/27-fdma.md)
- [28. Msg1 / Msg2 / Msg3 流程](./chapters/28-msg1-2-3.md)
- [29. 为什么 Msg1 用 16-bit 随机 ID](./chapters/29-why-msg1-random-id.md)
- [30. ID](./chapters/30-id.md)
- [31. Collision](./chapters/31-collision.md)
- [32. Slotted ALOHA](./chapters/32-slotted-aloha.md)
- [33. Slot（0.5 ms）](./chapters/33-slot.md)
- [34. Congestion](./chapters/34-congestion.md)
- [35. 何时 Inventory 成功](./chapters/35-when-inventory-succeeds.md)

### 能量模型

- [36. 能量 e_es, E_es^max](./chapters/36-energy-e-es.md)
- [37. nJ](./chapters/37-nj.md)
- [38. Power vs Energy（0.5 s 例子）](./chapters/38-power-vs-energy.md)
- [39. P_rx](./chapters/39-p-rx.md)
- [40. P_tx](./chapters/40-p-tx.md)
- [41. P_eh = p_in · ξ](./chapters/41-p-eh.md)
- [42. p_in](./chapters/42-p-in.md)
- [43. dBm](./chapters/43-dbm.md)
- [44. Receiver sensitivity −36 dBm](./chapters/44-receiver-sensitivity.md)
- [45. ξ(p_in) 效率](./chapters/45-xi-efficiency.md)
- [46. 为什么充电速度不同](./chapters/46-why-different-charge-rates.md)
- [47. ON state](./chapters/47-on-state.md)
- [48. OFF state](./chapters/48-off-state.md)
- [49. IC](./chapters/49-ic.md)
- [50. Turn-on E_es^up](./chapters/50-turn-on.md)
- [51. Turn-off E_es^low](./chapters/51-turn-off.md)

### EM 的问题与 P1–P3

- [52. EM](./chapters/52-em.md)
- [53. Monitoring 的含义](./chapters/53-monitoring-meaning.md)
- [54. 为什么 EM 不好 → P1 P2 P3](./chapters/54-why-em-bad.md)
- [55. P1](./chapters/55-p1.md)
- [56. P2（手机 1% 类比）](./chapters/56-p2.md)
- [57. P3](./chapters/57-p3.md)

### DCM：Duty-Cycled Monitoring

- [58. DCM](./chapters/58-dcm.md)
- [59. DCM 核心思想](./chapters/59-dcm-core-idea.md)
- [60. 为什么睡觉反而快（熬夜类比）](./chapters/60-why-sleeping-helps.md)
- [61. On timer](./chapters/61-on-timer.md)
- [62. T_pg](./chapters/62-t-pg.md)
- [63. Periodic](./chapters/63-periodic.md)
- [64. Aperiodic](./chapters/64-aperiodic.md)
- [65. T_on^timer ≥ T_pg](./chapters/65-ton-timer-ge-tpg.md)
- [66. Sleep state](./chapters/66-sleep-state.md)
- [67. 第一次 Paging 为什么重要](./chapters/67-first-paging.md)
- [68. Synchronization](./chapters/68-synchronization.md)
- [69. T_sl^DCM](./chapters/69-t-sl-dcm.md)
- [70. T_on^DCM](./chapters/70-t-on-dcm.md)
- [71. P_sl](./chapters/71-p-sl.md)
- [72. DCM 解决了什么](./chapters/72-what-dcm-solved.md)

### 拥塞控制与唤醒接收机

- [73. 600 设备问题](./chapters/73-600-devices-problem.md)
- [74. Congestion Control](./chapters/74-congestion-control.md)
- [75. Access Probability](./chapters/75-access-probability.md)
- [76. Occupancy](./chapters/76-occupancy.md)
- [77. Access Probability 的缺点](./chapters/77-access-probability-drawback.md)
- [78. Device Grouping](./chapters/78-device-grouping.md)
- [79. Low-Power Wake-Up Receiver（门铃）](./chapters/79-wakeup-receiver.md)
- [80. Preamble](./chapters/80-preamble.md)

### 物理层速览

- [81. OOK + Modulation](./chapters/81-ook-modulation.md)
- [82. BPSK](./chapters/82-bpsk.md)
- [83. OFDM](./chapters/83-ofdm.md)
- [84. FDD](./chapters/84-fdd.md)
- [85. Uplink / Downlink](./chapters/85-uplink-downlink.md)
- [86. Link Budget](./chapters/86-link-budget.md)
- [87. CDF](./chapters/87-cdf.md)

### Figure 5(b) 与论文结论

- [88. Figure 5(b) 在画什么](./chapters/88-figure-5b-meaning.md)
- [89. 为什么看 99%](./chapters/89-why-99.md)
- [90. Figure 5(b) 曲线含义](./chapters/90-figure-5b-curves.md)
- [91. 关键结论：50% / 66% / 83%](./chapters/91-key-conclusions.md)
- [92. 整篇论文逻辑链](./chapters/92-full-paper-logic.md)
- [93. 为什么复现 5(b) 不是 Fig.1](./chapters/93-why-reproduce-5b.md)

### 能力、学习路径与过关

- [94. 测试的六种能力](./chapters/94-six-skills.md)
- [95. 学习阶段 1–7（别跳代码）](./chapters/95-learning-stages.md)
- [96. 缩写表](./chapters/96-acronym-table.md)
- [97. 第一阶段过关标准](./chapters/97-stage1-checkpoint.md)

---

## 推荐学习节奏

1. Preface + 第 0–11 章：故事、标准、设备类型
2. 第 12–35 章：Backscatter / CBRA / Collision
3. 第 36–72 章：能量 + EM 问题 + DCM
4. 第 73–91 章：拥塞控制 + Figure 5(b) 结论
5. [逐图精读 Figure 1→5](./figures/README.md)
6. 第 92–97 章：过关自检，再考虑仿真

> 下一步：从 [Preface](./chapters/00-research-fit.md) 开始，或直接进入 [Figure 1 精读](./figures/figure-01-cbra.md)。
