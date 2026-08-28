> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Congestion control](./74-congestion-control.md) |
| Next | [Occupancy →](./76-occupancy.md) |

---

# 75. What is access probability?

## Probability = chance of happening

The reader can tell devices:

> "You received paging, but this round you only join with a certain probability."

For example:

$$
p_{\mathrm{access}}=0.1
$$

Out of \(N=600\) devices, roughly only:

$$
N\times p_{\mathrm{access}}=600\times0.1=60
$$

join.

---

Each tag:

```text
random number
↓
0.073 < 0.1
→ access

0.51 > 0.1
→ don't access
```

Then all 600 devices will not rush into the AOs at once.

The paper states clearly that the reader can set the access probability from the congestion/occupancy of prior CBRA.

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Congestion control](./74-congestion-control.md) |
| Next | [Occupancy →](./76-occupancy.md) |
