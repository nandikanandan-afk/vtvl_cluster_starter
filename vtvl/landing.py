"""Free-coast + one constant-throttle landing burn, with discrete active engines.

This is a RESTRICTED control family. Its best solution is not a globally
fuel-optimal landing trajectory. Failure of this optimizer is not proof that
an architecture cannot land. No hover requirement is imposed.
"""
from dataclasses import dataclass
from functools import lru_cache
import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize

from .config import Design, G0, Mission, Numerics, Vehicle
from .engines import booster_dry_mass_kg


@dataclass
class LandingResult:
    feasible: bool
    status: str
    active_engines: int = 0
    coast_s: float = math.nan
    burn_s: float = math.nan
    throttle: float = math.nan
    burn_propellant_kg: float = math.nan
    loaded_landing_propellant_kg: float = math.nan
    touchdown_propellant_kg: float = math.nan
    ignition_altitude_m: float = math.nan
    peak_proper_accel_g: float = math.nan
    peak_dynamic_pressure_pa: float = math.nan
    final_altitude_error_m: float = math.nan
    final_velocity_error_m_s: float = math.nan
    optimizer_success: bool = False
    optimizer_message: str = ''
    candidate_attempts: int = 0
    peak_thrust_accel_g: float = math.nan


def density(altitude_m, mission: Mission):
    # A smooth extension below zero is used ONLY during infeasible optimizer
    # iterations. Accepted solutions are independently checked above ground.
    return mission.sea_level_density_kg_m3 * np.exp(
        -np.clip(altitude_m, -5_000.0, 100_000.0) / mission.density_scale_height_m
    )


