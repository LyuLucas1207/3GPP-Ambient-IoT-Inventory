# LutzLampe

Repository for Lutz Lampe Ambient IoT thesis prep **and** the Figure 5(b) simulation environment.

Canonical paper (published IEEE version; arXiv `2501.15020v1` is for discrepancy notes only):

> Fast Inventory for 3GPP Ambient IoT Considering Device Unavailability Due to Energy Harvesting

The scientific core is a Python simulator under `Implements/`. The React page only **plays back** saved snapshots. Deleting the web UI does not change Figure 5(b).

```text
LutzLampe/                 ← git repository root
├── README.md
├── .gitignore
├── docker-compose.yml
├── docker-compose.prod.yml
├── Docs/                  ← lecture notes
├── Papers/                ← paper PDFs
├── Files/                 ← CV / other materials
└── Implements/            ← simulator (Python engine + React dashboard)
    ├── backend/
    ├── frontend/
    ├── docs/
    └── results/
```

## Quick start — development (hot reload)

Run from **this directory** (`LutzLampe/`). There is no Compose file under `Implements/`.

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

## Reproduce Figure 5(b) only

```bash
cd Implements/backend
source .venv/bin/activate
python scripts/reproduce_fig5b.py
```

or:

```bash
docker compose run --rm backend python scripts/reproduce_fig5b.py
```

Outputs:

- `Implements/results/fig5b_reproduced.png`
- `Implements/results/fig5b_reproduced.csv`
- `Implements/results/fig5b_metrics.json`

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

## What is simulated

- RF energy harvesting \(P_{eh}=p_{in}\xi(p_{in})\)
- Energy storage and EM / DCM state machines
- Device grouping from first detected paging
- Access-probability control from AO occupancy
- CBRA over 8 Device-1 AOs, Msg1 collision / retry
- Inventory completion times \(\rightarrow\) Figure 5(b)

Factory \((x,y)\) is **illustrative visualization**. Device \(p_{in}\) is sampled from the digitized Figure 5(a) CDF, not from \(1/d^2\).

## Parameter categories

### A. Directly specified by the paper (Device 1, published Table 1)

| Quantity | Value |
| --- | --- |
| \(N\) | 600 |
| \(E_{\max}=E_{\mathrm{up}}\) | 500 nJ |
| \(E_{\mathrm{low}}\) | 250 nJ |
| \(P_{rx}=P_{tx}\) | 1 μW |
| \(P_{sl}\) | 0.1 μW |
| paging / \(T_{pg}\) | 1 ms / 12 ms |
| Msg1 / Msg2 / Msg3 | 0.5 / 0.5 / 3 ms |
| \(T_{\mathrm{on}}^{\mathrm{timer}}\) / \(T_{\mathrm{on}}^{\mathrm{DCM}}\) | 18 ms / 3 ms |
| AOs | 4 time × 2 frequency = 8 |
| slot | 0.5 ms |

### B. Digitized from a figure

- `Implements/backend/data/fig5a_pin_cdf.csv` — Figure 5(a) \(p_{in}\) CDF.

### C. Reproduction assumptions (not fully specified by the paper)

- **Access probability update**: idle-AO Poisson load estimate targeting ~1 attempt per AO.
- **Aperiodic paging (EM)**: next paging as soon as the previous CBRA ends.
- **Initial energy**: stationary EM/DCM cycle phase from a shared `phase_u`.
- **OFF clears DCM sync**: IC off loses the sleep timer.
- **Group id**: `device_id % N_groups` (even split; first paging only syncs).

See `Implements/docs/REPRODUCTION_ASSUMPTIONS.md` and `Implements/docs/PAPER_NOTES.md`.

## Lecture notes

| Path | Contents |
| --- | --- |
| [Docs/content.md](./Docs/content.md) | Index (chapters 0–97) |
| [Docs/chapters/](./Docs/chapters/) | Chapter markdown |
| [Docs/figures/](./Docs/figures/README.md) | Figure 1–5 close reading |
| `Papers/` | Paper PDFs |
| `Files/` | CV and other materials |

Start from zero: [Docs/content.md](./Docs/content.md) → Preface → chapter 0.
