# Simulation model

Internal units: seconds, Joules, Watts. Display units: ms, nJ, μW, nW, dBm.

Slot loop: `dt = 0.5 ms`.

Energy:

- OFF: \(E \leftarrow \min(E_{\max}, E + P_{eh}\Delta t)\)
- ON: \(E \leftarrow E - P_{rx}\Delta t\)
- TX: \(E \leftarrow E - P_{tx}\Delta t\)
- SLEEP: \(E \leftarrow E + (P_{eh}-P_{sl})\Delta t\), clipped to \([0,E_{\max}]\)

EM: OFF↔ON at \(E_{\mathrm{up}}\) / \(E_{\mathrm{low}}\).

DCM before first paging: ON for \(T_{\mathrm{on}}^{\mathrm{timer}}\) then OFF even if \(E>E_{\mathrm{low}}\).

DCM after first paging: sleep/on with \(T_{sl}+T_{on}=N_g T_{pg}\), group \(=\) device id \(\bmod N_g\) (even split).

CBRA: eligible ON devices attempt with \(p_{\mathrm{access}}\), pick one of 8 AOs uniformly. One occupant → Msg1 success → Msg2/Msg3 → DONE. Multiple occupants → collision.

Web snapshots are stored every 100 ms. Playback is not the simulator.
