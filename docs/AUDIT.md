# Audit of the v0.1 starter (`vtvl_cluster_starter`)

Date: 2026-11-09. Scope: every file in `vtvl/`, `run_study.py`, `verify_results.py`,
`tests/`, `README.md`, the override JSONs and the legacy `results/` folders.

## 0. Input files

| Expected | Found | Action |
|---|---|---|
| `data/parameters_baseline.json` | Not in repo; found at `~/Downloads/parameters_baseline.json` | Copied byte-identical into `data/` |
| `docs/parameter_dataset.md` | Not in repo; only a **PDF** (`~/Downloads/Falcon 9-Class ... Study.pdf`) | PDF copied to `docs/parameter_dataset.pdf`; text extraction in `docs/parameter_dataset.md` (tables partly scrambled, PDF is authoritative) |

The legacy outputs (ideal-Δv proxy) were moved to `results/legacy_v0_1/` so they can't be
mixed up with new results. Tracked `__pycache__/*.pyc` files were untracked and a `.gitignore` added.

## 1. Architecture of the starter and what is reused

| Module | v0.1 content | Reuse |
|---|---|---|
| `config.py` | Frozen dataclasses `Vehicle`, `Mission`, `Design`, `Numerics` with hard-coded defaults | Pattern only (frozen dataclasses). All physical values now come from the JSON. |
| `engines.py` | `m_e = m_ref[φ + (1-φ)(N_ref/N)^β]`, `m_d = m_nonengine + N(m_e + m_int)` | Equations kept. `m_nonengine` is now derived from `m_d_ref`, not given. |
| `landing.py` | 1-D terminal descent from a prescribed 2 km / 200 m/s state, coast + one constant-throttle burn, SLSQP | Philosophy kept (no "T/W > 1 ⇒ infeasible", restricted control family stated, independent re-check). Dynamics replaced with 2-D polar. |
| `performance.py` | Two-stage ideal-Δv payload proxy, fixed 9,400 m/s | **Replaced** by integrated ascent + exact orbit insertion. |
| `study.py` | Couples dry mass → landing → reserve → payload | Coupling idea kept. A fixed-point iteration on R now replaces the one-way chain. |
| `run_study.py` | CLI, `ProcessPoolExecutor`, CSV with blanks for NaN, manifest with source hashes | CSV/manifest/hash approach reused. |
| `verify_results.py` | Tight re-integration with a ground event | Concept reused: independent SciPy `solve_ivp` (DOP853) replay of touchdown **and** orbit insertion. |
| `tests/test_model.py` | 13 unit tests | Mass-anchor and "cannot hover ≠ cannot land" ideas kept. Rewritten for the new model. |

## 2. Inventory of every numeric value in the v0.1 code

"JSON" = `data/parameters_baseline.json` path. "Removed" = the quantity no longer exists as
an input because it is now computed.

