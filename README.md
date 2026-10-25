# VTVL engine-cluster trade: runnable research starter

**Status: conceptual preliminary-design model, not a validated Falcon 9 model,
not flight software, and not a full launch-to-orbit simulation.**

The intended question is whether a preferred first-stage engine count changes
when propulsion dry mass, minimum throttle, landing fuel, and payload are coupled.
The current code resolves a *restricted terminal-landing problem* and feeds its
fuel requirement into a *two-stage ideal-delta-v payload proxy*. It does not yet
solve the complete ascent/reentry/landing optimal-control problem.

## Quick start

Use Python 3.10 or newer. Run commands from this directory. A virtual environment
is recommended. No C++ build, GPU, or proprietary vehicle data are needed.

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run_study.py --mode baseline --out results/my_baseline
python run_study.py --mode grid --physics analytic --starts 8 --out results/my_grid
python verify_results.py results/my_baseline
```

The included numerical results were generated with Python 3.13.5, NumPy 2.3.5,
and SciPy 1.17.0; `requirements-tested.txt` records those package versions.
Generic dependency ranges support other compatible installations, but each new
installation should run the tests and retain its own manifest.

For the atmospheric four-factor grid (more expensive):

```bash
python run_study.py --mode grid --physics drag --workers 4 --out results/my_drag_grid
```

For a smaller atmospheric cross-check:

```bash
python run_study.py --mode grid --counts 3 5 9 --phi 0.10 0.25 0.40 \
  --throttle 0.20 0.40 0.60 --speeds 200 --out results/my_crosscheck
