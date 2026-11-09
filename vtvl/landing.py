"""Landing burn: retrograde thrust, k engines at constant mass-flow fraction u.

Control family (restricted, stated): ONE burn, k in {1, 3} (k <= N) engines, constant u in
[u_min, u_max], thrust anti-parallel to the velocity relative to the atmosphere/ground
(gravity-turn descent). For each (k, u) the ignition altitude is solved so the speed reaches
zero exactly at h = 0. Among feasible (k, u) the least propellant wins; the acceleration cap
is |thrust + drag|/m <= a_max_land over the whole burn (peak can be at ignition because of
drag, or at touchdown because the mass is lowest).

Status per k:
  feasible            a constant-u burn satisfies all constraints
  infeasible_proven   analytic: (a) T(u_min, p0)/m_ign > a_cap. At touchdown v -> 0, so drag -> 0
                      and the non-grav acceleration is T/m_td >= T(u_min)/m_ign; no u >= u_min helps.
                      (b) T(u_max, p0)/((m_dry + m_res) g0) <= 1: the burn cannot null the velocity
                      (near v = 0 drag vanishes, net acceleration points down) at any touchdown mass.
  no_solution_found   the numerical search found no (u, ignition) pair; diagnostics recorded.
"Minimum thrust exceeds weight" is NOT a failure (a hoverslam with T/W > 1 can land).
"""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq

from .atmosphere import P0_SEA_LEVEL, atmosphere
from .config import Earth, Numerics, Vehicle
from .dynamics import constant_cd, make_dynamics
from .integrate import Event, integrate, locate

H_SCAN = (150.0, 300.0, 600.0, 1200.0, 2500.0, 5000.0, 10000.0, 20000.0, 40000.0)  # m, bracket search


@dataclass
class BurnEval:
    h_ig: float
    F: float                 # altitude at which speed reaches v_stop (negative: ground hit first)
    propellant: float = math.nan
    peak_accel: float = math.nan
    peak_at: str = ''
    t_burn: float = math.nan
    m_ign: float = math.nan
    m_td: float = math.nan
    v_ign: float = math.nan
    stopped: bool = False
    phase: object = None
    t_ig: float = math.nan
    y_ig: list = field(default_factory=list)
    v_final: float = math.nan     # vertical velocity at the stop point (= -landing_stop_speed)


@dataclass
class KResult:
    k: int
    status: str
    reason: str = ''
    u: float = math.nan
    burn: BurnEval | None = None
    scan: list = field(default_factory=list)      # (u, feasible, propellant, peak_accel_g)
    tw_min_td: float = math.nan                    # T(u_min, p0) / (m_td g0)
    tw_max_td: float = math.nan


@dataclass
class LandingResult:
    status: str
    reason: str
    k: int = 0
    u: float = math.nan
    propellant: float = math.nan
    h_ig: float = math.nan
    peak_accel_g: float = math.nan
    peak_at: str = ''
    t_burn: float = math.nan
    m_td: float = math.nan
    v_ign: float = math.nan
    tw_min_td: float = math.nan
    per_k: list = field(default_factory=list)
    burn_phase: object = None
    t_ig: float = math.nan
    y_ig: list = field(default_factory=list)


class Descent:
    """Recorded ballistic descent (fixed RK4 nodes) used to start burns at any altitude.
    ``phase`` (optional) carries drag/pressure diagnostics at the nodes."""

    def __init__(self, rhs, ts, ys, r_e, phase=None):
        self.rhs, self.ts, self.ys, self.r_e, self.phase = rhs, ts, ys, r_e, phase
        self.neg_h = [-(y[0] - r_e) for y in ys]   # increasing along a monotone descent

    def state_at_altitude(self, h_target: float):
        i = bisect.bisect_left(self.neg_h, -h_target)
        if i <= 0 or i >= len(self.ts):
            return None
        re = self.r_e
        g = lambda t, y: y[0] - re - h_target
        t0, y0, t1, y1 = self.ts[i - 1], self.ys[i - 1], self.ts[i], self.ys[i]
        ga, gb = g(t0, y0), g(t1, y1)
        if not (ga > 0.0 >= gb):
            return None
        s, ys = locate(self.rhs, t0, y0, t1 - t0, g, ga, gb)
        return t0 + s, ys

    @property
    def h_top(self) -> float:
        return self.ys[0][0] - self.r_e


