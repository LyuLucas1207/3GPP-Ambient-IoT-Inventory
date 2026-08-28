> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← batteryless + 电容水杯类比](./03-batteryless.md) |
| 下一章 | [Reader（BS / UE） →](./05-reader.md) |

---

# 4. Energy Harvesting 是什么？

## Energy Harvesting

直译：

> **能量采集**

就是设备从外界获得能量。

比如：

* 太阳能
* 振动
* 温差
* RF 无线电波

这篇 paper 主要讲：

# RF Energy Harvesting

---

## RF 是什么？

### RF = Radio Frequency

中文：

> **射频**

简单理解就是：

> 无线电信号。

Wi-Fi、5G、蓝牙、广播，都涉及 RF 信号。

Reader 在空气里发 RF：

```text
Reader
   )))))))))))))) RF wave
                 ↓
                Tag
```

Tag 的天线收到一点能量：

```text
RF signal
   ↓
antenna
   ↓
energy harvesting circuit
   ↓
capacitor
```

于是 capacitor 被充一点电。

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← batteryless + 电容水杯类比](./03-batteryless.md) |
| 下一章 | [Reader（BS / UE） →](./05-reader.md) |
