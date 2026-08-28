Follow this specification as the source of truth. First inspect both PDFs, then create a concrete implementation plan, and immediately start implementing Phase A. Do not stop after giving me the plan.

# Project Task: Build a Complete Reproducible 3GPP Ambient IoT Inventory Simulator

You are acting as a senior wireless-communications simulation engineer, research software engineer, Python backend engineer, and React/TypeScript frontend engineer.

Your task is to build a complete, reproducible research simulation environment for the paper:

**“Fast Inventory for 3GPP Ambient IoT Considering Device Unavailability Due to Energy Harvesting”**

The primary research objective is:

> Reproduce the behavior and curves of **Figure 5(b)** for **Device 1**, using a real system-level simulation rather than drawing or fitting arbitrary curves.

The final deliverable must be a complete Git repository that can be started with:

```bash
docker compose up --build
```

and opened at:

```text
http://localhost:3000
```

The simulation must also work independently of the frontend:

```bash
docker compose run --rm backend python scripts/reproduce_fig5b.py
```

This command must run the actual Python simulation and generate the Figure 5(b) reproduction results.

---

# 1. Source Material

Assume the repository contains:

```text
references/
├── 2501.15020v1.pdf
└── Fast_Inventory_for_3GPP_Ambient_IoT_Considering_Device_Unavailability_Due_to_Energy_Harvesting.pdf
```

The first PDF is the arXiv v1 version.

The second PDF is the published IEEE version.

Treat the **published IEEE version as the canonical source for implementation parameters**, unless explicitly noted otherwise.

Do NOT silently invent missing paper parameters.

Whenever the paper does not provide enough implementation detail:

1. identify the missing detail,
2. implement a reasonable reproducible assumption,
3. isolate it in configuration,
4. explain it in `README.md`,
5. label it clearly as a **reproduction assumption** rather than a paper-specified parameter.

Also create:

```text
docs/PAPER_NOTES.md
```

documenting important discrepancies between the arXiv and published versions.

Known example:

* arXiv and published versions contain some parameter differences.
* The RF energy-conversion-efficiency piecewise-condition must be checked carefully.
* The implementation must use the physically consistent published equation where `p_in = -36 dBm` gives approximately `5%` efficiency.

Never hide such discrepancies.

---

# 2. Primary Reproduction Target

Reproduce **Figure 5(b)** for **Device 1**.

The figure represents:

```text
x-axis:
Time since beginning of inventory stage

y-axis:
Percentage of A-IoT devices successfully inventoried
```

If device `i` finishes inventory at time:

```text
T_i
```

then the plotted curve is:

```text
F(t) =
number of devices with T_i <= t
-------------------------------- × 100%
              N
```

The simulation must produce completion times from protocol/energy behavior.

Do NOT mathematically generate an S-shaped curve.

Do NOT manually force points onto the paper curve.

Do NOT hard-code T50/T90/T99.

The curves must emerge from the simulator.

The published Figure 5(b) comparison should support at least:

```text
1. EM, aperiodic paging
2. DCM, periodic paging, 1 group
3. DCM, periodic paging, 4 groups
```

The paper reports the important qualitative result that EM has a long inventory-completion tail, while DCM combined with device grouping substantially reduces Device-1 inventory completion time.

The implementation should attempt to reproduce approximately the paper's reported behavior, especially the order of magnitude of T99.

If exact reproduction is impossible because an algorithm is underspecified in the paper, do NOT modify paper-specified physical parameters just to force the result.

Instead report the reproduction discrepancy.

---

# 3. Required Technology Stack

Use:

## Frontend

```text
React
TypeScript
Vite
Plotly.js
react-plotly.js
```

Use normal React/CSS for controls and protocol grids.

Do NOT use Canvas for the main device visualization unless a clear performance issue appears.

For approximately 600 devices, use a Plotly scatter plot.

Do NOT create 600 individual React DOM components for device dots.

Use one Plotly trace containing device markers.

## Backend

```text
Python 3.12
FastAPI
Pydantic
NumPy
SciPy if useful
Pandas
Matplotlib
```

## Testing

```text
pytest
```

## Infrastructure

```text
Docker
Docker Compose
```

Do NOT introduce unnecessary infrastructure such as:

```text
PostgreSQL
Redis
Celery
Kafka
authentication
cloud services
Next.js
```

This is a research simulator, not a SaaS product.

---

# 4. Architectural Rule

The most important architectural requirement is:

```text
SIMULATION CORE MUST BE COMPLETELY INDEPENDENT OF THE WEB UI.
```

Architecture:

```text
                         Browser
                            |
                            v
                   React / TypeScript
                            |
                         REST API
                            |
                            v
                       FastAPI
                            |
                            v
                 Python Simulation Core
                     /      |       \
                  Energy   CBRA    Strategies
                     \      |       /
                      Completion Times
                            |
                +-----------+------------+
                |                        |
                v                        v
         reproduce_fig5b.py          React UI
```

