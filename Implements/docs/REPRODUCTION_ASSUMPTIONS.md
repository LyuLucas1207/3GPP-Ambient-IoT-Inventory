# Reproduction assumptions

These are **not** claimed as paper equations.

## Access probability

Paper: reader indicates \(p_{\mathrm{access}}\) from previous Msg1 AO occupancy / congestion. No update formula.

Implemented in `simulator/access_control.py`:

\[
I/M \approx e^{-\lambda},\quad \hat A = M\lambda,\quad
p \leftarrow \mathrm{clip}\big(p\cdot M/\hat A,\, p_{\min}, 1\big)
\]

with smoothing and \(I\in\{0,M\}\) guards. Target: about one attempt per AO.

## Aperiodic paging (EM)

Paper: paging may be aperiodic. Exact schedule not given.

Implemented: start the next paging when the previous CBRA finishes (skip Msg2/Msg3 if no Msg1 success).

## Initial device phase

Paper: charging stage exists; devices are not synchronized. Exact \(t=0\) energy law not given.

Implemented: common stratified `phase_u` mapped onto the stationary EM or pre-inventory DCM cycle (`warmup_mode=stationary`). `warmup_mode=explicit` runs the real ON/OFF machine for `warmup_s` from \(E_{\mathrm{low}}\). These are not interchangeable. Warm-up time is **not** included in Figure 5(b).

\(p_{\mathrm{in}}\) uses stratified inverse-CDF sampling from digitized Figure 5(a) so the 600-device empirical tail is covered. `iid` remains available.

## Group assignment

Not a random `randint(0,3)` at birth.

Implemented: `group_id = device_id % N_groups` (even split, **preconfigured reproduction assumption**, not a published procedure). First paging only synchronizes the device to the reader’s paging epoch; only that group contends on paging `k`.

`first_paging_mod` is an alternate assumption, not an equally valid “paper mode”. It dumps everyone who hears the same paging into one group.

## OFF and synchronization

Default true: turning the IC off clears inventory sync, so the device must detect paging again. Group id is kept under `even_id_mod`.

`off_clears_inventory_sync=False` now recharges while remaining synced, then SLEEPs until the next group epoch. Do not wake a depleted device into ON.

## Periodic paging

DCM paging occasions are the global epoch grid \(0, T_{\mathrm{pg}}, 2T_{\mathrm{pg}}, \ldots\). If a CBRA overruns an epoch, that occasion is skipped.

## Factory coordinates

\((x,y)\) is visualization only. \(p_{in}\) comes from Figure 5(a), not from distance to the plotted reader.
