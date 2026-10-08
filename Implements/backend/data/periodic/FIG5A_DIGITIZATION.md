# Figure 5(a) \(p_{\mathrm{in}}\) CDF digitization

Canonical source: published IEEE PDF

`Papers/Fast_Inventory_for_3GPP_Ambient_IoT_Considering_Device_Unavailability_Due_to_Energy_Harvesting.pdf`

page 7, Figure 5(a) “CDF of A-IoT device received power”.

## Method

Rendered page 7 at 300 dpi. Read axis limits and grid intersections from the printed figure (not from Figure 5(b)).

- Horizontal: \(p_{\mathrm{in}}\) from \(-40\) to \(-5\) dBm, 5 dB ticks.
- Vertical: CDF from 0 to 1, 0.1 ticks.
- Paper excludes devices with \(p_{\mathrm{in}} < -36\) dBm; the curve is taken to start at \(-36\) dBm.

## Anchor points read from the figure

| \(p_{\mathrm{in}}\) (dBm) | CDF (approx.) |
| ---: | ---: |
| −36 | 0.00 |
| −35 | 0.08–0.12 |
| −30 | 0.50 (median) |
| −25 | 0.78–0.85 |
| −20 | 0.90 |
| −15 | 0.96 |
| −7 to −6 | 1.00 |

Grid-intersection error is about ±0.5 dB / ±0.03 in CDF. Points in `fig5a_pin_cdf.csv` interpolate these anchors. They are **not** fitted to Figure 5(b).

## Previous CSV (incorrect)

Median was −26.4 dBm and \(F(-30.5\,\mathrm{dBm})\approx 0.25\), which is a 3–4 dB right shift relative to the published figure.
