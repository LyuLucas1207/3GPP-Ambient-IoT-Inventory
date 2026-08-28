> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Carrier](./13-carrier.md) |
| 下一章 | [RFID →](./15-rfid.md) |

---

# 14. Backscatter 是什么？

这是 Ambient IoT / RFID 里非常重要的概念。

## Backscatter communication

中文：

> **反向散射通信**

普通手机：

```text
手机自己产生 RF signal
→ amplifier
→ antenna
→ 发出去
```

但是 ultra-low-power tag：

> 没电做这个。

于是它使用 Reader 已经发来的无线波。

Reader：

```text
))))))))))))))))
```

Tag 改变自己天线的电气特性：

```text
反射强
反射弱
反射强
反射弱
```

Reader 检测这个变化：

```text
1 0 1 0
```

这就是：

> backscatter。

非常像：

> 你没有手电筒，但别人拿手电照你；你用镜子改变反射方式来发送 Morse code。

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Carrier](./13-carrier.md) |
| 下一章 | [RFID →](./15-rfid.md) |
