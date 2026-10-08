# Cursor implementation prompt — fully separate the legacy periodic-paging simulator and the new aperiodic-paging paper, with complete recurrent PPO

You are working inside the existing `Implements/` repository. The repository already contains a working reproduction of the earlier paper **Fast Inventory for 3GPP Ambient IoT Considering Device Unavailability Due to Energy Harvesting**. That implementation must remain scientifically stable. A second source paper, **3GPP Ambient IoT Inventory with Aperiodic Paging**, must now be implemented as a separate simulator and a separate frontend page.

This is a **full implementation task**, not a UI mockup and not a partial protocol demo. Implement the complete new-paper simulator, the protocol-level comparisons, the controller-level comparisons, and the **real recurrent PPO training/inference pipeline**. Do not substitute PPO with a hand-written heuristic and do not label a rule-based controller as PPO.

---

# 1. Non-negotiable final architecture

The two papers must be separated at all major boundaries:

- separate frontend page routes;
- separate frontend API clients/hooks/types;
- separate FastAPI routers and request/response schemas;
- separate backend scientific simulator packages;
- separate result/reproduction commands;
- separate paper-specific state machines and configs.

At the same time, **paper-agnostic, stateless utility functions may and should be shared** when their semantics are truly identical. Do not duplicate generic RF conversion or generic curve metrics merely because there are two simulators.

The target architecture is:

```text
Implements/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── simulator.py                 # legacy-paper HTTP API only
│   │   │   └── aperiodic_simulator.py       # new-paper HTTP API only
│   │   └── schemas/
│   │       ├── simulator.py                 # legacy request/response models
│   │       └── aperiodic_simulator.py       # new-paper request/response models
│   │
│   ├── common/                              # ONLY paper-independent utilities
│   │   ├── __init__.py
│   │   ├── rf.py
│   │   ├── metrics.py
│   │   ├── rng.py                           # if useful
│   │   └── ...                              # only if genuinely common
│   │
│   ├── simulator/                           # EXISTING legacy scientific engine
│   │   ├── config.py
│   │   ├── channel.py
│   │   ├── energy.py
│   │   ├── cbra.py
│   │   ├── paging.py
│   │   ├── grouping.py
│   │   ├── simulation.py
│   │   └── ...
│   │
│   ├── aperiodic_simulator/                 # NEW scientific engine
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── device_types.py
│   │   ├── layout.py
│   │   ├── channel.py
│   │   ├── harvesting.py
│   │   ├── energy.py
│   │   ├── states.py
│   │   ├── timing.py
│   │   ├── cbra.py
│   │   ├── impairments.py
│   │   ├── paging_periodic.py
│   │   ├── paging_aperiodic.py
│   │   ├── grouping.py
│   │   ├── metrics.py
│   │   ├── simulation.py
│   │   ├── reference_targets.py
│   │   ├── run_store.py                     # only if new trace model differs
│   │   ├── controllers/
│   │   │   ├── base.py
│   │   │   ├── pfsa_pze.py
│   │   │   ├── dfsa_schoute.py
│   │   │   ├── cmebe.py
│   │   │   └── recurrent_ppo.py
│   │   └── rl/
│   │       ├── env.py
│   │       ├── policy.py                    # only if custom policy wrapper needed
│   │       ├── train.py
│   │       ├── evaluate.py
│   │       ├── checkpoint.py
│   │       └── checkpoints/
│   │
│   ├── scripts/
│   │   ├── ...legacy scripts...
│   │   ├── reproduce_aperiodic_fig4.py
│   │   ├── reproduce_aperiodic_fig5.py
│   │   ├── reproduce_aperiodic_fig6.py
│   │   ├── reproduce_aperiodic_fig7.py
│   │   ├── reproduce_aperiodic_fig8.py
│   │   ├── reproduce_aperiodic_tables.py
│   │   ├── train_aperiodic_ppo.py
│   │   └── validate_aperiodic_paper.py
│   └── tests/
│       ├── ...existing legacy tests...
│       └── aperiodic/
│           └── ...new-paper tests...
│
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── pages/
│       │   ├── PeriodicPagingPage.tsx       # renamed/adapted current SimulatorPage
│       │   ├── AperiodicPagingPage.tsx      # new paper UI
│       │   └── GlossaryPage.tsx
│       ├── api/
│       │   ├── http.ts                      # shared HTTP helper if useful
│       │   ├── simulator.ts                 # legacy API only
│       │   └── aperiodicSimulator.ts        # new API only
│       ├── hooks/
│       │   ├── usePeriodicSimulation.ts
│       │   └── useAperiodicSimulation.ts
│       ├── types/
│       │   ├── simulation.ts                # legacy types
│       │   └── aperiodicSimulation.ts       # new-paper types
│       ├── components/
│       │   ├── ui/                          # already shared
│       │   ├── ...existing legacy components...
│       │   └── aperiodic/                   # new-paper-specific inspectors/controls
│       └── ...shared plot/theme/i18n utilities...
│
└── results/
    ├── ...existing legacy files remain valid...
    └── aperiodic_paging/
        ├── figure4/
        ├── figure5/
        ├── figure6/
        ├── figure7/
        ├── figure8/
        ├── tables/
        └── validation/
```

The exact filenames can vary slightly if there is a strong implementation reason, but the **scientific engines, API namespaces, frontend routes, hooks, and types must remain clearly separated**.

---

# 2. Frontend routes must be separate

Use these canonical routes:

```text
/                     -> redirect to /periodic-paging
/periodic-paging      -> legacy paper / existing simulator
/aperiodic-paging     -> new aperiodic-paging paper simulator
/glossary              -> glossary
```

Update `frontend/src/App.tsx` accordingly.

The legacy page should be renamed from `SimulatorPage` to `PeriodicPagingPage` unless there is a compelling reason not to. Preserve its current scientific behavior and visual capabilities.

Add a visible page-level navigation control in the header, for example:

```text
[ Periodic Paging Paper ]   [ Aperiodic Paging Paper ]
```

This is navigation between two paper simulators, **not** merely a `paging_mode` switch in one giant page.

The new `/aperiodic-paging` page may still contain an internal **Periodic baseline vs Aperiodic proposed protocol** selector, because the new paper itself compares those two protocols. That internal selector must use the **new-paper engine**, not the old legacy engine.

---

# 3. HTTP API namespaces must also be separate

Keep `/api/health` as the only global endpoint.

All legacy simulator HTTP requests must use the `/api/simulator/...` namespace.

Canonical legacy endpoints:

```text
GET  /api/simulator/about
GET  /api/simulator/config/paper
GET  /api/simulator/config/fig5b-reference
POST /api/simulator/simulate
GET  /api/simulator/runs/{run_id}/strategies/{strategy}/devices/{device_id}/trace
```

