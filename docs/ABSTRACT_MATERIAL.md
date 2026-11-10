# Abstract material (PRELIMINARY: draft for the team, not final text)

Numbers come from `results/20261109_1839_baseline`, `results/20261109_1859_sensitivity`, `results/20261109_2016_maps` and `results/20261109_1754_calibration_N9_after_burn`. Cited sources are limited to those in `data/parameters_baseline.json` `meta.sources`. **Read `docs/ASSUMPTIONS.md` (D1-D5) and `docs/VERIFICATION.md` first: the headline result is not yet defensible as a single optimal N.**

## Status: completed vs planned
| Completed | Planned / not done |
|---|---|
| Parameter database with provenance; engine and dry-mass models; US76 atmosphere | Max-Q throttle bucket (identical for all N) to remove the steering-only artifact |
| 2-D ascent, exact 200 km orbit insertion, downrange recovery with coupled reserve | Landing-cap basis per the database definition (thrust + drag) with a robust calibration |
| Calibration at N = 9; baseline N = 1...27 (odd); reduced one-at-a-time and map sweeps | Robust multi-start search so feasibility labels do not depend on the starting kick |
| Independent replays of insertion and touchdown; step-halving test | Full sensitivity grid, N = 23...27 revisited, even N |
| | Mach-dependent descent aerodynamics (RETALT database, S20); engine-out; nozzle packing; cost |

## Methodology (draft paragraph)
We model a reusable LOX/RP-1 booster with constant total sea-level thrust (7,605 kN, S1) split over N identical engines (odd N = 1...27). Engine mass follows a calibrated fixed-plus-power-law relation, with the Akin mass-estimating relation (S7) as an alternative; non-engine dry mass is held fixed. The ascent is a 2-D planar point-mass simulation over a rotating spherical Earth with US Standard Atmosphere 1976 drag; a vertical rise, pitch kick and gravity turn are followed by a linear-tangent second stage, and the payload is the largest mass that reaches a 200 km circular orbit exactly. The booster is recovered downrange without boostback: coast, a retrograde entry burn sized to a peak dynamic-pressure limit, aerodynamic descent, and a one-burn landing with 1 or 3 engines at constant throttle. The recovery propellant reserve is solved as a fixed point with the ascent. The pitch kick is re-optimized separately for every engine count. Uncertain inputs are swept, not optimized.

## Equation summary
* Thrust: T = u·T_vac − p(h)·A_e, with T_vac = r_vs·T_sl, A_e = (T_vac − T_sl)/p0, mass flow ṁ = u·T_vac/(g0·Isp_vac).
* Minimum throttle (57 % of sea-level thrust, S1) converts to a mass-flow fraction u_min = (0.57 + r_vs − 1)/r_vs = 0.6026.
* Engine mass: m_e(N) = m_ref[φ + (1−φ)(9/N)^β]; booster dry mass m_d(N) = m_nonengine + N(m_e(N) + m_int).
* Dynamics: ṙ = v_r, θ̇ = v_t/r, v̇_r = v_t²/r − μ/r² + (T e_r − D v_rel,r/|v_rel|)/m, v̇_t = −v_r v_t/r + (T e_t − D v_rel,t/|v_rel|)/m.
* Reserve: R = (1 + ε_m)(m_entry + m_landing) + m_res, with R = Rec(MECO(R)).

## Parameters and assumptions
See `results/20261109_1839_baseline/tables/inputs_with_sources.md` (every input with value, units, source and confidence) and `docs/ASSUMPTIONS.md`. Key data issues reported, not hidden: the 2 % inconsistency among Isp_sl, Isp_vac and the thrust ratio; the 2 % mismatch among upper-stage thrust, Isp, burn time and propellant; and the unknown payload content of the 549,054 kg liftoff mass (assumed to exclude payload).

## Verification paragraph (draft)
Integrator accuracy was checked against the analytic constant-gravity landing burn and a vacuum Kepler coast, and the payload changed by 4.5 kg, 1.0 kg and 1.7 kg (N = 5, 9, 21) when every step was halved. Orbit-insertion residuals were below 1 m in radius and 0.003 m/s in velocity and were reproduced by an independent adaptive integrator; touchdowns were re-found independently at 1.0 m/s. A three-start optimizer test **failed**: from other initial pitch kicks, N = 5 and 21 returned no feasible solution and N = 9 was feasible in two of three starts (agreeing within 8 kg), so feasibility labels depend on the search start.

## Preliminary results (draft paragraph, to be revised after D1 and D3)
Calibrated at N = 9, the model reproduces the reusable anchor by construction (17,498 kg), but misses the expendable anchor by +3.7 % within the allowed parameter range and gives a recovery reserve of 40.6 t, above the 15 to 35 t plausibility range. Under the baseline assumptions, the reusable payload peaks at N = 21 (18,809 kg), only 0.83 % above N = 7 (18,653 kg), with a local minimum near N = 11 (16,883 kg); N = 21 is the largest count that produced a feasible solution, so the optimum lies at the edge of the evaluated feasible set. Across 25 one-at-a-time cases the best N was 21 in 18, 7 in 4, 17 in 2 and 13 in 1.

## Defensible findings (3 to 5)
1. Within this model, the payload cost of recovery is large: the best reusable case carries 4,921 kg less than the best expendable case, and the reserve is 30.6 to 44.7 t depending on N.
2. The payload ranking among feasible engine counts is small (hundreds of kg, under 1 % between the two best) and does not single out one N: best N changes with minimum throttle, φ, landing-acceleration cap and descent Cd.
3. Higher minimum throttle shrinks the feasible set: at 70 % only N = 13 and 21 were feasible in the sweep.
4. The ranking is sensitive to how max-Q is enforced: with steering-only max-Q at 35 kPa, expendable payload rises with N, whereas with max-Q relaxed to 40 kPa it falls with N, as engine mass alone implies. Any N-ranking claim must be tied to a max-Q treatment.
5. The database definition of the landing acceleration cap (thrust plus drag) could not be calibrated; results use the thrust-only variant.

**Not defensible yet:** a single optimal engine count; anything about N above 21; a statement that proves a given N cannot recover.

## Limitations and future work
Constant descent Cd (use RETALT Mach-dependent data, S20); no flip maneuver, winds or dispersions; no engine-out; no nozzle packing in 3.66 m (flag: 27 engines have a total exit area of 58.5 % of the base area, not a geometry check); instantaneous staging; single-burn landing; calibration used both knobs on payload anchors, so only the reserve and T/W checks are independent, and both fall outside their ranges.

## Figure captions
See `results/20261109_1839_baseline/figures/captions.md` (figures 1 to 6; fig. 5 has parts a and b).
