# Aperiodic-paging controllers

Every controller sees only the Eq. (5) round observation
`(S1, S2a, S2b, I, C, L_prev, p_prev)` plus `decoded = L·F − I − C`, which
is derived from the same observation. True backlog, energies, C2 and the
physical AO occupancy are never passed in (`base.py`).

| Module | Paper role | Adapts | Source |
|---|---|---|---|
| `pfsa_pze.py` | Figs. 5/6 (both protocols), PFSA baselines of Fig. 8 / Table V | p (L fixed) | Kodialam & Nandagopal, MobiCom 2006 (zero estimator) |
| `grouped.py` | periodic baseline with N_g > 1: one PZE state per paging group | p per group | engine assumption (avoids cross-group estimator oscillation) |
| `dfsa_schoute.py` | Fig. 7 baseline "DFSA-Schoute" | L only, p = 1 | Schoute, IEEE Trans. Commun. 31(4), 1983 — paper ref. [48] |
| `cmebe.py` | Fig. 7 baseline "CMEBE" | L only, p = 1 | Li & Wang, IEEE Commun. Lett. 15(3), 2011 — paper ref. [49] |
| `recurrent_ppo.py` | Figs. 7/8, Tables V/VI "RL" | L and p | paper Sec. IV / Table III |

## Equations

**PZE**: `n̂ = ln(max(I,1)/N) / ln(1 − p/N)`, `N = L·F`;
`p_next = min(1, N / (n̂ − S))`, with `p_next = 1` when `I = N` or `n̂ − S ≤ N`.

**DFSA-Schoute**: the backlog after the frame is `B̂ = 2.39·C`, where
2.39 = (1 − e⁻¹)/(1 − 2e⁻¹) is the mean collision multiplicity at load 1. The
next frame has `N = B̂` AOs, so `L = ceil(B̂ / F)` clipped to `[1, L_max]`.

**CMEBE**: `(n̂, α̂) = argmin (E[e]−I)² + (E[s]−decoded)² + (E[c]−C)²` with
`E[e] = N(1−1/N)^n`, `A = n(1−1/N)^(n−1)`, `B = N − E[e] − A`,
`E[s] = A + αB` and `E[c] = (1−α)B`. For fixed n, α has the closed form
`(s − A + B − c)/(2B)`, so the search is a 1-D scan over n. The backlog is
`n̂ − S`, and the capture-aware frame is `N* = (1 − α̂)·backlog`, because
x e⁻ˣ + α(1 − e⁻ˣ − x e⁻ˣ) is maximised at x = 1/(1−α). That gives
`L = ceil(N*/F)` clipped to `[1, L_max]`.

Per the paper (Sec. V-C), both DFSA baselines "adapt the number of access
resources based on the estimated backlog but do not control the access
probability", and all Figure 7 methods start from `L₁ = 1`.

## Assumptions

* All-collided frames are ambiguous. PZE floors I to 1. CMEBE scans n up to
  `s + 2c + 4·L_max·F`; any estimate that large already maps to `L_max`, so
  the bound never changes the action.
* `decoded` includes captured AOs, as in the reader's view. Capture is what
  CMEBE models and Schoute ignores.