All new-paper requests must use `/api/aperiodic-simulator/...`.

Canonical new endpoints should include at least:

```text
GET  /api/aperiodic-simulator/about
GET  /api/aperiodic-simulator/config/paper
POST /api/aperiodic-simulator/simulate
POST /api/aperiodic-simulator/reproduce/figure4
POST /api/aperiodic-simulator/reproduce/figure5
POST /api/aperiodic-simulator/reproduce/figure6
POST /api/aperiodic-simulator/reproduce/figure7
POST /api/aperiodic-simulator/reproduce/figure8
POST /api/aperiodic-simulator/reproduce/tables
GET  /api/aperiodic-simulator/ppo/status
GET  /api/aperiodic-simulator/runs/{run_id}/controllers/{controller}/devices/{device_id}/trace
```

The exact reproduction endpoint design may be consolidated into one endpoint with a typed `target` field if that is cleaner, but all new-paper endpoints must stay under `/api/aperiodic-simulator/`.

The PPO training pipeline must exist as a backend/CLI capability. It is acceptable and preferable for the expensive 1,000,000-step training job to be launched by CLI rather than holding an HTTP request open for hours. If an HTTP training endpoint is added, it must be a real job/status model, not a blocking fake endpoint.

Recommended CLI:

```bash
python backend/scripts/train_aperiodic_ppo.py --steps 1000000 --seed 42
```

Recommended status endpoint:

```text
GET /api/aperiodic-simulator/ppo/status
```

which returns, for example:

```json
{
  "available": true,
  "checkpoint": "...",
  "training_steps": 1000000,
  "architecture": "LSTM(128)+MLP(128,128)",
  "trained_scenario": "multi_source",
  "sha256": "..."
}
```

The frontend must never call the old un-namespaced endpoints once this refactor is complete. Temporary compatibility aliases are acceptable only during migration; they are not the canonical API and must not be used by the final frontend or tests.

`backend/app/main.py` should end up conceptually like:

```python
app.include_router(simulator_router, prefix="/api/simulator")
app.include_router(aperiodic_router, prefix="/api/aperiodic-simulator")
```

---

# 4. What may be shared, and what must NOT be shared

Yes, there are real common functions in the current repository that should be shared.

## 4.1 Backend functions that are good candidates for `backend/common/`

The existing legacy `simulator/channel.py` contains pure utilities whose mathematical meaning is the same in both papers:

```python
dbm_to_watts(...)
watts_to_dbm(...)
conversion_efficiency(...)
harvest_power_w(...)
```

Move or extract these into:

```text
backend/common/rf.py
```

The new paper explicitly reuses the earlier paper's RF-to-DC harvesting model, so these functions are appropriate shared utilities.

To avoid breaking old imports/tests, either:

1. update all legacy imports carefully, or
2. preferably keep compatibility re-exports in `simulator/channel.py`, e.g. import these functions from `common.rf`.

The existing generic inventory-curve functions are also suitable for sharing:

```python
inventory_curve(...)
first_time_at_or_above(...)
mae_rmse(...)
```

Move/extract them into:

```text
backend/common/metrics.py
```

A generic seeded RNG/helper may also be shared if it contains no paper assumptions.

## 4.2 Backend logic that must remain paper-specific

Do **not** share these merely to reduce code duplication:

- device parameter schemas;
- device state machines;
- warmup logic;
- paging logic;
- CBRA timing;
- periodic group synchronization;
- energy-feasibility rules;
- capture/reader observation semantics;
- controller logic;
- event-loop/simulation engine;
- legacy Figure 5(a) digitized CDF sampler;
- new-paper 18-BS geometry/link budget;
- run trace models if their semantics differ.

The old and new papers use similar terminology but not identical scientific models. Shared code is allowed only when the **equations and meaning are actually identical**.

## 4.3 Frontend code that may be shared

Continue sharing generic UI infrastructure:

- `components/ui/*`;
- theme/language toggles;
- `HudDock` shell;
- Plotly wrapper;
- generic formatting/math components;
- generic HTTP error parsing via `api/http.ts`;
- generic chart primitives if they accept neutral data models.

Do not force the two pages to share one huge simulation hook or one huge union type. Use:

```text
usePeriodicSimulation.ts
useAperiodicSimulation.ts
```

and separate request/result types.

If an existing visual component can be made genuinely generic with a small adapter, reuse it. If making it generic requires dozens of `if (paper === ...)` branches, keep separate paper-specific components instead.

---

# 5. Mandatory first step before editing

1. Inspect the entire repository.
2. Run the existing backend test suite and record the baseline. The current repository is expected to have 64 passing legacy tests.
3. Run the existing frontend typecheck/build.
4. Read the new paper fully, especially Sections III–V, Table II, Table III, Figures 2–8, Appendix A, and Appendix B.
5. Create a short architecture plan before making invasive edits.
6. Do not alter legacy scientific behavior to make the new paper easier to implement.

At every major milestone rerun the full legacy tests.

---

# 6. Most important scientific distinction

The old repository already calls one legacy strategy `EM, aperiodic paging`. **That is not the new paper's proposed aperiodic paging protocol.**

Never import or expose the old `EM` strategy as the proposed method on `/aperiodic-paging`.

The new paper's proposed protocol still uses DCM to acquire paging, but failed/rejected devices do not remain aligned to future paging opportunities.

## Proposed aperiodic state machine

```text
OFF / harvest
  -> energy reaches E_up
  -> MONITOR for at most T_mon
     -> no page in T_mon
          -> OFF
     -> page detected
          -> receive page
          -> access-probability decision p_s
               -> rejected
                    -> OFF after the opportunity
               -> participates in CBRA
                    -> success
                         -> DONE
                    -> collision / missed detection / other failure
                         -> OFF
  -> harvest back to E_up
  -> monitor again and reacquire a later page from scratch
```

There is **no cross-round paging synchronization** in the proposed aperiodic protocol.

There can still be low-power waiting/sleep **inside one CBRA round** while a device waits for its assigned Msg1/Msg2/Msg3 timing.

## New-paper periodic baseline

```text
initial DCM acquisition
  -> first detected page establishes inventory synchronization
  -> assign/aligned device to a paging group
  -> inter-round synchronized SLEEP using low-power clock
  -> wake only for its scheduled paging opportunity
  -> access-probability decision / CBRA
  -> failure or access rejection keeps periodic retry behavior
  -> if energy falls below E_low, device returns OFF and must recharge
```

For new-paper grouping, use first-catch / first-detected-paging phase assignment. Do not use the legacy `first_paging_spread` behavior in paper-reproduction mode.

---

# 7. Critical notation conflict with legacy code

