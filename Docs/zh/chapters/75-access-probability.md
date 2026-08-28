> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Congestion Control](./74-congestion-control.md) |
| 下一章 | [Occupancy →](./76-occupancy.md) |

---

# 75. Access Probability 是什么？

## Probability = 概率

Reader 可以告诉设备：

> “虽然你收到 paging，但这一轮只有一定概率参加。”

例如：

$$
p=0.1
$$

600 个设备中，大概只有：

$$
600\times0.1=60
$$

个参加。

---

每个 Tag：

```text
random number
↓
0.073 < 0.1
→ access

0.51 > 0.1
→ don't access
```

这样就不会 600 个全冲进 AO。

论文明确说 reader 可以根据先前 CBRA 的 congestion/occupancy 来决定 access probability。

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Congestion Control](./74-congestion-control.md) |
| 下一章 | [Occupancy →](./76-occupancy.md) |