```

The baseline and cross-check finish much sooner than the full atmospheric grid.
Difficult failed optimization branches can dominate runtime. Increase multistarts
and investigate failed cases instead of interpreting optimizer failure as physical
infeasibility. Parallelism is across design cases, not inside the integrator.

## One consistent vehicle family

Use a **generic Falcon-9-class, LOX/RP-1, two-stage vehicle with a downrange,
propulsively recovered first stage and an expendable upper stage**. The name
identifies the scale and architecture, not a reconstruction of SpaceX hardware.
All engines within a configuration are identical scaled conceptual engines.
Changing N does NOT mean installing N unchanged Merlin engines.

Only total sea-level thrust (7.607 MN), diameter (3.7 m), and the nine-engine
reference architecture are public SpaceX scale anchors. The other numerical
parameters below are assumptions, even where they resemble public estimates.
Do not cite this code as a source for real-engine mass or throttle limits.

| Parameter | Baseline | Status |
|---|---:|---|
| Total first-stage sea-level thrust | 7.607 MN | SpaceX scale anchor |
| Diameter | 3.7 m | SpaceX scale anchor |
| Reference engine count | 9 | Reference architecture |
| Gross liftoff mass cap | 550,000 kg | Assumed cap, not exact fixed mass |
| First-stage propellant capacity | 410,000 kg | Assumed tank-capacity proxy |
| Nonengine booster dry mass | 20,000 kg | Assumed; includes fixed recovery hardware |
| Reference engine mass | 470 kg | Assumed; not manufacturer-verified |
| Extra stage integration mass | 35 kg/engine | Assumed; separate from engine internal overhead |
| Engine mass exponent beta | 0.85 | Assumed; must be calibrated/sensitivity-tested |
| First-stage effective ascent Isp | 300 s | Assumed altitude-averaged value |
| Terminal landing Isp | 282 s | Assumed, constant with altitude/throttle |
| Upper-stage dry mass | 4,500 kg | Assumed retained dry-mass lump |
| Upper-stage propellant | 105,000 kg | Assumed fixed capacity/load |
| Upper-stage Isp | 348 s | Assumed fixed value |
| Required ideal two-stage delta-v | 9,400 m/s | Assumed LEO-class proxy, including loss allowance |
| Earlier recovery propellant | 8,000 kg | Assumed; consumed before terminal-descent boundary |
| Terminal-descent starting altitude | 2,000 m | Prescribed boundary, not an ignition altitude |
| Baseline downward entry speed | 200 m/s | Prescribed boundary, not stage-separation speed |
| Terminal velocity target | -0.5 m/s | Assumed; upward is positive |
| Landing fuel margin | 10% of nominal burn | Assumed carried mass, not a reliability confidence level |
| Trapped/unusable residual | 300 kg | Assumed, remains aboard at touchdown |
| Maximum landing proper acceleration | 5 g0 | Assumed non-gravitational load cap, includes drag |
| Landing burn duration bounds | 2 to 120 s | Assumed |
| Terminal dynamic-pressure cap | 80 kPa | Assumed, NOT an ascent max-Q constraint |
| Sea-level density / density scale height | 1.225 kg/m3 / 8,500 m | Illustrative exponential atmosphere |
| Base-first drag coefficient | 0.8 | Assumed constant; no aerodynamic calibration |

There is no fairing-jettison event. The upper-stage dry-mass lump is retained
through its ideal burn. Nozzle packaging, engine diameter, feed systems, center
of mass, gimbal clearance, landing-leg sizing, and thrust-structure redesign
are not validated. Consequently a mathematically feasible N is not necessarily
a buildable architecture.

## Four independent experimental factors

The default grid is N = 1,3,5,...,19; fixed-engine-mass fraction phi =
0.10,0.25,0.40; minimum throttle = 0.20,0.40,0.60; and downward terminal-entry
speed = 150,200,250 m/s. This gives 270 design-condition cases.

Landing propellant and payload are **outputs**, not extra free sweep variables.
A prescribed landing-fuel budget can be a separate feasibility experiment, but
must not replace solving the fuel requirement when assessing payload effects.

N is an architecture decision; phi is a mass-model uncertainty; minimum throttle
is an engine-technology parameter; entry speed is a recovery boundary condition.
Do not optimize uncertain parameters to conveniently favorable values. Compare
N within each fixed condition, then summarize the optimum across uncertainties.

Beta, drag coefficient, engine-interface mass, recovery allowance, load cap, and
fuel margin are useful second-round sensitivity variables. Their default values
are not data-fitted. Use `--config example_overrides.json` or Python dataclass
`replace` to change them. CLI physics and start-count options override their
JSON counterparts.

## Equations and bookkeeping

At constant total thrust T0, each engine has sea-level thrust Te = T0/N. The
engine mass model is

    me = mref * [phi + (1-phi)*(Nref/N)**beta]
    mdry = mnonengine + N*(me + mintegration)

This is equivalent to a fixed mass per engine plus a thrust-dependent term.
At N=Nref the reference engine mass is unchanged as phi varies. Do not count
stage-side plumbing/interface overhead again inside the engine mass.
For beta=1, phi=0, and zero interface overhead, total engine mass is independent
of N; that limiting case is tested.

Terminal descent uses upward-positive velocity:

    dh/dt = v
    dv/dt = [T - 0.5*rho(h)*Cd*A*v*abs(v)]/m - g0
    dm/dt = -T/(Isp*g0)

`physics=analytic` uses the exact no-drag, constant-gravity, constant-thrust
solution. `physics=drag` integrates an exponential-atmosphere, constant-Cd model
with SciPy `solve_ivp`. Both hold sea-level thrust and Isp constant over the low
altitude descent. Neither is a high-fidelity aerodynamic model.

The engine is off during a free coast. During the burn, throttle u must satisfy
umin <= u <= 1, and T=k*u*T0/N. The code enumerates k=1 and k=3, where k<=N.
For the default odd-N concept these can represent a central engine or the
central engine plus an opposed pair. Actual layout and torque feasibility are
NOT checked. A user-selected `--landing-engines 1` makes a controlled comparison
with single-engine-only landing. k does not change within a burn in version 0.1.

The inner optimizer chooses coast duration (hence ignition altitude), burn
duration, and a constant throttle for each k. SLSQP uses deterministic multiple
starts and scaled constraints. Terminal altitude and velocity are checked
separately from the optimizer success flag. Loads, terminal dynamic pressure,
monotone descent, burn duration, and propellant capacity are constrained.
The landing proper-acceleration cap uses (thrust + drag)/mass, not thrust/mass
alone and not net inertial acceleration including gravity. Thrust/mass is also
reported separately. Dense path checks are numerical samples, not a mathematical
continuous-time feasibility certificate.

**Not being able to hover is not an automatic landing failure.** Ignition timing
is free, and the code permits minimum-thrust/weight greater than one. No hover
condition is imposed. Conversely, permission to coast does not allow arbitrary
rapid on/off thrust pulsing; this version permits one powered burn.

If the nominal landing burn consumes B kg:

    initial_landing_propellant = (1 + margin)*B + trapped_residual
    propellant_at_touchdown = margin*B + trapped_residual
    reserve_at_MECO = earlier_recovery_propellant + initial_landing_propellant

The margin is included in the landing dynamics. Earlier recovery propellant is
carried during ascent but is assumed consumed BEFORE the terminal entry state.
It is not counted again in the landing mass. No nominal thrust-ramp/startup fuel
model is included.

For candidate payload L, upper-stage wet mass U, booster dry mass D, and reserve R:

    P1 = min(P1_capacity, M0_cap - D - U - L)
    M0 = D + P1 + U + L
    M_MECO = D + R + U + L
    dv1 = g0*Isp1*log(M0/M_MECO)
    dv2 = g0*Isp2*log((U+L)/(D2+L))

The payload root closes dv1+dv2=required_ideal_delta_v. First-stage ascent uses
P1-R, not P1; the retained reserve cannot be spent twice. Maximum gross mass and
first-stage tank capacity are both enforced. The upper stage is held fixed.

This is a **payload proxy**. A total ideal-delta-v budget does not demonstrate
orbital insertion, prove an achievable staging state, or verify ascent loads.
The code does not obtain its descent boundary from ascent. The earlier recovery
reserve is not optimized. Those are the most important limits of version 0.1.

## Files and API

`vtvl/config.py` owns immutable configuration; `engines.py` owns mass scaling;
`landing.py` owns dynamics, controls, and landing constraints; `performance.py`
owns mass closure and the payload proxy; `study.py` couples the calculations.
`run_study.py` handles sweeps and provenance. `verify_results.py` independently
reintegrates accepted controls and locates touchdown with a ground-crossing event.

```python
from dataclasses import replace
from vtvl import Design, Vehicle, Mission, Numerics, evaluate_design

