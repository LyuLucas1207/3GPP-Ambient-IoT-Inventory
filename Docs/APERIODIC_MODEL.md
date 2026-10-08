# Aperiodic-paging paper: model, assumptions, reproduction

Paper: *3GPP Ambient IoT Inventory with Aperiodic Paging* (Kota et al., `Papers/`).
Engine: `Implements/backend/app/aperiodic_simulator/`. API: `/api/aperiodic-simulator/...`.
Page: `/aperiodic-paging`.

The legacy simulator of *Fast Inventory … Energy Harvesting* stays in
`backend/app/simulator/` (`/api/simulator/...`, `/periodic-paging`). Its "EM"
strategy is **not** this paper's aperiodic protocol. The two engines share only
pure utilities in `backend/app/common/`:

- `rf.py`: dBm ↔ W conversion and the harvester efficiency curve
- `metrics.py`: inventory curve, first crossing time, MAE/RMSE

The FastAPI routers in `backend/app/routers/` only validate requests and call
`runtime/service.py` / `runtime/jobs.py`; no science lives there.

## Package layout

Paths relative to `backend/app/aperiodic_simulator/`.

| Module | Content |
|---|---|
| `core/config.py`, `core/states.py` | `SystemParams` (Table II), `Assumptions` (named open choices), `EpisodeConfig`, state enums |
| `core/timing.py` | message durations from bits/R, `T_EI(L)`, periodic interval, aperiodic round length |
| `core/simulation.py`, `core/trace.py` | continuous-time, round-driven episode with lazy DCM evaluation; device traces |
| `core/runner.py`, `core/batch.py` | one episode with a controller; seeded multi-process batches |
| `physics/device_types.py`, `physics/energy.py` | Type 1 / 2a / 2b parameters, `E_base`, `E_scale`, `Lmax` (Eq. 3) |
| `physics/layout.py`, `physics/channel.py`, `physics/harvesting.py` | factory, 18 BSs, 3GPP InF-DH path loss, coverage filter, single-/multi-source P_in |
| `physics/impairments.py` | capture (6 dB), missed detection, false alarm |
| `protocol/paging_aperiodic.py`, `protocol/paging_periodic.py` | the two protocols as objects driven by `core.simulation.Episode` |
| `protocol/cbra.py`, `protocol/grouping.py` | AO occupancy, Msg2/Msg3 allocation; paging groups |
| `controllers/` | PFSA/PZE, grouped PZE, DFSA-Schoute, CMEBE, Recurrent PPO adapter (see its README) |
| `rl/` | Gymnasium env, transforms, training, checkpoints (see its README) |
| `analysis/metrics.py`, `analysis/reference_targets.py` | §28 metrics; paper reference data and figure captions |
| `reproduction/reproduce.py`, `reproduction/controller_reproduce.py`, `reproduction/presets.py` | Figures 4–8 and Tables IV–VI |
| `runtime/service.py`, `runtime/jobs.py`, `runtime/run_store.py` | API payloads, background jobs, run cache |

The legacy engine `backend/app/simulator/` uses the same split: `core/` (config,
scenario, warm-up, simulation), `physics/` (channel, energy, device), `protocol/`
(paging, CBRA, grouping, access control, reader), `strategies/` (EM, DCM),
`analysis/` (metrics, Fig. 5(b) validation) and `runtime/` (run store).

One engine step is one CBRA round (paging → Msg1 → EI → Msg2 → Msg3), not a 0.5 ms tick.

## Equations implemented

- **Round timing**
  - Every duration is bits/R.
  - The EI stage is always included: `T_EI(L) = L·F·B_EI / R`.
  - Periodic interval: `T_page + L·T_msg1 + T_EI(L) + 0.5·L·F·(T_msg2 + T_msg3/F)`. This gives 82.00 ms at L=1 and 1089.14 ms at L=16, both tested.
  - Aperiodic round: Msg2 slots follow the decoded Msg1 count K, and Msg3 uses `ceil(K/F)` slots.
- **Energy**: `E_worst(L) = E_base + L·E_scale ≤ E_up − E_low`, which gives the global `Lmax = 83`.
  - Type 1 monitors with its receiver (P_rx).
  - Types 2a/2b monitor with the wake-up receiver (P_wurx).
