"""Fixed-step classical RK4 with exact event location (pure-Python scalar core).

Why fixed-step RK4: the payload solve nests several root solves around thousands of
trajectory propagations, and SciPy's per-step overhead dominated in profiling. Accuracy is
verified by (i) analytic solutions, (ii) step halving (payload change < 10 kg), and (iii) an
independent SciPy DOP853 replay of every reported touchdown and orbit insertion.

Events: g(t, y) changes sign over a step in the requested direction -> the crossing is located
by Illinois regula falsi on the sub-step length s, re-taking one RK4 step of length s from the
step start each time (so the located state has the same order of accuracy as the integrator).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

State = list  # list[float]


def rk4_step(f: Callable, t: float, y: Sequence[float], h: float) -> list:
    k1 = f(t, y)
    hh = 0.5 * h
    y1 = [a + hh * b for a, b in zip(y, k1)]
    k2 = f(t + hh, y1)
    y2 = [a + hh * b for a, b in zip(y, k2)]
    k3 = f(t + hh, y2)
    y3 = [a + h * b for a, b in zip(y, k3)]
    k4 = f(t + h, y3)
    h6 = h / 6.0
    return [a + h6 * (b1 + 2.0 * b2 + 2.0 * b3 + b4) for a, b1, b2, b3, b4 in zip(y, k1, k2, k3, k4)]


@dataclass
class Event:
    """Terminal event g(t, y) = 0. direction: +1 rising, -1 falling, 0 either."""
    name: str
    fn: Callable[[float, Sequence[float]], float]
    direction: int = 0


@dataclass
class Result:
    t: list = field(default_factory=list)
    y: list = field(default_factory=list)
    event: str | None = None   # name of the terminal event, or None if t_end reached
    t_final: float = 0.0
    y_final: list = field(default_factory=list)
    steps: int = 0


def _crossed(g0: float, g1: float, direction: int) -> bool:
    if direction > 0:
        return g0 < 0.0 <= g1
    if direction < 0:
        return g0 > 0.0 >= g1
    return (g0 < 0.0 <= g1) or (g0 > 0.0 >= g1)


def locate(f: Callable, t: float, y: Sequence[float], h: float, g: Callable, ga: float, gb: float,
           tol_s: float = 1e-10, max_iter: int = 60) -> tuple[float, list]:
    """Find s in (0, h] with g(t+s, RK4(t, y, s)) = 0 given g(t,y)=ga and g at s=h equal gb."""
    a, b = 0.0, h
    fa, fb = ga, gb
    side = 0
    yb = None
    for _ in range(max_iter):
        s = b - fb * (b - a) / (fb - fa) if fb != fa else 0.5 * (a + b)
        if not (a < s < b):
            s = 0.5 * (a + b)
        ys = rk4_step(f, t, y, s)
        gs = g(t + s, ys)
        if gs == 0.0 or (b - a) < tol_s:
            return s, ys
        if (gs > 0) == (fb > 0):
            b, fb, yb = s, gs, ys
            if side == -1:
                fa *= 0.5
            side = -1
        else:
            a, fa = s, gs
            if side == +1:
                fb *= 0.5
            side = +1
        if abs(b - a) < tol_s:
            break
    s = b
    return s, (yb if yb is not None else rk4_step(f, t, y, s))


def integrate(f: Callable, t0: float, y0: Sequence[float], dt: float, t_end: float,
              events: Sequence[Event] = (), record: bool = True, max_steps: int = 2_000_000) -> Result:
    """Integrate y' = f(t, y) from t0 with fixed step dt until t_end or the first terminal event."""
    t, y = t0, list(y0)
    res = Result()
    if record:
        res.t.append(t)
        res.y.append(y)
    gvals = [ev.fn(t, y) for ev in events]
    steps = 0
    while t < t_end - 1e-12:
        h = min(dt, t_end - t)
        yn = rk4_step(f, t, y, h)
        steps += 1
        if steps > max_steps:
            raise RuntimeError('integrate: max_steps exceeded')
        gnew = [ev.fn(t + h, yn) for ev in events]
        hit = None
        for i, ev in enumerate(events):
            if _crossed(gvals[i], gnew[i], ev.direction):
                s, ys = locate(f, t, y, h, ev.fn, gvals[i], gnew[i])
                if hit is None or s < hit[0]:
                    hit = (s, ys, ev.name)
        if hit is not None:
            s, ys, name = hit
            t, y = t + s, ys
            if record:
                res.t.append(t)
                res.y.append(y)
            res.event, res.t_final, res.y_final, res.steps = name, t, y, steps
            return res
        t, y, gvals = t + h, yn, gnew
        if record:
            res.t.append(t)
            res.y.append(y)
    res.t_final, res.y_final, res.steps = t, y, steps
    return res


def state_at_crossing(f: Callable, ts: Sequence[float], ys: Sequence[Sequence[float]], g: Callable,
                      direction: int = 0) -> tuple[float, list] | None:
    """Re-locate the first crossing of g along a recorded fixed-step trajectory (used to start a
    burn at an arbitrary ignition altitude without re-integrating the whole descent)."""
    g_prev = g(ts[0], ys[0])
    for i in range(1, len(ts)):
        g_now = g(ts[i], ys[i])
        if _crossed(g_prev, g_now, direction):
            s, yv = locate(f, ts[i - 1], ys[i - 1], ts[i] - ts[i - 1], g, g_prev, g_now)
            return ts[i - 1] + s, yv
        g_prev = g_now
    return None