React must NEVER contain the scientific simulation logic.

The React app only:

* submits configuration,
* displays results,
* explores device state,
* plays saved simulation snapshots.

---

# 5. Repository Structure

Create approximately this structure:

```text
ambient-iot-simulator/
│
├── README.md
├── docker-compose.yml
├── .gitignore
├── .env.example
│
├── references/
│   ├── 2501.15020v1.pdf
│   └── Fast_Inventory_for_3GPP_Ambient_IoT_Considering_Device_Unavailability_Due_to_Energy_Harvesting.pdf
│
├── docs/
│   ├── PAPER_NOTES.md
│   ├── SIMULATION_MODEL.md
│   └── REPRODUCTION_ASSUMPTIONS.md
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       │
│       ├── api/
│       │   └── simulation.ts
│       │
│       ├── components/
│       │   ├── SimulationControls.tsx
│       │   ├── FactoryView.tsx
│       │   ├── InventoryCurve.tsx
│       │   ├── DeviceInspector.tsx
│       │   ├── EnergyHistory.tsx
│       │   ├── CBRAInspector.tsx
│       │   ├── MetricsPanel.tsx
│       │   └── AssumptionsPanel.tsx
│       │
│       ├── hooks/
│       │   └── useSimulation.ts
│       │
│       └── types/
│           └── simulation.ts
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── simulation.py
│   │   └── schemas/
│   │       └── simulation.py
│   │
│   ├── simulator/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── scenario.py
│   │   ├── channel.py
│   │   ├── energy.py
│   │   ├── device.py
│   │   ├── reader.py
│   │   ├── paging.py
│   │   ├── access_control.py
│   │   ├── cbra.py
│   │   ├── metrics.py
│   │   ├── simulation.py
│   │   └── strategies/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── em.py
│   │       └── dcm.py
│   │
│   ├── scripts/
│   │   ├── reproduce_fig5a.py
│   │   └── reproduce_fig5b.py
│   │
│   ├── data/
│   │   ├── fig5a_pin_cdf.csv
│   │   └── reference_fig5b/
│   │
│   └── tests/
│       ├── test_channel.py
│       ├── test_energy.py
│       ├── test_cbra.py
│       ├── test_em.py
│       ├── test_dcm.py
│       └── test_reproducibility.py
│
└── results/
    ├── .gitkeep
    └── reference/
```

Minor deviations are acceptable if architecturally justified.

---

# 6. Published Paper Parameters — Device 1

Create a strongly typed central configuration object.

Paper parameters must NOT be spread as magic constants throughout the source code.

Use SI units internally.

For Device 1, implement at least:

```text
Number of devices N:
600

Maximum energy storage E_es_max:
500 nJ

Turn-on threshold E_es_up:
500 nJ

Turn-off threshold E_es_low:
0.5 * E_es_max = 250 nJ

Receiver power P_rx:
1 uW

Transmit power P_tx:
1 uW

Sleep-state power P_sl:
0.1 uW

Paging duration:
1 ms

Periodic paging period T_pg:
12 ms

Msg1 duration:
0.5 ms

Msg2 duration:
0.5 ms

Msg3 duration:
3 ms

DCM on duration after inventory acquisition:
3 ms in the published version

DCM pre-inventory on-timer:
18 ms

Number of Msg1 access occasions in time:
4

Number of Msg1 access occasions in frequency:
2

Total Device-1 Msg1 AOs:
4 * 2 = 8
```

Use:

```text
simulation base time step = 0.5 ms
```

for the slot-level simulation unless a more accurate event-driven approach is implemented.

Keep all units internally explicit:

```text
time: seconds
energy: Joules
power: Watts
received RF power: dBm at interface boundary, Watts internally
```

Provide frontend-friendly derived units such as:

```text
ms
nJ
uW
nW
dBm
```

only for display.

---

# 7. RF Power and Energy Harvesting Model

Each A-IoT device has a received RF power:

```text
p_in
```

The paper uses:

```text
P_eh = p_in * xi(p_in)
```

where:

```text
P_eh
```

is harvested electrical power and:

```text
xi(p_in)
```

is the RF-to-energy conversion efficiency.

Implement:

```python
dbm_to_watts(dbm)
```

using:

```text
P_W = 10 ^ ((P_dBm - 30) / 10)
```

Implement the published piecewise conversion efficiency carefully.

The physically consistent published relationship must satisfy:

```text
p_in = -36 dBm
xi approximately 0.05
```

Use:

```text
xi(p_in) = (p_in + 41) / 100,       p_in <= -10 dBm

xi(p_in) = (-2*p_in + 11) / 100,    p_in > -10 dBm
```