def _burn(veh: Vehicle, earth: Earth, num: Numerics, desc: Descent, k: int, u: float, h_ig: float,
          record: bool = False) -> BurnEval:
    st = desc.state_at_altitude(h_ig)
    if st is None:
        return BurnEval(h_ig, math.nan)
    t0, y0 = st
    eng = veh.engine
    tv, ae, md = eng.t_vac, eng.a_e, eng.mdot

    def control(t, y, h, p, q, d, vr, vrt, vrel):
        T = k * (u * tv - p * ae)
        if vrel > 0.0:
            return T, -vr / vrel, -vrt / vrel, k * u * md
        return T, 1.0, 0.0, k * u * md

    rhs, terms = make_dynamics(earth, veh.area, constant_cd(veh.cd_desc), control)
    re = earth.r_e
    vstop = num.landing_stop_speed
    chatter = (veh.a_max_land - earth.g0) * num.dt('landing') / 2.0
    if not (1.5 * chatter < vstop <= veh.v_td):
        raise ValueError(f'landing_stop_speed {vstop} must be in (1.5*{chatter:.3f}, v_td={veh.v_td}] m/s')
    # Stop when the VERTICAL velocity rises through -v_stop. (|v| can overshoot through zero inside
    # one step because the retrograde direction flips; v_r is smooth.) In a retrograde-thrust descent
    # the flight path steepens monotonically, so the horizontal speed is ~0 at this point; the
    # independent replay checks the full touchdown speed.
    evs = [Event('stop', lambda t, y: y[2] + vstop, +1), Event('ground', lambda t, y: y[0] - re, -1)]
    t_guard = 600.0  # s, numerical guard; a landing burn is tens of seconds
    res = integrate(rhs, t0, y0, num.dt('landing'), t0 + t_guard, evs, record=True)
    yf = res.y_final
    hf = yf[0] - re
    diag = [terms(ti, yi)[1] for ti, yi in zip(res.t, res.y)]
    if veh.land_cap_basis == 'thrust_plus_drag':
        a_ng = [math.hypot(d[8], d[9]) for d in diag]
    elif veh.land_cap_basis == 'thrust_only':
        a_ng = [d[3] / yi[4] for d, yi in zip(diag, res.y)]
    else:
        raise ValueError(f'unknown landing cap basis {veh.land_cap_basis!r}')
    # At the stop node the velocity is ~0 so drag ~ 0: a_ng there is T/m_td.
    i_pk = int(np.argmax(a_ng))
    n = len(a_ng)
    peak_at = 'ignition' if i_pk == 0 else ('touchdown' if i_pk >= n - 2 else 'mid-burn')
    v_ign = diag[0][6]
    ev = BurnEval(h_ig, 0.0, propellant=y0[4] - yf[4], peak_accel=a_ng[i_pk], peak_at=peak_at,
                  t_burn=res.t_final - t0, m_ign=y0[4], m_td=yf[4], v_ign=v_ign, t_ig=t0, y_ig=list(y0),
                  v_final=yf[2])
    if res.event == 'stop':
        ev.F, ev.stopped = hf, True
    elif res.event == 'ground':
        vg = diag[-1][6]
        a_net = abs(veh.engine.thrust(u, P0_SEA_LEVEL, k) / yf[4] - earth.g0)
        ev.F = -vg * vg / (2.0 * max(a_net, 0.5))
    else:
        ev.F = -1.0e6   # hovered/never stopped within the time limit: treat as failure side
    if record:
        from .ascent import Phase
        d = np.array(diag)
        ev.phase = Phase('landing_burn', np.array(res.t), np.array(res.y), q=d[:, 1], thrust=d[:, 3],
                         mdot=d[:, 4], a_ng=np.array(a_ng), h=d[:, 0], vrel=d[:, 6], drag=d[:, 2])
    return ev


