"""Engine thrust/mass-flow model, engine-mass models and booster dry-mass bookkeeping.

Units: N, kg, m, s, Pa. Category of every quantity:
  published data  -> read from the parameter database (see params.py)
  calculations    -> the functions below

Assumption (stated): every engine count N uses the same cycle, chamber pressure
and expansion ratio, so Isp_vac and the vacuum/sea-level thrust ratio r_vs are
the same for all N; only the engine size (throat and exit area) scales with 1/N.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .atmosphere import P0_SEA_LEVEL
from .params import ParameterSet


def massflow_fraction_from_sl_thrust_fraction(f_sl: float, r_vs: float) -> float:
    """Convert a throttle stated as a fraction of rated sea-level thrust (at sea level)
    into the equivalent mass-flow fraction u of the linear thrust model.

    T(u, p) = u*T_vac - p*A_e,  A_e = (T_vac - T_sl)/p0,  T_vac = r_vs*T_sl
    => u*T_vac - (T_vac - T_sl) = f_sl*T_sl  =>  u = (f_sl + r_vs - 1)/r_vs   [-]
    """
    return (f_sl + r_vs - 1.0) / r_vs


@dataclass(frozen=True)
class Engine:
    """One engine of the cluster (all N engines identical).

    t_sl   rated sea-level thrust [N]
    t_vac  rated vacuum thrust [N]
    a_e    nozzle exit area [m^2]
    mdot   rated (u = 1) mass flow [kg/s]
    isp_vac vacuum specific impulse [s]
    g0     standard gravity [m/s^2]
    """
    t_sl: float
    t_vac: float
    a_e: float
    mdot: float
    isp_vac: float
    g0: float

    def thrust(self, u: float, p: float, k: int = 1) -> float:
        """Thrust of k engines at mass-flow fraction u and ambient pressure p [N]."""
        return k * (u * self.t_vac - p * self.a_e)

    def massflow(self, u: float, k: int = 1) -> float:
        """Propellant mass flow of k engines at mass-flow fraction u [kg/s]."""
        return k * u * self.mdot

    def isp(self, u: float, p: float) -> float:
        """Effective specific impulse at (u, p) [s] = T/(mdot*g0)."""
        return self.thrust(u, p) / (self.massflow(u) * self.g0)


def make_engine(P: ParameterSet, n_engines: int) -> Engine:
    """Engine for a cluster of ``n_engines`` at constant total sea-level thrust."""
    t_tot = P.v('engine.total_sl_thrust', 'N')
    r_vs = P.v('engine.vac_to_sl_thrust_ratio', '-')
    isp_vac = P.v('engine.isp_vac', 's')
    g0 = P.v('mission.earth_model', 'SI')['g0']
    t_sl = t_tot / n_engines
    t_vac = r_vs * t_sl
    a_e = (t_vac - t_sl) / P0_SEA_LEVEL
    mdot = t_vac / (g0 * isp_vac)
    return Engine(t_sl=t_sl, t_vac=t_vac, a_e=a_e, mdot=mdot, isp_vac=isp_vac, g0=g0)


# ---------------------------------------------------------------------------------------
# Engine dry mass models (calibrated to m_ref at the reference engine, 845 kN SL)
# ---------------------------------------------------------------------------------------
def akin_raw_mass(t_n: float, P: ParameterSet) -> float:
    """Uncalibrated Akin MER (S7 slide 25): m = a*T + b*T*sqrt(eps) + c  [kg], T in N."""
    co = P.v('engine.akin_mer_coefficients', 'kg, N')
    eps = P.v('engine.nozzle_expansion_ratio', '-')
    return co['a_thrust_kg_per_N'] * t_n + co['b_expansion_kg_per_N'] * t_n * math.sqrt(eps) + co['c_fixed_kg']


def akin_scale(P: ParameterSet) -> float:
    """Scale factor so the Akin MER equals m_ref at the reference engine (computed, not the JSON 0.56)."""
    t_ref = P.v('engine.total_sl_thrust', 'N') / P.v('engine.reference_engine_count', '-')
    return P.v('engine.reference_engine_dry_mass', 'kg') / akin_raw_mass(t_ref, P)


def engine_mass(P: ParameterSet, n_engines: int, model: str | None = None) -> float:
    """Dry mass of ONE engine for a cluster of ``n_engines`` [kg]."""
    model = model or P.v('engine.engine_mass_model', '-')
    m_ref = P.v('engine.reference_engine_dry_mass', 'kg')
    n_ref = P.v('engine.reference_engine_count', '-')
    if model == 'fixed_plus_powerlaw':
        phi = P.v('engine.fixed_mass_fraction', '-')
        beta = P.v('engine.mass_scaling_exponent', '-')
        return m_ref * (phi + (1.0 - phi) * (n_ref / n_engines) ** beta)
    if model == 'akin_scaled':
        t_e = P.v('engine.total_sl_thrust', 'N') / n_engines
        return akin_scale(P) * akin_raw_mass(t_e, P)
    raise ValueError(f'Unknown engine mass model {model!r}')


@dataclass(frozen=True)
class DryMass:
    """Booster dry-mass breakdown [kg]."""
    n_engines: int
    engine_each: float
    engines_total: float
    integration_total: float
    nonengine: float          # structure, tanks, thrust structure, avionics, recovery hardware
    recovery_hardware: float  # legs + grid fins (inside nonengine)
    total: float              # reusable configuration
    expendable_total: float   # recovery hardware removed


def booster_dry_mass(P: ParameterSet, n_engines: int, model: str | None = None) -> DryMass:
    """m_d(N) = m_nonengine + N*(m_e(N) + m_int),  m_nonengine = m_d_ref - N_ref*(m_ref + m_int).

    The thrust structure scales with total thrust (constant), so it is inside m_nonengine.
    Recovery hardware f_rec*m_d_ref is inside m_nonengine and identical for every N.
    """
    m_d_ref = P.v('booster.dry_mass_at_reference', 'kg')
    m_ref = P.v('engine.reference_engine_dry_mass', 'kg')
    m_int = P.v('engine.per_engine_integration_mass', 'kg')
    n_ref = P.v('engine.reference_engine_count', '-')
    f_rec = P.v('booster.recovery_hardware_fraction', '-')
    nonengine = m_d_ref - n_ref * (m_ref + m_int)
    m_e = engine_mass(P, n_engines, model)
    eng_tot = n_engines * m_e
    int_tot = n_engines * m_int
    total = nonengine + eng_tot + int_tot
    rec = f_rec * m_d_ref
    return DryMass(n_engines, m_e, eng_tot, int_tot, nonengine, rec, total, total - rec)


def stage1_propellant_capacity(P: ParameterSet) -> float:
    """P1 [kg] closing the official GLOW at N = 9 without payload (tanks identical for all N).

    P1 = M0 - m_d_ref - m_d2 - P2 - m_bay   (assumes 549,054 kg excludes payload)
    """
    return (P.v('booster.glow_full_vehicle', 'kg') - P.v('booster.dry_mass_at_reference', 'kg')
            - P.v('upper_stage.dry_mass', 'kg') - P.v('upper_stage.propellant', 'kg')
            - P.v('upper_stage.payload_bay_overhead', 'kg'))
