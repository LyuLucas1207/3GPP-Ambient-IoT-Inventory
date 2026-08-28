> **Nav** · [Figure notes](./README.md) · [TOC content.md](../content.md)

| | |
|---|---|
| Previous figure | [← Figure 3: EM vs DCM](./figure-03-em-vs-dcm.md) |
| Next figure | [Figure 5(a): Received-power CDF →](./figure-05a-cdf.md) |

---

# Figure 4: Device grouping

Figure 4 is drawing:

> Do not let every Device wake up every round and contend for the same Paging wave.

## The core picture

```text
Paging 1 → Group A
Paging 2 → Group B
Paging 3 → Group C
Paging 4 → Group D
Paging 5 → Group A
...
```

## Why is it needed?

With access probability alone:

```text
Wake up → spend energy listening to Paging → randomly draw “skip this round” → energy wasted
```

Grouping:

- Lowers contention in the same round
- Cuts pointless listening
- So access probability does not have to be pushed so extreme

## Relation to Figure 5(b)

Device 1:

> DCM alone does not help much; **DCM + 4 groups** clearly cuts 99% completion time by about 50%.

Because the bottleneck shifted from “no energy” to “too crowded.”

## Pass criterion

You can explain:

> Why is DCM alone not enough with 600 Devices and 8 AOs?


---

> **Nav**
>
> - [↑ Figure notes](./README.md)
> - [↑ TOC](../content.md)
> - [← Figure 3: EM vs DCM](./figure-03-em-vs-dcm.md)
> - [Figure 5(a): Received-power CDF →](./figure-05a-cdf.md)
