# 3GPP-Ambient-IoT-Inventory

A **system-level simulator** for 3GPP Ambient IoT inventory: batteryless tags harvest RF energy, and a reader identifies them with paging and CBRA (Msg1–Msg3). This repo **implements the simulation environment** and provides a **preliminary reproduction** of the paper’s Device-1 Figure 5(b) comparison (EM, DCM 1-group, DCM 4-group). It does not claim a finished curve-for-curve reproduction until `python scripts/validate_fig5b.py` reports PASS on the scientific checks.

Canonical source: the **published IEEE** paper (arXiv `2501.15020v1` is for discrepancy notes only):

> Fast Inventory for 3GPP Ambient IoT Considering Device Unavailability Due to Energy Harvesting

The scientific core is the Python Monte Carlo engine under `Implements/`. The React dashboard only **plays back** saved snapshots. Deleting the web UI does not change Figure 5(b).

```text
3GPP-Ambient-IoT-Inventory/   ← git repository root
├── README.md
├── .gitignore
├── docker-compose.yml
├── docker-compose.prod.yml
├── Docs/                  ← paper walkthrough notes (en / zh)
├── Papers/                ← paper PDFs
├── Files/
└── Implements/            ← simulator (Python engine + React dashboard)
    ├── backend/
    ├── frontend/
    ├── docs/
    └── results/
```

## Quick start — development (hot reload)

Run from **this directory** (the repository root). There is no Compose file under `Implements/`.

```bash
docker compose up --build
```

- Frontend (Vite HMR): http://localhost:3000
- Backend (Uvicorn `--reload`): http://localhost:8000
- Health: http://localhost:8000/api/health

If Docker Hub returns `failed to fetch anonymous token` / `EOF`, wait and retry. Base images already pulled locally will be reused (`pull_policy: missing`). Dev containers run `pip install` / `npm ci` on **every start** so bind-mounted source and the frontend `node_modules` volume cannot go stale.

If you see `Bind for 0.0.0.0:8000 failed: port is already allocated`, the stack is already running. Open the URLs above; do not start a second copy. Rebuild with `docker compose down` first, then `docker compose up --build`.

Stop:

```bash
docker compose down
```

## Production demo (no hot reload)

```bash
docker compose down
docker compose -f docker-compose.prod.yml up --build
```

Open http://localhost:3000. Do not run both compose files at once; they share ports 3000 and 8000.

## Figure 5(b) simulation (preliminary reproduction)

```bash
cd Implements/backend
source .venv/bin/activate
python scripts/reproduce_fig5b.py
python scripts/diagnose_fig5b_tail.py
python scripts/validate_fig5b.py
python scripts/validate_fig5b.py --quick
python scripts/validate_fig5b.py --monte-carlo 20
python scripts/digitize_fig5b.py
python scripts/compare_assumptions.py --quick
```

or:

```bash
docker compose run --rm backend python scripts/reproduce_fig5b.py
```

Outputs:

- `Implements/results/fig5b_reproduced.png`
- `Implements/results/fig5b_reproduced.csv`
- `Implements/results/fig5b_metrics.json`
- `Implements/results/fig5b_tail_diagnosis.json`
- `Implements/results/fig5b_validation.json`

Call this a Figure 5(b) **reproduction** only when validation PASS includes: 4-group T99 faster than EM, reduction in a **30–70%** band around the paper’s ~50% (an ~80% cut is not “near 50%”), 4-group T99 in [6, 16] s (paper ≈ 10 s), EM T99 in [12, 28] s (paper ≈ 20 s), DCM 1-group not a clear win vs EM, digitized-curve error reported, and multi-seed direction stable. Paper configuration uses a **fixed 3 ms** DCM ON window; experimental early-sleep is a separate checkbox, default off.

## Local development (without Docker)

Terminal 1:

```bash
cd Implements/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Terminal 2:

```bash
cd Implements/frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`.

Tests:

```bash
cd Implements/backend
source .venv/bin/activate
pytest
```

Frontend:

```bash
cd Implements/frontend
npm run lint
npm run build
```

## What is simulated

- RF energy harvesting $P_{\mathrm{eh}}=p_{\mathrm{in}}\,\xi(p_{\mathrm{in}})$
- Energy storage and EM / DCM state machines
- Device grouping at first detected paging (default: spread across groups; not “everyone who hears paging 0 is group 0”)
- Access-probability control from AO occupancy (Schoute / occupancy counts)
- CBRA over 8 Device-1 AOs, Msg1 collision / retry
- Inventory completion times $\rightarrow$ Figure 5(b)

Factory $(x,y)$ is **illustrative visualization**. Device $p_{\mathrm{in}}$ is sampled from the digitized Figure 5(a) CDF, not from $1/d^{2}$.

Noise, interference, and channel decoding failures are **not** modelled. Msg1 fails only on AO collision or energy depletion.

## Parameter categories

### A. Directly specified by the paper (Device 1, published Table 1)

| Quantity | Value |
| --- | --- |
| $N$ | 600 |
| $E_{\max}=E_{\mathrm{up}}$ | 500 nJ |
| $E_{\mathrm{low}}$ | 250 nJ |
| $P_{\mathrm{rx}}=P_{\mathrm{tx}}$ | 1 μW |
| $P_{\mathrm{sl}}$ | 0.1 μW |
| paging / $T_{\mathrm{pg}}$ | 1 ms / 12 ms |
| Msg1 / Msg2 / Msg3 | 0.5 / 0.5 / 3 ms |
| $T_{\mathrm{on}}^{\mathrm{timer}}$ / $T_{\mathrm{on}}^{\mathrm{DCM}}$ | 18 ms / 3 ms |
| AOs | 4 time × 2 frequency = 8 |
| slot | 0.5 ms |

### B. Digitized from a figure

- `Implements/backend/data/fig5a_pin_cdf.csv` — Figure 5(a) $p_{\mathrm{in}}$ CDF.
- `Implements/backend/data/reference_fig5b/*.csv` — Figure 5(b) Device-1 curves (IEEE page 7). See `reference_fig5b/DIGITIZATION.md`.

### C. Reproduction assumptions (not fully specified by the paper)

- **Access probability update**: Schoute occupancy counts targeting ~1 attempt per AO, **per paging group**. Not a paper equation.
- **Aperiodic paging (EM)**: next paging as soon as the previous CBRA ends.
- **Initial energy**: default `stationary` independent cycle phase. `explicit` and `harvest_only` charging stages are experiments; charging time is **not** on the Figure 5(b) axis.
- **OFF clears DCM sync**: IC off loses the sleep timer.
- **Group id**: default `first_paging_spread` (group drawn at first detection, not paging index). Alternatives: `even_id_mod`, `random_preconfigured`, `first_paging_mod`.

See `Implements/docs/REPRODUCTION_ASSUMPTIONS.md` and `Implements/docs/PAPER_NOTES.md`.

## Paper walkthrough notes

English notes are under `Docs/en/`; Chinese notes are under `Docs/zh/`. Both tracks use the paper’s vocabulary (inventory, energy harvesting, EM, DCM, CBRA, AO, access probability, device grouping, Figure 5(b)).

| Path | Contents |
| --- | --- |
| [Docs/en/content.md](./Docs/en/content.md) | English index (chapters 0–97) |
| [Docs/zh/content.md](./Docs/zh/content.md) | Chinese index (chapters 0–97) |
| [Docs/en/story.md](./Docs/en/story.md) | English real-world story (factory inventory) |
| [Docs/en/chapters/](./Docs/en/chapters/) | English chapter markdown |
| [Docs/en/figures/](./Docs/en/figures/README.md) | Figure 1–5 close reading |
| `Papers/` | Paper PDFs |
| `Files/` | Supporting files |

Start from zero: [Docs/en/content.md](./Docs/en/content.md) → Preface → chapter 0.

## Acknowledgments

This work was prepared under the supervision of **Prof. Lutz Lampe**. The inventory model and Figure 5(b) follow the IEEE paper cited above; this repository is an independent implementation, not a substitute for that publication.