| File:line | Represents | Old | New | Why |
|---|---|---|---|---|
| config.py:4 | g0 | 9.80665 | 9.80665 (`mission.earth_model.g0`) | Same constant, now read from JSON |
| config.py:10 | Total SL thrust | 7,607,000 N | **7,605,000 N** (`engine.total_sl_thrust`, S1) | 845 kN × 9 is official; 7,607 kN is from S5/S13 |
| config.py:11 | Diameter | 3.7 m | **3.66 m** (`booster.diameter`, S1) | Official value |
| config.py:12 | N_ref | 9 | 9 (`engine.reference_engine_count`) | Same |
| config.py:14 | Liftoff mass cap | 550,000 kg | 549,054 kg (`booster.glow_full_vehicle`, S3) used as **closure** at N = 9 with no payload | v0.1 off-loaded propellant when payload grew, which contradicts the fixed-tank assumption |
| config.py:15 | Stage-1 propellant | 410,000 kg | **404,654 kg**, recomputed in code (`booster.propellant_capacity`) | Closes 549,054 kg at N = 9 |
| config.py:16 | Non-engine dry mass | 20,000 kg | **21,545 kg derived** = 26,000 − 9·(470 + 25) | Derived from `m_d_ref`, so there is no double counting |
| config.py:17 | m_ref | 470 kg | 470 kg (S13, low confidence) | Same value, now sourced |
| config.py:18 | β | 0.85 | **0.90** (assumption, 0.8–1.0) | JSON baseline |
| config.py:19 | m_int | 35 kg | **25 kg** (assumption, 0–50) | JSON baseline |
| config.py:20 | Ascent Isp (constant) | 300 s | **Removed.** Thrust = u·T_vac − p·A_e, ṁ = u·T_vac/(g0·Isp_vac) | Altitude-dependent thrust |
| config.py:21 | Landing Isp | 282 s | **Removed.** Derived SL Isp = 288.35 s (see §3.2) | Same engine model in every phase |
| config.py:22 | Upper dry | 4,500 kg | 4,500 kg (S5) | Same |
| config.py:23 | Upper propellant | 105,000 kg | **111,500 kg** (S5) | JSON |
| config.py:24 | Upper Isp | 348 s | 348 s (S5) | Same |
| config.py:40 | Terminal-descent start altitude | 2,000 m | **Removed** | Landing ignition is now solved |
| config.py:41 | Touchdown velocity | −0.5 m/s | Tolerance `v_td` = 2.0 m/s (assumption) | JSON |
| config.py:43 | Required ideal Δv | 9,400 m/s | **Removed** | Exact 200 km circular insertion |
| config.py:45 | Earlier recovery propellant | 8,000 kg | **Removed** | Entry burn simulated from the actual MECO state |
| config.py:46 | Landing margin | 0.10 (landing only) | ε_m = 0.10 on **entry + landing** (assumption) | Prompt §6.4.5 |
| config.py:47 | Trapped residual | 300 kg | **1,500 kg** (assumption, 500–3,000) | JSON |
| config.py:48 | Landing propellant cap | 25,000 kg | **Removed** (25 t is now a plausibility check, S5) | A cap would create an artificial boundary |
| config.py:49–50 | Burn-time bounds | 2 / 120 s | Removed. The ignition root solve has no artificial bounds | — |
| config.py:51 | Landing accel cap | 5 g | **3 g** (S17) | JSON |
| config.py:52 | Terminal q cap | 80 kPa | Replaced by `q_entry_max` (calibrated) on post-entry-burn peak q | JSON |
| config.py:53 | Liftoff T/W screen | 1.2 | Removed as a screen. Liftoff T/W is reported (must be > 1 to lift off) | Unsourced |
| config.py:54 | Landing engines | (1, 3) | (1, 3) (`engine.landing_burn_engines_allowed`) | Same |
| config.py:56–57 | ρ0, scale height | 1.225, 8,500 m | **US Standard Atmosphere 1976** | JSON |
| config.py:58 | Descent Cd | 0.8 | **1.0** (assumption, 0.7–1.4) | JSON |
| config.py:89–92 | Design defaults φ, u_min, entry speed | 0.25, 0.40, 200 m/s | φ = 0.07; u_min = 0.57 SL-thrust fraction (0.6026 mass flow); entry speed removed | JSON |
| config.py:107–117 | Solver settings | rtol 2e-7 etc. | New `Numerics` (fixed-step RK4 sizes, root tolerances) recorded in every manifest | Numerical settings, not physics |
| landing.py:45 | Density clip | −5 km / 100 km | Removed (US76 with exponential extension above 86 km) | — |
| landing.py:174, 189, 211–215 | Coast bound 30 s, scale 10, multistart guesses | various | Removed | New solver |
| landing.py:148–152 | Constraint scalings | /1000, /200, /1e5 | Removed | New solver |
| run_study.py:150, 165–167 | Default grids | N = 1…19, φ {.1,.25,.4}, u {.2,.4,.6}, speed {150,200,250} | N = 1,3,…,27; sweeps from JSON ranges | Prompt §6.6, §8 |
| verify_results.py:255, 275 | Replay tolerances | 1e-11, 0.02 s, 10 s | DOP853 rtol 1e-10 independent replay | — |
| example_overrides.json, g4.json, g6.json | v0.1 overrides | — | Obsolete (old schema) | Kept for history, unused |

## 3. Errors and weak assumptions found

### 3.1 Starter model
1. **Payload from an ideal-Δv proxy.** The 9,400 m/s target includes a fixed loss allowance, so gravity and drag losses don't respond to N or to the MECO state. This doesn't demonstrate orbit insertion.
2. **Fixed 8,000 kg "earlier recovery" allowance.** Entry-burn propellant doesn't depend on the MECO state, so the R ↔ MECO coupling is missing.
3. **1-D terminal descent from a prescribed state** (2 km, 200 m/s). That state isn't linked to ascent and has no horizontal velocity.
4. **Unsourced masses and thrust** (7,607 kN, 3.7 m, 20 t non-engine, 410 t propellant, 105 t upper propellant, 300 kg residual).
5. **Mass closure.** `P1 = min(capacity, 550 t − …)` silently off-loads propellant as payload grows, which conflicts with full tanks for every N.
6. **The margin applied only to the landing burn.** The 8 t allowance carried no margin.
7. **Constant-Isp engines.** There's no pressure-thrust term, so throttle was a thrust fraction with no conversion.
8. **Liftoff-T/W screen of 1.2** was arbitrary. **The 25 t landing-propellant cap** could create a false feasibility boundary.
9. **Default min throttle 0.40** (a forum value) was used as baseline. The official value is 0.57.

