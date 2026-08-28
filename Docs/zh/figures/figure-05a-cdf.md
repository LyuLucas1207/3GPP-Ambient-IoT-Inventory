> **导航** · [逐图目录](./README.md) · [总目录 content.md](../content.md)

| | |
|---|---|
| 上一图 | [← Figure 4：Device Grouping](./figure-04-grouping.md) |
| 下一图 | [Figure 5(b)：Successfully Inventoried Ratio vs Time →](./figure-05b-inventory.md) |

---

# Figure 5(a)：Received Power CDF

纵轴：累积比例  
横轴：\(p_{in}\)（或 received power）

问的是：

> 有多少比例的 Device，收到的 RF 功率 ≤ 某个值？

## 为什么重要？

\[
P_{eh}=p_{in}\,\xi(p_{in})
\]

远处 Device：\(p_{in}\) 低 → 充电慢 → 更容易拖慢 99% inventory。

论文常用灵敏度门槛（如 \(-36\,\mathrm{dBm}\)）：更弱的不计入评估。

## 过关标准

看到 CDF 右/左尾时，能联想到：

> “最后那几个难 inventory 的，往往是能量最差的那批。”


---

> **导航**
>
> - [↑ 逐图目录](./README.md)
> - [↑ 总目录](../content.md)
> - [← Figure 4：Device Grouping](./figure-04-grouping.md)
> - [Figure 5(b)：Successfully Inventoried Ratio vs Time →](./figure-05b-inventory.md)
