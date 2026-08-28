> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← \(T_{\mathrm{on}}^{\mathrm{timer}}\ge T_{pg}\)](./65-ton-timer-ge-tpg.md) |
| Next | [Why the first paging matters →](./67-first-paging.md) |

---

# 66. What is the sleep state?

DCM adds one more state:

## Sleep state

It is different from fully OFF.

SLEEP:

* cannot do normal Rx/Tx
* can harvest energy
* still keeps a low-power timer
* knows when it should wake

The paper says that in the sleep state the device can keep a sleep timer and harvest energy, but cannot transmit/receive.

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← \(T_{\mathrm{on}}^{\mathrm{timer}}\ge T_{pg}\)](./65-ton-timer-ge-tpg.md) |
| Next | [Why the first paging matters →](./67-first-paging.md) |