The old code uses `T_pg` as paging periodicity. The new paper Appendix uses `T_pg` for the paging **message duration**.

Do not reuse the old variable meaning.

Use explicit new-paper names:

```text
t_page_s
t_msg1_s
t_msg2_s
t_msg3_s
t_ei_s(L)
periodic_round_interval_s(L)
```

Never overload one value for both page duration and paging periodicity.

---

# 8. New-paper system parameters — Table II

Create a separate configuration model inside `aperiodic_simulator/config.py`. Do not mutate the legacy `SimConfig` or legacy `DeviceParams` to represent the new paper.

## Global/system values

- Factory: 120 m × 60 m
- 18 BSs on the paper/3GPP square-lattice factory layout
- one of the two centrally located BSs acts as reader
- BS height: 8 m
- device height: 1.5 m
- carrier frequency: 0.9 GHz
- path loss: 3GPP InF-DH
- polarization mismatch: 3 dB
- shadow fading margin: 4 dB
- on-object antenna penalty: 0.9 dB
- effective BS RX sensitivity: -106 dBm
- BS TX power: 33 dBm
- BS TX antenna gain: 6 dBi
- frequency resources: `F = 8`
- data rate: `R = 7 kbps`
- paging message: 80 bits
- Msg1: 38 bits
- Msg2: 88 bits
- Msg3: 144 bits
- EI overhead: 24 bits
- false alarm rate: 0.1%
- missed detection rate: 1%
- capture ratio: 6 dB
- monitoring interval `T_mon = 100 ms`
- sleep power `P_sl = 0.1 µW`
- wake-up receiver power for type 2a/2b: `1 µW`

## Device type 1

- RX sensitivity: -36 dBm
- TX/RX power: 1 µW
- `E_up = 5 µJ`
- `E_low = 2.5 µJ`
- backscatter loss: 6 dB

## Device type 2a

- RX sensitivity: -40 dBm
- TX power: 200 µW
- RX power: 50 µW
- `E_up = 25 µJ`
- `E_low = 12.5 µJ`
- backscatter loss: 6 dB
- backscatter gain: 10 dB
- use WuRX for paging monitoring

## Device type 2b

- RX sensitivity: -70 dBm
- TX power consumption: 200 µW
- RX power consumption: 50 µW
- active transmit power: -20 dBm
- `E_up = 25 µJ`
- `E_low = 12.5 µJ`
- use WuRX for paging monitoring

For protocol-level Figures 5 and 6:

```text
N_tot = 15000
```

with an even pre-coverage split across type 1, type 2a, and type 2b.

---

# 9. Message timing and hard timing oracles

Compute message durations from bits and data rate, not rounded constants:

```python
t_page_s = 80 / 7000
t_msg1_s = 38 / 7000
t_msg2_s = 88 / 7000
t_msg3_s = 144 / 7000

def t_ei_s(L: int, F: int = 8, B_EI: int = 24, R: float = 7000.0) -> float:
    return (L * F + B_EI) / R
```

Expected values:

```text
t_page   ≈ 11.428571 ms
t_msg1   ≈  5.428571 ms
t_msg2   ≈ 12.571429 ms
t_msg3   ≈ 20.571429 ms
```

For the new-paper **periodic protocol-level baseline**, every round reserves:

```text
0.5 * L * F
```

Msg2/Msg3 resources.

Use:

```python
K_fixed = 0.5 * L * F
T_periodic = (
    t_page_s
    + L * t_msg1_s
    + t_ei_s(L)
    + K_fixed * t_msg2_s
    + (K_fixed / F) * t_msg3_s
)
```

This must reproduce the paper's stated round/page intervals:

```text
L = 1  -> ~82 ms
L = 16 -> ~1089.14 ms, i.e. ~1090 ms
```

These are mandatory unit tests and early implementation gates.

For proposed aperiodic paging, Msg2 and Msg3 are provisioned dynamically based on the round's actual detected/resolved Msg1 successes. The next page begins when the current round actually ends. Therefore its page interval naturally changes from round to round.

Keep all round timing in `aperiodic_simulator/timing.py` or equivalent and expose component durations in diagnostics.

---

# 10. EI stage is mandatory

The new engine must model:

```text
Paging -> Msg1 AOs -> EI -> Msg2 -> Msg3
```

The EI duration is:

```python
T_EI(L) = (L * F + B_EI) / R
```

EI must be represented in:

- round timing;
- device energy accounting;
- protocol event payloads;
- CBRA inspector UI;
- mid-round depletion counts;
- trace data.

Do not treat EI as a zero-time label.

---

# 11. Per-round energy feasibility and Lmax

Implement Appendix A exactly.

For each device type:

```python
E_base = (
    P_wurx * T_mon
    + P_rx * t_page_s
    + P_rx * B_EI / R
    + (P_tx - P_sl) * (t_msg1_s + t_msg3_s)
    + (P_rx - P_sl) * t_msg2_s
)

E_scale = (
    P_rx * F / R
    + P_sl * (t_msg1_s + F * t_msg2_s + t_msg3_s)
)

Lmax_type = floor((E_up - E_low - E_base) / E_scale)
Lmax = min(Lmax_type over all supported device types)
```

Required validation:

```text
Type 1 bound: around 170
Type 2a/2b: limiting
Global Lmax: exactly 83
```

Add a unit test:

```python
assert compute_global_lmax(...) == 83
```

The deterministic bound assumes zero harvesting during the round. The actual simulator may still account for harvesting during low-power waiting intervals, but controller actions must satisfy `L <= 83`.

---

# 12. Heterogeneous per-device energy/state model

The new paper has three device types in the same episode. Do not use one global device-parameter object.

Represent per-device type/parameters explicitly and vectorize where useful.

Required power behavior:

## OFF

- unavailable for TX/RX;
- harvest RF energy;
- negligible circuit consumption.

## Pre-page MONITOR

- type 1 monitoring draw = RX power;
- type 2a/2b monitoring draw = WuRX power;
- monitoring lasts at most `T_mon`.

## Paging reception

- actual paging receive uses RX power.

## Msg1

- TX power during its selected Msg1 time/frequency AO;
- low-power waiting/sleep outside its active part.

## EI

- RX power for EI reception.

## Msg2

- low-power waiting until scheduled Msg2;
- RX power for the device's Msg2.

## Msg3

- low-power waiting until scheduled Msg3;
- TX power for the device's Msg3.

## Periodic inter-round state

- synchronized SLEEP;
- net energy evolution includes harvesting and `P_sl`.

## Proposed aperiodic after rejection/failure

- return to OFF;
- do not remain in synchronized inter-round sleep.

Maintain a stage-level energy ledger with at least:

```text
paging
msg1
EI
msg2
msg3
```

