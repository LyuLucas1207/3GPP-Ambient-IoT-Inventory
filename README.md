# 3GPP-Ambient-IoT-Inventory

**System-level simulators** for 3GPP Ambient IoT inventory: batteryless devices harvest RF energy, and a reader identifies them with paging and CBRA (Msg1–Msg3). The repo holds two separate engines, one per paper:

| Paper | Engine | API | Page |
| --- | --- | --- | --- |
| *Fast Inventory … Device Unavailability Due to Energy Harvesting* (periodic paging, EM/DCM) | `Implements/backend/app/simulator/` | `/api/simulator/...` | `/periodic-paging` |
| *3GPP Ambient IoT Inventory with Aperiodic Paging* (Kota et al.) | `Implements/backend/app/aperiodic_simulator/` | `/api/aperiodic-simulator/...` | `/aperiodic-paging` |

`/api/health` is the only shared endpoint. `Implements/backend/app/common/` holds only pure utilities (RF unit conversion, harvester efficiency, inventory-curve metrics). The legacy "EM" strategy is **not** the aperiodic-paging paper's protocol. For the aperiodic paper see [Aperiodic-paging paper](#aperiodic-paging-paper) and [Docs/APERIODIC_MODEL.md](./Docs/APERIODIC_MODEL.md).

The first engine provides a **preliminary reproduction** of the periodic-paging paper's Device-1 Figure 5(b) comparison (EM, DCM 1-group, DCM 4-group). It does not claim a finished curve-for-curve reproduction until `python scripts/validate_fig5b.py` reports PASS on the scientific checks.

Canonical source for the periodic-paging paper: the **published IEEE** version (arXiv `2501.15020v1` is for discrepancy notes only):

> Fast Inventory for 3GPP Ambient IoT Considering Device Unavailability Due to Energy Harvesting

The scientific core is the Python Monte Carlo engine under `Implements/`. The React dashboard only **plays back** saved snapshots. Deleting the web UI does not change Figure 5(b).

