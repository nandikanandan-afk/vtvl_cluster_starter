"""Vehicle assembly from the parameter database, and numerical settings.

All PHYSICAL numbers come from ``params.ParameterSet``. The ``Numerics`` dataclass holds
only NUMERICAL settings (step sizes, tolerances, search bounds); they are written to every
run manifest and verified by convergence tests. Units: SI (N, kg, m, s, Pa, rad).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict, replace

from .engines import (DryMass, Engine, booster_dry_mass, make_engine,
                      massflow_fraction_from_sl_thrust_fraction, stage1_propellant_capacity)
from .params import ParameterSet


@dataclass(frozen=True)
class Numerics:
    """Numerical settings (not physics). ``step_scale`` multiplies every RK4 step (halving test)."""
    step_scale: float = 1.0
    dt_stage1: float = 0.25        # s
    dt_stage2: float = 1.0         # s
    dt_coast: float = 1.0          # s
    dt_entry: float = 0.1          # s
    dt_descent: float = 0.2        # s
    dt_landing: float = 0.05       # s
    insertion_xtol: float = 1e-11  # scipy.optimize.root (hybr) relative tolerance
    fixed_point_tol_R: float = 1.0      # kg  (prompt: |dR| < 1 kg)
    fixed_point_tol_L: float = 0.1      # kg
    fixed_point_max_iter: int = 40
    landing_stop_speed: float = 0.05    # m/s; burn integration stops here, root puts it at h = 0
    landing_ignition_tol: float = 1e-3  # m on the final altitude
    landing_u_scan: int = 11            # points in the fuel-vs-throttle verification scan
    entry_q_tol: float = 1.0            # Pa on the post-burn peak dynamic pressure
    kick_time_bounds: tuple = (2.0, 40.0)     # s after liftoff
    kick_angle_bounds: tuple = (0.05, 12.0)   # deg from vertical
    kick_opt_rhobeg: float = 0.15             # COBYLA initial step (scaled variables)
    kick_opt_tol: float = 1e-4                # COBYLA final trust radius (scaled variables)
    kick_opt_maxfun: int = 80

    def dt(self, name: str) -> float:
        return getattr(self, 'dt_' + name) * self.step_scale

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Earth:
    """Spherical rotating Earth. ``omega_eff`` = omega_E*cos(i) is the in-plane rotation rate.

    For a due-east launch from latitude 28.562 deg the orbit inclination equals the latitude;
    the 0.062 deg difference to the 28.5 deg target is neglected (stated assumption)."""
    mu: float
    r_e: float
    omega: float
    omega_eff: float
    g0: float
    gravity: str = 'inverse_square'   # 'constant' only in verification tests
    atmosphere: bool = True           # False only in verification tests


def make_earth(P: ParameterSet, **overrides) -> Earth:
    em = P.v('mission.earth_model', 'SI')
    lat = math.radians(P.v('mission.launch_site_latitude_deg', 'deg'))
    e = Earth(mu=em['mu'], r_e=em['R_E'], omega=em['omega_E'], omega_eff=em['omega_E'] * math.cos(lat),
              g0=em['g0'])
    return replace(e, **overrides) if overrides else e


@dataclass(frozen=True)
class Vehicle:
    """Everything the trajectory code needs for one engine count N and one mode."""
    n_engines: int
    mode: str                     # 'reusable' or 'expendable'
    engine: Engine
    dry: DryMass
    m_dry1: float                 # booster dry mass used in this mode [kg]
    p1: float                     # booster propellant loaded [kg]
    u_min: float                  # minimum MASS-FLOW fraction (converted from SL thrust fraction)
    u_min_sl_fraction: float      # official-style minimum throttle (SL thrust fraction)
    u_max: float
    area: float                   # reference area [m^2]
    cd_mach: tuple
    cd_vals: tuple                # ascent Cd table already multiplied by the Cd scale
    cd_desc: float
    t2: float                     # upper-stage vacuum thrust [N]
    mdot2: float                  # upper-stage rated mass flow [kg/s]
    m_d2: float
    p2: float
    u2_min: float
    m_bay: float
    m_fair: float
    q_fair: float
    q_max: float                  # Pa
    a_max_asc: float              # m/s^2 (non-gravitational, axial)
    a_max_land: float             # m/s^2 (non-gravitational, thrust+drag over mass)
    h_eb: float                   # m
    q_entry_max: float | None     # Pa (calibrated)
    v_td: float                   # m/s
    eps_m: float
    m_res: float
    k_land: tuple
    k_entry_ref: int
    n_ref: int
    r_orbit: float
    v_circ: float
    h_pad: float

    @property
    def upper_wet(self) -> float:
        """Upper stage + full payload bay, excluding payload [kg]."""
        return self.m_d2 + self.p2 + self.m_bay

    def glow(self, payload: float) -> float:
        return self.m_dry1 + self.p1 + self.upper_wet + payload


def make_vehicle(P: ParameterSet, n_engines: int, mode: str = 'reusable', mass_model: str | None = None) -> Vehicle:
    if mode not in ('reusable', 'expendable'):
        raise ValueError(mode)
    eng = make_engine(P, n_engines)
    dry = booster_dry_mass(P, n_engines, mass_model)
    g0 = P.v('mission.earth_model', 'SI')['g0']
    r_vs = P.v('engine.vac_to_sl_thrust_ratio', '-')
    f_min = P.v('engine.min_throttle_sl_thrust_fraction', '-')
    cd_tab = P.v('booster.ascent_drag_coefficient_table', '-')
    k_cd = P.v('booster.ascent_cd_scale', '-')
    d = P.v('booster.diameter', 'm')
    em = P.v('mission.earth_model', 'SI')
    r_orb = em['R_E'] + P.v('mission.target_orbit_altitude', 'm')
    q_entry = P.get('recovery.entry_severity_limit_peak_q').value
    return Vehicle(
        n_engines=n_engines, mode=mode, engine=eng, dry=dry,
        m_dry1=dry.total if mode == 'reusable' else dry.expendable_total,
        p1=stage1_propellant_capacity(P),
        u_min=massflow_fraction_from_sl_thrust_fraction(f_min, r_vs), u_min_sl_fraction=f_min,
        u_max=P.v('engine.max_throttle', '-'),
        area=math.pi * d * d / 4.0,
        cd_mach=tuple(cd_tab['mach']), cd_vals=tuple(k_cd * c for c in cd_tab['cd']),
        cd_desc=P.v('booster.descent_drag_coefficient', '-'),
        t2=P.v('upper_stage.vac_thrust', 'N'),
        mdot2=P.v('upper_stage.vac_thrust', 'N') / (g0 * P.v('upper_stage.isp_vac', 's')),
        m_d2=P.v('upper_stage.dry_mass', 'kg'), p2=P.v('upper_stage.propellant', 'kg'),
        u2_min=P.v('upper_stage.min_throttle', '-'),
        m_bay=P.v('upper_stage.payload_bay_overhead', 'kg'),
        m_fair=P.v('upper_stage.fairing_jettison_mass', 'kg'),
        q_fair=P.v('upper_stage.fairing_jettison_dynamic_pressure', 'Pa'),
        q_max=P.v('mission.max_dynamic_pressure', 'Pa'),
        a_max_asc=P.v('mission.ascent_axial_accel_cap_g', 'g0') * g0,
        a_max_land=P.v('recovery.landing_max_accel_g', 'g0 (non-gravitational, thrust+drag over mass)') * g0,
        h_eb=P.v('recovery.entry_burn_start_altitude', 'm'),
        q_entry_max=q_entry,
        v_td=P.v('recovery.touchdown_speed_max', 'm/s'),
        eps_m=P.v('recovery.landing_propellant_margin', '-'),
        m_res=P.v('recovery.residual_propellant', 'kg'),
        k_land=tuple(P.v('engine.landing_burn_engines_allowed', 'count')),
        k_entry_ref=P.v('engine.entry_burn_engines', 'count'),
        n_ref=P.v('engine.reference_engine_count', '-'),
        r_orbit=r_orb, v_circ=math.sqrt(em['mu'] / r_orb),
        h_pad=P.v('mission.launch_pad_altitude', 'm'),
    )


def cd_interp(mach: float, xs: tuple, ys: tuple) -> float:
    """Piecewise-linear Cd(M), clamped outside the table."""
    if mach <= xs[0]:
        return ys[0]
    n = len(xs)
    for i in range(1, n):
        if mach <= xs[i]:
            x0, x1 = xs[i - 1], xs[i]
            return ys[i - 1] + (ys[i] - ys[i - 1]) * (mach - x0) / (x1 - x0)
    return ys[-1]
