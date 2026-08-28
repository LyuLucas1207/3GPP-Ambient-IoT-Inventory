> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Low-Power Wake-Up Receiver（门铃）](./79-wakeup-receiver.md) |
| 下一章 | [OOK + Modulation →](./81-ook-modulation.md) |

---

# 80. Preamble 是什么？

论文说 paging 带：

> preamble。

## Preamble = 前导序列

就是正式消息之前先发一个已知 pattern：

```text
101010101...
```

设备知道：

> “只要我检测到这个 pattern，就说明 paging 要来了。”

很像你敲门：

```text
咚咚—咚咚咚
```

里面的人听到这个特殊节奏：

> “哦，是自己人。”

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Low-Power Wake-Up Receiver（门铃）](./79-wakeup-receiver.md) |
| 下一章 | [OOK + Modulation →](./81-ook-modulation.md) |
