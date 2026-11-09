"""U.S. Standard Atmosphere 1976, 0-86 km geometric altitude; isothermal exponential above.

Units: altitude m (geometric), density kg/m^3, pressure Pa, speed of sound m/s.
The numbers below are the defining constants of the standard (physical constants),
not study inputs. Above 86 km (geopotential 84.852 km) the model is isothermal at
the 86 km molecular-scale temperature; that under-predicts density above ~120 km,
where drag is negligible for this study (stated in docs/ASSUMPTIONS.md).
"""
from __future__ import annotations

import bisect
import math

import numpy as np

P0_SEA_LEVEL = 101325.0          # Pa
_R_EARTH_GEOPOT = 6356766.0      # m, US76 effective Earth radius for geopotential altitude
_G0 = 9.80665                    # m/s^2
_R_AIR = 8314.32 / 28.9644       # J/(kg K)
_GAMMA = 1.4

# Layer base geopotential altitude [m], lapse rate [K/m], base temperature [K], base pressure [Pa]
_HB = [0.0, 11000.0, 20000.0, 32000.0, 47000.0, 51000.0, 71000.0, 84852.0]
_LR = [-0.0065, 0.0, 0.0010, 0.0028, 0.0, -0.0028, -0.0020, 0.0]
_TB = [288.15]
_PB = [P0_SEA_LEVEL]
for _i in range(len(_HB) - 1):
    _dh = _HB[_i + 1] - _HB[_i]
    _t1 = _TB[_i] + _LR[_i] * _dh
    if _LR[_i] == 0.0:
        _p1 = _PB[_i] * math.exp(-_G0 * _dh / (_R_AIR * _TB[_i]))
    else:
        _p1 = _PB[_i] * (_t1 / _TB[_i]) ** (-_G0 / (_R_AIR * _LR[_i]))
    _TB.append(_t1)
    _PB.append(_p1)
_SCALE_TOP = _R_AIR * _TB[-1] / _G0  # isothermal scale height above 84.852 km geopotential


def atmosphere(h: float) -> tuple[float, float, float]:
    """(density, pressure, speed of sound) at geometric altitude h [m]. Scalar, fast."""
    hg = _R_EARTH_GEOPOT * h / (_R_EARTH_GEOPOT + h)
    i = bisect.bisect_right(_HB, hg) - 1
    if i < 0:
        i = 0
    tb, pb, lr, hb = _TB[i], _PB[i], _LR[i], _HB[i]
    if i == len(_HB) - 1:
        t = tb
        p = pb * math.exp(-(hg - hb) / _SCALE_TOP)
    elif lr == 0.0:
        t = tb
        p = pb * math.exp(-_G0 * (hg - hb) / (_R_AIR * tb))
    else:
        t = tb + lr * (hg - hb)
        p = pb * (t / tb) ** (-_G0 / (_R_AIR * lr))
    rho = p / (_R_AIR * t)
    return rho, p, math.sqrt(_GAMMA * _R_AIR * t)


def atmosphere_vec(h) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorised wrapper of :func:`atmosphere` (post-processing only)."""
    h = np.asarray(h, dtype=float)
    out = np.array([atmosphere(float(x)) for x in h.ravel()]).reshape(h.shape + (3,))
    return out[..., 0], out[..., 1], out[..., 2]


def temperature(h: float) -> float:
    """Kinetic temperature [K] (test helper)."""
    rho, p, _ = atmosphere(h)
    return p / (_R_AIR * rho)
