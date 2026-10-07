# Reproduction assumptions

These are **not** claimed as paper equations.

## Access probability

Paper: reader indicates \(p_{\mathrm{access}}\) from previous Msg1 AO occupancy / congestion. No update formula.

Default `occupancy_counts` (Schoute):

\[
\hat n = S + 2.39\,C,\quad
p \leftarrow \mathrm{clip}\big(p\cdot M/\hat n,\, p_{\min}, 1\big)
\]

with smoothing. \(S,C\) are singleton and collision AO counts. All-idle with listeners present raises \(p\). Empty paging (\(n_{\mathrm{eligible}}=0\)) is not a load observation.

Scope default `per_group`: each paging group has its own controller, because p is carried in that paging message. `global` is a comparison mode.

Other modes: `poisson_idle` (gated), `poisson_idle_ungated`, `fixed`.

Target: about one attempt per AO (slotted ALOHA optimum). Not chosen to match T99.

## Aperiodic paging (EM)

Paper: paging may be aperiodic. Exact schedule not given.

Implemented: start the next paging when the previous CBRA finishes (skip Msg2/Msg3 if no Msg1 success).

## Initial device phase

Paper: charging stage exists; devices are not synchronized. Exact \(t=0\) energy law not given. EM T99 ≈ 20 s is P1: a device near \(E_{\mathrm{low}}\) with \(p_{\mathrm{in}}\approx-36\,\mathrm{dBm}\) needs ~20 s to reach \(E_{\mathrm{up}}\).

| Mode | Meaning |
| --- | --- |
| `stationary` (default) | Independent cycle phase from shared `phase_u` |
| `explicit` | From \(E_{\mathrm{low}}\)/OFF, run each strategy’s machine for `warmup_s` |
| `harvest_only` | All strategies stay OFF and harvest `warmup_s` (identical physical charge) |

Warm-up time is **not** included in Figure 5(b). EM and DCM may differ after `explicit` because their pre-inventory machines differ; `harvest_only` forces the same energy.

\(p_{\mathrm{in}}\) uses stratified inverse-CDF sampling from digitized Figure 5(a). `iid` remains available.

## Group assignment

Paper: first detected paging sets the wake phase (odd/even for \(N_g=2\)). It does **not** say that every device hearing the same occasion must share a group.

| Mode | Meaning |
| --- | --- |
| `first_paging_spread` (default) | Group drawn uniformly at first detection |
| `first_paging_mod` | \(g =\) first paging index \(\bmod N_g\) (often unbalanced) |
| `even_id_mod` | \(g = i \bmod N_g\) at t=0 |
| `random_preconfigured` | shuffled even split at t=0 |

Thereafter the device wakes every \(N_g T_{pg}\) on its group’s epochs.

## OFF and synchronization

Default true: turning the IC off clears inventory sync, so the device must detect paging again.

`off_clears_inventory_sync=False` recharges while remaining synced, then SLEEPs until the next group epoch. Do not wake a depleted device into ON.

## DCM ON window after paging

Paper default `sleep_when_not_attempting=False`. Published Table 1: \(T_{\mathrm{on}}^{\mathrm{DCM}}=3\,\mathrm{ms}\) is the on duration **after the device acquires the inventory stage**, for monitoring A-IoT paging. Combined with \(T_{\mathrm{sl}}^{\mathrm{DCM}}+T_{\mathrm{on}}^{\mathrm{DCM}}=T_{\mathrm{pg}}\), each synced 1-group occasion is 3 ms ON + 9 ms SLEEP. 4-group devices wake every \(4T_{pg}=48\,\mathrm{ms}\) but the ON duration is still 3 ms. The paper does **not** say a failed access-probability draw may end that ON window after the 1 ms paging.

`sleep_when_not_attempting=True` is labeled `experimental_early_sleep_after_access_rejection` in the UI and payload. It is an unpublished duty-cycle change (non-attempters ~1 ms ON then SLEEP). Do not use it as the paper curve, and do not adopt it because the strict 3 ms model’s 4-group tail is slower than EM.

After a CBRA that already occupied paging + Msg1 (≥ 3 ms), unsuccessful attempters return to SLEEP so they do not start a **second** 3 ms ON. That is not the same as shortening unused occasions to 1 ms.

SLEEP energy is unchanged by default: \(\Delta E=(P_{eh}-P_{sl})\Delta t\). Weak devices still drain in SLEEP. Early-sleep only changes the ON/SLEEP duty cycle.

The left-panel **SLEEP net-power min** is an experimental clamp \(P_{\mathrm{net}}=\max(x,\,P_{eh}-P_{sl})\). Empty / \(-\infty\) is the paper formula. \(x=0\) (nW) stops SLEEP drain. That is not a paper claim; do not treat it as a SLEEP-formula “fix”.

## Grouping and access controller (not T99-fitted)

`first_paging_spread` exists because assigning \(g=\) paging index \(\bmod N_g\) dumps every device that is ON at t=0 into group 0, which fights Fig. 4’s load-spreading purpose. `occupancy_counts` is a Schoute ALOHA load estimate (target ~1 attempt/AO) because the paper gives no \(p_{\mathrm{access}}\) equation. Neither default was chosen to match a T99 number. Keep them unless a paper-text reason appears; do not retune them to hide the strict-mode tail.

## Periodic paging

DCM paging occasions are the global epoch grid \(0, T_{\mathrm{pg}}, 2T_{\mathrm{pg}}, \ldots\). If a CBRA overruns an epoch, that occasion is skipped. Device-1 full CBRA is 6.5 ms < 12 ms, so overruns are rare.

## Factory coordinates

\((x,y)\) is visualization only. \(p_{in}\) comes from Figure 5(a), not from distance to the plotted reader.

## Channel

No noise, interference, or decoding failures. Msg1 fails only on collision or energy depletion.
