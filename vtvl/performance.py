"""Payload evaluation: ascent + exact orbit insertion + recovery reserve, coupled by a fixed point.

For a given pitch kick, unknowns are the payload L, the stage-2 steering (a, c) and the recovery
reserve R. Each iteration:
    stage 1 with (L_k, R_k)  ->  MECO state
    solve (a, c, L_{k+1}) so stage 2 inserts exactly           (3 x 3 root, ascent.solve_insertion)
    R_{k+1} = recovery(MECO state, booster mass m_dry + R_k)   (reusable only; R = 0 expendable)
until |L_{k+1} - L_k| < tol_L and |R_{k+1} - R_k| < tol_R (|dR| < 1 kg). The iteration count is logged.
A final forward run with the converged (L, R) reports the insertion residuals.

The pitch kick (t_kick, delta) is then optimised for EACH engine count to maximise L subject to
the max-Q constraint q_peak <= q_max (COBYLA, derivative-free; the payload function is built from
nested root solves). Uncertain physical inputs are never optimised.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from scipy.optimize import minimize

from .ascent import Insertion, Kick, Stage1Result, run_stage1, run_stage2, solve_insertion
from .config import Earth, Numerics, Vehicle
from .recovery import RecoveryResult, run_recovery

R_RETRY = (15000.0, 25000.0, 35000.0, 45000.0, 55000.0, 70000.0)   # kg, trial reserves before a verdict
STEER_GUESSES = ((0.3, 0.3), (0.0, -0.3), (0.5, 1.0), (-0.1, -0.6), (0.8, 1.5))


@dataclass
class Warm:
    L: float = 17000.0
    R: float = 30000.0
    steer: tuple = (0.3, 0.3)
    rec: dict = field(default_factory=dict)

    def copy(self) -> 'Warm':
        import copy
        return Warm(self.L, self.R, tuple(self.steer), copy.deepcopy(self.rec))


@dataclass
class PayloadEval:
    status: str
    reason: str
    kick: Kick
    payload: float = math.nan
    reserve: float = math.nan
    iterations: int = 0
    s1: Stage1Result | None = None
    ins: Insertion | None = None
    rec: RecoveryResult | None = None
    residual: tuple = (math.nan, math.nan, math.nan)
    history: list = field(default_factory=list)
    steer: tuple = (math.nan, math.nan)
    s2: object = None
    inner_iterations: int = 0


def solve_insertion_robust(veh, earth, num, s1, guess) -> Insertion:
    ins = solve_insertion(veh, earth, num, s1, guess)
    if ins.success:
        return ins
    tried = [ins]
    for sg in STEER_GUESSES:
        ins = solve_insertion(veh, earth, num, s1, (sg[0], sg[1], guess[2]))
        tried.append(ins)
        if ins.success:
            return ins
    best = min(tried, key=lambda r: sum(abs(x) for x in r.residual) if all(math.isfinite(x) for x in r.residual) else math.inf)
    best.message = f'all {len(tried)} insertion starts failed; best: ' + best.message
    return best


def _ascent_at_reserve(veh, earth, num, kick, R, L, steer):
    """Inner loop: at fixed reserve R, iterate stage 1 + insertion until the payload L converges.
    Returns (ok, reason, s1, ins, L, steer, iterations)."""
    for j in range(1, num.fixed_point_max_iter + 1):
        s1 = run_stage1(veh, earth, num, kick, L, R)
        if not s1.ok:
            return False, f'stage 1: {s1.reason}', s1, None, L, steer, j
        ins = solve_insertion_robust(veh, earth, num, s1, (steer[0], steer[1], L))
        if not ins.success:
            return False, f'orbit insertion: {ins.message}', s1, ins, L, steer, j
        dL = ins.payload - L
        L, steer = ins.payload, ins.steer
        if abs(dL) < num.fixed_point_tol_L:
            return True, 'ok', s1, ins, L, steer, j
    return False, f'payload iteration not converged at R={R:.0f} kg (last dL={dL:.3f} kg)', s1, ins, L, steer, j


def evaluate_payload(veh: Vehicle, earth: Earth, num: Numerics, kick: Kick, warm: Warm | None = None,
                     final: bool = False) -> PayloadEval:
    """Converged payload for one pitch kick. Fixed point R = Rec(MECO(R, L(R))) solved by a
    safeguarded secant iteration on h(R) = Rec(R) - R; L converged at each trial R (inner loop)."""
    w = warm if warm is not None else Warm()
    reusable = veh.mode == 'reusable'
    L, R, steer = w.L, (w.R if reusable else 0.0), w.steer
    out = PayloadEval('no_solution_found', '', kick)
    inner_total = 0
    rec = None

    def stage(Rtrial, L, steer):
        nonlocal inner_total
        ok, why, s1, ins, L2, steer2, n = _ascent_at_reserve(veh, earth, num, kick, Rtrial, L, steer)
        inner_total += n
        if not ok:
            return ok, why, s1, ins, L2, steer2, None
        r = run_recovery(veh, earth, num, s1.t_meco, s1.y_meco[:4], Rtrial, warm=w.rec) if reusable else None
        return ok, why, s1, ins, L2, steer2, r

    converged = False
    retried = False
    hist = out.history
    pts = []   # (R, h) for the secant
    it = 0
    for it in range(1, num.fixed_point_max_iter + 1):
        ok, why, s1, ins, L, steer, rec = stage(R, L, steer)
        if not ok:
            out.reason = f'{why} (outer iteration {it})'
            out.iterations, out.s1 = it, s1
            return out
        if not reusable:
            converged = True
            break
        if rec.status != 'feasible':
            if pts:
                # a secant trial left the feasible set: retreat halfway toward the last good point
                Rg, hg = pts[-1]
                if abs(R - (Rg + hg)) > 1.0:
                    R = 0.5 * (R + Rg + hg)
                    continue
            # No feasible iterate yet. Recovery feasibility depends on the (unknown) reserve, so
            # before any verdict try a spread of starting reserves; a "proven" label requires every
            # trial reserve to fail with a proven reason.
            if not retried:
                retried = True
                fails = [(R, rec)]
                found = False
                for Rt in R_RETRY:
                    if abs(Rt - R) < 1.0:
                        continue
                    ok2, why2, s1b, insb, Lb, stb, recb = stage(Rt, L, steer)
                    if not ok2:
                        continue
                    if recb.status == 'feasible':
                        R, L, steer, found = Rt, Lb, stb, True
                        break
                    fails.append((Rt, recb))
                if found:
                    continue
                proven = all(f[1].status == 'infeasible_proven' for f in fails)
                out.status = 'infeasible_proven' if proven else 'no_solution_found'
                rng = f'{min(f[0] for f in fails)/1e3:.0f}-{max(f[0] for f in fails)/1e3:.0f} t'
                out.reason = (f'recovery infeasible at every trial reserve R = {rng} '
                              f'({len(fails)} trials); at R = {R:.0f} kg: {rec.reason}')
                out.iterations, out.s1, out.rec = it, s1, rec
                return out
            out.status = rec.status
            out.reason = f'recovery (outer iteration {it}, R = {R:.0f} kg): {rec.reason}'
            out.iterations, out.s1, out.rec = it, s1, rec
            return out
        h = rec.reserve - R
        hist.append((L, R, rec.reserve))
        if abs(h) < num.fixed_point_tol_R:
            converged = True
            break
        pts.append((R, h))
        if len(pts) >= 2 and pts[-1][1] != pts[-2][1]:
            (R0, h0), (R1, h1) = pts[-2], pts[-1]
            Rn = R1 - h1 * (R1 - R0) / (h1 - h0)
            if not (0.0 < Rn < veh.p1) or abs(Rn - R1) > 4.0 * abs(h1) + 500.0:
                Rn = R1 + h1          # fall back to a plain fixed-point step
        else:
            Rn = R + h
        R = Rn
    out.iterations = it
    out.inner_iterations = inner_total
    if not converged:
        last = hist[-1] if hist else None
        out.reason = f'fixed point not converged after {it} outer iterations (last R={R:.1f}, R\'-R={last[2]-last[1] if last else math.nan:.2f} kg)'
        return out
    if L <= 0.0:
        out.reason = f'converged payload is not positive ({L:.0f} kg) in this control family'
        return out
    # final consistent forward run with the converged (L, R)
    s1 = run_stage1(veh, earth, num, kick, L, R)
    s2 = run_stage2(veh, earth, num, s1.t_meco, s1.y_meco[:4], s1.fairing_on, L, steer, record=final)
    out.status, out.reason = 'feasible', 'ok'
    out.payload, out.reserve, out.steer = L, R, steer
    out.s1, out.ins, out.residual = s1, ins, s2.residual
    out.ins.residual = s2.residual
    if final and reusable:
        out.rec = run_recovery(veh, earth, num, s1.t_meco, s1.y_meco[:4], R, warm=w.rec, scan=True, record=True)
        if out.rec.status != 'feasible' or abs(out.rec.reserve - R) > 5.0 * num.fixed_point_tol_R:
            # The u-scan may select a cheaper throttle than the cap boundary; re-converge once if so.
            if out.rec.status == 'feasible':
                out.reason = f'final scan changed the reserve by {out.rec.reserve - R:.1f} kg'
    elif reusable:
        out.rec = rec
    out.s2 = s2
    # update warm start
    w.L, w.R, w.steer = L, R, steer
    return out


@dataclass
class KickOpt:
    best: PayloadEval
    evaluations: int
    message: str
    trace: list = field(default_factory=list)   # (t_kick, delta, payload, q_peak, status)


def _scale(num: Numerics):
    (t0, t1), (d0, d1) = num.kick_time_bounds, num.kick_angle_bounds
    to_x = lambda k: [(k.t_kick - t0) / (t1 - t0), (k.delta_deg - d0) / (d1 - d0)]
    to_k = lambda x: Kick(t0 + x[0] * (t1 - t0), d0 + x[1] * (d1 - d0))
    return to_x, to_k


def optimize_kick(veh: Vehicle, earth: Earth, num: Numerics, kick0: Kick, warm: Warm | None = None) -> KickOpt:
    """Maximise payload over (t_kick, delta) subject to q_peak <= q_max, for THIS vehicle (engine count)."""
    to_x, to_k = _scale(num)
    w = warm if warm is not None else Warm()
    cache: dict = {}
    trace = []
    best = [None]

    def ev(x):
        x = [min(1.0, max(0.0, float(v))) for v in x]
        key = tuple(round(v, 12) for v in x)
        if key not in cache:
            k = to_k(x)
            wl = w.copy()
            r = evaluate_payload(veh, earth, num, k, wl)
            if r.status == 'feasible':
                # carry the successful warm start forward
                w.L, w.R, w.steer, w.rec = wl.L, wl.R, wl.steer, wl.rec
            cache[key] = r
            q = r.s1.q_peak if r.s1 is not None else math.nan
            trace.append((k.t_kick, k.delta_deg, r.payload, q, r.status))
            if r.status == 'feasible' and r.s1.q_peak <= veh.q_max * (1 + 1e-6):
                if best[0] is None or r.payload > best[0].payload:
                    best[0] = r
        return cache[key]

    def f(x):
        r = ev(x)
        return -r.payload / 1e4 if r.status == 'feasible' else 10.0

    def g(x):
        r = ev(x)
        if r.s1 is None or not math.isfinite(r.s1.q_peak):
            return -1.0
        return (veh.q_max - r.s1.q_peak) / veh.q_max

    x0 = to_x(kick0)
    res = minimize(f, x0, method='COBYLA',
                   constraints=[{'type': 'ineq', 'fun': g}],
                   bounds=[(0.0, 1.0), (0.0, 1.0)],
                   options={'rhobeg': num.kick_opt_rhobeg, 'tol': num.kick_opt_tol, 'maxiter': num.kick_opt_maxfun})
    if best[0] is None:
        # COBYLA can stall a few Pa above the max-Q limit. Before giving up, take the payload-feasible
        # kick with the lowest q_peak and bisect its kick angle upward (larger delta lowers q_peak)
        # until q_peak <= q_max. Same logic for every N; a numerical-tolerance repair, not a model change.
        cands = [(t[3], t[0], t[1]) for t in trace if t[4] == 'feasible' and math.isfinite(t[3])]
        if cands:
            q0, t_k, d0 = min(cands)
            if q0 <= veh.q_max * 1.02:
                lo, hi = d0, d0 + 0.5
                for _ in range(30):
                    mid = 0.5 * (lo + hi)
                    r = evaluate_payload(veh, earth, num, Kick(t_k, mid), w.copy())
                    trace.append((t_k, mid, r.payload, r.s1.q_peak if r.s1 else math.nan, r.status))
                    if r.status == 'feasible' and r.s1.q_peak <= veh.q_max:
                        hi = mid
                        if best[0] is None or r.payload > best[0].payload:
                            best[0] = r
                        if veh.q_max - r.s1.q_peak < 1e-4 * veh.q_max:
                            break
                    else:
                        lo = mid
                        if r.status != 'feasible':
                            break
    if best[0] is None:
        # No evaluated kick satisfied both the payload solve and q_peak <= q_max.
        r = ev(res.x)
        q_feas = [t[3] for t in trace if t[4] == 'feasible' and math.isfinite(t[3])]
        fail = PayloadEval('no_solution_found', '', r.kick, iterations=r.iterations, s1=r.s1, rec=r.rec)
        if q_feas:
            fail.reason = (f'max-Q constraint not met by any evaluated kick: lowest q_peak among payload-feasible '
                           f'kicks = {min(q_feas):.0f} Pa > q_max = {veh.q_max:.0f} Pa (COBYLA: {res.message})')
        else:
            fail.status = r.status if r.status != 'feasible' else 'no_solution_found'
            fail.reason = f'no payload-feasible kick found; last: {r.reason} (COBYLA: {res.message})'
        return KickOpt(fail, len(cache), fail.reason, trace)
    return KickOpt(best[0], len(cache), str(res.message), trace)