def _ignition_root(veh, earth, num, desc, k, u, h_guess=None) -> BurnEval | None:
    """Solve F(h_ig) = 0 (speed reaches v_stop exactly at h = 0)."""
    cache = {}

    def F(h):
        if h not in cache:
            cache[h] = _burn(veh, earth, num, desc, k, u, h)
        return cache[h].F

    h_top = desc.h_top - 1.0
    grid = sorted(set([h for h in H_SCAN if h < h_top] + ([h_guess * 0.97, h_guess * 1.03] if h_guess else [])))
    lo = hi = None
    prev = None
    for h in grid:
        f = F(h)
        if not math.isfinite(f):
            continue
        if f < 0:
            prev = h
        elif prev is not None:
            lo, hi = prev, h
            break
    if lo is None:
        return None
    h_star = brentq(F, lo, hi, xtol=num.landing_ignition_tol * 1e-3, rtol=1e-14, maxiter=200)
    ev = _burn(veh, earth, num, desc, k, u, h_star)
    return ev if ev.stopped or abs(ev.F) < num.landing_ignition_tol else None


def solve_k(veh: Vehicle, earth: Earth, num: Numerics, desc: Descent, m_desc: float, k: int,
            warm: dict | None = None, scan: bool = False) -> KResult:
    eng, cap, g0 = veh.engine, veh.a_max_land, earth.g0
    t_min = eng.thrust(veh.u_min, P0_SEA_LEVEL, k)
    t_max = eng.thrust(veh.u_max, P0_SEA_LEVEL, k)
    out = KResult(k, 'no_solution_found')
    m_td_lower = veh.m_dry1 + veh.m_res
    # (a) touchdown acceleration bound
    if t_min / m_desc > cap:
        out.status = 'infeasible_proven'
        out.reason = (f'k={k}: T(u_min,SL)={t_min/1e3:.0f} kN; even at the ignition mass {m_desc/1e3:.2f} t '
                      f'the touchdown non-grav accel would exceed {t_min/m_desc/g0:.2f} g > cap {cap/g0:.2f} g '
                      f'(needs m_td >= {t_min/cap/1e3:.1f} t)')
        out.tw_min_td = t_min / (m_desc * g0)
        return out
    # (b) cannot null velocity
    if t_max / (m_td_lower * g0) <= 1.0:
        out.status = 'infeasible_proven'
        out.reason = (f'k={k}: T(u_max,SL)={t_max/1e3:.0f} kN <= weight at the lightest possible touchdown '
                      f'mass {m_td_lower/1e3:.2f} t (T/W={t_max/(m_td_lower*g0):.3f})')
        return out
    # (c) ignition-load bound: at the instant of ignition the non-grav acceleration is
    #     (T + D)/m >= (T(u_min, p) + D)/m. If that exceeds the cap at EVERY point of the computed
    #     descent, no ignition point and no throttle history >= u_min can respect the cap.
    ph = desc.phase
    if veh.land_cap_basis == 'thrust_plus_drag' and ph is not None and len(ph.h) > 1:
        above = ph.h > 1.0
        m_n = ph.y[above, 4]
        load = np.array([(eng.thrust(veh.u_min, atmosphere(h)[1], k) + d) / m
                         for h, d, m in zip(ph.h[above], ph.drag[above], m_n)])
        if load.size and load.min() > cap + 0.01 * g0:
            i = int(np.argmin(load))
            out.status = 'infeasible_proven'
            out.reason = (f'k={k}: at every ignition point of the descent, drag + {k} engine(s) at u_min already '
                          f'exceed the cap: min (T_min+D)/m = {load[i]/g0:.3f} g at h = {ph.h[above][i]:.0f} m '
                          f'(D/m = {ph.drag[above][i]/m_n[i]/g0:.2f} g, T_min/m = {(load[i]*m_n[i]-ph.drag[above][i])/m_n[i]/g0:.2f} g) '
                          f'> cap {cap/g0:.2f} g')
            out.tw_min_td = t_min / (m_desc * g0)
            return out

    def evaluate(u, h_guess=None):
        return _ignition_root(veh, earth, num, desc, k, u, h_guess)

    w = warm or {}
    hg = w.get('h_ig')

    def feas(ev):
        return ev is not None and ev.peak_accel <= cap * (1 + 1e-9)

    e_hi = evaluate(veh.u_max, hg)
    if feas(e_hi):
        u_star, e_star = veh.u_max, e_hi
    else:
        e_lo = evaluate(veh.u_min, hg)
        if e_lo is None:
            out.reason = f'k={k}: no ignition altitude found at u_min (descent top {desc.h_top:.0f} m)'
            return out
        if not feas(e_lo):
            out.reason = (f'k={k}: constant-throttle family: peak non-grav accel at u_min = '
                          f'{e_lo.peak_accel/g0:.3f} g ({e_lo.peak_at}) > cap {cap/g0:.2f} g')
            out.tw_min_td = t_min / (e_lo.m_td * g0)
            if e_lo.peak_at == 'touchdown':
                out.status = 'infeasible_proven'
                out.reason += (f'; at touchdown drag ~ 0 so accel = T/m_td = {t_min/e_lo.m_td/g0:.3f} g; '
                               f'higher u only raises T')
            return out
        # root of peak(u) - cap between u_min (feasible) and u_max (infeasible)
        cache = {}

        def gfun(u):
            ev = evaluate(u, cache.get('h'))
            cache[u] = ev
            if ev is None:
                return 1.0
            cache['h'] = ev.h_ig
            return ev.peak_accel / cap - 1.0

        ua, ub = veh.u_min, veh.u_max
        u0 = w.get('u')
        if u0 is not None and ua < u0 < ub:
            # warm bracket around the previous solution
            for du in (2e-3, 1e-2, 5e-2):
                a_, b_ = max(ua, u0 - du), min(ub, u0 + du)
                if gfun(a_) < 0 < gfun(b_):
                    ua, ub = a_, b_
                    break
        u_star = brentq(gfun, ua, ub, xtol=1e-7, rtol=1e-12, maxiter=100)
        u_star = u_star - 1e-7  # stay on the feasible side of the cap
        e_star = evaluate(u_star, cache.get('h'))
        if not feas(e_star):
            out.reason = f'k={k}: acceleration-cap boundary solve failed (u={u_star:.6f})'
            return out
    out.status, out.u, out.burn = 'feasible', u_star, e_star
    out.reason = 'ok'
    out.tw_min_td = t_min / (e_star.m_td * g0)
    out.tw_max_td = t_max / (e_star.m_td * g0)
    if scan:
        best = (e_star.propellant, u_star, e_star)
        for u in np.linspace(veh.u_min, veh.u_max, num.landing_u_scan):
            ev = evaluate(float(u), e_star.h_ig)
            ok = feas(ev)
            out.scan.append((float(u), bool(ok), ev.propellant if ev else math.nan,
                             ev.peak_accel / g0 if ev else math.nan))
            if ok and ev.propellant < best[0] - 1e-6:
                best = (ev.propellant, float(u), ev)
        if best[1] != u_star:
            out.u, out.burn = best[1], best[2]
            out.reason = 'scan found a cheaper feasible throttle than the cap boundary'
    return out


