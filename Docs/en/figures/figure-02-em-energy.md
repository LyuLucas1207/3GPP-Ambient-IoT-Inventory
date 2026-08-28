> **Nav** · [Figure notes](./README.md) · [TOC content.md](../content.md)

| | |
|---|---|
| Previous figure | [← Figure 1: CBRA procedure](./figure-01-cbra.md) |
| Next figure | [Figure 3: EM vs DCM →](./figure-03-em-vs-dcm.md) |

---

# Figure 2: Energy-Based Monitoring (EM) energy state

Figure 2 plots how capacitor energy changes over time under **Energy-Based Monitoring (EM)**.

## The sawtooth you should see

```text
E_up  ─────────────────
         ╱╲      ╱╲
        ╱  ╲    ╱  ╲
       ╱    ╲  ╱    ╲
E_low ─/──────╲/──────
       OFF  ON  OFF  ON
```

Intuition:

| State | Energy | Can it hear Paging? |
|---|---|---|
| OFF | Rising (harvest) | No |
| ON | Falling (Rx/Tx/monitor) | Yes |

Thresholds:

- Reach \(E_{es}^{up}\) → switch ON
- Reach \(E_{es}^{low}\) → switch OFF

Typical Device 1 settings, intuitively:

- \(E_{es}^{max}=500\,\mathrm{nJ}\)
- \(E_{es}^{up}=E_{es}^{max}\)
- \(E_{es}^{low}=0.5E_{es}^{max}\)

## Relation to Figure 1

Figure 1 assumes the Device is “present and able to communicate.”

Figure 2 tells you: in reality the Device is often **not present at all** — it is OFF, charging.

That is the starting point of P1/P2/P3 later.

## Pass criterion

You can explain: why can “always ON, always listening” actually make inventory slower?

> Because energy is driven very low, far-away devices with weak \(p_{in}\) take a long time to charge before they can join Figure 1’s procedure again.


---

> **Nav**
>
> - [↑ Figure notes](./README.md)
> - [↑ TOC](../content.md)
> - [← Figure 1: CBRA procedure](./figure-01-cbra.md)
> - [Figure 3: EM vs DCM →](./figure-03-em-vs-dcm.md)
