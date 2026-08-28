# Ambient IoT beginner guide · TOC

> Lecture notes for a **research-fit test** when you are new to wireless communications / IoT / 3GPP / Ambient IoT.
>
> Goal: build vocabulary and system intuition from zero, then understand and reproduce paper **Figure 5(b)**.

## How to use this

1. **One chapter = one `.md` file** (click a link below).
2. **Folders group files only**: `chapters/` holds the text; `figures/` holds the close reading of each figure — not “one folder per chapter”.
3. Every chapter has **back to TOC**, **previous**, and **next**.
4. Chapter numbers **0–97** match the lecture sections one-to-one (plus a Preface).

## Related materials

- Paper PDFs: [`../Papers/`](../Papers/)
- CV and other files: [`../Files/`](../Files/)
- Full single-file backup: [`ambient_iot_beginner_guide.md`](./ambient_iot_beginner_guide.md)
- **Real-world story (fast intuition)**: [`story.md`](./story.md)
- **Figure close-reading track**: [`figures/README.md`](./figures/README.md)
- Chinese notes: [`../zh/content.md`](../zh/content.md)

---

## Chapter list

### Orientation and story

- [**Story · put the paper back in the real world**](./story.md) ← start here: factory inventory / no energy / congestion / RF charging
- [Preface · research-fit test](./chapters/00-research-fit.md)
- [0. Warehouse story and inventory](./chapters/00-warehouse-story.md)

### Basics: IoT / standards / devices

- [1. IoT](./chapters/01-iot.md)
- [2. A-IoT (vs. a phone)](./chapters/02-a-iot.md)
- [3. Batteryless + capacitor cup analogy](./chapters/03-batteryless.md)
- [4. Energy harvesting / RF / antenna link](./chapters/04-energy-harvesting.md)
- [5. Reader (BS / UE)](./chapters/05-reader.md)
- [6. BS + the 120 m × 60 m factory](./chapters/06-bs.md)
- [7. UE](./chapters/07-ue.md)
- [8. 3GPP (Samsung / Apple example)](./chapters/08-3gpp.md)
- [9. Release 18 / 19](./chapters/09-release-18-19.md)
- [10. TR 38.769](./chapters/10-tr-38-769.md)
- [11. Device 1 / Device 2](./chapters/11-device-1-2.md)

### Physical-layer intuition: CW / backscatter / RFID / NR

- [12. CW](./chapters/12-cw.md)
- [13. Carrier](./chapters/13-carrier.md)
- [14. Backscatter (mirror / flashlight)](./chapters/14-backscatter.md)
- [15. RFID](./chapters/15-rfid.md)
- [16. UHF](./chapters/16-uhf.md)
- [17. A-IoT vs RFID](./chapters/17-aiot-vs-rfid.md)
- [18. NR](./chapters/18-nr.md)
- [19. R2D / D2R](./chapters/19-r2d-d2r.md)

### Inventory and random access

- [20. Paging](./chapters/20-paging.md)
- [21. Random access](./chapters/21-random-access.md)
- [22. CBRA](./chapters/22-cbra.md)
- [23. CFRA](./chapters/23-cfra.md)
- [24. Contention (stall analogy)](./chapters/24-contention.md)
- [25. AO](./chapters/25-ao.md)
- [26. Time–frequency resources](./chapters/26-time-frequency-resources.md)
- [27. FDMA](./chapters/27-fdma.md)
- [28. Msg1 / Msg2 / Msg3 procedure](./chapters/28-msg1-2-3.md)
- [29. Why Msg1 uses a 16-bit random ID](./chapters/29-why-msg1-random-id.md)
- [30. ID](./chapters/30-id.md)
- [31. Collision](./chapters/31-collision.md)
- [32. Slotted ALOHA](./chapters/32-slotted-aloha.md)
- [33. Slot (0.5 ms)](./chapters/33-slot.md)
- [34. Congestion](./chapters/34-congestion.md)
- [35. When inventory succeeds](./chapters/35-when-inventory-succeeds.md)

### Energy model

- [36. Energy \(e_{es}\), \(E_{es}^{\max}\)](./chapters/36-energy-e-es.md)
- [37. nJ](./chapters/37-nj.md)
- [38. Power vs energy (0.5 s example)](./chapters/38-power-vs-energy.md)
- [39. \(P_{rx}\)](./chapters/39-p-rx.md)
- [40. \(P_{tx}\)](./chapters/40-p-tx.md)
- [41. \(P_{eh}=p_{in}\cdot\xi\)](./chapters/41-p-eh.md)
- [42. \(p_{in}\)](./chapters/42-p-in.md)
- [43. dBm](./chapters/43-dbm.md)
- [44. Receiver sensitivity −36 dBm](./chapters/44-receiver-sensitivity.md)
- [45. \(\xi(p_{in})\) efficiency](./chapters/45-xi-efficiency.md)
- [46. Why charging rates differ](./chapters/46-why-different-charge-rates.md)
- [47. ON state](./chapters/47-on-state.md)
- [48. OFF state](./chapters/48-off-state.md)
- [49. IC](./chapters/49-ic.md)
- [50. Turn-on \(E_{es}^{\mathrm{up}}\)](./chapters/50-turn-on.md)
- [51. Turn-off \(E_{es}^{\mathrm{low}}\)](./chapters/51-turn-off.md)

