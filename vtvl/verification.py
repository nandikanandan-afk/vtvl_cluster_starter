"""Independent re-integration of reported solutions (verification, not validation).

The equations of motion are RE-IMPLEMENTED here (not imported from dynamics.py) and integrated
with SciPy's adaptive DOP853 (rtol 1e-10) with event detection, so an error in the production
RK4 integrator, its event locator or its dynamics closure would show up as a mismatch.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.integrate import solve_ivp

from .atmosphere import atmosphere
from .config import Earth, Vehicle, cd_interp

RTOL, ATOL = 1e-10, 1e-8


def _drag_and_p(earth: Earth, veh: Vehicle, y, cd_fn):
    r, th, vr, vt, m = y
    rho, p, a = atmosphere(r - earth.r_e) if earth.atmosphere else (0.0, 0.0, 1.0)
    vrt = vt - earth.omega_eff * r
    v = math.hypot(vr, vrt)
    D = 0.5 * rho * v * v * cd_fn(v / a) * veh.area
    return D, p, vr, vrt, v


def _eom(earth, y, T, er, et, D, vr, vrt, v, mdot):
    r, th, _, vt, m = y
    g = earth.g0 if earth.gravity == 'constant' else earth.mu / (r * r)
    dr_, dt_ = (D * vr / v, D * vrt / v) if v > 0 else (0.0, 0.0)
    return [vr, vt / r, vt * vt / r - g + (T * er - dr_) / m, -vr * vt / r + (T * et - dt_) / m, -mdot]


def replay_stage2(veh: Vehicle, earth: Earth, t0: float, y_sep, fairing_on: bool, payload: float, steer):
    """Re-integrate stage 2 to depletion. Returns dict with residuals (dr, v_r, dv_t)."""
    a, c = steer
    tau = veh.p2 / veh.mdot2
    cdf = lambda M: cd_interp(M, veh.cd_mach, veh.cd_vals)
    m0 = veh.m_d2 + veh.p2 + veh.m_bay - (0.0 if fairing_on else veh.m_fair) + payload
    state = {'m_burnout': m0 - veh.p2, 'fairing_on': fairing_on}

    def f(t, y):
        D, p, vr, vrt, v = _drag_and_p(earth, veh, y, cdf)
        u = min(1.0, max(veh.u2_min, (veh.a_max_asc * y[4] + D) / veh.t2))
        tp = a - c * (t - t0) / tau
        n = 1.0 / math.sqrt(1.0 + tp * tp)
        return _eom(earth, y, u * veh.t2, tp * n, n, D, vr, vrt, v, u * veh.mdot2)

    def burnout(t, y):
        return y[4] - state['m_burnout']
    burnout.terminal, burnout.direction = True, -1

    def fairing(t, y):
        D, p, vr, vrt, v = _drag_and_p(earth, veh, y, cdf)
        rho = atmosphere(y[0] - earth.r_e)[0]
        return 0.5 * rho * v * v - veh.q_fair
    fairing.terminal, fairing.direction = True, -1

    y = list(y_sep[:4]) + [m0]
    t = t0
    while True:
        evs = [burnout] + ([fairing] if state['fairing_on'] else [])
        sol = solve_ivp(f, (t, t + 3000.0), y, method='DOP853', rtol=RTOL, atol=ATOL, events=evs)
        t, y = float(sol.t[-1]), list(sol.y[:, -1])
        if state['fairing_on'] and len(sol.t_events) > 1 and len(sol.t_events[1]):
            y[4] -= veh.m_fair
            state['m_burnout'] -= veh.m_fair
            state['fairing_on'] = False
            continue
        break
    return dict(dr=y[0] - veh.r_orbit, vr=y[2], dvt=y[3] - veh.v_circ, t_final=t, m_final=y[4],
                success=bool(sol.success) and len(sol.t_events[0]) > 0)


def replay_landing(veh: Vehicle, earth: Earth, t0: float, y_ign, k: int, u: float, t_extend: float = 30.0):
    """Re-integrate the landing burn from the ignition state with a ground (h = 0) event.

    Thrust stays on (retrograde) until the ground event or until the vertical velocity becomes
    positive (the vehicle would start climbing; that is reported as touchdown_found = False)."""
    eng = veh.engine
    cdf = lambda M: veh.cd_desc

    def f(t, y):
        D, p, vr, vrt, v = _drag_and_p(earth, veh, y, cdf)
        T = k * (u * eng.t_vac - p * eng.a_e)
        er, et = (-vr / v, -vrt / v) if v > 0 else (1.0, 0.0)
        return _eom(earth, y, T, er, et, D, vr, vrt, v, k * u * eng.mdot)

    def ground(t, y):
        return y[0] - earth.r_e
    ground.terminal, ground.direction = True, -1

    def climbing(t, y):
        return y[2]
    climbing.terminal, climbing.direction = True, +1

    sol = solve_ivp(f, (t0, t0 + 600.0), list(y_ign), method='DOP853', rtol=RTOL, atol=ATOL,
                    events=[ground, climbing], max_step=0.05)
    found = len(sol.t_events[0]) > 0
    if found:
        yg = sol.y_events[0][0]
        vrt = yg[3] - earth.omega_eff * yg[0]
        return dict(touchdown_found=True, h=float(yg[0] - earth.r_e), speed=float(math.hypot(yg[2], vrt)),
                    v_vertical=float(yg[2]), v_horizontal=float(vrt), mass=float(yg[4]), t=float(sol.t_events[0][0]))
    if len(sol.t_events[1]):
        # velocity nulled above the deck: engine cut-off at v = 0, then free fall from h_c
        yc = sol.y_events[1][0]
        h_c = float(yc[0] - earth.r_e)
        vrt = yc[3] - earth.omega_eff * yc[0]
        return dict(touchdown_found=True, h=0.0, speed=math.hypot(math.sqrt(2 * earth.g0 * max(h_c, 0.0)), vrt),
                    v_vertical=-math.sqrt(2 * earth.g0 * max(h_c, 0.0)), v_horizontal=float(vrt), mass=float(yc[4]),
                    t=float(sol.t_events[1][0]), nulled_above_deck_m=h_c)
    yc = sol.y[:, -1]
    return dict(touchdown_found=False, h=float(yc[0] - earth.r_e), speed=math.nan, v_vertical=float(yc[2]),
                v_horizontal=math.nan, mass=float(yc[4]), t=math.nan)