where `p_in` inside this expression is the numerical value in dBm.

Then:

```text
P_eh_W = dbm_to_watts(p_in_dbm) * xi(p_in_dbm)
```

Add sanity tests.

At:

```text
p_in = -36 dBm
```

the received RF power should be approximately:

```text
0.251 uW
```

and with approximately 5% conversion efficiency:

```text
P_eh approximately 12.56 nW
```

Charging from:

```text
250 nJ -> 500 nJ
```

with negligible OFF-state consumption should therefore require approximately:

```text
19.9 seconds
```

This is a critical physical sanity check.

---

# 8. Figure 5(a) Received-Power Distribution

The simulation must NOT assign arbitrary uniform received RF powers.

The paper's Figure 5(a) provides the CDF of received device power `p_in`.

Use that distribution to generate device received powers.

Create:

```text
backend/data/fig5a_pin_cdf.csv
```

with columns such as:

```text
cdf,pin_dbm
```

Digitize Figure 5(a) from the provided paper.

Do NOT invent fake CDF coordinates and label them as paper data.

If automated digitization is difficult:

1. manually sample a sufficient number of points from the figure,
2. store them in CSV,
3. document the method,
4. provide the original figure/page reference in `PAPER_NOTES.md`.

Sampling devices:

```python
u = rng.uniform(0, 1, N)
pin_dbm = inverse_cdf(u)
```

Use interpolation over the digitized CDF.

The paper excludes devices whose received power is below approximately:

```text
-36 dBm
```

from the evaluated device population.

Respect this cutoff.

---

# 9. Factory Visualization

The paper uses an indoor factory environment approximately:

```text
120 m x 60 m
```

The frontend must display approximately 600 devices as points in this space.

Important:

The visual `(x, y)` position of devices is NOT automatically allowed to determine RF received power using a naïve free-space formula.

Unless the full paper/3GPP D1T1 propagation model is explicitly implemented, treat:

```text
x,y
```

as visualization coordinates, while:

```text
p_in
```

comes from the Figure 5(a) distribution.

Clearly state this in the UI and README.

Generate visual positions reproducibly using the simulation seed:

```text
x ~ Uniform(0, 120)
y ~ Uniform(0, 60)
```

The reader/base station should be visibly shown separately.

---

# 10. Device Model

Each simulated device should contain at least:

```text
id

x
y

pin_dbm
harvest_power_w

energy_j
state

inventoried
completion_time_s

group_id

first_paging_detected
first_paging_time

access_attempts
collision_count
successful_msg1_count

timer information required by EM/DCM
```

Suggested states:

```text
OFF
ON
SLEEP
ACCESS
COLLISION
DONE
```

`ACCESS` and `COLLISION` may be event/display states rather than long-lived physical states.

The scientific state machine must remain clean.

---

# 11. Energy Update Rules

Implement energy conservation explicitly.

Clamp energy to:

```text
0 <= E <= E_es_max
```

## OFF

The IC is unavailable for communication.

OFF-state consumption is treated as negligible according to the model.

The device harvests:

```text
E_new =
min(E_max, E + P_eh * dt)
```

## ON / RX monitoring

The device consumes receiver power.

Use:

```text
E_new =
E - P_rx * dt
```

Do not silently add harvesting in ON/RX unless the source model explicitly supports simultaneous harvesting there.

## TX

Use:

```text
E_new =
E - P_tx * dt
```

for transmission intervals.

## SLEEP

The paper states that a sleeping DCM device can harvest RF energy while consuming sleep-state power.

Use:

```text
E_new =
min(
    E_max,
    E + (P_eh - P_sl) * dt
)
```

If this becomes negative for a particular device, naturally allow energy to decrease.

Respect energy thresholds and state transitions.

---

# 12. EM Strategy

Implement conventional Energy-Based Monitoring.

Core conceptual state behavior:

```text
OFF
 |
 | energy >= E_up
 v
ON
 |
 | energy <= E_low
 v
OFF
```

While ON and waiting for paging:

```text
consume P_rx
```

Once energy reaches/breaches the turn-off threshold:

```text
transition to OFF
```

while OFF:

```text
harvest until E_up
```

After successful inventory:

```text
DONE
```

The EM mechanism produces long unavailability periods for weak-power devices after they drain energy.

The approximately `-36 dBm` worst-edge example should naturally generate an order-of-magnitude recharge time close to 20 seconds.

---

# 13. DCM Strategy — Before Detecting Inventory

Before a DCM device detects its first inventory paging:

1. It harvests while OFF.
2. When energy reaches `E_up`, it enters ON.
3. It monitors for paging.
4. If no paging is detected within:

```text
T_on_timer = 18 ms
```

it returns to OFF even if energy has not dropped to `E_low`.

This is the key pre-inventory DCM behavior.

