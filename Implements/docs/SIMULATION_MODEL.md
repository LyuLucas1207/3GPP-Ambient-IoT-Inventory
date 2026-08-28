# Simulation model

Internal units: seconds, Joules, Watts. Display units: ms, nJ, μW, nW, dBm.

Slot loop: `dt = 0.5 ms`.

Energy:

- OFF: \(E \leftarrow \min(E_{\max}, E + P_{eh}\Delta t)\)
- ON: \(E \leftarrow E - P_{rx}\Delta t\)
- TX: \(E \leftarrow E - P_{tx}\Delta t\)
- SLEEP: \(E \leftarrow E + \max(x,\,P_{eh}-P_{sl})\Delta t\), clipped to \([0,E_{\max}]\). Paper \(x=-\infty\) (weak devices still drain). The left-panel nW field is an experimental floor; \(x=0\) stops SLEEP drain.

EM: OFF↔ON at \(E_{\mathrm{up}}\) / \(E_{\mathrm{low}}\).

DCM before first paging: ON for \(T_{\mathrm{on}}^{\mathrm{timer}}\) then OFF even if \(E>E_{\mathrm{low}}\).

DCM after first paging: wake every \(N_g T_{pg}\). Table 1 \(T_{\mathrm{on}}^{\mathrm{DCM}}=3\,\mathrm{ms}\) is the **monitoring** on-duration after the device acquires the inventory stage (paper: “on duration for monitoring A-IoT paging in the DCM mechanism”), with \(T_{\mathrm{sl}}^{\mathrm{DCM}}+T_{\mathrm{on}}^{\mathrm{DCM}}=T_{\mathrm{pg}}\) (1-group) or the group period \(N_g T_{pg}\). Paper default: every synced occasion stays ON for 3 ms, including devices that draw “no access”. `sleep_when_not_attempting=True` is an experimental early-sleep optimization (SLEEP after the 1 ms paging if not attempting) and is **not** the paper configuration. Group is assigned at first detection (`first_paging_spread` by default). Devices in the current CBRA stay ON through Msg1–Msg3 rather than expiring mid-exchange; unsuccessful attempters return to SLEEP when that CBRA (already ≥ 3 ms) ends, so they do not pay a second \(T_{\mathrm{on}}^{\mathrm{DCM}}\).

CBRA: eligible ON devices attempt with \(p_{\mathrm{access}}\), pick one of 8 AOs uniformly. Four **time** AOs are sequential; two **frequency** AOs share a time slot. Occupancy uses devices that actually transmit. One occupant → Msg1 success → Msg2/Msg3 → DONE. Multiple occupants → collision.

Web snapshots are stored every 100 ms. Playback is not the simulator.
