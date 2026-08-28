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

This implementation follows the **published** Device-1 comparison: EM aperiodic, DCM 1-group, DCM 4-groups. It is a **preliminary reproduction** until `scripts/validate_fig5b.py` PASSes.

## Figure 5(a)

CDF of \(p_{in}\) for D1T1 120 m × 60 m factory, one of 18 BSs at 33 dBm, devices below −36 dBm excluded.

Re-digitized from the published IEEE Figure 5(a) (page 7). Median \(p_{in}\approx -30\,\mathrm{dBm}\), \(F(-35\,\mathrm{dBm})\approx 0.10\). Method: `backend/data/FIG5A_DIGITIZATION.md`. Do not fit this CDF to Figure 5(b).

## Grouping

Paper (Device Grouping for Congestion Control, Fig. 4): a device that receives odd-numbered paging continues odd-numbered paging (\(N_g=2\)). Wake period \(N_g T_{pg}\).

Default here: `first_paging_spread` — grouping happens at first detection, but the group id is a uniform draw, **not** `paging_index % N_g`. Using the paging index would put every device that is ON at t=0 into group 0, which fights Fig. 4’s purpose. `first_paging_mod` is the paper-literal alternative and is compared in `scripts/compare_assumptions.py`. Preconfigured `even_id_mod` / `random_preconfigured` are also available.

## DCM ON after paging

Paper: \(T_{\mathrm{on}}^{\mathrm{DCM}}\) is the on duration for monitoring A-IoT paging after the device acquires the inventory stage. Device 1 Table 1: 3 ms. \(T_{\mathrm{sl}}^{\mathrm{DCM}}+T_{\mathrm{on}}^{\mathrm{DCM}}=T_{\mathrm{pg}}\). Paper configuration therefore keeps a **fixed 3 ms ON** each synced occasion (`sleep_when_not_attempting=False`).

Do **not** claim that 3 ms applies only to devices that actually send Msg1 — the paper does not say that.

`sleep_when_not_attempting=True` is an experimental early-sleep option in the left-hand panel (default unchecked). It was previously used as a paper default because the strict 3 ms 4-group curve had a P1 recharge tail slower than EM. That is outcome-driven and is not allowed as the published configuration.

## Access probability

The paper does not give an update equation. Default: Schoute occupancy counts (`occupancy_counts`) with **per-group** p (the paging message carries p). Target: about one attempt per AO (slotted ALOHA), not a T99 fit. Gated Poisson idle remains as a comparison mode.

## Warm-up

Default `warmup_mode=stationary`: closed-form ON/OFF (EM) or \(T_{\mathrm{on}}^{\mathrm{timer}}\) (DCM) cycle phase. That is why EM’s 99% tail can approach ~20 s: some weak devices are near \(E_{\mathrm{low}}\) when inventory starts (paper P1).

`explicit`: same machine for `warmup_s` from \(E_{\mathrm{low}}\)/OFF, no paging. `harvest_only`: all strategies stay OFF and harvest the same duration (comparable energy, not the paper default). Charging time is **not** on the Figure 5(b) axis.

## Channel errors

Noise, interference, and decoding failures are not modelled.