The purpose is to preserve a higher stored energy level compared with EM.

Implement timers carefully at the 0.5 ms simulation resolution.

---

# 14. DCM Strategy — After Detecting Inventory

After a DCM device receives its first paging message:

* it recognizes that the reader is conducting an inventory,
* it becomes synchronized with the known periodic paging schedule,
* it alternates between low-power sleep and short ON windows.

For periodic Device-1 paging:

```text
T_pg = 12 ms
```

and published Device-1 DCM ON duration:

```text
T_on_DCM = 3 ms
```

enforce the conceptual timing relationship:

```text
T_sleep_DCM + T_on_DCM = relevant paging period
```

For one-group DCM, wake every paging period.

For grouped DCM, wake only for the assigned paging group as described below.

---

# 15. Device Grouping

Implement configurable grouping:

```text
N_groups = 1
N_groups = 4
```

For four groups, do NOT simply randomly assign a permanent group unless that is explicitly chosen as a documented approximation.

Prefer behavior consistent with the paper's description:

A device becomes associated with the paging phase/group corresponding to the paging occasion on which it first detects the inventory.

Conceptually:

```text
group_id = first_detected_paging_index % N_groups
```

Thereafter it only wakes for paging occasions belonging to its group.

The wake periodicity becomes:

```text
N_groups * T_pg
```

For Device 1 and 4 groups:

```text
4 * 12 ms = 48 ms
```

A device in group 0 may therefore react to:

```text
paging 0, 4, 8, 12, ...
```

group 1:

```text
paging 1, 5, 9, 13, ...
```

etc.

Document the exact implementation.

---

# 16. Paging Models

Implement both:

```text
periodic paging
aperiodic paging
```

## Periodic paging

For DCM:

```text
T_pg = 12 ms
```

according to the paper.

## Aperiodic paging

The exact aperiodic paging scheduling algorithm is not completely specified in the paper.

Therefore implement this as an explicit, isolated reproduction assumption.

A reasonable default is an event-driven / earliest-feasible next paging mechanism after the previous CBRA-related message exchange is complete.

Do NOT pretend this scheduling rule comes directly from the paper.

Put it behind a strategy/config abstraction such as:

```python
AperiodicPagingPolicy
```

so it can be changed later without rewriting EM.

Expose the selected assumption in:

```text
docs/REPRODUCTION_ASSUMPTIONS.md
```

---

# 17. CBRA Model

Implement the A-IoT contention-based random-access logic.

Conceptual flow:

```text
Paging
   |
   v
eligible device
   |
   v
access probability decision
   |
   v
random Msg1 AO selection
   |
   +---- same AO used by >1 devices ---> collision / retry later
   |
   +---- exactly one device -----------> Msg1 success
                                             |
                                             v
                                            Msg2
                                             |
                                             v
                                            Msg3
                                             |
                                             v
                                            DONE
```

Device 1 has:

```text
4 time-domain AOs
x
2 frequency-domain AOs
=
8 total AOs
```

Each attempting device independently selects an AO uniformly:

```python
ao_index = rng.integers(0, 8)
```

For each AO:

```text
0 devices:
idle

1 device:
Msg1 success

>1 devices:
collision
all colliding devices fail that attempt
```

Successful devices proceed through Msg2 and Msg3 timing and energy costs.

After successful Msg3:

```text
inventoried = True
completion_time = current_time
state = DONE
```

A successfully inventoried device must not join future CBRAs.

---

# 18. Access Probability Adjustment

The paper states that congestion can be controlled by indicating an access probability based on prior AO occupancy/congestion.

However, the exact controller equation is not fully specified.

Therefore:

* implement a reasonable occupancy-feedback controller,
* isolate it in `access_control.py`,
* document it as an assumption,
* make it replaceable.

Do not simply choose an arbitrary constant probability solely to make Figure 5(b) look correct.

A reasonable first implementation can use idle-AO-based load estimation.

If:

```text
M = total number of AOs
I = number of idle AOs
```

under a Poisson offered-load approximation:

```text
I / M ≈ exp(-lambda)
```

so:

```text
lambda_hat = -ln(I / M)
```

and approximate attempt load:

```text
A_hat = M * lambda_hat
```

Target approximately:

```text
A_target ≈ M
```

and update access probability smoothly toward this target.

Handle edge cases:

```text
I = 0
I = M
```

Use configurable clipping:

```text
p_min <= p_access <= 1
```

and optional exponential smoothing to avoid oscillation.

Record the access probability over time for inspection.

This exact rule MUST be labeled as a reproduction assumption.

---

# 19. Initial Conditions and Pre-Inventory Warm-Up

The paper does not completely specify the random energy/cycle phase of all devices exactly at `t = 0` of the inventory stage.

Do NOT start all devices identically.

That would artificially synchronize them.