### Problems of EM and P1–P3

- [52. EM](./chapters/52-em.md)
- [53. What monitoring means](./chapters/53-monitoring-meaning.md)
- [54. Why EM is poor → P1 P2 P3](./chapters/54-why-em-bad.md)
- [55. P1](./chapters/55-p1.md)
- [56. P2 (phone 1% analogy)](./chapters/56-p2.md)
- [57. P3](./chapters/57-p3.md)

### DCM: Duty-Cycled Monitoring

- [58. DCM](./chapters/58-dcm.md)
- [59. Core idea of DCM](./chapters/59-dcm-core-idea.md)
- [60. Why sleeping can be faster (all-nighter analogy)](./chapters/60-why-sleeping-helps.md)
- [61. On timer](./chapters/61-on-timer.md)
- [62. \(T_{pg}\)](./chapters/62-t-pg.md)
- [63. Periodic](./chapters/63-periodic.md)
- [64. Aperiodic](./chapters/64-aperiodic.md)
- [65. \(T_{\mathrm{on}}^{\mathrm{timer}}\ge T_{pg}\)](./chapters/65-ton-timer-ge-tpg.md)
- [66. Sleep state](./chapters/66-sleep-state.md)
- [67. Why the first paging matters](./chapters/67-first-paging.md)
- [68. Synchronization](./chapters/68-synchronization.md)
- [69. \(T_{\mathrm{sl}}^{\mathrm{DCM}}\)](./chapters/69-t-sl-dcm.md)
- [70. \(T_{\mathrm{on}}^{\mathrm{DCM}}\)](./chapters/70-t-on-dcm.md)
- [71. \(P_{sl}\)](./chapters/71-p-sl.md)
- [72. What DCM solved](./chapters/72-what-dcm-solved.md)

### Congestion control and wake-up receiver

- [73. The 600-device problem](./chapters/73-600-devices-problem.md)
- [74. Congestion control](./chapters/74-congestion-control.md)
- [75. Access probability](./chapters/75-access-probability.md)
- [76. Occupancy](./chapters/76-occupancy.md)
- [77. Drawback of access probability](./chapters/77-access-probability-drawback.md)
- [78. Device grouping](./chapters/78-device-grouping.md)
- [79. Low-power wake-up receiver (doorbell)](./chapters/79-wakeup-receiver.md)
- [80. Preamble](./chapters/80-preamble.md)

### Physical-layer skim

- [81. OOK + modulation](./chapters/81-ook-modulation.md)
- [82. BPSK](./chapters/82-bpsk.md)
- [83. OFDM](./chapters/83-ofdm.md)
- [84. FDD](./chapters/84-fdd.md)
- [85. Uplink / downlink](./chapters/85-uplink-downlink.md)
- [86. Link budget](./chapters/86-link-budget.md)
- [87. CDF](./chapters/87-cdf.md)

### Figure 5(b) and paper conclusions

- [88. What Figure 5(b) plots](./chapters/88-figure-5b-meaning.md)
- [89. Why look at 99%](./chapters/89-why-99.md)
- [90. Meaning of the Figure 5(b) curves](./chapters/90-figure-5b-curves.md)
- [91. Key results: 50% / 66% / 83%](./chapters/91-key-conclusions.md)
- [92. Logic chain of the whole paper](./chapters/92-full-paper-logic.md)
- [93. Why reproduce 5(b), not Fig. 1](./chapters/93-why-reproduce-5b.md)

### Skills, learning path, and checkpoint

- [94. Six skills being tested](./chapters/94-six-skills.md)
- [95. Learning stages 1–7 (do not skip to code)](./chapters/95-learning-stages.md)
- [96. Acronym table](./chapters/96-acronym-table.md)
- [97. Stage-1 pass criteria](./chapters/97-stage1-checkpoint.md)

---

## Suggested pace

1. Preface + chapters 0–11: story, standards, device types
2. Chapters 12–35: backscatter / CBRA / collision
3. Chapters 36–72: energy + EM problems + DCM
4. Chapters 73–91: congestion control + Figure 5(b) conclusions
5. [Close-read Figure 1→5](./figures/README.md)
6. Chapters 92–97: self-check, then consider simulation

> Next: start at the [Preface](./chapters/00-research-fit.md), or jump to the [Figure 1 close reading](./figures/figure-01-cbra.md).