for diagnostics and Table IV.

---

# 13. Mid-round depletion and Figure 5 `w/o depletion`

For periodic paging, a device can start a new synchronized CBRA attempt with insufficient residual energy and fall below `E_low` during the round.

Count the first stage where depletion occurs:

```text
paging
msg1
EI
msg2
msg3
```

For the Figure 5 `w/o depletion` curves, implement a dedicated switch that ignores the **mid-round E_low failure after the periodic wake-up**, allowing that current CBRA attempt to complete.

Do not disable:

- paging monitoring costs;
- harvesting;
- inter-round sleep drain;
- access probability;
- congestion.

The new-paper proposed aperiodic scheme should produce zero mid-round depletion for feasible `L <= Lmax` if the implementation is consistent with the paper's feasibility construction.

---

# 14. Layout, channel, coverage, and harvesting

Do not use the legacy digitized old-paper CDF as the primary new-paper channel generator.

The new paper requires geometry, heterogeneous coverage, capture power, and two harvesting scenarios.

Create a new geometry/channel implementation in `aperiodic_simulator/layout.py` and `aperiodic_simulator/channel.py`.

Required flow:

1. Uniformly distribute devices in the 120 m × 60 m factory.
2. Construct the 18-BS square-lattice layout used by the paper/3GPP setup.
3. Select a central BS as reader.
4. Implement the cited 3GPP InF-DH path loss and Table II link-budget penalties.
5. Determine device communication eligibility with type-dependent link constraints.
6. Compute uplink received power at the reader for capture decisions.
7. Preserve link-budget intermediate values in diagnostics.

## Single-source harvesting

- only reader BS contributes CW energy;
- exclude devices with incident power below -36 dBm, as the paper states for this scenario.

## Multi-source harvesting

- all 18 BSs contribute CW energy;
- sum received RF power in **linear watts**, then convert to the aggregate incident power used for harvesting;
- the extra BSs are energy sources only, not extra readers and not signaling/interference nodes.

Use the shared `common.rf.conversion_efficiency()` / harvesting utility if it is mathematically identical to the earlier published model.

Important average validation targets for `N_tot=15000`:

```text
Single-source:
N_eff ≈ 6440
Type shares ≈ 17.3% type1, 41.3% type2a, 41.3% type2b

Multi-source:
N_eff ≈ 9035
Type shares ≈ 12.3% type1, 32.3% type2a, 55.3% type2b
```

Do not tune unexplained constants just to force these values. If a cited external model leaves an implementation detail under-specified, expose that detail as a named assumption and record it in the validation report.

Also generate a Figure-4-style CDF for incident power in both harvesting scenarios.

---

# 15. Capture, missed detection, and false alarms

The new engine needs separate layers for:

1. physical AO occupancy;
2. physical capture/resolution;
3. reader observation.

Requirements:

- collisions may resolve through a 6 dB capture threshold;
- apply 1% missed-detection probability;
- apply 0.1% false-alarm probability;
- do not collapse actual occupancy and reader-observed status into one variable.

Keep this in an isolated `impairments.py` or equivalent module with deterministic unit tests under fixed RNG seeds.

The paper cites external sources for some exact lower-level models. If an exact detail is not in the supplied paper, document the chosen standard interpretation explicitly instead of hiding it in `simulation.py`.

---

# 16. PFSA/PZE — required for Figures 5 and 6

Protocol-level Figures 5 and 6 compare periodic and aperiodic protocols while keeping `L` fixed. RL and dynamic `L` adaptation are disabled there.

Both methods use PFSA with a PZE-based access-probability update.

The existing legacy `AccessProbabilityController` / Schoute-like logic is not the new paper's required Figure 5/6 controller.

Implement a separate:

```text
aperiodic_simulator/controllers/pfsa_pze.py
```

The PZE estimator must infer backlog from the fraction/count of empty AOs in the previous round using the standard formula from the cited PZE reference.

If the estimator degenerates because all resources are idle, enforce the paper's fallback:

```text
p_s = 1
```

to avoid stalling.

Document the exact estimator equation and cited source in code/README.

---

# 17. New-paper periodic grouping

For new-paper periodic baselines:

```text
N_g = 1 or 4
```

Group assignment must be based on the first detected paging opportunity / phase.

After assignment, a device listens only every `N_g`-th paging opportunity for its group.

Do not use `first_paging_spread` in paper-reproduction mode.

A useful multi-source `N_g=4` validation target is the strongly imbalanced paper result:

```text
Group 1 ≈ 69.5%
Group 2 ≈ 23.9%
Group 3 ≈ 4.7%
Group 4 ≈ 1.9%
```

Expose observed group populations in both backend metrics and the new page UI.

---

# 18. New engine must be event-driven / phase-driven

Do not reuse the legacy 0.5 ms global slot loop for the new paper's large simulations.

`N_tot=15000` and curves extending toward 1200 s would require millions of global time steps and huge snapshot arrays.

The new engine must be continuous-time event/phase driven.

Each device should store enough lazy state to update only when required, e.g.:

```text
energy_j
scientific_state
last_update_time_s
power_mode
next_energy_threshold_time
monitor_deadline
sync/group state if periodic
completion status
```

Use vectorized round-level operations for population filters and AO selection where practical.

Support two runtime modes:

## `paper_batch`

- up to 15000 devices;
- up to 100 seeded episodes per curve;
- no dense full-population snapshots every 100 ms;
- collect aggregate curves, round events, sampled device traces, and scientific diagnostics.

## `interactive`

- smaller populations/time horizon;
- enough state snapshots/events for the visual factory/playback page.

Never serialize 15000-device arrays at high frequency for a 1200 s paper batch.

---

# 19. New-paper backend configuration model

Because the two HTTP APIs are separated, do **not** add a `paper_mode` field to one mega schema.

Legacy requests remain legacy-specific.

Create a new request model such as:

```python
class AperiodicSimulateRequest(BaseModel):
    num_devices: int = 15000
    seed: int = 42
    harvesting_scenario: Literal["single_source", "multi_source"]
    paging_mode: Literal["aperiodic", "periodic"]
    controller: Literal["pfsa_pze", "dfsa_schoute", "cmebe", "recurrent_ppo"]
    ppo_enabled: bool = False
    L_mode: Literal["fixed", "adaptive"] = "fixed"
    L_fixed: int = 16
    N_g: int = 1
    enforce_midround_depletion: bool = True
    alpha: float = 0.5
    F: int = 8
    runtime_mode: Literal["interactive", "paper_batch"] = "interactive"
    num_episodes: int = 1
```

Enforce valid combinations:

- proposed aperiodic protocol has no periodic group scheduling;
- `N_g` matters only for periodic mode;
- PPO ON implies `controller="recurrent_ppo"` and adaptive `L` + adaptive `p`;
- PPO OFF defaults to PFSA/PZE for Figures 5/6;
- controller-level baselines may select DFSA-Schoute or CMEBE;
- `L_fixed <= 83`;
- paper-batch endpoints can use 100 episodes.

Keep new response types separate from legacy responses.

---

# 20. PPO switch behavior in `/aperiodic-paging`

The new page must have a prominent real switch:

```text
Recurrent PPO       [ OFF / ON ]
```

Do not implement a fake PPO behind this switch.

## PPO OFF

Default behavior:

```text
Aperiodic/periodic protocol selected by user
Fixed L
PFSA/PZE access control
No RL
```

This is the mode used for protocol-level Figures 5 and 6.

When PPO is OFF, show:

```text
Temporal resources L: [1] [8] [16] [32] [custom]
Non-RL controller: PFSA/PZE (default)
```

Advanced mode may also expose DFSA-Schoute and CMEBE for controller comparisons.

## PPO ON

Behavior:

```text
Aperiodic protocol
Recurrent PPO controller
Adaptive L_s
Adaptive p_s
Lmax = 83
```

When PPO is ON:

- disable the fixed-L input;
- disable PFSA access-probability control as the active controller;
- display `L: adaptive by PPO`;
- display `p: adaptive by PPO`;
- display checkpoint status/path/hash;
- display the most recent observation and PPO action in interactive mode.

Example UI diagnostics:

```text
Round 17
Previous L = 32
Previous p = 0.48
Observation: S1=..., S2a=..., S2b=..., idle=..., collision=...
PPO multiplier m = 1.42
PPO multiplier q = 0.73
Next L = 46
Next p = 0.350
```

If a trained checkpoint is missing:

- `PPO` switch must be disabled or fail clearly;
- show `PPO checkpoint not available`;
- show the training command;
- **never silently substitute PFSA or a heuristic while reporting PPO ON**.

---

# 21. Real recurrent PPO — complete implementation required

The project must contain a real trainable recurrent PPO implementation and a real saved policy used for inference.

Using a mature PyTorch implementation such as `sb3-contrib` `RecurrentPPO` is acceptable and consistent with the paper's statement that a mature PPO implementation is used. It is **not** acceptable to replace learning with hand-authored rules.

If using `sb3-contrib`, add explicit dependency pins compatible with the project Python version, for example:

```text
torch
stable-baselines3
sb3-contrib
gymnasium
```

If a custom PyTorch recurrent PPO is implemented instead, it must include the same PPO/GAE/clipping logic and be tested. Do not implement PPO from scratch solely for novelty if a mature library can reproduce the specified architecture more reliably.

## 21.1 Observation/state

The online state for round `s` is exactly the previous-round observable vector:

```text
x_s = [
  S1_(s-1),
  S2a_(s-1),
  S2b_(s-1),
  I_(s-1),
  C_(s-1),
  L_(s-1),
  p_(s-1)
]
```

Do not expose hidden simulator truth such as:

- exact remaining backlog;
- current energy of all devices;
- next wake times;
- ground-truth availability population;
- type-2 collision ground truth used only by reward.

Normalize/scale observations for training if necessary, but preserve the semantic vector and document normalization.

## 21.2 Recurrent architecture

Paper target:

```text
Actor:  LSTM 1×128 -> MLP 128 -> MLP 128 -> action head
Critic: LSTM 1×128 -> MLP 128 -> MLP 128 -> value head
Activation: ReLU for MLP layers
```

Use separate actor/critic recurrent state unless the chosen mature implementation forces a clearly documented equivalent.

The recurrent hidden state must reset at episode boundaries and persist across CBRA rounds within one episode.

## 21.3 Action semantics

PPO outputs bounded multiplicative corrections:

```text
m_s in [0.25, 10]
q_s in [0.1, 10]
```

Then the environment applies:

```python
L_s = min(math.ceil(m_s * L_prev), Lmax)
p_s = clip(q_s * p_prev, 0, 1)
```

Because standard continuous PPO policies often emit a normalized Box action, use a deterministic documented transform from policy action space to the physical multiplier ranges. A log-space transform is reasonable because the multipliers span more than one order of magnitude, but the exact transform is not specified by the paper; record it explicitly in the PPO README/checkpoint metadata.

Do not allow the neural network to bypass the environment clipping/ceiling/`Lmax` rules.

## 21.4 Reward

Implement the paper's reward:

```python
t_success = t_msg1_s / F + t_msg2_s + t_msg3_s / F
t_collision = t_msg1_s / F

reward = (
    (1 - alpha) * (S1 + S2a + S2b) * t_success
    - alpha * C2 * t_collision
) / T_round
```

where `C2` is the number of collision resources that contain type 2a/2b devices.

Important separation:

```text
C2 may be used by the offline training reward.
C2 must NOT be added to the online PPO observation.
```

Default:

```text
alpha = 0.5
```

## 21.5 PPO hyperparameters — Table III

Use:

```text
Learning rate                 3e-4
Discount factor gamma         0.9
GAE lambda                    0.95
Clip range                    0.2
Entropy coefficient           0.01
Value-function coefficient    0.02
Max gradient norm             0.5
Steps per rollout             2048
Mini-batch size               256
Epochs per update             10
Total training steps          1,000,000
Reward alpha                  0.5
Lmax                          83
m range                       [0.25, 10]
q range                       [0.1, 10]
```

## 21.6 PPO training distribution

Training episodes must sample:

```text
N_tot from [100, 15000]
homogeneous single-type episodes and heterogeneous three-type episodes
initial L from {1, 2, 4, 8, 16, 32}
initial p uniformly from (0, 1]
random initial availability/network configuration
```

Train under the multi-source harvesting scenario, matching the paper's statement that the controller was trained there and later evaluated in single-source as well.

Use deterministic master seeds and record:

- package versions;
- training seed(s);
- config hash;
- git commit if available;
- checkpoint SHA-256;
- training step count;
- action-transform details;
- observation normalization details.

## 21.7 Checkpoint/inference

Training must save a checkpoint under a clear new-paper path, e.g.:

```text
backend/aperiodic_simulator/rl/checkpoints/recurrent_ppo_alpha_0p5.zip
```

or a generated results/checkpoints directory.

`recurrent_ppo.py` must provide a clean controller adapter that takes the paper observation and recurrent hidden state and returns physical `(L_next, p_next)` plus diagnostic `(m, q)`.

Frontend PPO ON uses this real checkpoint via backend inference.

---

# 22. PPO environment API

Create a Gymnasium-compatible environment or an equivalent clearly isolated environment adapter for training.

One RL step = one CBRA round.