def solve_landing(veh: Vehicle, earth: Earth, num: Numerics, desc: Descent, m_desc: float,
                  warm: dict | None = None, scan: bool = False, record: bool = False) -> LandingResult:
    per_k = []
    for k in veh.k_land:
        if k > veh.n_engines:
            continue
        per_k.append(solve_k(veh, earth, num, desc, m_desc, k, (warm or {}).get(k), scan))
    feas = [r for r in per_k if r.status == 'feasible']
    if feas:
        best = min(feas, key=lambda r: r.burn.propellant)
        b = best.burn
        if record:
            b = _burn(veh, earth, num, desc, best.k, best.u, b.h_ig, record=True)
        return LandingResult('feasible', best.reason, best.k, best.u, b.propellant, b.h_ig,
                             b.peak_accel / earth.g0, b.peak_at, b.t_burn, b.m_td, b.v_ign,
                             best.tw_min_td, per_k, b.phase, b.t_ig, b.y_ig)
    status = 'infeasible_proven' if per_k and all(r.status == 'infeasible_proven' for r in per_k) else 'no_solution_found'
    return LandingResult(status, ' | '.join(r.reason for r in per_k), per_k=per_k,
                         tw_min_td=min((r.tw_min_td for r in per_k if math.isfinite(r.tw_min_td)), default=math.nan))
