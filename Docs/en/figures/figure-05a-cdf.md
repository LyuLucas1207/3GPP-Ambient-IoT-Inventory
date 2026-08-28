> **Nav** · [Figure notes](./README.md) · [TOC content.md](../content.md)

| | |
|---|---|
| Previous figure | [← Figure 4: Device grouping](./figure-04-grouping.md) |
| Next figure | [Figure 5(b): Successfully inventoried ratio vs time →](./figure-05b-inventory.md) |

---

# Figure 5(a): Received-power CDF

Vertical axis: cumulative fraction  
Horizontal axis: \(p_{in}\) (or received power)

The question is:

> What fraction of Devices receive RF power ≤ some value?

## Why does this matter?

\[
P_{eh}=p_{in}\,\xi(p_{in})
\]

Far Devices: low \(p_{in}\) → slow charging → more likely to drag down 99% inventory.

The paper often uses a sensitivity threshold (e.g. \(-36\,\mathrm{dBm}\)): weaker devices are excluded from the evaluation.

## Pass criterion

When you see the left/right tail of the CDF, you can connect it to:

> “The last few that are hard to inventory are usually the ones with the worst energy.”


---

> **Nav**
>
> - [↑ Figure notes](./README.md)
> - [↑ TOC](../content.md)
> - [← Figure 4: Device grouping](./figure-04-grouping.md)
> - [Figure 5(b): Successfully inventoried ratio vs time →](./figure-05b-inventory.md)