Conceptually:

```text
reset()
  -> sample episode configuration
  -> initialize first L and p
  -> return first observation

step(action)
  -> map action to m,q
  -> derive L_s,p_s
  -> execute one aperiodic CBRA round
  -> calculate observable next state
  -> calculate reward
  -> terminated = all N_eff inventoried
  -> truncated = scientific safety/time limit
```

Do not advance the RL environment by 0.5 ms simulation ticks.

---

# 23. Frontend `/aperiodic-paging` controls

Create a dedicated control panel appropriate to the new paper.

Minimum controls:

```text
Scenario
  N_tot
  seed
  runtime mode: interactive / paper batch
  harvesting: single-source / multi-source

Protocol
  proposed aperiodic
  periodic baseline
  N_g = 1 / 4 / custom when periodic
  mid-round depletion ON/OFF (for w/o depletion comparison)

Resources / controller
  Recurrent PPO [OFF/ON]
  fixed L when PPO OFF
  PFSA/PZE default when PPO OFF
  optional DFSA-Schoute / CMEBE advanced baseline selection
  alpha when PPO ON or training/evaluation preset

Physical layer / advanced
  F=8
  capture 6 dB
  missed detection 1%
  false alarm 0.1%
  EI enabled
```

Add paper preset buttons:

```text
Reproduce Figure 4
Reproduce Figure 5(a)
Reproduce Figure 5(b)
Reproduce Figure 6(a)
Reproduce Figure 6(b)
Reproduce Figure 7
Reproduce Figure 8
Reproduce Table IV
Reproduce Table V
Reproduce Table VI
```

For expensive 100-episode presets, show clear progress/working state and avoid trying to animate all devices.

---

# 24. New-page visualization requirements

The new page should reuse the existing visual language where sensible, but it needs new-paper-specific inspectors.

## Inventory plot

Always provide inventoried ratio vs time.

## Round/controller plot

For adaptive controller runs, add:

```text
L_s vs round
p_s vs round
m_s vs round
q_s vs round
reward vs round
success / idle / collision counts vs round
resource efficiency vs round or aggregate
```

## CBRA inspector

Must show:

```text
Paging
Msg1 AO grid
EI
Msg2 count/resources
Msg3 count/resources
```

For periodic runs, visually distinguish fixed downstream allocation and unused reserved resources.

For aperiodic runs, show dynamic Msg2/Msg3 provisioning.

## Device trace

Distinguish at least:

```text
OFF
MONITOR
INTRA_ROUND_SLEEP/WAIT
RX
TX
INTERROUND_SYNC_SLEEP   # periodic only
DONE
```

Do not collapse proposed aperiodic OFF and periodic synchronized SLEEP into the same scientific state.

## PPO status

Display:

```text
checkpoint available?
training steps
trained scenario
checkpoint hash
current recurrent controller status
```

---

# 25. Figure 5/6 protocol-level reproduction

Use common seed sequences across compared strategies so the compared methods see the same device placement/network/initial conditions.

Average over 100 seeded episodes for final paper-comparison outputs.

## Figure 5 — single-source

```text
N_tot = 15000
mixed type1/type2a/type2b
```

Panel (a): fixed `L=16`.

Panel (b): fixed `L=1`.

Curves:

```text
aperiodic paging
periodic paging, Ng=1
periodic paging, Ng=1, w/o depletion
periodic paging, Ng=4
periodic paging, Ng=4, w/o depletion
```

Validation targets:

- aperiodic pulls clearly ahead in the later part of `L=16` inventory;
- short `L=1` paging intervals hurt periodic device availability strongly;
- T99 improvement vs periodic `Ng=4` is about 78% for `L=16`;
- T99 improvement vs periodic `Ng=4` is about 75% for `L=1`;
- about 61.9% of devices have `P_harv < P_sl` in this scenario, mostly type 2;
- proposed aperiodic mid-round depletion is zero.

### Table IV reference depletion means

```text
periodic L=16, Ng=1: paging 1817, msg1 299, EI 328, msg2 91, msg3 633, total 3168
periodic L=16, Ng=4: paging  535, msg1 342, EI 409, msg2 111, msg3 861, total 2258
periodic L=1,  Ng=1: paging 5628, msg1 673, EI 103, msg2 32, msg3 233, total 6669
periodic L=1,  Ng=4: paging 4553, msg1 620, EI 118, msg2 36, msg3 234, total 5561
aperiodic L=16: all zero
aperiodic L=1:  all zero
```

Use these as validation targets, not constants to force in code.

## Figure 6 — multi-source

Same mixed population with panels `L=16` and `L=1`.

Curves:

```text
aperiodic
periodic Ng=1
periodic Ng=4
```

Qualitative targets:

- `L=16`: methods are relatively close in energy-rich conditions;
- residual aperiodic gain is largely fixed Msg2/Msg3 resource wastage in periodic mode;
- `Ng=4` improves availability but can lose time due to group imbalance/resource waste;
- `L=1`: aperiodic advantage widens due to periodic monitoring energy drain.

---

# 26. Figure 7/8 and Tables V/VI — controller-level reproduction

Implement these only after the protocol engine is scientifically stable, but they are part of the final required scope.

## Figure 7

Compare under the proposed aperiodic framework:

```text
Recurrent PPO
DFSA-Schoute
CMEBE
```

Initialize `L1 = 1` for all Figure 7 methods.

The paper's qualitative/numeric target is about a 16% average identification-time reduction for RL vs the best DFSA baseline, CMEBE.

## Table V numeric targets — average identification time in seconds

```text
Multi-source:
N=1000:  RL 12.7, PFSA L1 19.3, L8 12.9, L32 14.5
N=7500:  RL 80.1, PFSA L1 140.4, L8 85.0, L32 82.9
N=15000: RL 158.7, PFSA L1 283.8, L8 167.7, L32 166.2

Single-source:
N=1000:  RL 172.4, PFSA L1 175.2, L8 184.2, L32 283.1
N=7500:  RL 315.2, PFSA L1 313.7, L8 326.0, L32 448.2
N=15000: RL 387.0, PFSA L1 402.6, L8 407.5, L32 590.0
```

## Figure 8

Resource efficiency:

```text
successfully identified devices / total allocated access resources
```

Compare RL and PFSA with the paper's fixed-L variants over device population size.

## Table VI targets for N=15000

```text
alpha   multi time   multi RE   single time   single RE
0.00    159.3        41.4       918.8         0.7
0.25    159.0        44.1       395.7         3.8
0.50    158.7        44.3       387.0         5.4
0.75    160.4        36.1       1058.3        0.7
```

Do not hard-code these outputs. Use them as regression/validation targets with tolerances and confidence intervals.

---

