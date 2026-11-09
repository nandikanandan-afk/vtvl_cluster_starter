"""Two-knob calibration at N = 9, then frozen for every other N (prompt section 6.5).

Knob 1 (expendable anchor 22,800 kg, tolerance 1 %): ascent Cd scale, range [0.8, 1.2] (JSON).
Knob 2 (reusable anchor, band 17.4-18.5 t, target 17.5 t): q_entry_max. The JSON gives no range
except the DLR model bound q < 200 kPa (an upper bound only), so the search is confined to
(0, 200 kPa]. Ranges are never stretched: if the anchor cannot be reached, the closest in-range
value and the mismatch are reported (status 'anchor_not_reachable').

Every evaluation re-optimises the pitch kick (performance.optimize_kick).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .ascent import Kick
from .config import Numerics, make_earth, make_vehicle
from .params import ParameterSet
from .performance import KickOpt, Warm, optimize_kick

Q_ENTRY_UPPER = 200000.0   # Pa, DLR model bound (S6), quoted in parameters_baseline.json


@dataclass
class CalPoint:
    knob_value: float
    payload: float
    status: str
    reason: str
    kick: Kick | None = None
    reserve: float = math.nan


@dataclass
class Calibration:
    knob: str
    status: str            # 'calibrated' | 'anchor_not_reachable' | 'no_feasible_point'
    value: float
    payload: float
    target: float
    message: str
    points: list = field(default_factory=list)


def _evaluate(P: ParameterSet, num: Numerics, n: int, mode: str, kick: Kick, warm: Warm) -> tuple[KickOpt, CalPoint]:
    veh = make_vehicle(P, n, mode)
    earth = make_earth(P)
    ko = optimize_kick(veh, earth, num, kick, warm)
    b = ko.best
    return ko, CalPoint(math.nan, b.payload if b.status == 'feasible' else math.nan, b.status, b.reason, b.kick, b.reserve)


def _secant_root(fn, a, fa, b, fb, xtol, ftol, max_iter=25):
    """Illinois regula falsi for an increasing/decreasing scalar function with a sign change on [a, b]."""
    side = 0
    for _ in range(max_iter):
        c = b - fb * (b - a) / (fb - fa)
        fc = fn(c)
        if abs(fc) <= ftol or abs(b - a) <= xtol:
            return c, fc
        if (fc > 0) == (fb > 0):
            b, fb = c, fc
            if side == -1:
                fa *= 0.5
            side = -1
        else:
            a, fa = c, fc
            if side == +1:
                fb *= 0.5
            side = +1
    return c, fc


def calibrate_expendable(P: ParameterSet, num: Numerics, kick0: Kick, n: int = 9) -> Calibration:
    target = P.v('validation_targets.expendable_leo_payload', 'kg')
    lo, hi = P.get('booster.ascent_cd_scale').range
    pts = []
    warm = Warm(L=target, R=0.0)
    state = {'kick': kick0}

    def L_of(s):
        ko, cp = _evaluate(P.with_overrides({'booster.ascent_cd_scale': s}, 'calibration'), num, n, 'expendable',
                           state['kick'], warm)
        cp.knob_value = s
        pts.append(cp)
        if cp.status == 'feasible':
            state['kick'] = cp.kick
        return cp.payload

    l_lo, l_hi = L_of(lo), L_of(hi)
    f_lo, f_hi = l_lo - target, l_hi - target
    if not (math.isfinite(f_lo) and math.isfinite(f_hi)):
        return Calibration('booster.ascent_cd_scale', 'no_feasible_point', math.nan, math.nan, target,
                           'expendable payload not computable at a range end', pts)
    if f_lo * f_hi > 0:
        best = min(pts, key=lambda p: abs(p.payload - target))
        within = abs(best.payload - target) <= 0.01 * target
        msg = (f'anchor {target:.0f} kg not bracketed by Cd scale in [{lo}, {hi}]: L({lo}) = {l_lo:.0f} kg, '
               f'L({hi}) = {l_hi:.0f} kg. Closest in-range value {best.knob_value} gives {best.payload:.0f} kg '
               f'({100*(best.payload/target-1):+.2f} %).')
        return Calibration('booster.ascent_cd_scale', 'calibrated' if within else 'anchor_not_reachable',
                           best.knob_value, best.payload, target, msg, pts)
    s, fs = _secant_root(lambda s: L_of(s) - target, lo, f_lo, hi, f_hi, xtol=1e-4, ftol=0.002 * target)
    return Calibration('booster.ascent_cd_scale', 'calibrated', s, fs + target, target,
                       f'calibrated: L = {fs + target:.0f} kg', pts)


def calibrate_reusable(P: ParameterSet, num: Numerics, kick0: Kick, n: int = 9,
                       q_trials=(60000.0, 80000.0, 100000.0, 140000.0, Q_ENTRY_UPPER)) -> Calibration:
    target = 17500.0   # prompt section 6.5 (band = validation_targets.reusable_drone_ship_leo_payload.range)
    band = P.get('validation_targets.reusable_drone_ship_leo_payload').range
    pts = []
    warm = Warm(L=target, R=30000.0)
    state = {'kick': kick0}

    def L_of(q):
        ko, cp = _evaluate(P.with_overrides({'recovery.entry_severity_limit_peak_q': q}, 'calibration'), num, n,
                           'reusable', state['kick'], warm)
        cp.knob_value = q
        pts.append(cp)
        if cp.status == 'feasible':
            state['kick'] = cp.kick
        return cp.payload

    vals = []
    for q in q_trials:
        L = L_of(q)
        vals.append((q, L))
    feas = [(q, L) for q, L in vals if math.isfinite(L)]
    if not feas:
        return Calibration('recovery.entry_severity_limit_peak_q', 'no_feasible_point', math.nan, math.nan, target,
                           'N = 9 reusable has no feasible solution at any trial q_entry_max: ' +
                           '; '.join(f'{p.knob_value:.0f} Pa: {p.status}: {p.reason[:160]}' for p in pts), pts)
    # bracket target between consecutive feasible trials (payload increases with q_entry_max)
    for (qa, La), (qb, Lb) in zip(feas, feas[1:]):
        if (La - target) * (Lb - target) <= 0:
            q, f = _secant_root(lambda q: L_of(q) - target, qa, La - target, qb, Lb - target, xtol=50.0, ftol=10.0)
            in_band = band[0] <= f + target <= band[1]
            return Calibration('recovery.entry_severity_limit_peak_q', 'calibrated' if in_band else 'anchor_not_reachable',
                               q, f + target, target, f'calibrated: L = {f + target:.0f} kg', pts)
    best = min(feas, key=lambda t: abs(t[1] - target))
    return Calibration('recovery.entry_severity_limit_peak_q', 'anchor_not_reachable', best[0], best[1], target,
                       f'target {target:.0f} kg not bracketed by feasible q_entry_max trials {feas}', pts)
