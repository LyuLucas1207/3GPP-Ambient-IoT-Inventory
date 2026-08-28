> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Sleep state](./66-sleep-state.md) |
| 下一章 | [Synchronization →](./68-synchronization.md) |

---

# 67. 为什么第一次 Paging 特别重要？

第一次之前：

Tag 不知道：

> Reader 有没有开始 inventory。

所以它只能：

```text
醒
听
睡
醒
听
睡
```

但是第一次收到 paging 后：

> “哦！我现在知道 inventory 已经开始，而且 paging 每 12 ms 一次。”

于是以后可以：

```text
       paging
         ↓
sleep sleep ON
         ↓
       paging
         ↓
sleep sleep ON
```

这叫：

# Synchronization

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Sleep state](./66-sleep-state.md) |
| 下一章 | [Synchronization →](./68-synchronization.md) |
