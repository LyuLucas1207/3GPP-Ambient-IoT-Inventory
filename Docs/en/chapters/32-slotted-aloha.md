> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Collision](./31-collision.md) |
| 下一章 | [Slot（0.5 ms） →](./33-slot.md) |

---

# 32. Slotted ALOHA 是什么？

这个名字你也会看到。

## ALOHA

是一个经典 random access protocol。

最简单思想：

> 谁想说就尝试说。

Slotted ALOHA 增加：

> 只能在规定的时间槽开始说。

于是：

```text
slot 1
slot 2
slot 3
slot 4
```

Tag 随机挑 slot。

论文的 Msg1 random access 就是基于 slotted-ALOHA 思路。

现在你不用学它的数学理论。

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Collision](./31-collision.md) |
| 下一章 | [Slot（0.5 ms） →](./33-slot.md) |
