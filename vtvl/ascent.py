"""Ascent: stage 1 (vertical rise, pitch kick, zero-AoA gravity turn) and stage 2
(linear-tangent steering) with an exact 200 km circular insertion solve.

Units SI; angles in rad internally, kick angle given in deg.

Stage-1 control (identical logic for every N):
  * all N engines lit; throttle u = min(1, u_cap) with
        u_cap = (a_max_asc*m + D + N*p*A_e) / (N*T_vac,e)     [axial (T - D)/m <= a_max_asc]
    floored at u_min (a floor hit is reported as a cap violation).
  * vertical rise until t_kick; thrust then held at delta from the local vertical until the
    velocity relative to the atmosphere has turned to delta; then thrust along v_rel (gravity turn).
  * MECO when the ascent propellant P1 - R has been burned (R = recovery reserve).
  * stage separation is instantaneous (no coast, no mass loss).
Stage-2 control:
  * pitch above local horizontal psi(tau) = atan(a - c*tau/tau_ref), tau_ref = P2/mdot2.
  * throttle u2 = clip((a_max_asc*m + D)/T2, u2_min, 1) (same 4 g cap; MVac thrust is its
    vacuum value, ambient-pressure loss neglected above ~70 km).
  * burn to depletion of P2. Fairing (m_fair) is jettisoned at the first downward crossing of
    q = q_fair, in whichever stage that occurs; the rest of m_bay goes to orbit.
Payload = the mass L for which the linear-tangent family exactly reaches r = R_E + h_orb,
v_r = 0, v_t = sqrt(mu/r) at depletion ((a, c, L) solved together, 3 equations).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import root

from .atmosphere import atmosphere
from .config import Earth, Numerics, Vehicle, cd_interp
from .dynamics import make_dynamics
from .integrate import Event, integrate

T_MAX_ASCENT = 2000.0  # s, hard stop for a runaway propagation (numerical guard)


@dataclass(frozen=True)
class Kick:
    t_kick: float      # s after liftoff
    delta_deg: float   # deg from local vertical


@dataclass
class Phase:
    """Recorded trajectory segment with diagnostics at every RK4 node."""
    name: str
    t: np.ndarray
    y: np.ndarray            # (n, 5)
    q: np.ndarray
    thrust: np.ndarray
    mdot: np.ndarray
    a_ng: np.ndarray         # |thrust + drag| / m  [m/s^2]
    h: np.ndarray
    vrel: np.ndarray
    drag: np.ndarray


def _phase_record(name, res, terms) -> Phase:
    t = np.array(res.t)
    y = np.array(res.y)
    diag = [terms(ti, yi)[1] for ti, yi in zip(res.t, res.y)]
    d = np.array(diag) if diag else np.zeros((0, 10))
    return Phase(name, t, y, q=d[:, 1], thrust=d[:, 3], mdot=d[:, 4],
                 a_ng=np.hypot(d[:, 8], d[:, 9]), h=d[:, 0], vrel=d[:, 6], drag=d[:, 2])


def _q_event(earth: Earth, q_level: float) -> Event:
    re, om = earth.r_e, earth.omega_eff

    def g(t, y):
        rho = atmosphere(y[0] - re)[0]
        vrt = y[3] - om * y[0]
        return 0.5 * rho * (y[2] * y[2] + vrt * vrt) - q_level
    return Event('fairing', g, -1)


def _crash_event(earth: Earth) -> Event:
    re = earth.r_e
    return Event('crash', lambda t, y: y[0] - re + 1.0, -1)


@dataclass
class Stage1Result:
    ok: bool
    reason: str
    m0: float
    t_meco: float = math.nan
    y_meco: list = field(default_factory=list)   # [r, theta, vr, vt, m_stack]
    fairing_on: bool = True
    t_fairing: float = math.nan
    q_peak: float = math.nan
    t_qpeak: float = math.nan
    a_ng_peak: float = math.nan
    throttle_floor_hit: bool = False
    phases: list = field(default_factory=list)


def run_stage1(veh: Vehicle, earth: Earth, num: Numerics, kick: Kick, payload: float, reserve: float) -> Stage1Result:
    eng = veh.engine
    N, tv, ae, md = veh.n_engines, eng.t_vac, eng.a_e, eng.mdot
    a_cap, umin = veh.a_max_asc, veh.u_min
    floor_hit = [False]

    def throttle(p, d, m):
        u = (a_cap * m + d + N * p * ae) / (N * tv)
        if u >= 1.0:
            u = 1.0
        elif u < umin:
            u = umin
            floor_hit[0] = True
        return N * (u * tv - p * ae), N * u * md

    sd, cd_ = math.sin(math.radians(kick.delta_deg)), math.cos(math.radians(kick.delta_deg))

    def c_vertical(t, y, h, p, q, d, vr, vrt, vrel):
        T, mdot = throttle(p, d, y[4])
        return T, 1.0, 0.0, mdot

    def c_kick(t, y, h, p, q, d, vr, vrt, vrel):
        T, mdot = throttle(p, d, y[4])
        return T, cd_, sd, mdot

    def c_gt(t, y, h, p, q, d, vr, vrt, vrel):
        T, mdot = throttle(p, d, y[4])
        if vrel > 0.0:
            return T, vr / vrel, vrt / vrel, mdot
        return T, 1.0, 0.0, mdot

    xs, ys = veh.cd_mach, veh.cd_vals
    cdf = lambda mach: cd_interp(mach, xs, ys)
    dyn = {name: make_dynamics(earth, veh.area, cdf, c) for name, c in
           (('vertical', c_vertical), ('kick', c_kick), ('gravity_turn', c_gt))}

    r0 = earth.r_e + veh.h_pad
    m0 = veh.glow(payload)
    y = [r0, 0.0, 0.0, earth.omega_eff * r0, m0]
    t = 0.0
    meco_mass = m0 - (veh.p1 - reserve)
    if reserve < 0 or reserve >= veh.p1:
        return Stage1Result(False, f'invalid reserve {reserve:.1f} kg', m0)
    fairing_on = True
    t_fair = math.nan
    out = Stage1Result(False, '', m0)
    delta = math.radians(kick.delta_deg)
    order = ['vertical', 'kick', 'gravity_turn']
    seg = 0
    dt = num.dt('stage1')
    while True:
        name = order[seg]
        rhs, terms = dyn[name]
        evs = [Event('meco', lambda t, y: y[4] - meco_mass, -1), _crash_event(earth)]
        if fairing_on:
            evs.append(_q_event(earth, veh.q_fair))
        t_end = kick.t_kick if name == 'vertical' else T_MAX_ASCENT
        if name == 'kick':
            om = earth.omega_eff
            evs.append(Event('angle', lambda t, y: math.atan2(y[3] - om * y[0], y[2]) - delta, +1))
        res = integrate(rhs, t, y, dt, t_end, evs)
        out.phases.append(_phase_record(name, res, terms))
        t, y = res.t_final, list(res.y_final)
        if res.event == 'crash':
            out.reason = f'stage 1 descended below the pad in phase {name}'
            return out
        if res.event == 'fairing':
            y[4] -= veh.m_fair
            meco_mass -= veh.m_fair
            fairing_on, t_fair = False, t
            continue
        if res.event == 'meco':
            break
        if t >= T_MAX_ASCENT - 1e-9:
            out.reason = 'stage 1 propagation time limit'
            return out
        seg += 1
        if seg >= len(order):
            out.reason = 'stage 1 phase logic error'
            return out
    qs = np.concatenate([ph.q for ph in out.phases])
    ts = np.concatenate([ph.t for ph in out.phases])
    i = int(np.argmax(qs))
    out.ok, out.reason = True, 'ok'
    out.t_meco, out.y_meco = t, y
    out.fairing_on, out.t_fairing = fairing_on, t_fair
    out.q_peak, out.t_qpeak = float(qs[i]), float(ts[i])
    out.a_ng_peak = float(max(np.max(ph.a_ng) for ph in out.phases))
    out.throttle_floor_hit = floor_hit[0]
    return out


@dataclass
class Stage2Result:
    ok: bool
    reason: str
    y_final: list = field(default_factory=list)
    t_final: float = math.nan
    residual: tuple = (math.nan, math.nan, math.nan)   # (dr [m], v_r [m/s], dv_t [m/s])
    t_fairing: float = math.nan
    a_ng_peak: float = math.nan
    burn_time: float = math.nan
    phases: list = field(default_factory=list)
    throttle_floor_hit: bool = False


def stage2_initial_mass(veh: Vehicle, payload: float, fairing_on: bool) -> float:
    return veh.m_d2 + veh.p2 + veh.m_bay - (0.0 if fairing_on else veh.m_fair) + payload


def run_stage2(veh: Vehicle, earth: Earth, num: Numerics, t0: float, y_sep, fairing_on: bool,
               payload: float, steer: tuple, record: bool = False) -> Stage2Result:
    a, c = steer
    tau_ref = veh.p2 / veh.mdot2
    t2, md2, a_cap, u2min = veh.t2, veh.mdot2, veh.a_max_asc, veh.u2_min
    floor_hit = [False]

    def control(t, y, h, p, q, d, vr, vrt, vrel):
        u = (a_cap * y[4] + d) / t2
        if u >= 1.0:
            u = 1.0
        elif u < u2min:
            u = u2min
            floor_hit[0] = True
        tp = a - c * (t - t0) / tau_ref
        nrm = 1.0 / math.sqrt(1.0 + tp * tp)
        return u * t2, tp * nrm, nrm, u * md2

    xs, ys = veh.cd_mach, veh.cd_vals
    rhs, terms = make_dynamics(earth, veh.area, lambda mach: cd_interp(mach, xs, ys), control)
    m_start = stage2_initial_mass(veh, payload, fairing_on)
    m_burnout = m_start - veh.p2
    y = [y_sep[0], y_sep[1], y_sep[2], y_sep[3], m_start]
    t = t0
    out = Stage2Result(False, '')
    dt = num.dt('stage2')
    r_escape = 2.0 * veh.r_orbit   # numerical guard for absurd trial steering / payload
    while True:
        evs = [Event('burnout', lambda t, y: y[4] - m_burnout, -1), _crash_event(earth),
               Event('escape', lambda t, y: y[0] - r_escape, +1)]
        if fairing_on:
            evs.append(_q_event(earth, veh.q_fair))
        if m_burnout <= 0.0:
            out.reason = 'non-physical trial payload (burnout mass <= 0)'
            out.residual = (-veh.r_orbit, -1e4, -1e4)
            return out
        res = integrate(rhs, t, y, dt, t0 + T_MAX_ASCENT, evs, record=record)
        if record:
            out.phases.append(_phase_record('stage2', res, terms))
        t, y = res.t_final, list(res.y_final)
        if res.event == 'fairing':
            y[4] -= veh.m_fair
            m_burnout -= veh.m_fair
            fairing_on = False
            out.t_fairing = t
            continue
        break
    out.y_final, out.t_final, out.burn_time = y, t, t - t0
    out.residual = (y[0] - veh.r_orbit, y[2], y[3] - veh.v_circ)
    out.throttle_floor_hit = floor_hit[0]
    if record and out.phases:
        out.a_ng_peak = float(max(np.max(ph.a_ng) for ph in out.phases))
    if res.event == 'burnout':
        out.ok, out.reason = True, 'ok'
    elif res.event == 'crash':
        out.reason = 'stage 2 re-entered (altitude < 0)'
    elif res.event == 'escape':
        out.reason = 'stage 2 trial trajectory left the numerical domain (r > 2 r_orbit)'
    else:
        out.reason = 'stage 2 time limit'
    return out


@dataclass
class Insertion:
    success: bool
    message: str
    steer: tuple = (math.nan, math.nan)
    payload: float = math.nan
    residual: tuple = (math.nan, math.nan, math.nan)
    nfev: int = 0


RES_SCALE = (1000.0, 10.0, 10.0)   # m, m/s, m/s : residual scaling for the root solver
L_SCALE = 1.0e4                    # kg


def solve_insertion(veh: Vehicle, earth: Earth, num: Numerics, s1: Stage1Result, guess: tuple) -> Insertion:
    """Solve (a, c, L) so the stage-2 linear-tangent burn reaches the target circular orbit."""
    y_sep = s1.y_meco[:4]
    nfev = [0]

    def F(x):
        nfev[0] += 1
        r = run_stage2(veh, earth, num, s1.t_meco, y_sep, s1.fairing_on, x[2] * L_SCALE, (x[0], x[1]))
        return [r.residual[i] / RES_SCALE[i] for i in range(3)]

    x0 = [guess[0], guess[1], guess[2] / L_SCALE]
    sol = root(F, x0, method='hybr', options={'xtol': num.insertion_xtol})
    a, c, ls = sol.x
    r = run_stage2(veh, earth, num, s1.t_meco, y_sep, s1.fairing_on, ls * L_SCALE, (a, c))
    ok = r.ok and abs(r.residual[0]) < 1.0 and abs(r.residual[1]) < 1e-2 and abs(r.residual[2]) < 1e-2
    msg = 'converged' if ok else f'root: {sol.message}; stage2: {r.reason}; residual={r.residual}'
    return Insertion(ok, msg, (a, c), ls * L_SCALE, r.residual, nfev[0])