vehicle = Vehicle()
mission = Mission()
design = Design(engine_count=9, fixed_engine_mass_fraction=0.25,
                min_throttle=0.40, terminal_entry_speed_m_s=200.0)
result = evaluate_design(design, vehicle, mission, Numerics(physics='drag'))
print(result['landing_status'])
print(result['payload_proxy_kg'])

# A controlled sensitivity, changing only one assumption:
heavier_interfaces = replace(vehicle, integration_mass_per_engine_kg=70.0)
comparison = evaluate_design(design, heavier_interfaces, mission)
```

## Outputs and interpretation

`cases.csv` retains every case, including failures. Failed numeric outputs are
blank rather than zero. `best_counts.csv` compares N within identical phi,
throttle, and speed conditions and reports both the maximum and counts within
1% of it. `manifest.json` records all assumptions, grid values, solver settings,
software versions, run time, and Python source hashes.

Important columns: `booster_dry_kg`, `landing_active_engines`,
`landing_burn_propellant_kg`, `landing_loaded_landing_propellant_kg`,
`recovery_reserve_at_meco_kg`, `landing_throttle`, `landing_coast_s`,
`landing_ignition_altitude_m`, `landing_peak_proper_accel_g`,
`landing_peak_thrust_accel_g`, `payload_proxy_kg`, and `landing_status`.
`landing_peak_dynamic_pressure_pa` is a terminal-descent quantity only; in the
analytic benchmark it is a diagnostic evaluated from the illustrative density,
not a constrained aerodynamic flight result.

`FEASIBLE_RESTRICTED_CONTROL` means an accepted trajectory was found in the
chosen coast/constant-throttle family. `NO_FEASIBLE_SOLUTION_FOUND` does NOT
prove an architecture impossible. Some failures have a specific minimum-thrust
versus allowed-touchdown-mass/load-cap rejection in the message; others are just
optimizer failures. `landing_optimizer_success=False` can accompany a feasible
candidate if physical residual checks pass despite the solver exit status;
inspect and rerun these before publication. Successful optimization does not
prove global optimality either.

Included data: a 10-case atmospheric engine-count baseline, a 270-case no-drag
four-factor sweep, and a 27-case atmospheric cross-check at N=3,5,9 and entry
speed 200 m/s. The 270-case atmospheric grid is supported but is NOT included
as completed data. Its first attempted run exceeded this environment's time
limit; the smaller atmospheric sweeps completed. Do not merge different physics
modes as though they were one experiment.

The baseline can prefer a small engine count because mass penalties dominate
and the assumed load cap excludes the one-engine design. This is a result of
these assumptions, not a prediction of the optimal real Falcon 9 architecture.
Report small payload gaps and their sensitivity instead of presenting a single
integer as universal. The default allowed engine counts and control family can
also bias the apparent winner.

## Verification before publication

The tests check the reference mass anchor, the linear-mass invariant, fuel and
margin bookkeeping, payload mass/delta-v closure, reserve monotonicity, drag
sign, no-hover landing feasibility, tighter reintegration, invalid inputs, and
failure handling. The exact no-drag solution is compared with an independent
ODE integration. `verify_results.py` performs a finer replay with actual ground
and propellant-exhaustion events. Neither check is flight-data validation.

Before using results as paper conclusions, expand multistarts, refine controls
and integration tolerances, rerun apparent infeasibilities, compare k=1 versus
k=1/3 versus a permitted 3-to-1 schedule, and calibrate mass/aerodynamic inputs.
Always reoptimize each design before comparing its payload. A controller tuned
only to N=9 can manufacture a spurious architecture ranking.

## Next model increments

1. Calibrate the engine mass family with same-propellant/same-cycle engine data,
   retaining uncertainty and correlations. Fit beta and fixed mass jointly.
2. Replace constant throttle with piecewise-continuous control and a limited
   number of discrete engine shutdown/restart events. Include ignition delay,
   thrust ramps, throttle slew, and minimum on-time. Inspect engine geometry.
3. Replace the delta-v proxy with a planar curved-Earth ascent and upper-stage
   trajectory, then a 3-DOF point-mass model. Carry reserves at MECO and require
   target orbital radius, energy, and flight-path angle. A 200-km circular LEO
   can be the chosen subsequent mission, but is NOT verified by v0.1.
4. Propagate the booster from the actual staging state through entry and
   downrange return, making the earlier recovery reserve and terminal-entry
   state endogenous. Do not label the present fixed 8,000 kg allowance a full
   recovery prediction.
5. Add ascent max-Q, acceleration, heating, angle-of-attack/load constraints,
   gimbal bounds, fairing events, feed/ullage limits, nozzle packing, and
   thrust-structure/landing-leg mass changes. Couple Isp and available thrust
   to ambient pressure and engine design. Add 6-DOF only when attitude/gimbal
   or engine-out questions demand it.
6. Run uncertainty experiments on ignition delay, thrust, mass, atmosphere, and
   navigation error. Distinguish closed-loop robustness from merely replanning
   with perfect knowledge of each disturbance. A carried 10% fuel margin alone
   is not a demonstrated success probability.

A useful paper contribution would be a map N*(phi, umin, recovery severity),
including near-optimal sets and robustness bands, not a preselected claim that
more engines always reduce landing fuel. Adding unconstrained variables alone
is not novelty.

## Primary sources and novelty caution

SpaceX, Falcon 9 official vehicle specifications:
https://www.spacex.com/vehicles/falcon-9/

Dresia et al. (2021), *Multidisciplinary Design Optimization of Reusable Launch
Vehicles for Different Propellants and Objectives*, Journal of Spacecraft and
Rockets, DOI 10.2514/1.A34944:
https://elib.dlr.de/141082/1/1.A34944.pdf
This is close prior work: it already couples engine architecture, engine mass,
and recovery sizing. Its recovery calculation uses a delta-v approximation;
its discussion identifies engine mass correlations as a limitation. Do not claim
that all earlier work treats these topics independently. Explicit constrained
landing trajectories and an uncertainty-aware fixed-thrust architecture map are
a candidate narrower contribution, not a confirmed literature-wide novelty claim.

Sagliano et al. (2025), *Operational Atmospheric Landing Guidance for Reusable
Rockets*, AIAA SciTech, DOI 10.2514/6.2025-2597:
https://elib.dlr.de/216768/1/Operational_landing_guidance.pdf
This supplies motivation for later finite ignition/idle/thrust-transient models;
its engine-specific settings are not assumed to be Merlin settings here.

NASA Glenn, Ideal Rocket Equation:
https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/

SciPy official APIs:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html
https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html
