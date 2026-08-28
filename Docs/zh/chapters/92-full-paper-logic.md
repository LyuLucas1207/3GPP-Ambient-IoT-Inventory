> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← 关键结论：50% / 66% / 83%](./91-key-conclusions.md) |
| 下一章 | [为什么复现 5(b) 不是 Fig.1 →](./93-why-reproduce-5b.md) |

---

# 92. 所以整篇论文真正的逻辑是一条链

你现在一定要先建立这个脑图：

```text
A-IoT device 没电池
        ↓
必须 energy harvesting
        ↓
有时候没电
        ↓
没电就收不到 paging
        ↓
inventory 变慢
        ↓
传统 EM 会把能量消耗太低
        ↓
需要很久 recharge
        ↓
提出 DCM
        ↓
不要一直醒着
        ↓
保留更多 energy
        ↓
更容易参与 inventory
```

但是：

```text
600 devices
   ↓
同时 access
   ↓
congestion / collision
   ↓
需要 access probability
```

但是：

```text
access probability
   ↓
很多 device 醒了却不能发
   ↓
浪费 energy
   ↓
device grouping
```

最后：

```text
DCM
+
access probability
+
device grouping
+
optional low-power wake-up receiver
        ↓
faster inventory
```

这就是整篇 paper。

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← 关键结论：50% / 66% / 83%](./91-key-conclusions.md) |
| 下一章 | [为什么复现 5(b) 不是 Fig.1 →](./93-why-reproduce-5b.md) |
