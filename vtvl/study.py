"""Couple dry mass -> landing fuel -> stage-separation reserve -> payload."""
from dataclasses import asdict
import math
from .config import Design, G0, Mission, Numerics, Vehicle
from .engines import booster_dry_mass_kg, engine_mass_kg
from .landing import solve_landing
from .performance import solve_payload


def evaluate_design(design: Design, vehicle: Vehicle | None = None,
                    mission: Mission | None = None, numerics: Numerics | None = None) -> dict:
    vehicle, mission, numerics = vehicle or Vehicle(), mission or Mission(), numerics or Numerics()
    dry = booster_dry_mass_kg(design, vehicle)
    landing = solve_landing(design, vehicle, mission, numerics)
    row = {
        **asdict(design), 'physics': numerics.physics,
        'engine_mass_exponent': vehicle.engine_mass_exponent,
        'single_engine_thrust_n': vehicle.total_sl_thrust_n / design.engine_count,
        'single_engine_dry_kg': engine_mass_kg(design, vehicle), 'booster_dry_kg': dry,
        **{'landing_' + key: value for key, value in asdict(landing).items()},
        'recovery_reserve_at_meco_kg': math.nan,
        'payload_proxy_kg': math.nan, 'payload_feasible': False,
    }
    if landing.feasible:
        reserve = mission.other_recovery_propellant_kg + landing.loaded_landing_propellant_kg
        row['recovery_reserve_at_meco_kg'] = reserve
        row['single_engine_min_thrust_weight_at_touchdown'] = (
            design.min_throttle * vehicle.total_sl_thrust_n / design.engine_count
            / ((dry + landing.touchdown_propellant_kg) * G0)
        )
        row.update(solve_payload(dry, reserve, vehicle, mission))
    return row
