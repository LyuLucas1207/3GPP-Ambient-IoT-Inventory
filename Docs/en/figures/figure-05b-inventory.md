> **Nav** · [Figure notes](./README.md) · [TOC content.md](../content.md)

| | |
|---|---|
| Previous figure | [← Figure 5(a): Received-power CDF](./figure-05a-cdf.md) |
| Next figure | [Figure 5(c): Device 2 inventory curve →](./figure-05c-device2.md) |

---

# Figure 5(b): Successfully inventoried A-IoT device ratio vs time

This is the figure the professor asked you to reproduce.

## Axes

| Axis | Meaning |
|---|---|
| Horizontal | Time (ms) |
| Vertical | Successfully inventoried A-IoT device ratio (%) |

For \(N=600\):

\[
R(t)=\frac{\#\{i:T_i^{\mathrm{success}}\le t\}}{600}\times 100\%
\]

## Common curves (Device 1, published version)

1. **EM, aperiodic paging**
2. **DCM, periodic paging, 1 group**
3. **DCM, periodic paging, 4 groups**

Key conclusions:

- DCM alone: for Device 1, **does not help much**
- DCM + 4 groups: 99% completion time **≈ 50% reduction**

The reason in one sentence:

> 600 devices are too crowded, so access probability is pushed very low; grouping eases both contention and wasted listening.

## Where does each point come from?

The curve is not drawn by hand. It is simulation statistics:

```text
Finish one system simulation
→ Record each Device's success time T_i
→ For each t, count the fraction already successful
→ Get one stepwise / smoothly rising curve
```

## Pass criterion

You can answer the professor:

> Why does DCM alone not improve Device 1 much?


---

> **Nav**
>
> - [↑ Figure notes](./README.md)
> - [↑ TOC](../content.md)
> - [← Figure 5(a): Received-power CDF](./figure-05a-cdf.md)
> - [Figure 5(c): Device 2 inventory curve →](./figure-05c-device2.md)