# 27. DFSA-Schoute and CMEBE are real baselines, not placeholders

Implement both baselines in separate controller modules.

The supplied paper cites their original references rather than reproducing every estimator equation. Use the cited methods faithfully and document source equations/assumptions in code comments or a controller README.

Do not implement generic names that actually call PFSA underneath.

---

# 28. Reference curve digitization and validation

Add new-paper reference-data support analogous in spirit to the legacy reference setup, but do not mix files.

Suggested location:

```text
backend/data/aperiodic_paper/
```

If Figures 4–8 are digitized, store:

- CSV points;
- README with source page/figure;
- plot crop/calibration method;
- axis mapping;
- uncertainty notes.

Never tune simulator parameters directly against digitized y-values without documenting the calibration/assumption.

For each final curve report at least:

```text
T50
T90
T95
T99
final inventoried ratio
MAE/RMSE vs digitized reference if available
mean and quantiles across episodes
number of rounds/pages
idle/success/collision AO statistics
resource efficiency
mid-round depletion by stage
group population distribution where applicable
type-specific completion metrics
```

---

# 29. Required tests

All existing legacy tests must remain passing.

Add new tests covering at minimum:

## Shared utility regression

- `dbm_to_watts` and `watts_to_dbm` round trip;
- shared RF conversion produces the same legacy values as before extraction;
- legacy metrics still produce identical outputs after common-module extraction.

## New timing

- durations from bits/R;
- `T_EI(L)`;
- periodic interval `~82 ms` for `L=1`;
- periodic interval `~1089.14 ms` for `L=16`.

## Energy feasibility

- type-specific `E_base`/`E_scale` sanity;
- global `Lmax == 83`;
- type 1 monitor uses RX power;
- type 2a/2b pre-page monitor uses WuRX power.

## State transitions

- proposed aperiodic access rejection -> OFF;
- proposed aperiodic collision/failure -> OFF;
- proposed aperiodic success -> DONE;
- no cross-round synchronization in proposed mode;
- periodic failure -> synchronized retry;
- periodic first-catch group assignment;
- periodic depletion -> OFF/recharge.

## CBRA/resource allocation

- EI timing/energy;
- periodic fixed `0.5*L*F` downstream reservation;
- aperiodic dynamic downstream reservation;
- unused periodic Msg2/Msg3 resources counted as wasted time/resources.

## Impairments

- 6 dB capture threshold behavior;
- false alarm separated from physical occupancy;
- missed detection separated from physical success;
- deterministic results for seeded impairment tests.

## PFSA/PZE

- estimator unit tests;
- all-idle fallback -> `p=1`;
- bounds `0 < p <= 1`.

## PPO environment/controller

- observation contains exactly the allowed fields;
- hidden backlog/energy is not exposed;
- action transform obeys multiplier ranges;
- `L` clipping to 83;
- `p` clipping to `(0,1]` with an explicit numerical floor if required by implementation;
- recurrent hidden state persists across steps and resets across episodes;
- `C2` affects reward but not observation;
- checkpoint save/load yields deterministic inference under deterministic policy mode;
- PPO ON cannot silently fall back when checkpoint is missing.

## Reproducibility

- same master seed -> same network/device population;
- compared strategies share the same seeded scenario realization;
- batch result aggregation deterministic under fixed seed sequence.

## API separation

- legacy endpoints exist only under `/api/simulator/...` canonically;
- new endpoints exist under `/api/aperiodic-simulator/...`;
- frontend API clients use their correct namespace;
- schemas do not leak legacy strategy enums into new-paper requests.

---

# 30. Validation script

Create:

```text
backend/scripts/validate_aperiodic_paper.py
```

It should run or load a controlled validation suite and print/save a concise scientific report:

```text
Shared RF utility regression             PASS/FAIL
Figure 4 CDF/channel checks              PASS/FAIL
Single-source N_eff/type shares          PASS/FAIL/tolerance
Multi-source N_eff/type shares           PASS/FAIL/tolerance
L=1 periodic interval                    PASS/FAIL
L=16 periodic interval                   PASS/FAIL
Lmax=83                                  PASS/FAIL
Ng=4 group distribution                  diagnostic
Figure 5 T99 reductions                  diagnostic/tolerance
Figure 6 qualitative ordering            diagnostic
Table IV depletion counts                diagnostic/tolerance
PPO checkpoint integrity                 PASS/FAIL
Figure 7 RL vs CMEBE gain                diagnostic/tolerance
Table V values                           diagnostic/tolerance
Table VI alpha trends                    diagnostic/tolerance
```

If a target is missed, report the likely responsible layer:

```text
layout/link budget
harvesting model
initial availability
PFSA/PZE
capture/detection
round timing
energy state transitions
group synchronization
PPO action transform/training
```

Do not hide failures by widening tolerances silently.

---

# 31. Preserve legacy implementation behavior

The old `/periodic-paging` page and `backend/simulator/` package are a completed reproduction baseline.

Requirements:

- the existing 64 backend tests must continue to pass;
- existing Figure 5(b) reproduction scripts must still run;
- existing scientific assumptions must not change unless a separate bug is explicitly found and documented;
- old UI defaults remain the same;
- old results remain loadable/reproducible;
- only its HTTP endpoint namespace and page route are intentionally reorganized.

When extracting shared functions, use compatibility imports/re-exports to avoid unnecessary breakage.

---

# 32. Frontend implementation details

Refactor the current code roughly as follows:

```text
Current:
SimulatorPage.tsx
useSimulation.ts
api/simulation.ts

Target:
PeriodicPagingPage.tsx
usePeriodicSimulation.ts
api/simulator.ts

after adding:
AperiodicPagingPage.tsx
useAperiodicSimulation.ts
api/aperiodicSimulator.ts
```

Legacy `types/simulation.ts` may retain its current name for compatibility. New types go into `types/aperiodicSimulation.ts`.

Create `api/http.ts` for `parseError()` / generic JSON request helpers if useful, since that is genuinely shared.

Do not create a single mega `SimulationResult` union with dozens of optional fields if separate types are clearer.

Use the existing theme/i18n system on both pages.

Add translations for new-paper terms such as:

```text
Aperiodic paging
Periodic baseline
Recurrent PPO
PFSA/PZE
DFSA-Schoute
CMEBE
EI
Type 2a
Type 2b
Single-source harvesting
Multi-source harvesting
Adaptive L
Adaptive p
Checkpoint
Resource efficiency
```

---

# 33. New paper page header/navigation

The page header should make paper context unmistakable.

Example:

```text
3GPP Ambient IoT Inventory Simulator

[ Periodic Paging Paper ] [ Aperiodic Paging Paper ]

Aperiodic paper: Kota et al.
Protocol: Aperiodic | Periodic baseline
PPO: OFF | ON
```

