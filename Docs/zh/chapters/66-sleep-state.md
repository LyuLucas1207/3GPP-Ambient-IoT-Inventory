> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← T_on^timer ≥ T_pg](./65-ton-timer-ge-tpg.md) |
| 下一章 | [第一次 Paging 为什么重要 →](./67-first-paging.md) |

---

# 66. Sleep state 又是什么？

DCM 里面增加一个：

## Sleep state

区别于完全 OFF。

Sleep：

* 不能正常 Rx/Tx
* 可以 harvest energy
* 还保持一个低功耗 timer
* 知道什么时候该醒

论文说 sleep state 中 device 可以维持 sleep timer，同时 harvesting，但不能 transmit/receive。

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← T_on^timer ≥ T_pg](./65-ton-timer-ge-tpg.md) |
| 下一章 | [第一次 Paging 为什么重要 →](./67-first-paging.md) |
