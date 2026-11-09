"""2-D planar point-mass dynamics over a spherical rotating Earth (polar coordinates).

State y = [r, theta, v_r, v_t, m]   (m, rad, m/s, m/s, kg), inertial velocity components.
Equations:
    dr/dt     = v_r
    dtheta/dt = v_t / r
    dv_r/dt   = v_t^2/r - g(r) + (T e_r - D v_rel,r/|v_rel|)/m
    dv_t/dt   = -v_r v_t / r   + (T e_t - D v_rel,t/|v_rel|)/m
    dm/dt     = -mdot
with g = mu/r^2, the atmosphere co-rotating at omega_eff (v_rel,t = v_t - omega_eff*r),
drag D = 0.5*rho*|v_rel|^2*Cd*A opposite to v_rel, and thrust T along the unit vector
(e_r, e_t) chosen by a control law. The control law returns (T, e_r, e_t, mdot).
"""
from __future__ import annotations

import math
from typing import Callable

from .atmosphere import atmosphere
from .config import Earth


def make_dynamics(earth: Earth, area: float, cd_of_mach: Callable[[float], float], control: Callable):
    """Return (rhs, terms). ``terms(t, y)`` returns (dy/dt, diagnostics tuple)

    diagnostics = (h, q, D, T, mdot, mach, vrel, p, a_ng_r, a_ng_t)  with a_ng the
    non-gravitational (thrust + drag) acceleration components [m/s^2].
    control(t, y, h, p, q, D, vr, vrt, vrel) -> (T [N], e_r, e_t, mdot [kg/s])
    """
    mu, re, om, g0 = earth.mu, earth.r_e, earth.omega_eff, earth.g0
    const_g = earth.gravity == 'constant'
    atm_on = earth.atmosphere
    sqrt = math.sqrt

    def terms(t, y):
        r, th, vr, vt, m = y
        h = r - re
        if atm_on:
            rho, p, a = atmosphere(h)
        else:
            rho, p, a = 0.0, 0.0, 1.0
        vrt = vt - om * r
        vrel = sqrt(vr * vr + vrt * vrt)
        q = 0.5 * rho * vrel * vrel
        mach = vrel / a
        d = q * cd_of_mach(mach) * area if q > 0.0 else 0.0
        T, er, et, mdot = control(t, y, h, p, q, d, vr, vrt, vrel)
        g = g0 if const_g else mu / (r * r)
        if vrel > 0.0:
            dr_ = d * vr / vrel
            dt_ = d * vrt / vrel
        else:
            dr_ = dt_ = 0.0
        ar = (T * er - dr_) / m
        at = (T * et - dt_) / m
        return [vr, vt / r, vt * vt / r - g + ar, -vr * vt / r + at, -mdot], (h, q, d, T, mdot, mach, vrel, p, ar, at)

    def rhs(t, y):
        return terms(t, y)[0]

    return rhs, terms


def constant_cd(cd: float) -> Callable[[float], float]:
    return lambda mach: cd


def specific_energy(earth: Earth, y) -> float:
    """Inertial specific orbital energy [J/kg] (vacuum Kepler test)."""
    r, th, vr, vt, m = y
    return 0.5 * (vr * vr + vt * vt) - earth.mu / r


def angular_momentum(y) -> float:
    """Specific angular momentum r*v_t [m^2/s]."""
    return y[0] * y[3]