Do not call the old legacy EM strategy the new paper's aperiodic method anywhere in the new page.

---

# 34. Scientific diagnostics exposed to UI

The new simulator response should expose enough data for interpretation without sending enormous arrays.

At minimum include:

```text
metadata/config
paper parameters
reproduction assumptions
N_eff and type mix
reader/BS layout
static device sample for interactive mode
inventory curves
round summaries
controller history
L history
p history
m/q history when PPO
reward history when PPO
AO physical/observed stats
resource allocation/waste
mid-round depletion counts
group populations
resource efficiency
warnings
checkpoint metadata when PPO
```

For batch mode, sampled device traces are sufficient; do not send full 15000-device trajectories.

---

# 35. Result/storage separation

Keep existing legacy result files valid.

New-paper generated results must go under a clearly separate subtree such as:

```text
results/aperiodic_paging/
```

Store machine-readable CSV/JSON plus plots.

For PPO, store training/evaluation metadata next to checkpoints and result files.

A new run store may be implemented inside `aperiodic_simulator/run_store.py` if the trace model differs from the legacy `DeviceTraceBank`. Do not contort the legacy trace bank to represent new scientific states unless a truly generic abstraction emerges naturally.

---

# 36. Implementation order

Work in this exact order. Keep the repository runnable after each phase.

## Phase 0 — baseline and routing separation

1. run legacy tests/build;
2. rename frontend page/hook/API client to periodic-specific names;
3. create `/periodic-paging` route and root redirect;
4. move legacy FastAPI router to canonical `/api/simulator/...` namespace;
5. verify old simulator behavior is unchanged.

## Phase 1 — common utilities

1. extract only pure shared RF/math/metrics functions;
2. keep compatibility imports in legacy modules;
3. add regression tests proving no legacy numerical changes.

## Phase 2 — new config/layout/channel

1. create `aperiodic_simulator/` package;
2. implement three device types;
3. implement 18-BS geometry/link budget;
4. implement single/multi-source harvesting;
5. validate Figure 4 / N_eff / type shares.

## Phase 3 — new energy/state/timing engine

1. event-driven device state handling;
2. exact message durations;
3. EI;
4. Appendix Lmax calculation;
5. periodic fixed round timing oracle tests.

## Phase 4 — new periodic baseline

1. DCM acquisition;
2. first-catch group assignment;
3. synchronized retry;
4. fixed Msg2/Msg3 reservation;
5. mid-round depletion accounting;
6. w/o depletion switch.

## Phase 5 — proposed aperiodic protocol

1. return-to-OFF after rejection/failure;
2. no cross-round synchronization;
3. dynamic downstream resource allocation;
4. adaptive page interval from actual round duration;
5. zero-depletion feasibility checks.

## Phase 6 — impairments and PFSA/PZE

1. capture;
2. missed detection;
3. false alarm;
4. PZE access controller;
5. common-seed comparisons.

## Phase 7 — Figure 5/6/Table IV

1. 100-episode batch workflows;
2. figure/table scripts;
3. validation report;
4. new frontend page for non-RL mode.

## Phase 8 — controller baselines

1. DFSA-Schoute;
2. CMEBE;
3. controller abstraction finalized.

## Phase 9 — real recurrent PPO

1. Gymnasium/event-driven RL environment;
2. recurrent PPO policy config;
3. exact observation/action/reward;
4. training pipeline;
5. 1,000,000-step checkpoint;
6. evaluation/inference adapter;
7. PPO status API;
8. frontend PPO ON/OFF wiring.

## Phase 10 — Figure 7/8/Tables V/VI

1. controller comparison batch scripts;
2. resource-efficiency plots;
3. alpha sweep;
4. paper target validation.

## Phase 11 — final integration

1. all backend tests;
2. frontend typecheck/build;
3. both routes manually verified;
4. both API namespaces verified;
5. final reproduction commands documented.

Do not skip lower-layer validation just because later UI or PPO code runs.

---

# 37. Anti-shortcut / anti-fake rules

The following are explicitly forbidden:

- calling the legacy `EM` strategy the new-paper aperiodic protocol;
- using one mega simulator with hundreds of paper-specific branches when separate engines are required;
- fake PPO / heuristic labeled as PPO;
- random untrained neural net labeled PPO;
- hard-coded Figure 7/8 actions or curves;
- hard-coded paper output values returned by API;
- fitting arbitrary hidden constants to digitized curves without documentation;
- exposing hidden backlog or device energy to the PPO observation;
- putting `C2` into online observation;
- using the legacy slot loop for 15000×1200 s paper batch runs;
- changing old-paper scientific assumptions to improve new-paper results;
- using old un-namespaced API endpoints from final frontend code;
- sharing modules whose scientific semantics differ just because names look similar.

---

# 38. Completion criteria

The task is complete only when all of the following are true:

1. `/periodic-paging` runs the original paper simulator.
2. `/aperiodic-paging` runs the new-paper simulator.
3. Legacy HTTP requests use `/api/simulator/...`.
4. New HTTP requests use `/api/aperiodic-simulator/...`.
5. `backend/simulator/` remains the legacy scientific engine.
6. `backend/aperiodic_simulator/` contains the new scientific engine.
7. only truly common pure utilities are shared through `backend/common/`.
8. Figure 4 channel/CDF validation exists.
9. Figures 5 and 6 and Table IV can be reproduced by scripts/API presets.
10. PFSA/PZE is implemented for protocol-level comparisons.
11. DFSA-Schoute and CMEBE are implemented.
12. real recurrent PPO is trainable and has a saved checkpoint.
13. PPO ON in the frontend uses the trained checkpoint, not a heuristic.
14. Figure 7, Figure 8, Table V, and Table VI workflows exist.
15. `Lmax=83` and the 82 ms / 1090 ms timing oracles pass tests.
16. all old tests still pass.
17. all new tests pass.
18. frontend typecheck/build passes.
19. validation output reports discrepancies instead of hiding them.
20. final README/reproduction notes clearly explain how to run both simulators and train/evaluate PPO.

---

# 39. Final response expected from Cursor after implementation

When implementation is finished, report:

1. architecture summary;
2. exact changed/new file list;
3. shared utility modules and why they are scientifically safe to share;
4. legacy endpoint migration summary;
5. new API endpoint list;
6. new frontend route list;
7. exact equations/assumptions implemented;
8. all test/build results;
9. commands to reproduce Figures 4–8 and Tables IV–VI;
10. PPO training command and checkpoint metadata;
11. validation results against paper targets;
12. remaining deviations/ambiguities and their likely causes.

Do not end with only “implemented successfully.” Provide the actual validation evidence.
