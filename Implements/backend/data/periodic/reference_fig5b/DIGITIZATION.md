# Figure 5(b) Device-1 digitization

Canonical source: published IEEE PDF

`Papers/Fast_Inventory_for_3GPP_Ambient_IoT_Considering_Device_Unavailability_Due_to_Energy_Harvesting.pdf`

IEEE Communications Standards Magazine, December 2025, **page 7**, Figure 5(b)
“ratio of A-IoT devices that have successfully been inventoried in time (device 1)”.

The arXiv 6-page preprint is **not** used. These CSVs are **not** copied from the simulator.

## Image extraction

- Rendered the embedded raster on page 7 (stacked panels a, b, c).
- Panel (b) crop in that raster: rows **888–1595** (0-based), full width 1002 px.
- Script: `python scripts/digitize_fig5b.py`

## Axis calibration (panel-b crop pixels)

| Spine | Pixel | Data |
| --- | --- | --- |
| Left / t = 0 | x = 110 | 0 ms |
| Right / t max | x = 936 | 2.5×10⁴ ms = 25000 ms |
| Bottom / 0 % | y = 662 | 0 % |
| Top / 100 % | y = 22 | 100 % |

x ticks on the printed figure are 0, 0.5, 1.0, 1.5, 2.0, 2.5 with a ×10⁴ ms scale (EM T99 mark at 2.0 = 20 s matches the text).

y ticks 0, 10, …, 100. Light horizontal grid lines sit ~64–68 px apart; the 90 % grid is near row 87.

Linear map:

```text
time_ms    = (x - 110) / (936 - 110) * 25000
ratio_pct  = (662 - y) / (662 -  22) * 100
```

## Curve identification

Hue of non-gray, non-white strokes inside the axes:

| Strategy | Colour on the figure | Hue window |
| --- | --- | --- |
| EM, aperiodic paging | purple | ~0.72–0.95 |
| DCM, 1 group | orange | ~0.03–0.14 |
| DCM, 4 groups | green | ~0.28–0.50 |

Each curve is followed left→right: in every column the matching-colour cluster nearest the previous row is kept (so the trace does not jump to the legend or another curve).

## Uncertainty

- Line thickness 2–4 px → about **±0.6 %** in ratio, **±150 ms** in time.
- Legend sits inside the top of the axes and overlaps the 95–100 % band. Points above ~95 % have **±2 %** extra vertical error, especially the green plateau.
- Anti-aliased pale strokes near 100 % can break the trace before 25 s; the CSV stops at the last confident pixel rather than inventing a tail.
- Grid-intersection check vs paper text: EM T99 near 2.0×10⁴ ms; 4-group T99 near 1.0×10⁴ ms.
- This digitizer run (panel-b crop, Y1=22): EM T50/T90 ≈ 1.5 s / 9.4 s, trace ends ~97 % at 17 s (99 % tail too faint). DCM 1-group T50/T90 ≈ 2.3 s / 11.6 s, same faint 99 % tail. DCM 4-group T50/T90/T99 ≈ 1.1 s / 2.5 s / 5.2 s. The 4-group 95–100 % band overlaps the in-axes legend, so pixel T99 is earlier than the paper’s written ≈10 s; treat 5–12 s as the uncertainty interval for 4-group T99 from pixels. Paper-stated T99 anchors remain 20 s (EM) and 10 s (4-group).

Do **not** replace missing tail pixels with the simulator curve.
