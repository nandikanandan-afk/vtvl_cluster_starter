# Verification and validation (v0.2, PRELIMINARY)

**Verification** = does the code solve its equations correctly? **Validation** = does it match real Falcon 9 numbers?
They are reported separately. Validation is limited to the N = 9 anchors.

## A. Verification

### Unit and physics tests (`python -m unittest discover -s tests`, 27 tests, all passing at the last run)
| Required check | Test | Result |
|---|---|---|
| Total liftoff thrust identical for all N (1 N) | `test_total_liftoff_thrust_identical_for_all_N` | pass |
| Mass flow = T/(g0·Isp) in every case | `test_mass_flow_consistency` | pass |
| Engine mass equals m_ref at N = 9 for every φ, β; Akin scaled equals m_ref at 845 kN | `test_powerlaw_reference_anchor_for_all_phi_beta`, `test_akin_equals_mref_at_845kN` | pass (computed Akin scale 0.5643; the JSON's 0.56 is the rounded value) |
| Dry-mass bookkeeping; N = 9 gives m_d_ref; GLOW closes to 549,054 kg; no double counting | `test_dry_mass_reference_and_glow_closure`, `test_no_double_counting` | pass |
| β = 1, φ = 0, m_int = 0 gives N-invariant dry mass | `test_beta1_phi0_mint0_total_engine_mass_invariant` | pass |
| Mass conservation: ascent propellant is exactly P1 − R; mass-flow integral equals mass change per phase | `test_stage1_mass_bookkeeping_and_massflow` | pass |
| Reserve bookkeeping: ascent + entry + landing + margin + residual = loaded propellant; touchdown mass = dry + margin + residual | `test_reserve_bookkeeping` | pass |
| No-drag constant-gravity landing burn vs analytic solution | `test_landing_burn_matches_analytic_constant_gravity_no_drag` | pass (v within 1e-6 m/s, h within 1e-5 m) |
| Vacuum Kepler coast conserves energy and angular momentum | `test_vacuum_kepler_coast_conserves_energy_and_momentum` | pass (energy 1e-10, momentum 1e-12 relative) |
| Orbit-insertion residuals within tolerance, confirmed by an independent integrator | `test_insertion_residuals_independent_replay` | pass |
| Touchdown by independent re-integration with event detection | `test_touchdown_independent_replay` | pass |
| Chosen landing throttle is fuel-optimal over a throttle scan | `test_scanned_throttle_is_fuel_optimal` | pass |
| US76 atmosphere vs table values; RK4 is fourth-order | `test_us76_reference_values`, `test_harmonic_oscillator_fourth_order` | pass |

### Baseline run checks (`results/20261109_1839_baseline/verification_*.{csv,json}`)
* **Insertion residuals** (9 feasible reusable cases): max |Δr| = 0.94 m, |v_r| = 0.0019 m/s, |Δv_t| = 0.0021 m/s (tolerances 100 m, 1 m/s, 1 m/s). The independent DOP853 replay gives 0.94 m, 0.0020 m/s, 0.0021 m/s.
* **Touchdown:** the independent replay found a touchdown in all 9 cases; max touchdown speed 1.0003 m/s (v_td = 2 m/s). The 1.0 m/s is the numerical stop speed in the model (see ASSUMPTIONS A-LAND-CTRL), not a free result.
* **Step halving** (every RK4 step halved, kick re-optimised), required change < 10 kg: N = 5: −4.5 kg, N = 9: +1.0 kg, N = 21: −1.7 kg. **Pass.**
* **Optimizer robustness (three different starting kicks), required agreement < 10 kg: FAILED, reported as is.**
  * N = 9: two of three starts feasible (17,500.0 kg and 17,492.7 kg; spread including the baseline value 7.3 kg), the third start returned `infeasible_proven`.
  * N = 5 and N = 21: all three alternative starts returned `infeasible_proven` or `no_solution_found`, although the baseline start gave 18,171.6 kg and 18,808.8 kg.
  * Interpretation: the `status` labels in the payload search depend on the starting kick, because a poor kick gives a MECO state from which the recovery rules cannot be met. Only screens that do not depend on the trajectory (for example one engine at minimum throttle already above the acceleration cap at N = 1) are independent of the start. The `infeasible_proven` label in this study means "proven for the trajectories evaluated, by the stated analytic screen", not "proven for every possible ascent".

### Convergence of the coupled solve
Fixed point R = Rec(MECO(R)) is solved to |ΔR| < 1 kg; iteration counts are in `cases.csv` (`outer_iterations`, `inner_iterations`).

### Code defects found and fixed during the study
1. Fragile `infeasible_proven` labelling at the first iterate of the reserve: fixed by trying seven starting reserves before any verdict (the first calibration run was discarded: `results/20261109_1746_calibration_N9_SUPERSEDED_fragile_labels`).
2. A root bracket error in the landing throttle solve and an over-strict stop-speed guard caused 21 of 200 sensitivity cases and 3 of 96 map cases to die from code exceptions (N = 13 and every `a_max_land = 4` case). Fixed (bisection fallback, stop-speed guard); only those cases were rerun (`rerun_exceptions.py`; originals kept as `cases_original.csv`). The map sweep ran on the pre-fix code, and the fixed code was in place for the reruns; source hashes in the manifests reflect the files at the end of each run.
3. Kick-optimizer trials that raised an exception now count as failed trials instead of ending the case.

## B. Validation (N = 9 only)
| Anchor | Target | Model | Status |
|---|---|---|---|
| Expendable payload | 22,800 kg (1 %) | 23,644 kg at the best in-range Cd scale (0.8) | **Not reached: +3.7 %.** Range not stretched. |
| Reusable payload | 17,400-18,500 kg (target 17,500) | 17,498 kg | Met by calibrating q_entry_max (70,232 Pa), so this is a fit, not an independent check. |
| N = 9 recovery propellant | 15-35 t plausibility; 25 t (S5, GTO) | 40.6 t | **Outside the range.** |
| N = 9 landing T/W at minimum throttle | 1.6-1.8 | 1.58 | Slightly below. |

Both calibration knobs were used on payload anchors, so only the last two rows are independent plausibility checks, and both are outside their ranges. The model should not be described as validated.

## C. Not verified
* Aerodynamic descent with a constant Cd (no Mach dependence; RETALT database not used).
* Max-Q by steering only, and the landing-cap basis (`thrust_only`): modelling choices with large effects on the N ranking (ASSUMPTIONS D1, D3).
* Nozzle packing, engine-out, the flip maneuver, winds, dispersions.