- **States**
  - The **proposed aperiodic protocol** has no cross-round synchronization. Rejection, collision or failure sends the device OFF (then DCM recharge); success sends it to DONE.
  - In the **periodic baseline**, a device is assigned its group at first catch. After a failure it sleeps synchronized until its group's next page. Depletion sends it OFF and it reacquires through DCM.
  - Mid-round depletion is enforced per stage. `would_deplete_by_stage` is a diagnostic, and the "w/o depletion" curves disable enforcement.
- **CBRA**: the periodic baseline reserves `0.5·L·F` Msg2/Msg3 resources (unused ones are counted as wasted). The aperiodic protocol allocates dynamically.
- **PFSA/PZE**: `n̂ = ln(I/N)/ln(1−p/N)` and `p = min(1, N/(n̂ − S))`, with `p = 1` if all AOs are idle or the backlog is ≤ N. For periodic N_g > 1 there is one estimator per group.
- **DFSA-Schoute**: backlog `2.39·C`, `L = ceil(backlog/F)`, p = 1.
- **CMEBE**: capture-aware minimum-error estimate of (n, α). Frame `(1−α̂)(n̂−S)`, `L = ceil(·/F)`, p = 1.
- **RL**
  - State Eq. (5): `[S1, S2a, S2b, I, C, L_prev, p_prev]`.
  - Actions Eqs. (6)–(7): `L = min(ceil(m·L_prev), 83)`, `p = clip(q·p_prev)`, with m ∈ [0.25, 10] and q ∈ [0.1, 10].
  - Reward Eq. (8): `((1−α)·S·t_S − α·C2·t_C)/T_round`.
- **Total identification time** Eq. (4): `T_total_s` is the time until all N_eff devices are identified. It is None when an episode is truncated, and batches report `episodes_incomplete`.

## Named assumptions (open in the paper)

All of them live in `config.Assumptions` and are returned by `/config/paper`.
The two with numeric effect were checked against reported paper statistics,
never against curve shapes:

- `uplink_offset_db = −5.6`: the residual uplink-budget term. Type 1 and type 2a coverage each independently imply about −5.6 dB.
- `harvest_during_monitor = False`: the DCM model of [19]. It reproduces the paper's N_g = 4 groups (69.5/23.9/4.8/1.8 % vs 69.5/23.9/4.7/1.9 %).

Others:

- stationary initial DCM phase
- energy capped at E_up
- false alarm observed as a collision
- capture rule: strongest ≥ 6 dB over the sum of the interferers
- PZE all-collided idle floor 1
- `p_floor = 1e-4`
- periodic Msg3 time-equivalent `K/F`

## Reproduce

```bash
cd Implements/backend && source .venv/bin/activate
python scripts/reproduce_aperiodic_fig4.py                     # CDF of P_in, N_eff, type shares
python scripts/reproduce_aperiodic_fig5.py --episodes 100      # + Table IV
python scripts/reproduce_aperiodic_fig6.py --episodes 100
python scripts/reproduce_aperiodic_fig7.py --episodes 100      # needs the alpha=0.5 checkpoint for RL
python scripts/reproduce_aperiodic_fig8.py --episodes 100
python scripts/reproduce_aperiodic_tables.py --episodes 100    # Tables V and VI
python scripts/validate_aperiodic_paper.py                     # §30 report
```

- Outputs go to `Implements/results/aperiodic/<figure>/`: JSON, CSV and PNG with the paper curves dashed.
- The validation report goes to `Implements/results/aperiodic/validation/validation_report.md`.
- The page's "Paper reproduction" panel loads these cached outputs, or recomputes them as a background job.
- A cached result is never overwritten by a run with fewer episodes.

Reference data (vector-extracted figure curves and the tables) is in
`backend/data/aperiodic/`. It is used for validation and overlays only.

## Recurrent PPO

```bash
python backend/scripts/train_aperiodic_ppo.py --steps 1000000 --seed 42          # paper setting (alpha 0.5)
python backend/scripts/train_aperiodic_ppo.py --steps 1000000 --seed 42 --alpha 0.25
```

- The shipped checkpoints are **20,480-step smoke checkpoints** (seed 42, α ∈ {0, 0.25, 0.5, 0.75}). They are real RecurrentPPO policies with SHA-256-verified metadata, but they are not the paper's 1,000,000-step policy.
- The API (`/ppo/status`, simulation warnings), the page and the validation report all state this.
- Retraining with the command above replaces them.
- See `backend/app/aperiodic_simulator/rl/README.md`.