```text
3GPP-Ambient-IoT-Inventory/   ← git repository root
├── README.md
├── .gitignore
├── docker-compose.yml
├── docker-compose.prod.yml
├── Docs/                  ← walkthrough notes (en / zh) + reproduction notes
├── Papers/                ← paper PDFs
├── Files/
└── Implements/            ← simulators (Python engines + React dashboard)
    ├── backend/
    │   ├── app/
    │   │   ├── main.py               ← FastAPI app, /api/health
    │   │   ├── routers/              ← thin HTTP layer per paper (no science)
    │   │   ├── schemas/              ← request/response models per paper
    │   │   ├── simulator/            ← periodic-paging paper engine (legacy)
    │   │   │   └── core/ physics/ protocol/ strategies/ analysis/ runtime/
    │   │   ├── aperiodic_simulator/  ← aperiodic-paging paper engine
    │   │   │   └── core/ physics/ protocol/ controllers/ rl/ analysis/ reproduction/ runtime/
    │   │   └── common/               ← pure shared utilities (rf.py, metrics.py)
    │   ├── data/                 ← reference data: data/periodic/ and data/aperiodic/
    │   ├── scripts/              ← reproduction / validation / PPO training CLIs
    │   └── tests/                ← tests/periodic/, tests/aperiodic/, tests/common/
    ├── frontend/
    └── results/               ← results/periodic/ and results/aperiodic/
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

## Aperiodic-paging paper

Engine `app/aperiodic_simulator/`, page http://localhost:3000/aperiodic-paging. On the page, **Paper configuration** (or the header button *Run paper configuration*) applies the settings of one curve of Fig. 5(a)/(b), 6(a)/(b) or 7 and runs it. The run stage at the top right animates the factory, the inventory curve and the time–frequency map of the current CBRA round. Paper Figures 4–8 and Tables IV–VI from the command line:

```bash
cd Implements/backend
source .venv/bin/activate
python scripts/reproduce_aperiodic_fig4.py
python scripts/reproduce_aperiodic_fig5.py --episodes 100      # Figure 5 + Table IV
python scripts/reproduce_aperiodic_fig6.py --episodes 100
python scripts/reproduce_aperiodic_fig7.py --episodes 100
python scripts/reproduce_aperiodic_fig8.py --episodes 100
python scripts/reproduce_aperiodic_tables.py --episodes 100    # Tables V, VI
python scripts/validate_aperiodic_paper.py                     # validation report, likely layer per miss
```

Outputs go to `Implements/results/aperiodic/`.

Recurrent PPO (sb3-contrib RecurrentPPO, Table III settings):

```bash
python backend/scripts/train_aperiodic_ppo.py --steps 1000000 --seed 42   # run from Implements/
```

The repository ships **20,480-step smoke checkpoints** for α ∈ {0, 0.25, 0.5, 0.75}. They are real trained policies with SHA-256-verified metadata, but they fall far short of the paper's 1,000,000 steps, and the API and page say so. Run the command above to replace them.

Equations, named assumptions and module map: [Docs/APERIODIC_MODEL.md](./Docs/APERIODIC_MODEL.md). Controller sources: `app/aperiodic_simulator/controllers/README.md`. PPO details: `app/aperiodic_simulator/rl/README.md`.

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

- `Implements/results/periodic/fig5b_reproduced.png`
- `Implements/results/periodic/fig5b_reproduced.csv`
- `Implements/results/periodic/fig5b_metrics.json`
- `Implements/results/periodic/fig5b_tail_diagnosis.json`
- `Implements/results/periodic/fig5b_validation.json`

Call this a Figure 5(b) **reproduction** only when validation PASS includes: 4-group T99 faster than EM, reduction in a **30–70%** band around the paper’s ~50% (an ~80% cut is not “near 50%”), 4-group T99 in [6, 16] s (paper ≈ 10 s), EM T99 in [12, 28] s (paper ≈ 20 s), DCM 1-group not a clear win vs EM, digitized-curve error reported, and multi-seed direction stable. Paper configuration uses a **fixed 3 ms** DCM ON window; experimental early-sleep is a separate checkbox, default off.

## Local development (without Docker)

Terminal 1:

```bash
cd Implements/backend
./start.sh
```

`start.sh` creates `.venv` if needed, installs `requirements.txt`, then runs Uvicorn with `--reload` on port 8000.

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

- `Implements/backend/data/periodic/fig5a_pin_cdf.csv` — Figure 5(a) $p_{\mathrm{in}}$ CDF.
- `Implements/backend/data/periodic/reference_fig5b/*.csv` — Figure 5(b) Device-1 curves (IEEE page 7). See `reference_fig5b/DIGITIZATION.md`.

### C. Reproduction assumptions (not fully specified by the paper)

- **Access probability update**: Schoute occupancy counts targeting ~1 attempt per AO, **per paging group**. Not a paper equation.
- **Aperiodic paging (EM)**: next paging as soon as the previous CBRA ends.
- **Initial energy**: default `stationary` independent cycle phase. `explicit` and `harvest_only` charging stages are experiments; charging time is **not** on the Figure 5(b) axis.
- **OFF clears DCM sync**: IC off loses the sleep timer.
- **Group id**: default `first_paging_spread` (group drawn at first detection, not paging index). Alternatives: `even_id_mod`, `random_preconfigured`, `first_paging_mod`.

See `Docs/REPRODUCTION_ASSUMPTIONS.md` and `Docs/PAPER_NOTES.md`.

## Paper walkthrough notes

English notes are under `Docs/en/`; Chinese notes are under `Docs/zh/`. Both tracks use the paper’s vocabulary (inventory, energy harvesting, EM, DCM, CBRA, AO, access probability, device grouping, Figure 5(b)).

| Path | Contents |
| --- | --- |
| [Docs/en/content.md](./Docs/en/content.md) | English index (chapters 0–97) |
| [Docs/zh/content.md](./Docs/zh/content.md) | Chinese index (chapters 0–97) |
| [Docs/en/story.md](./Docs/en/story.md) | English real-world story (factory inventory) |
| [Docs/en/chapters/](./Docs/en/chapters/) | English chapter markdown |
| [Docs/en/figures/](./Docs/en/figures/README.md) | Figure 1–5 close reading |
| [Docs/PAPER_NOTES.md](./Docs/PAPER_NOTES.md) | arXiv vs published IEEE discrepancies |
| [Docs/SIMULATION_MODEL.md](./Docs/SIMULATION_MODEL.md) | Energy, EM/DCM, and CBRA model |
| [Docs/REPRODUCTION_ASSUMPTIONS.md](./Docs/REPRODUCTION_ASSUMPTIONS.md) | Assumptions the paper does not specify |
| [Docs/APERIODIC_MODEL.md](./Docs/APERIODIC_MODEL.md) | Aperiodic-paging paper: model, assumptions, reproduction, PPO |
| `Papers/` | Paper PDFs |
| `Files/` | Supporting files |

Start from zero: [Docs/en/content.md](./Docs/en/content.md) → Preface → chapter 0.

## Acknowledgments

This work was prepared under the supervision of **Prof. Lutz Lampe**. The inventory model and Figure 5(b) follow the IEEE paper cited above; this repository is an independent implementation, not a substitute for that publication.
