# Aperiodic-paging paper reference data

Reference targets for the aperiodic-paging paper (`Papers/3GPP Ambient IoT Inventory with Aperiodic Paging.pdf`).
They are used **only for validation and plotting**. The simulator never reads them, and the API never returns them as simulation output.

They are kept separate from the legacy `data/periodic/`.

## Figures 4–8 (exact vector extraction)

| Figure | PDF page | Files |
|---|---|---|
| Fig. 4, CDF of P_in | 8 | `figure4/{single_source,multi_source}.csv` (`pin_dbm,cdf`) |
| Fig. 5(a) L=16 / 5(b) L=1, single-source | 9 | `figure5/{a_L16,b_L1}_{aperiodic,periodic_Ng1,periodic_Ng1_wo_depletion,periodic_Ng4,periodic_Ng4_wo_depletion}.csv` |
| Fig. 6(a) L=16 / 6(b) L=1, multi-source | 10 | `figure6/{a_L16,b_L1}_{aperiodic,periodic_Ng1,periodic_Ng4}.csv` |
| Fig. 7, RL vs DFSA-Schoute vs CMEBE | 10 | `figure7/{recurrent_ppo,dfsa_schoute,cmebe}.csv` |
| Fig. 8, resource efficiency vs N_tot (×10³) | 11 | `figure8/{pfsa_L1,pfsa_L8,pfsa_L32,recurrent_ppo}.csv` |

Method (`scripts/digitize_aperiodic_figures.py`):

- The figures are MATLAB vector graphics inside the PDF. No pixel tracing is involved.
- `mutool draw -F svg` converts each page to SVG. The stroked paths are then mapped to page coordinates.
- **Axes:** each axes box is found from its dark frame (`#262626`).
- **Calibration:** the light-grey gridlines (`#dfdfdf`) sit exactly at the printed tick values, so the data mapping is a least-squares fit of gridline positions to tick values. Tick values were read from the rendered figures.
- **Uncertainty:** the maximum fit residual for each panel is stored in `calibration.json`. All residuals are at most 0.003 axis units, which is negligible compared with the line width.
- **Curve identity:** curves are identified by MATLAB's default colour order, matched against the legend.
- The longest polyline of each colour inside the box is the data curve. The two-point line of the same colour is the legend sample.
- **Fig. 5:** the periodic curves end at 99.1–99.9% at 1200 s because the paper's x-axis stops at 1200 s.

## Tables

- `table4_depletion.csv`: Table IV, mean mid-round depletion events per episode (single-source).
- `table5_identification_time.csv`: Table V, mean total identification time in seconds.
- `table6_alpha.csv`: Table VI, alpha sweep at N_tot = 15000 (time in seconds, resource efficiency in %).
- `scalar_targets.json`: values stated in the text (timing oracles, Lmax, N_eff and type shares, the P_harv < P_sl share, T99 reductions, N_g = 4 group populations, the RL-vs-CMEBE gain).

## Calibration notes

Simulator parameters are never fitted to these y-values. The two named assumptions that were checked against reported paper statistics are documented in `app/aperiodic_simulator/core/config.py` (`Assumptions`):

- `uplink_offset_db = -5.6`: the residual uplink budget term. Type 1 and type 2a coverage each independently imply about −5.6 dB.
- `harvest_during_monitor = False`: the DCM model of [19]. It reproduces the multi-source N_g = 4 first-catch group populations.
