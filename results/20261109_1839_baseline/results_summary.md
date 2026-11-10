# Results summary (PRELIMINARY)

> Every number below is read from files in `results/20261109_1839_baseline`, `results/20261109_1859_sensitivity`, `results/20261109_2016_maps` and `results/20261109_1754_calibration_N9_after_burn` by `make_summary.py`.
> **Model variant:** thrust-only landing acceleration cap, max-Q enforced by steering only (no throttle bucket),
> q_entry_max enforced after the entry burn only. See `docs/ASSUMPTIONS.md` (D1-D5) before using any conclusion.

## Calibration at N = 9 (frozen for all other N)
* Ascent Cd scale = 0.8 (range 0.8-1.2) gives an expendable payload of 23,644 kg, +3.70 % vs the 22,800 kg anchor: **anchor NOT reached within 1 %** (status `anchor_not_reachable`); the range was not stretched.
* q_entry_max = 70,232 Pa gives a reusable payload of 17,498 kg at N = 9 in the baseline run (target 17,500 kg, band 17,400-18,500 kg).
* N = 9 recovery reserve R = 40,575 kg (entry 30,321 kg, landing 5,201 kg), vs the 15,000-35,000 kg plausibility range and the 25,000 kg S5 estimate (a GTO case): **above the range**.
* N = 9 landing thrust-to-weight at minimum throttle at touchdown mass = 1.58, vs 1.6-1.8 expected: **slightly below**.

## Case status counts
* Baseline: {'expendable/feasible': 14, 'reusable/feasible': 9, 'reusable/infeasible_proven': 3, 'reusable/no_solution_found': 2}
* Sensitivity (reduced N set): {'feasible': 119, 'infeasible_proven': 50, 'no_solution_found': 31}; maps: {'feasible': 52, 'infeasible_proven': 35, 'no_solution_found': 9}.
* `infeasible_proven` carries an analytic reason in `cases.csv`; `no_solution_found` is a solver/search failure, **not** proof of infeasibility.

## 1. Which N maximizes payload, and by how much over the next best?
Reusable baseline: best N = 21 with 18,809 kg; next best N = 7 with 18,653 kg;
gap 156 kg (0.83 %). Counts within 1 % of the best: 7;21.
Feasible counts: 5;7;9;11;13;15;17;19;21; infeasible_proven: 1;25;27; no_solution_found: 3;23.
Expendable reference (no recovery): best N = 27, gap to second 6.4 kg (0.027 %).

## 2. How does dry mass change with N?
Booster dry mass rises from 24,761 kg (N = 1) to 26,000 kg (N = 9) to 27,499 kg (N = 27); the non-engine part is fixed at 21,545 kg.

## 3. How does minimum throttle limit recovery, and which constraints are active?
* Among feasible baseline cases the landing burn uses k = 1 or k = 3 as follows: {5: 1, 7: 1, 9: 1, 11: 1, 13: 1, 15: 3, 17: 3, 19: 3, 21: 3}; constant throttle u = {5: 0.614, 7: 0.828, 9: 1.0, 11: 1.0, 13: 1.0, 15: 0.635, 17: 0.709, 19: 0.783, 21: 0.856}.
* The peak landing acceleration occurs at: {'touchdown': 9}. Cases with k = 3 sit on the 3 g cap at touchdown (cap active); cases at u = 1 with k = 1 are limited by available thrust, not by the minimum throttle.
* Feasibility vs minimum throttle: `figures/fig4_feasibility_umin_vs_N.png`. At 70 % minimum throttle only the counts in `tables/sensitivity_best_N.md` (row `u_min=0.7`) are feasible.
* The entry-burn rule (drag plus one engine at minimum throttle above the 4 g cap) is what makes N = 1 and N >= 25 `infeasible_proven` in the baseline.

## 4. How much propellant is reserved for recovery?
Feasible baseline reserve R ranges from 30,621 kg (N = 21) to 44,722 kg (N = 11).

## 5. Is the optimum interior or at a boundary?
Baseline: best_is_boundary_of_feasible_set = True (N = 21 is the largest feasible count; N = 23 is `no_solution_found` and N >= 25 `infeasible_proven`). The optimum is **at the edge of the feasible set, not an interior optimum**, and N = 23 could not be evaluated, so whether the true optimum lies further out is **not established**.

## 6. Does it move under sensitivity?
One-at-a-time sweeps (N in 3, 5, 7, 9, 13, 17, 21, 25): distribution of best N over the 25 cases with a feasible N: {7: 4, 13: 1, 17: 2, 21: 18}. Maps (min throttle x beta, min throttle x phi): {5: 1, 7: 1, 17: 3, 21: 7}.
It changes with u_min, phi, a_max_land and Cd_desc; see `figures/fig5a_best_N_sensitivity.png` and `fig5b_best_N_maps.png`.

## 7. Is the payload gap larger than numerical and modeling uncertainty?
Numerical (see `docs/VERIFICATION.md`):
  - N=5: step-halving change -4.5 kg (pass=True); three-start payloads [nan] kg, statuses [infeasible_proven;no_solution_found;infeasible_proven], spread incl. baseline nan kg (pass=False)
  - N=9: step-halving change +1.0 kg (pass=True); three-start payloads [17500.0;17492.7] kg, statuses [infeasible_proven;feasible;feasible], spread incl. baseline 7.3 kg (pass=False)
  - N=21: step-halving change -1.7 kg (pass=True); three-start payloads [nan] kg, statuses [infeasible_proven;no_solution_found;infeasible_proven], spread incl. baseline nan kg (pass=False)
Modeling: **no.** The baseline gap between N = 21 and N = 7 is 0.83 %, smaller than the swing in best N under single-parameter changes, and the N ranking is entangled with the max-Q steering artifact (expendable payload rises with N at 35 kPa but falls with N at 40 kPa; `docs/ASSUMPTIONS.md` D3).

## 8. Supported and unsupported conclusions
Supported (within this model variant, weakly): the recovery reserve is tens of tonnes (section 4) and the best reusable case carries 4,921 kg less payload than the best expendable case; the payload solve itself is numerically converged (step halving changes payload by a few kg, insertion residuals below 1 m).
At the baseline starting kick, N = 1, 25 and 27 were labelled `infeasible_proven` and N = 3 and 23 `no_solution_found`; because of the robustness failure below these labels are **suggestive, not established**.
**Optimizer robustness FAILED the three-start test** (see section 7): from other starting pitch kicks N = 5 and N = 21 found no feasible solution at all, and N = 9 only 2 of 3 times, so `infeasible_proven`/`no_solution_found` labels in the payload search are conditional on the starting kick and are **not** intrinsic properties of N (only screens that do not depend on the kick, such as one engine at minimum throttle exceeding the cap at N = 1, are). The feasible-N window is therefore **not established**.
Not supported: a single optimal N; any claim about N > 21; any claim that more engines raise payload through physics (the trend is partly a max-Q artifact); agreement with Falcon 9 beyond the N = 9 anchors (expendable anchor missed by +3.7 %, reserve and T/W outside the plausibility ranges).
