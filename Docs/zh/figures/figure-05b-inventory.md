> **导航** · [逐图目录](./README.md) · [总目录 content.md](../content.md)

| | |
|---|---|
| 上一图 | [← Figure 5(a)：Received Power CDF](./figure-05a-cdf.md) |
| 下一图 | [Figure 5(c)：Device 2 Inventory Curve →](./figure-05c-device2.md) |

---

# Figure 5(b)：Successfully Inventoried Ratio vs Time

这是教授要你复现的图。

## 坐标

| 轴 | 含义 |
|---|---|
| 横轴 | Time (ms) |
| 纵轴 | Successfully inventoried A-IoT device ratio (%) |

对 \(N=600\)：

\[
R(t)=\frac{\#\{i:T_i^{\mathrm{success}}\le t\}}{600}\times 100\%
\]

## 常见曲线（Device 1，正式版）

1. **EM, aperiodic paging**
2. **DCM, periodic paging, 1 group**
3. **DCM, periodic paging, 4 groups**

关键结论：

- 单独 DCM：对 Device 1 **不明显**
- DCM + 4 groups：99% completion time **约减少 50%**

原因一句话：

> 600 设备太挤，access probability 被压很低；grouping 同时减轻 contention 和无效监听。

## 每个点怎么来的？

不是手动画曲线，而是仿真统计：

```text
跑完一轮 system simulation
→ 每个 Device 记录成功时间 T_i
→ 对每个 t 统计已成功比例
→ 得到一条阶梯/平滑上升曲线
```

## 过关标准

能回答教授：

> Why does DCM alone not improve Device 1 much?


---

> **导航**
>
> - [↑ 逐图目录](./README.md)
> - [↑ 总目录](../content.md)
> - [← Figure 5(a)：Received Power CDF](./figure-05a-cdf.md)
> - [Figure 5(c)：Device 2 Inventory Curve →](./figure-05c-device2.md)