Implement a configurable pre-inventory warm-up / charging stage.

During warm-up:

```text
reader provides RF energy
no inventory paging is transmitted
devices follow their EM or DCM pre-inventory behavior
```

Use deterministic random initial conditions based on the seed.

A reasonable reproducible initialization can include:

```text
initial energy sampled from a documented range
randomized timer/cycle phase
```

followed by a sufficiently long warm-up.

The warm-up duration should be configurable.

Choose a default long enough for device cycles to decorrelate; for example, tens of seconds or based on the worst-case recharge scale.

Do NOT include warm-up time in Figure 5(b).

Define:

```text
t = 0
```

exactly as the beginning of the inventory stage.

Document the warm-up policy prominently.

---

# 20. Common Random Numbers and Reproducibility

Strategy comparison must be fair.

Generate a common base scenario from a deterministic seed:

```python
scenario = Scenario.generate(seed=42)
```

The same base scenario should provide, where scientifically applicable:

```text
same p_in values
same visual coordinates
same base random variables
same device identities
```

Then simulate:

```text
EM
DCM 1 group
DCM 4 groups
```

using controlled random-number streams.

The simulation should be exactly reproducible for the same:

```text
configuration + seed
```

Add a unit/integration test verifying deterministic output.

---

# 21. Simulation Resolution and Performance

Internally simulate with:

```text
dt = 0.5 ms
```

or an equivalent exact event-driven implementation.

For a 25-second simulation:

```text
50,000 slots
```

and 600 devices is manageable in NumPy/Python.

Prefer vectorized NumPy operations for:

```text
energy updates
state masks
device eligibility
```

where they improve clarity and speed.

Do not sacrifice correctness for premature optimization.

---

# 22. Web Snapshot Strategy

DO NOT send every 0.5 ms state of all 600 devices to the frontend.

The scientific simulator runs at full resolution.

The web visualization uses snapshots such as:

```text
50 ms
or
100 ms
```

intervals.

Make snapshot interval configurable.

Example:

```text
simulation:
0.5 ms internal resolution

visualization:
100 ms snapshot resolution
```

The frontend playback is a replay of simulation results.

It is NOT the simulation itself.

No WebSocket is required.

Use:

```text
POST /api/simulate
```

wait for completion, then return results.

---

# 23. Result Data Model

Return a result containing at least:

```text
metadata
configuration
paper_parameters
reproduction_assumptions

static_devices

strategy_results
    curves
    metrics
    snapshots
    paging_events
    access_probability_history

warnings
```

Static device information can include:

```text
id
x
y
pin_dbm
harvest_power_nw
```

Dynamic snapshot information can include:

```text
state
energy_nj
inventoried
```

Avoid unnecessary duplication if simple.

---

# 24. Metrics

For every strategy compute:

```text
T50
T90
T95
T99
final inventoried ratio
number of paging messages
total Msg1 attempts
total collisions
collision rate
```

Define:

```text
T99 =
first time at which >= 99% of devices are inventoried
```

If the threshold is not reached before simulation timeout, return:

```text
null
```

rather than fabricating a value.

---

# 25. Figure 5(b) Reproduction Script

Implement:

```text
backend/scripts/reproduce_fig5b.py
```

It must:

1. load canonical paper configuration,
2. generate the common scenario,
3. run:

   * EM aperiodic,
   * DCM periodic 1 group,
   * DCM periodic 4 groups,
4. compute inventory-ratio curves,
5. calculate T50/T90/T99,
6. plot with Matplotlib,
7. save raw CSV results,
8. save a JSON summary.

Outputs:

```text
results/fig5b_reproduced.png
results/fig5b_reproduced.csv
results/fig5b_metrics.json
```

Print a useful console summary such as:

```text
Running Device-1 Figure 5(b) reproduction...

N: 600
Seed: 42

EM aperiodic:
T50 = ...
T90 = ...
T99 = ...

DCM periodic, 1 group:
T50 = ...
T90 = ...
T99 = ...

DCM periodic, 4 groups:
T50 = ...
T90 = ...
T99 = ...

Results saved to results/
```

Do NOT make this script depend on FastAPI or React.

---

# 26. Reference Figure Overlay

If possible, digitize the published Figure 5(b) curves into:

```text
backend/data/reference_fig5b/
```

For example:

```text
em.csv
dcm_1_group.csv
dcm_4_group.csv
```

These data must be obtained by actual figure digitization, not invented.

Provide an optional overlay in the frontend:

```text
Simulation
Paper reference
Both
```

Use different line styles for simulated and digitized reference data.

If the reference data are unavailable, the feature should degrade gracefully.

---

# 27. Reproduction Error Metrics

If digitized Figure 5(b) data exist, calculate comparison metrics such as:

```text
MAE
RMSE
T99 error
```

For example:

```text
MAE =
mean absolute difference between
simulation ratio and digitized reference ratio
at common time coordinates
```

Do NOT claim "exact reproduction" based only on visual similarity.

Display reproduction metrics explicitly.

---

# 28. Frontend Layout

Build a clean, research-oriented single-page dashboard.

Suggested title:

```text
3GPP Ambient IoT Inventory Simulator
```

Subtitle:

```text
Reproduction of Figure 5(b):
Fast Inventory for 3GPP Ambient IoT Considering
Device Unavailability Due to Energy Harvesting
```

Use a professional scientific visual style.

Avoid flashy consumer-app aesthetics.

The dashboard should contain:

```text
1. Simulation Controls
2. Factory / Device View
3. Main Figure 5(b) Reproduction
4. Metrics Panel
5. Device Inspector
6. Device Energy History
7. CBRA Inspector
8. Reproduction Assumptions
```

---

# 29. Simulation Controls

Default to paper configuration:

```text
N = 600
Device Type = 1
Seed = 42
Max simulation time approximately 25 s
```

Support strategy selection:

```text
EM
DCM - 1 Group
DCM - 4 Groups
```

Include a prominent:

```text
Run Paper Configuration
```

button.

Separate settings into:

```text
Paper Parameters
Advanced / Reproduction Assumptions
```

Paper mode should lock or clearly identify canonical paper parameters.

Exploration mode may permit user modifications.

Never visually blur the difference between:

```text
paper-specified parameter
```

and:

```text
reproduction assumption
```

---

# 30. Factory View — Use Plotly

Use:

```text
react-plotly.js
```

with one Plotly scatter trace for the devices.

Do NOT render each device as an individual React component.

The plot represents:

```text
120 m x 60 m
```

Each marker represents one A-IoT device.

Allow:

```text
hover
click
zoom
pan
```

Use a second trace for the Reader/Base Station.

---

# 31. Device State Colors

Use a consistent state mapping.

For example:

```text
OFF / harvesting:
gray

ON / listening:
blue

SLEEP:
purple

ACCESS:
orange

COLLISION:
red

DONE:
green
```

Exact colors can be chosen by the frontend implementation but must remain consistent and accessible.

Include a legend.

---

# 32. Device Hover

Hovering over a device should display concise information:

```text
Device #417

State:
SLEEP

Energy:
431 / 500 nJ

p_in:
-34.8 dBm

Harvest Power:
...

Group:
2
```

Do not overload the tooltip with every field.

---

# 33. Device Click / Inspector

Clicking a device should select it.

Show a side panel with detailed information such as:

```text
Device ID

Received RF Power
Harvesting Power

Current Energy
Maximum Energy

Current State

Strategy
Group

First Paging Detection

CBRA Attempts
Collision Count

Inventory Completed?
Completion Time
```

Also show that selected device's energy history.

---

# 34. Time Playback

Provide:

```text
Play / Pause
Time slider
Current simulation time
```

The user must be able to inspect saved snapshots over time.

Example:

```text
0 s --------------------●------------------ 25 s
                        8.4 s
```

Playback only updates the snapshot displayed.

Do NOT rerun the simulation while dragging the slider.

---

# 35. Main Figure 5(b) Plot

Use Plotly for the interactive frontend version.

Display:

```text
Successfully inventoried A-IoT device ratio (%)
```

versus:

```text
Time
```

for selected strategies.

At minimum:

```text
EM, aperiodic paging
DCM, periodic paging, 1 group
DCM, periodic paging, 4 groups
```

Provide clear legend labels matching paper terminology.

Allow optional paper-reference overlay.

Show T50/T90/T99 in an adjacent metrics panel.

---

# 36. CBRA Inspector

Implement a protocol-level inspector.

Allow selecting a paging event.

Show:

```text
Paging index
Paging time

Eligible devices
Attempting devices

Access probability

Successful Msg1 count
Collision count
Idle AO count
```

Render Device-1's 8 AOs as a simple React/CSS grid:

```text
              Frequency
              F0        F1

Time 0       AO0       AO1
Time 1       AO2       AO3
Time 2       AO4       AO5
Time 3       AO6       AO7
```

Each cell can show:

```text
IDLE
SUCCESS
COLLISION
```

and optionally device IDs.

Do not use Canvas here.

A normal CSS grid is sufficient.

---

# 37. Device Energy History

For a selected device, provide a Plotly energy-vs-time graph.

Show:

```text
E_up
E_low
```

as reference lines.

This should make the EM/DCM behavior visually understandable.

Where practical, allow comparing the same scenario/device under:

```text
EM
DCM
```

to illustrate energy preservation.

---

# 38. Backend API

At minimum implement:

```text
GET /api/health
GET /api/config/paper
POST /api/simulate
```

Optional:

```text
GET /api/about
```

`POST /api/simulate` accepts a Pydantic configuration object.

Example conceptual request:

```json
{
  "num_devices": 600,
  "device_type": 1,
  "strategies": [
    "em",
    "dcm_1_group",
    "dcm_4_group"
  ],
  "seed": 42,
  "max_time_s": 25,
  "snapshot_interval_ms": 100
}
```

Validate invalid configurations cleanly.

---

# 39. Docker

Implement:

```text
docker compose up --build
```

Services:

```text
backend
frontend
```

Backend:

```text
python:3.12-slim
FastAPI
uvicorn
```

Frontend:

multi-stage Docker build:

```text
Node build stage
-> npm run build
-> serve static files using nginx
```

Ports:

```text
Frontend:
localhost:3000

Backend:
localhost:8000
```

The frontend should call the backend correctly from Docker networking and from the browser.

Avoid hard-coded localhost mistakes.

Use environment variables where appropriate.

---

# 40. Local Non-Docker Development

README must also explain:

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Figure 5(b) only

```bash
cd backend
python scripts/reproduce_fig5b.py
```

---

# 41. Tests

Implement meaningful tests.

At minimum:

## RF conversion test

Verify:

```text
-36 dBm -> approximately 0.251 uW
```

## Efficiency test

Verify:

```text
xi(-36 dBm) ≈ 0.05
```

## Harvest-power test

Verify:

```text
P_eh(-36 dBm) ≈ 12.56 nW
```

## Recharge-time sanity test

Verify approximately:

```text
250 nJ / 12.56 nW ≈ 19.9 s
```

## Energy boundaries

Verify:

```text
0 <= E <= E_max
```

## EM transition

Verify:

```text
OFF -> ON at E_up
ON -> OFF at E_low
```

## DCM timer

Verify pre-inventory ON period exits after configured on-timer if no paging is received.

## DCM synchronization

Verify wake timing follows periodic paging after first detection.

## CBRA

Verify:

```text
one device in AO -> success
multiple devices in same AO -> collision
zero devices -> idle
```

## Reproducibility

Same:

```text
seed + config
```

must generate the same numerical result.

---

# 42. Documentation

Create a strong README.

The first screen should immediately explain:

```text
# 3GPP Ambient IoT Inventory Simulator

Simulation environment for reproducing Figure 5(b)
of "Fast Inventory for 3GPP Ambient IoT Considering
Device Unavailability Due to Energy Harvesting".
```

Then:

```bash
docker compose up --build
```

and:

```text
Open http://localhost:3000
```

Then:

```bash
docker compose run --rm backend python scripts/reproduce_fig5b.py
```

Explain what is simulated:

```text
RF energy harvesting
energy storage
EM
DCM
device grouping
paging
access probability
CBRA
AO collision
retries
inventory completion
```

---

# 43. Documentation Must Distinguish Three Categories

Create a table in the README/docs:

## A. Directly specified by paper

Examples:

```text
N
energy thresholds
power consumption
paging duration
T_pg
Msg durations
AO counts
DCM timers
```

## B. Digitized from paper

Example:

```text
Figure 5(a) p_in CDF
Figure 5(b) optional reference curves
```

## C. Reproduction assumptions

Examples:

```text
aperiodic paging scheduling rule
exact access-probability controller
initial energy/cycle phase
warm-up procedure
```

This distinction is mandatory.

---

# 44. Scientific Integrity

This requirement is critical.

Never alter paper-specified parameters purely to make a curve look closer to Figure 5(b).

If results differ:

1. inspect implementation,
2. verify units,
3. verify timing,
4. verify initial conditions,
5. verify p_in distribution,
6. test reasonable values of ONLY underspecified assumptions,
7. report sensitivity.

If an underspecified assumption is calibrated, document:

```text
what changed
why
range tested
effect on T99/curve
```

Never present calibration as if it came directly from the paper.

---

# 45. Diagnostics

Include a debug mode.

It should be possible to inspect a specific device and print an event trace such as:

```text
Device 417

t = -4.200 s  OFF
t = -2.013 s  reaches E_up
t = -2.012 s  ON
t = -1.994 s  DCM timer expires
t = -1.993 s  OFF
...
t = 0.214 s   first paging detected
t = 0.215 s   group = 2
t = 0.228 s   Msg1 attempt
t = 0.228 s   collision
...
t = 2.516 s   Msg1 success
t = 2.520 s   Msg3 complete
t = 2.520 s   DONE
```

This will greatly simplify debugging.

---

# 46. Performance Expectations

Target:

```text
N = 600
25-second simulation
3 strategies
```

to run comfortably on a normal laptop.

Avoid obviously quadratic operations over all device pairs.

CBRA collision handling should group by AO, not compare every device against every other device.

---

# 47. UI Responsiveness