### 3.2 Data issues in the JSON that must be handled (reported, not hidden)
1. **Engine Isp/thrust set is ~2 % inconsistent.** With a fixed-geometry nozzle, T_vac/T_sl = Isp_vac/Isp_sl. 312/283 = 1.1025 ≠ 1.082. **Resolution (baseline):** keep `r_vs` = 1.082 (sets A_e, as the JSON says) and `Isp_vac` = 312 s (sets ṁ, as the JSON says), giving a derived **Isp_sl = 288.35 s** (+1.9 % vs 283 s). Sensitivity case: Isp_sl = 283 s with r_vs = 1.082 ⇒ Isp_vac = 306.2 s (just below the 309–315 s range; flagged).
2. **Upper-stage set ~2 % inconsistent.** 981 kN, 348 s ⇒ ṁ = 287.45 kg/s. 111.5 t then burns in 387.9 s, not 397 s; 397 s would need 114.1 t. **Resolution:** keep thrust (official), Isp and P2 (S5). Burn time is an output (≈ 388 s at full throttle, longer when throttled for the 4 g cap). Reported.
3. **549,054 kg may include payload.** We assume it does not (JSON note). If it did, P1 would be ~22.8 t smaller (~382 t, outside the 395–418.7 t range). Reported as a limitation.
4. **Total thrust typo** (7,686 kN in S1 Table 2-1). 7,605 kN is used.

### 3.3 Min-throttle conversion (shown as required)
The official 57 % is a fraction of rated **sea-level thrust** at sea level. With
T = u·T_vac − p·A_e, A_e = (T_vac − T_sl)/p0 and T_vac = r_vs·T_sl:

    u·T_vac − (T_vac − T_sl) = 0.57·T_sl   ⇒   u_min,flow = (0.57 + r_vs − 1)/r_vs = (0.57 + 0.082)/1.082 = 0.6026

Sweep endpoints: 0.40 → 0.4455 and 0.70 → 0.7227 (mass-flow fractions). The same
conversion is applied to every swept value, in code (`engines.massflow_fraction_from_sl_thrust_fraction`).

Derived engine values at N = 9: T_vac,e = 914.29 kN, A_e = 0.6838 m² (exit diameter 0.933 m,
consistent with the 0.92 m engine diameter in S13), ṁ_max = 298.82 kg/s.

## 4. Minimum set of changes and implementation order

1. `params.py`: JSON loader with provenance, range validation, override-by-name. Every run writes the resolved set. `data/parameters_supplement.json` holds the few labeled assumptions the JSON states only in prose (fairing split 1,900/500 kg and the 10 Pa jettison trigger; Cd scale 0.8–1.2).
2. `atmosphere.py`: US76 0–86 km, exponential above.
3. `integrate.py`: fixed-step RK4 with exact event location (fast pure-Python scalar core). Verified against analytic solutions and an independent SciPy DOP853 replay.
4. `engines.py`: thrust/mass-flow model, throttle conversion, power-law and Akin-scaled engine mass, dry mass.
5. `ascent.py`: 2-D polar point mass over a rotating spherical Earth, gravity-turn stage 1 with an optimized pitch kick, linear-tangent stage 2 with an exact 200 km circular insertion solve.
6. `landing.py` + `recovery.py`: coast → entry burn (q-sized) → aerodynamic descent → landing burn (k ∈ {1, 3}, constant u, ignition root, u-scan), with feasibility status labels.
7. `performance.py`: payload evaluation with a joint fixed point on (payload, R), plus a per-N pitch-kick optimization.
8. `calibration.py`: two knobs at N = 9 (ascent Cd scale; q_entry_max), then frozen.
9. `study.py` / `run_study.py`: N sweep, sensitivity, multiprocessing, outputs. `figures.py`.
10. Tests at every stage, then `docs/VERIFICATION.md`, results, `results_summary.md` and `ABSTRACT_MATERIAL.md`.
