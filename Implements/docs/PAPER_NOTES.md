# Paper notes: arXiv v1 vs published IEEE

Canonical implementation source: **published IEEE** paper.

## RF conversion efficiency

Published / physically consistent form used here:

```text
xi = (p_in + 41) / 100      if p_in <= -10 dBm
xi = (-2 * p_in + 11) / 100 if p_in  > -10 dBm
```

At \(p_{in}=-36\,\mathrm{dBm}\), \(\xi=0.05\), \(P_{eh}\approx 12.56\,\mathrm{nW}\), and charging 250 nJ takes \(\approx 19.9\,\mathrm{s}\).

arXiv v1 prints the piecewise **inequalities swapped**. That form would give \(\xi(-36\,\mathrm{dBm})\approx 83\%\), which contradicts the paper’s own 5% / 20 s example. Do not use the arXiv inequality direction.

## Table 1

arXiv Table I states times in **slots** (0.5 ms). Published Table 1 uses milliseconds. Device-1 values match after conversion, except:

- arXiv \(T_{\mathrm{on}}^{\mathrm{DCM}}\) Device 1 = 4 slots = **2 ms**
- published Device 1 \(T_{\mathrm{on}}^{\mathrm{DCM}}\) = **3 ms**  ← used here

## Figure 5(b) narrative

- arXiv emphasizes DCM leaving \(e_{es}\gtrsim 428\,\mathrm{nJ}\) and ~10 s for 99%.
- Published Device 1: EM T99 \(\approx 20\,\mathrm{s}\); DCM without grouping does **not** help much; DCM + grouping \(\approx 50\%\) T99 reduction.

This reproduction follows the **published** Device-1 comparison: EM aperiodic, DCM 1-group, DCM 4-groups.

## Figure 5(a)

CDF of \(p_{in}\) for D1T1 120 m × 60 m factory, one of 18 BSs at 33 dBm, devices below −36 dBm excluded.

Re-digitized from the published IEEE Figure 5(a) (page 7). Median \(p_{in}\approx -30\,\mathrm{dBm}\), \(F(-35\,\mathrm{dBm})\approx 0.10\). Method: `backend/data/FIG5A_DIGITIZATION.md`. Do not fit this CDF to Figure 5(b).

## Grouping

Default reproduction assumption: \(g = i \bmod N_g\) (even split). First paging only synchronizes the device to the reader epoch. Alternative `first_paging_mod` exists in `AssumptionParams.group_assignment` but is not the default.

## Access probability

The paper does not give an update equation. This build uses an idle-AO Poisson load estimate. If no device is eligible, occupancy is not treated as “load too low” (p is left unchanged).

## Warm-up

Default `warmup_mode=stationary`: closed-form ON/OFF (EM) or \(T_{\mathrm{on}}^{\mathrm{timer}}\) (DCM) cycle phase. `warmup_mode=explicit` now actually runs that machine for `warmup_s` from \(E_{\mathrm{low}}\)/OFF with no paging. The two are **not** equivalent: a shared 60 s charge does not reproduce a uniform stationary phase, so EM T99 can differ by several seconds. The charging stage is **not** on the Figure 5(b) axis.
