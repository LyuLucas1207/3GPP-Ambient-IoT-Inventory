> **导航** · [逐图目录](./README.md) · [总目录 content.md](../content.md)

| | |
|---|---|
| 上一图 | [← Figure 1：CBRA Procedure](./figure-01-cbra.md) |
| 下一图 | [Figure 3：EM vs DCM →](./figure-03-em-vs-dcm.md) |

---

# Figure 2：EM 能量状态

Figure 2 画的是 **Energy-Based Monitoring (EM)** 下，电容能量随时间怎么变。

## 你要看到的锯齿

```text
E_up  ─────────────────
         ╱╲      ╱╲
        ╱  ╲    ╱  ╲
       ╱    ╲  ╱    ╲
E_low ─/──────╲/──────
       OFF  ON  OFF  ON
```

直觉：

| 状态 | 能量 | 能不能听 Paging |
|---|---|---|
| OFF | 上升（harvest） | 不能 |
| ON | 下降（Rx/Tx/monitor） | 能 |

阈值：

- 到 \(E_{es}^{up}\) → 转 ON
- 到 \(E_{es}^{low}\) → 转 OFF

Device 1 常见设定直觉：

- \(E_{es}^{max}=500\,\mathrm{nJ}\)
- \(E_{es}^{up}=E_{es}^{max}\)
- \(E_{es}^{low}=0.5E_{es}^{max}\)

## 和图 1 的关系

Figure 1 假设 Device “在场且能通信”。

Figure 2 告诉你：现实里很多时候 Device **根本不在场**——正在 OFF 充电。

这就是后面 P1/P2/P3 的起点。

## 过关标准

能解释：为什么“一直 ON 监听”反而可能让 inventory 变慢？

> 因为能量被打到很低，远处弱 \(p_{in}\) 设备要充很久才能再次参加 Figure 1 的流程。


---

> **导航**
>
> - [↑ 逐图目录](./README.md)
> - [↑ 总目录](../content.md)
> - [← Figure 1：CBRA Procedure](./figure-01-cbra.md)
> - [Figure 3：EM vs DCM →](./figure-03-em-vs-dcm.md)