def propagate(
    design: Design, vehicle: Vehicle, mission: Mission, numerics: Numerics,
    active_engines: int, coast_s: float, burn_s: float, throttle: float,
    samples: int | None = None, force_numeric: bool = False,
) -> dict:
    """Evaluate a prescribed control. Constant sea-level thrust and Isp.

    Initial landing fuel = (1 + margin)*nominal_burn + trapped_residual.
    The margin is CARRIED in the dynamics and remains aboard at touchdown.
    """
    count = samples or numerics.path_samples
    dry = booster_dry_mass_kg(design, vehicle)
    thrust = active_engines * vehicle.total_sl_thrust_n / design.engine_count * throttle
    exhaust_speed = vehicle.landing_isp_s * G0
    flow = thrust / exhaust_speed
    used = flow * burn_s
    loaded = (1 + mission.landing_margin_fraction) * used + mission.trapped_residual_kg
    initial_mass = dry + loaded
    final_mass = initial_mass - used
    ctimes = np.linspace(0.0, coast_s, count) if coast_s > 0 else np.array([0.0])
    btimes = np.linspace(0.0, burn_s, count)
    h0, v0 = mission.terminal_entry_altitude_m, -design.terminal_entry_speed_m_s

    if numerics.physics == 'analytic' and not force_numeric:
        ch = h0 + v0 * ctimes - 0.5 * G0 * ctimes**2
        cv = v0 - G0 * ctimes
        cm = np.full_like(ctimes, initial_mass)
        bm = initial_mass - flow * btimes
        if flow == 0.0:
            bv = cv[-1] - G0 * btimes
            bh = ch[-1] + cv[-1] * btimes - 0.5 * G0 * btimes**2
        else:
            lr = np.log1p(flow * btimes / bm)
            bv = cv[-1] - G0 * btimes + exhaust_speed * lr
            bh = ch[-1] + cv[-1] * btimes - 0.5 * G0 * btimes**2 + exhaust_speed * (
                btimes - bm / flow * lr
            )
    else:
        area = math.pi * vehicle.diameter_m**2 / 4
        cd = mission.landing_drag_coefficient if numerics.physics == 'drag' else 0.0

        def ode(thrust_now: float):
            def rhs(t, y):
                h, v, mass = y
                drag = -0.5 * density(h, mission) * cd * area * v * abs(v)
                return (v, (thrust_now + drag) / mass - G0, -thrust_now / exhaust_speed)
            return rhs

        initial = np.array([h0, v0, initial_mass])
        if coast_s > 0:
            coast = solve_ivp(
                ode(0), (0.0, coast_s), initial, t_eval=ctimes,
                rtol=numerics.rtol, atol=numerics.atol, max_step=numerics.max_step_s,
            )
            if not coast.success:
                raise RuntimeError('Coast integration failed: ' + coast.message)
            ch, cv, cm = coast.y
            initial = coast.y[:, -1]
        else:
            ch, cv, cm = np.array([h0]), np.array([v0]), np.array([initial_mass])
        burn = solve_ivp(
            ode(thrust), (0.0, burn_s), initial, t_eval=btimes,
            rtol=numerics.rtol, atol=numerics.atol, max_step=numerics.max_step_s,
        )
        if not burn.success:
            raise RuntimeError('Burn integration failed: ' + burn.message)
        bh, bv, bm = burn.y

    t = np.concatenate((ctimes, coast_s + btimes[1:]))
    h = np.concatenate((ch, bh[1:]))
    v = np.concatenate((cv, bv[1:]))
    masses = np.concatenate((cm, bm[1:]))
    f = np.concatenate((np.zeros_like(ctimes), np.full(len(btimes) - 1, thrust)))
    # An instantaneous thrust step is assumed at ignition (not a ramp model).
    q = 0.5 * density(h, mission) * v**2
    # Proper acceleration includes drag, unlike thrust-to-weight alone.
    # Include the exact ignition instant rather than dropping the thrust jump.
    cd_area = (mission.landing_drag_coefficient * math.pi * vehicle.diameter_m**2 / 4
               if numerics.physics == 'drag' else 0.0)
    coast_drag = -0.5 * density(ch, mission) * cd_area * cv * np.abs(cv)
    burn_drag = -0.5 * density(bh, mission) * cd_area * bv * np.abs(bv)
    proper_g = max(float(np.max(np.abs(coast_drag / cm))),
                   float(np.max(np.abs((thrust + burn_drag) / bm)))) / G0
    return dict(
        t=t, h=h, v=v, mass=masses, thrust=f, dynamic_pressure=q,
        used=used, loaded=loaded, final_mass=final_mass,
        touchdown_propellant=final_mass - dry, ignition_h=float(ch[-1]),
        h_final=float(bh[-1]), v_final=float(bv[-1]),
        peak_proper_g=proper_g,
        peak_thrust_g=thrust / (final_mass * G0),
        peak_q=float(np.max(q)),
    )


def _inequalities(p: dict, mission: Mission, physics: str) -> np.ndarray:
    # All values must be >= 0. The no-drag benchmark does not enforce q.
    result = [
        mission.max_landing_proper_accel_g - p['peak_proper_g'],
        (mission.max_landing_propellant_kg - p['loaded']) / 1000.0,
        float(np.min(p['h'][:-1])) / 1000.0,
        -float(np.max(p['v'])) / 200.0,
    ]
    if physics == 'drag':
        result.append((mission.max_terminal_dynamic_pressure_pa - p['peak_q']) / 100_000)
    return np.array(result)


def _accepted(p: dict, mission: Mission, numerics: Numerics) -> bool:
    return (
        abs(p['h_final']) <= numerics.altitude_tolerance_m
        and abs(p['v_final'] - mission.touchdown_velocity_m_s) <= numerics.velocity_tolerance_m_s
        and float(np.min(_inequalities(p, mission, numerics.physics))) >= -numerics.constraint_tolerance
        and p['touchdown_propellant'] >= mission.trapped_residual_kg - 1e-5
    )


