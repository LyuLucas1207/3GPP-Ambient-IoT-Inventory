> **Nav** · [Figure notes](./README.md) · [TOC content.md](../content.md)

| | |
|---|---|
| Previous figure | [← Figure 2: EM energy state](./figure-02-em-energy.md) |
| Next figure | [Figure 4: Device grouping →](./figure-04-grouping.md) |

---

# Figure 3: EM vs Duty-Cycled Monitoring (DCM)

This is one of the most important intuition figures in the whole paper.

## EM

```text
Charge full → keep listening → drain very low → OFF → a large gap that takes a long time to refill
```

## DCM

```text
Charge full → listen only a short while → sleep on purpose → a small gap that refills quickly
```

## The counter-intuitive point

“Going to sleep earlier” is not laziness. It is:

> **shortening recharge time, which raises the chance of joining the next inventory.**

Matching formula intuition:

\[
T_{recharge}=\frac{\Delta E}{P_{eh}}
\]

The smaller \(\Delta E\), the faster recovery.

## Pass criterion

You can contrast them in one sentence:

> EM drinks the cup down to half empty, then slowly fills it; DCM takes only a sip and then goes to refill, so the cup stays relatively full.


---

> **Nav**
>
> - [↑ Figure notes](./README.md)
> - [↑ TOC](../content.md)
> - [← Figure 2: EM energy state](./figure-02-em-energy.md)
> - [Figure 4: Device grouping →](./figure-04-grouping.md)
