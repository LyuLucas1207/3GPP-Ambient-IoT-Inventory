> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Aperiodic](./64-aperiodic.md) |
| 下一章 | [Sleep state →](./66-sleep-state.md) |

---

# 65. 为什么 \(T_{on}^{timer}\ge T_{pg}\)？

因为设备醒来以后：

> 至少应该保持醒着足够久，有机会碰到一次 paging。

假设 paging 每：

$$
12ms
$$

一次。

而你只醒：

$$
2ms
$$

很可能：

```text
wake
sleep

        paging
```

完全错过。

所以论文说最好：

$$
T_{on}^{timer}\ge T_{pg}
$$

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Aperiodic](./64-aperiodic.md) |
| 下一章 | [Sleep state →](./66-sleep-state.md) |