def solve_landing(design: Design, vehicle: Vehicle, mission: Mission, numerics: Numerics) -> LandingResult:
    best = None
    attempts = 0
    messages = []
    dry = booster_dry_mass_kg(design, vehicle)
    ballistic_time = (
        -design.terminal_entry_speed_m_s
        + math.sqrt(design.terminal_entry_speed_m_s**2 + 2 * G0 * mission.terminal_entry_altitude_m)
    ) / G0
    max_coast = max(30.0, 2 * ballistic_time)
    for active in mission.allowed_landing_engine_counts:
        if active > design.engine_count:
            continue
        fmax = active * vehicle.total_sl_thrust_n / design.engine_count
        max_used = (mission.max_landing_propellant_kg - mission.trapped_residual_kg) / (
            1 + mission.landing_margin_fraction
        )
        max_final_mass = dry + mission.trapped_residual_kg + mission.landing_margin_fraction * max_used
        if design.min_throttle * fmax / (max_final_mass * G0) > mission.max_landing_proper_accel_g:
            messages.append(f'k={active}: minimum thrust exceeds load cap even at maximum allowed touchdown mass')
            continue

        @lru_cache(maxsize=2048)
        def evaluate_cached(x0: float, x1: float, u: float):
            return propagate(design, vehicle, mission, numerics, active, 10*x0, 10*x1, u)

        def evaluate(x):
            return evaluate_cached(*map(float, x))

        def objective(x):
            return evaluate(x)['used'] / 1000.0

        def eq(x):
            p = evaluate(x)
            return np.array([p['h_final'] / 1000.0,
                             (p['v_final'] - mission.touchdown_velocity_m_s) / 200.0])

        def iq(x):
            return _inequalities(evaluate(x), mission, numerics.physics)

        u_cap = mission.max_landing_proper_accel_g * G0 * (dry + mission.trapped_residual_kg) / fmax
        bounds = [(0.0, max_coast / 10.0),
                  (mission.min_landing_burn_s / 10.0, mission.max_landing_burn_s / 10.0),
                  (design.min_throttle, 1.0)]
        # Deterministic, equal multistart budget for every engine architecture.
        for start in range(numerics.multistarts):
            coast_guess = ballistic_time * (0.05, 0.30, 0.60, 0.80, 0.15, 0.45)[start % 6]
            u_guess = float(np.clip(u_cap * (0.98, 0.8, 0.6, 0.95)[start % 4], design.min_throttle, 1.0))
            accel_guess = max(2.0, fmax * u_guess / (dry * 1.12) - G0)
            burn_guess = np.clip((design.terminal_entry_speed_m_s + G0 * coast_guess) / accel_guess,
                                 mission.min_landing_burn_s + 0.1, mission.max_landing_burn_s * 0.8)
            x0 = [coast_guess / 10, burn_guess / 10, u_guess]
            result = minimize(
                objective, x0, method='SLSQP', bounds=bounds,
                constraints=[{'type': 'eq', 'fun': eq}, {'type': 'ineq', 'fun': iq}],
                options={'maxiter': numerics.max_iterations, 'ftol': numerics.optimizer_ftol},
            )
            attempts += 1
            p = evaluate(result.x)
            if _accepted(p, mission, numerics):
                # Denser path check: do not accept an optimizer flag alone.
                p = propagate(design, vehicle, mission, numerics, active,
                              10*result.x[0], 10*result.x[1], result.x[2], samples=301)
                if _accepted(p, mission, numerics) and (best is None or p['used'] < best.burn_propellant_kg):
                    best = LandingResult(
                        True, 'FEASIBLE_RESTRICTED_CONTROL', active,
                        10*float(result.x[0]), 10*float(result.x[1]), float(result.x[2]),
                        p['used'], p['loaded'], p['touchdown_propellant'], p['ignition_h'],
                        p['peak_proper_g'], p['peak_q'], p['h_final'],
                        p['v_final'] - mission.touchdown_velocity_m_s,
                        bool(result.success), str(result.message), attempts, p['peak_thrust_g'],
                    )
        if best is None:
            messages.append(f'k={active}: no accepted multistart solution')
    if best is None:
        return LandingResult(False, 'NO_FEASIBLE_SOLUTION_FOUND',
                             optimizer_message='; '.join(messages), candidate_attempts=attempts)
    best.candidate_attempts = attempts
    return best
