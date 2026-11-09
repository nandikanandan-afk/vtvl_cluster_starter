"""Downrange recovery of the booster from the actual MECO state (no boostback; drone ship at
the impact point, so the touchdown position is free).

Phases (all 2-D polar point mass, descent Cd = Cd_desc constant, engines-first attitude assumed
immediately after separation; the flip is not modeled):
 1. ballistic coast with drag until h = h_eb on the way down (or apogee if apogee < h_eb);
 2. entry burn, thrust anti-parallel to v_rel; duration t_eb solved so the peak dynamic pressure
    of the following aerodynamic descent equals q_entry_max (t_eb = 0 if already below);
 3. aerodynamic (ballistic) descent;
 4. landing burn (landing.py).
Reserve: R = (1 + eps_m)(m_entry + m_landing) + m_res. Margin and residual stay on board.

ENTRY-BURN ENGINE RULE (identical for every N; see docs/ASSUMPTIONS.md A-ENTRY):
  target thrust T* = (k_ref/N_ref) * N * (T_vac,e - p A_e)   (Falcon 9 practice: 3 of 9 engines)
  cap-limited thrust T_cap = a_cap*m - D, with a_cap = ascent axial cap a_max_asc
  each allowed k (1, 3; k <= N) can deliver [k T(u_min), k T(u_max)]; the delivered thrust is the
  point of the allowed sets, not above T_cap, closest to T*. It is re-evaluated continuously
  (engine count switches are located exactly as events). If even one engine at u_min exceeds
  T_cap the rule cannot be met -> entry burn infeasible_proven (analytic: T_1(u_min)/m > a_cap).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .ascent import Phase, _phase_record, _crash_event
from .atmosphere import atmosphere
from .config import Earth, Numerics, Vehicle
from .dynamics import constant_cd, make_dynamics
from .integrate import Event, integrate
from .landing import Descent, LandingResult, solve_landing

T_MAX_RECOVERY = 3000.0   # s, numerical guard
V_ENTRY_FLOOR = 30.0      # m/s, a burn slowing below this is "too long" (bracket guard, numerical)


@dataclass
class EntryEval:
    t_eb: float
    q_peak: float
    m_entry: float
    ok: bool
    reason: str = ''
    k_profile: list = field(default_factory=list)   # [(t_start, k), ...]
    y_end: list = field(default_factory=list)
    t_end: float = math.nan
    desc: Descent | None = None
    desc_record: object = None
    h_qpeak: float = math.nan
    phases: list = field(default_factory=list)
    t_limit: float = math.nan   # longest burn the entry rule admits (if it ran out), s


@dataclass
class RecoveryResult:
    status: str
    reason: str
    reserve: float = math.nan          # R' computed from the burns [kg]
    m_entry: float = math.nan
    m_landing: float = math.nan
    margin: float = math.nan
    residual: float = math.nan
    h_apogee: float = math.nan
    entry_start_h: float = math.nan
    entry_start_speed: float = math.nan
    t_eb: float = math.nan
    entry_k_profile: list = field(default_factory=list)
    q_peak_desc: float = math.nan
    h_qpeak: float = math.nan
    landing: LandingResult | None = None
    phases: list = field(default_factory=list)
    downrange_m: float = math.nan


def _select_entry_thrust(veh: Vehicle, p: float, m: float, d: float):
    """Return (k, thrust) per the entry rule, or (0, 0) if no allowed setting respects the cap."""
    eng = veh.engine
    tv1 = eng.t_vac - p * eng.a_e
    target = veh.k_entry_ref / veh.n_ref * veh.n_engines * tv1
    t_cap = veh.a_max_asc * m - d
    best = None
    for k in veh.k_land:
        if k > veh.n_engines:
            continue
        lo, hi = eng.thrust(veh.u_min, p, k), eng.thrust(veh.u_max, p, k)
        if lo > t_cap:
            continue
        cand = min(max(target, lo), min(hi, t_cap))
        key = (abs(cand - target), -cand)
        if best is None or key < best[0]:
            best = (key, k, cand)
    if best is None:
        return 0, 0.0
    return best[1], best[2]


def _entry_dynamics(veh: Vehicle, earth: Earth, k_fixed: int):
    eng = veh.engine
    tv, ae, md = eng.t_vac, eng.a_e, eng.mdot

    def control(t, y, h, p, q, d, vr, vrt, vrel):
        k, T = _select_entry_thrust(veh, p, y[4], d)
        if k != k_fixed:
            # Outside this segment's validity; keep k_fixed at the closest admissible throttle.
            lo, hi = eng.thrust(veh.u_min, p, k_fixed), eng.thrust(veh.u_max, p, k_fixed)
            T = min(max(T, lo), hi)
        u = (T / k_fixed + p * ae) / tv
        if vrel > 0.0:
            return T, -vr / vrel, -vrt / vrel, k_fixed * u * md
        return T, 1.0, 0.0, k_fixed * u * md

    return make_dynamics(earth, veh.area, constant_cd(veh.cd_desc), control)


def _ballistic(veh: Vehicle, earth: Earth):
    return make_dynamics(earth, veh.area, constant_cd(veh.cd_desc), lambda *a: (0.0, 1.0, 0.0, 0.0))


def _peak_q(ph: Phase) -> tuple[float, float]:
    """Peak q over recorded nodes with 3-point parabolic refinement. Returns (q_peak, h_at_peak)."""
    q = ph.q
    i = int(np.argmax(q))
    if 0 < i < len(q) - 1:
        a, b, c = q[i - 1], q[i], q[i + 1]
        den = a - 2 * b + c
        if den < 0:
            x = 0.5 * (a - c) / den
            return float(b - 0.25 * (a - c) * x), float(ph.h[i])
    return float(q[i]), float(ph.h[i])


def run_entry(veh: Vehicle, earth: Earth, num: Numerics, t0: float, y0: list, t_eb: float,
              record: bool = False) -> EntryEval:
    """Entry burn of duration t_eb from (t0, y0), then ballistic descent to the ground."""
    re, om = earth.r_e, earth.omega_eff
    t, y = t0, list(y0)
    m_start = y0[4]
    phases = []
    k_prof = []
    if t_eb > 0.0:
        while t < t0 + t_eb - 1e-12:
            # current rule selection at this state
            rho, p, a = atmosphere(y[0] - re)
            vrt = y[3] - om * y[0]
            vrel = math.hypot(y[2], vrt)
            d = 0.5 * rho * vrel * vrel * veh.cd_desc * veh.area
            k, _ = _select_entry_thrust(veh, p, y[4], d)
            if k == 0:
                g0 = earth.g0
                ev = EntryEval(t_eb, math.nan, m_start - y[4], False,
                               f'entry rule limit at t={t - t0:.3f} s: drag D/m={d/y[4]/g0:.2f} g plus one engine at '
                               f'u_min T/m={veh.engine.thrust(veh.u_min, p, 1)/y[4]/g0:.2f} g exceeds the '
                               f'{veh.a_max_asc/g0:.2f} g cap (m={y[4]/1e3:.2f} t, h={(y[0]-re)/1e3:.1f} km)',
                               k_prof)
                ev.t_limit = t - t0
                return ev
            k_prof.append((t - t0, k))
            rhs, terms = _entry_dynamics(veh, earth, k)

            def switch(tt, yy, k=k):
                rho_, p_, _ = atmosphere(yy[0] - re)
                # fires when the rule selects a different engine count (or none)
                vrt_ = yy[3] - om * yy[0]
                v_ = math.hypot(yy[2], vrt_)
                d_ = 0.5 * rho_ * v_ * v_ * veh.cd_desc * veh.area
                return 1.0 if _select_entry_thrust(veh, p_, yy[4], d_)[0] == k else -1.0

            slow = Event('slow', lambda tt, yy: math.hypot(yy[2], yy[3] - om * yy[0]) - V_ENTRY_FLOOR, -1)
            res = integrate(rhs, t, y, num.dt('entry'), t0 + t_eb,
                            [Event('switch', switch, -1), slow, _crash_event(earth)], record=record)
            if record:
                phases.append(_phase_record(f'entry_burn_k{k}', res, terms))
            t, y = res.t_final, list(res.y_final)
            if res.event == 'slow':
                return EntryEval(t_eb, 0.0, m_start - y[4], False, 'entry burn nulled the velocity (too long)', k_prof)
            if res.event == 'crash':
                return EntryEval(t_eb, math.nan, m_start - y[4], False, 'entry burn reached the ground', k_prof)
            if res.event == 'switch':
                # nudge past the discontinuity so the next selection is evaluated on the new side
                continue
    m_entry = m_start - y[4]
    rhs_b, terms_b = _ballistic(veh, earth)
    res = integrate(rhs_b, t, y, num.dt('descent'), t + T_MAX_RECOVERY,
                    [Event('ground', lambda tt, yy: yy[0] - re, -1)], record=True)
    ph = _phase_record('aero_descent', res, terms_b)
    q_pk, h_pk = _peak_q(ph)
    desc = Descent(rhs_b, res.t, res.y, re, ph)
    ev = EntryEval(t_eb, q_pk, m_entry, True, 'ok', k_prof, y, t, desc, ph, h_pk, phases)
    return ev


def run_recovery(veh: Vehicle, earth: Earth, num: Numerics, t_meco: float, y_meco4: list, reserve: float,
                 warm: dict | None = None, scan: bool = False, record: bool = False) -> RecoveryResult:
    """Simulate recovery from MECO with booster mass m_dry1 + reserve. Returns R' = f(R)."""
    w = warm if warm is not None else {}
    re = earth.r_e
    q_lim = veh.q_entry_max
    if q_lim is None:
        raise ValueError('q_entry_max must be calibrated before running recovery')
    m_b = veh.m_dry1 + reserve
    y = list(y_meco4) + [m_b]
    phases = []
    # 1. coast
    rhs_b, terms_b = _ballistic(veh, earth)
    h_eb = veh.h_eb
    t = t_meco
    h_apo = y[0] - re
    if y[2] > 0.0:
        res = integrate(rhs_b, t, y, num.dt('coast'), t + T_MAX_RECOVERY,
                        [Event('apogee', lambda tt, yy: yy[2], -1)], record=record)
        if record:
            phases.append(_phase_record('coast_up', res, terms_b))
        t, y = res.t_final, list(res.y_final)
        h_apo = y[0] - re
    if y[0] - re > h_eb:
        res = integrate(rhs_b, t, y, num.dt('coast'), t + T_MAX_RECOVERY,
                        [Event('h_eb', lambda tt, yy: yy[0] - re - h_eb, -1)], record=record)
        if record:
            phases.append(_phase_record('coast_down', res, terms_b))
        t, y = res.t_final, list(res.y_final)
    out = RecoveryResult('no_solution_found', '', h_apogee=h_apo, entry_start_h=y[0] - re,
                         entry_start_speed=math.hypot(y[2], y[3] - earth.omega_eff * y[0]))
    # 2. entry burn sizing: q_peak(t_eb) = q_lim, q_peak decreasing in t_eb
    cache = {}

    def E(teb):
        teb = max(0.0, float(teb))
        if teb not in cache:
            cache[teb] = run_entry(veh, earth, num, t, y, teb)
        return cache[teb]

    e0 = E(0.0)
    if not e0.ok:
        out.reason = 'ballistic descent failed: ' + e0.reason
        return out
    if e0.q_peak <= q_lim:
        e_star = e0
    else:
        # bracket
        tg = w.get('t_eb')
        lo, hi = 0.0, None
        trial = [tg * 0.98, tg * 1.02] if tg else []
        trial += [2.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0]
        for tb in sorted(set(x for x in trial if x > 0)):
            ev = E(tb)
            if not ev.ok:
                if math.isfinite(ev.t_limit):
                    # The rule admits burns only up to t_limit. q_peak decreases with t_eb, so if the
                    # longest admissible burn still exceeds q_lim, no admissible single burn can meet it.
                    t_adm = max(0.0, ev.t_limit - 1e-6)
                    e_adm = E(t_adm)
                    if e_adm.ok and e_adm.q_peak <= q_lim:
                        hi = t_adm
                        break
                    out.status = 'infeasible_proven'
                    out.reason = (ev.reason + f'; the longest admissible burn ({t_adm:.2f} s) leaves post-burn '
                                  f'peak q = {e_adm.q_peak:.0f} Pa > q_entry_max = {q_lim:.0f} Pa')
                    return out
                # trial burn too long (velocity nulled / reached ground): bisect back into the valid range
                a_, b_ = lo, tb
                for _ in range(40):
                    mid = 0.5 * (a_ + b_)
                    em = E(mid)
                    if em.ok and em.q_peak <= q_lim:
                        hi = mid
                        break
                    if em.ok:
                        a_ = lo = mid
                    else:
                        b_ = mid
                break
            if ev.q_peak > q_lim:
                lo = tb
            else:
                hi = tb
                break
        if hi is None:
            last = E(lo)
            out.reason = (f'no entry-burn duration found with post-burn peak q <= {q_lim:.0f} Pa '
                          f'(best {last.q_peak:.0f} Pa at t_eb = {lo:.1f} s)')
            return out
        # Illinois on f = q_peak - q_lim
        fa, fb = E(lo).q_peak - q_lim, E(hi).q_peak - q_lim
        a_, b_ = lo, hi
        side = 0
        for _ in range(80):
            c_ = b_ - fb * (b_ - a_) / (fb - fa) if fb != fa else 0.5 * (a_ + b_)
            if not (min(a_, b_) < c_ < max(a_, b_)):
                c_ = 0.5 * (a_ + b_)
            ev = E(c_)
            if not ev.ok:
                c_ = 0.5 * (a_ + b_)
                ev = E(c_)
            fc = ev.q_peak - q_lim
            if abs(fc) < num.entry_q_tol or abs(b_ - a_) < 1e-9:
                break
            if (fc > 0) == (fb > 0):
                b_, fb = c_, fc
                if side == -1:
                    fa *= 0.5
                side = -1
            else:
                a_, fa = c_, fc
                if side == +1:
                    fb *= 0.5
                side = +1
        # use the feasible side (q <= q_lim)
        e_star = ev if ev.q_peak <= q_lim + num.entry_q_tol else E(hi)
    if record:
        e_star = run_entry(veh, earth, num, t, y, e_star.t_eb, record=True)
        phases += e_star.phases
    m_desc = e_star.y_end[4]
    # 3-4. landing
    land = solve_landing(veh, earth, num, e_star.desc, m_desc, warm=w.get('landing'), scan=scan, record=record)
    out.landing = land
    out.t_eb, out.m_entry, out.entry_k_profile = e_star.t_eb, e_star.m_entry, e_star.k_profile
    out.q_peak_desc, out.h_qpeak = e_star.q_peak, e_star.h_qpeak
    if land.status != 'feasible':
        out.status, out.reason = land.status, 'landing: ' + land.reason
        return out
    out.m_landing = land.propellant
    out.margin = veh.eps_m * (out.m_entry + out.m_landing)
    out.residual = veh.m_res
    out.reserve = out.m_entry + out.m_landing + out.margin + out.residual
    out.status, out.reason = 'feasible', 'ok'
    if record:
        # descent up to ignition, then the landing burn
        ph = e_star.desc_record
        keep = ph.h >= land.h_ig
        phases.append(Phase('aero_descent', ph.t[keep], ph.y[keep], ph.q[keep], ph.thrust[keep], ph.mdot[keep],
                            ph.a_ng[keep], ph.h[keep], ph.vrel[keep], ph.drag[keep]))
        phases.append(land.burn_phase)
        out.phases = phases
        out.downrange_m = float(land.burn_phase.y[-1][1] * re)
    # warm-start info for the next fixed-point iteration
    w['t_eb'] = out.t_eb
    w['landing'] = {r.k: {'u': r.u, 'h_ig': r.burn.h_ig} for r in land.per_k if r.status == 'feasible'}
    return out
