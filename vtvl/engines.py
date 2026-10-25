"""Fixed-total-thrust, homologous-engine mass model."""
from .config import Design, Vehicle


def engine_mass_kg(design: Design, vehicle: Vehicle) -> float:
    thrust_ratio = vehicle.reference_engine_count / design.engine_count
    phi = design.fixed_engine_mass_fraction
    return vehicle.reference_engine_mass_kg * (
        phi + (1.0 - phi) * thrust_ratio ** vehicle.engine_mass_exponent
    )


def booster_dry_mass_kg(design: Design, vehicle: Vehicle) -> float:
    return vehicle.nonengine_booster_dry_kg + design.engine_count * (
        engine_mass_kg(design, vehicle) + vehicle.integration_mass_per_engine_kg
    )
