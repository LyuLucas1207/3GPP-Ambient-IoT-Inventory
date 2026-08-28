> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Msg1 / Msg2 / Msg3 流程](./28-msg1-2-3.md) |
| 下一章 | [ID →](./30-id.md) |

---

# 29. 为什么 Msg1 用 random ID？

论文给例子：

> 16-bit random ID。

因为 Reader 一开始还不知道：

> 你是谁。

Tag 先临时生成一个短 ID：

```text
101001101011...
```

用它完成初步 handshake。

之后 Msg3 再报告真正 device ID。

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Msg1 / Msg2 / Msg3 流程](./28-msg1-2-3.md) |
| 下一章 | [ID →](./30-id.md) |
