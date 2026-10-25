"""Two-stage ideal-delta-v PAYLOAD PROXY, not orbital trajectory propagation."""
import math
from scipy.optimize import brentq
from .config import G0, Mission, Vehicle


def mass_and_delta_v(payload_kg: float, booster_dry_kg: float,
                     recovery_reserve_kg: float, vehicle: Vehicle) -> dict:
    if payload_kg < 0 or booster_dry_kg <= 0 or recovery_reserve_kg < 0:
        raise ValueError('Invalid mass inputs')
    upper_wet = vehicle.upper_stage_dry_kg + vehicle.upper_stage_propellant_kg
    capacity = vehicle.liftoff_mass_cap_kg - booster_dry_kg - upper_wet - payload_kg
    prop1 = min(vehicle.first_stage_propellant_capacity_kg, capacity)
    liftoff = booster_dry_kg + prop1 + upper_wet + payload_kg
    meco = booster_dry_kg + recovery_reserve_kg + upper_wet + payload_kg
    if prop1 <= recovery_reserve_kg or liftoff <= meco:
        return dict(valid=False, delta_v_m_s=-math.inf)
    dv1 = G0 * vehicle.ascent_isp_s * math.log(liftoff / meco)
    dv2 = G0 * vehicle.upper_stage_isp_s * math.log(
        (upper_wet + payload_kg) / (vehicle.upper_stage_dry_kg + payload_kg)
    )
    return dict(valid=True, delta_v_m_s=dv1+dv2, stage1_delta_v_m_s=dv1,
                stage2_delta_v_m_s=dv2, first_stage_loaded_propellant_kg=prop1,
                first_stage_ascent_propellant_kg=prop1-recovery_reserve_kg,
                liftoff_mass_kg=liftoff, liftoff_twr=vehicle.total_sl_thrust_n/(G0*liftoff))


def solve_payload(booster_dry_kg: float, recovery_reserve_kg: float,
                  vehicle: Vehicle, mission: Mission) -> dict:
    def residual(payload):
        return mass_and_delta_v(payload, booster_dry_kg, recovery_reserve_kg, vehicle)['delta_v_m_s'] - mission.required_ideal_delta_v_m_s
    upper_wet = vehicle.upper_stage_dry_kg + vehicle.upper_stage_propellant_kg
    upper = vehicle.liftoff_mass_cap_kg - booster_dry_kg - upper_wet - recovery_reserve_kg - 1.0
    if upper <= 0 or residual(0.0) < 0:
        return dict(payload_feasible=False, payload_proxy_kg=math.nan, payload_status='NO_NONNEGATIVE_PAYLOAD')
    payload = brentq(residual, 0.0, upper, xtol=1e-6)
    details = mass_and_delta_v(payload, booster_dry_kg, recovery_reserve_kg, vehicle)
    if details['liftoff_twr'] < mission.min_liftoff_twr:
        return dict(payload_feasible=False, payload_proxy_kg=math.nan, payload_status='LIFTOFF_TWR_SCREEN_FAILED', **details)
    return dict(payload_feasible=True, payload_proxy_kg=payload, payload_status='IDEAL_DV_PROXY_CLOSED', **details)