The React application should remain responsive with:

```text
600 markers
~250 visualization snapshots
multiple curves
```

Use a single Plotly device scatter.

Memoize computed frontend data where useful.

Do not prematurely optimize beyond this.

---

# 48. Error Handling

The application must handle:

```text
backend unavailable
simulation timeout
invalid parameter
T99 not reached
missing reference curve data
missing digitized CDF
```

with readable messages.

Do not silently fail.

---

# 49. Completion Criteria

Do not consider the project complete until ALL of the following are true:

* [ ] `docker compose up --build` succeeds.
* [ ] Frontend opens on `localhost:3000`.
* [ ] Backend health endpoint works.
* [ ] Default simulation uses N = 600.
* [ ] Device-1 paper parameters are centralized.
* [ ] RF energy harvesting is physically unit-tested.
* [ ] `-36 dBm` sanity checks pass.
* [ ] EM state machine works.
* [ ] DCM pre-inventory timer works.
* [ ] DCM synchronized sleep/wake works.
* [ ] 1-group DCM works.
* [ ] 4-group DCM works.
* [ ] CBRA uses 8 AOs for Device 1.
* [ ] Msg1 collisions are actually simulated.
* [ ] Successful Msg3 produces completion times.
* [ ] Access probability control is implemented and documented.
* [ ] Warm-up/initial-condition policy is documented.
* [ ] `p_in` values are generated from digitized Figure 5(a), not arbitrary uniform RF powers.
* [ ] Figure 5(b) curves arise from the simulator.
* [ ] T50/T90/T99 are calculated from device completion times.
* [ ] `reproduce_fig5b.py` works independently of the web application.
* [ ] PNG/CSV/JSON reproduction results are generated.
* [ ] Frontend factory view displays approximately 600 interactive devices.
* [ ] Device hover works.
* [ ] Device click/inspector works.
* [ ] Timeline playback works.
* [ ] Figure 5(b) interactive chart works.
* [ ] CBRA AO inspector works.
* [ ] Device energy-history plot works.
* [ ] Paper parameters and assumptions are visibly distinguished.
* [ ] Tests pass.
* [ ] README provides Docker and local setup instructions.
* [ ] Important arXiv/published discrepancies are documented.

---

# 50. Implementation Order

Do NOT spend the first phase making the frontend beautiful.

Implement in this order:

## Phase A — Scientific Core

```text
config
units
RF energy harvesting
Figure 5(a) CDF
device model
energy model
EM
DCM
paging
CBRA
grouping
access control
metrics
```

Run tests after each module.

## Phase B — Reproduction

Implement:

```text
reproduce_fig5b.py
```

Get real curves and inspect:

```text
T50
T90
T99
```

Verify that the physical behavior is sensible.

Only when this works continue.

## Phase C — API

Wrap the exact same simulator with FastAPI.

Do NOT duplicate simulation logic.

## Phase D — React Dashboard

Implement:

```text
FactoryView
time playback
InventoryCurve
MetricsPanel
DeviceInspector
EnergyHistory
CBRAInspector
```

## Phase E — Docker + Documentation

Make the repository fully reproducible.

---

# 51. Important Behavioral Instruction for You, the Coding Agent

Do not stop after scaffolding.

Do not just create empty modules with TODOs.

Continue implementing until the system actually runs.

When encountering ambiguity from the source paper:

* inspect both PDFs,
* determine whether one version clarifies the other,
* if still ambiguous, implement and document a scientifically reasonable assumption.

Do not ask me routine implementation questions if a reasonable engineering decision can be made.

Do ask only if there is a truly blocking scientific ambiguity that cannot reasonably be isolated as an assumption.

After each major stage:

1. run the relevant tests,
2. run the simulator,
3. inspect numerical outputs,
4. fix obvious physical/unit/timing errors before continuing.

Keep the code readable and research-oriented rather than over-engineered.

---

# 52. Final Deliverable Summary

The completed repository should allow a professor to do either:

```bash
docker compose up --build
```

and interactively explore the simulation,

OR simply run:

```bash
docker compose run --rm backend python scripts/reproduce_fig5b.py
```

to reproduce Figure 5(b).

The scientific pipeline must be:

```text
Figure 5(a) p_in distribution
             |
             v
       RF received power
             |
             v
       harvesting power
             |
             v
        stored energy
             |
             v
     EM / DCM state machine
             |
             v
           Paging
             |
             v
  Access probability controller
             |
             v
       CBRA / AO selection
             |
             v
    collision / success / retry
             |
             v
          Msg3 success
             |
             v
       completion time T_i
             |
             v
       inventory ratio F(t)
             |
             v
         Figure 5(b)
```

That causal chain must remain visible in the source code, documentation, tests, and frontend.

Start by inspecting the PDFs and repository, then implement the scientific core first.
