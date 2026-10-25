"""SI units throughout. Values are STUDY ASSUMPTIONS unless noted otherwise."""
from dataclasses import dataclass

G0 = 9.80665


@dataclass(frozen=True)
class Vehicle:
    # Public SpaceX scale anchors, not a calibrated reproduction of Falcon 9.
    total_sl_thrust_n: float = 7_607_000.0
    diameter_m: float = 3.7
    reference_engine_count: int = 9
    # Everything below is an assumed conceptual-vehicle parameter.
    liftoff_mass_cap_kg: float = 550_000.0
    first_stage_propellant_capacity_kg: float = 410_000.0
    nonengine_booster_dry_kg: float = 20_000.0
    reference_engine_mass_kg: float = 470.0
    engine_mass_exponent: float = 0.85
    integration_mass_per_engine_kg: float = 35.0
    ascent_isp_s: float = 300.0
    landing_isp_s: float = 282.0
    upper_stage_dry_kg: float = 4_500.0
    upper_stage_propellant_kg: float = 105_000.0
    upper_stage_isp_s: float = 348.0

    def __post_init__(self) -> None:
        for key, value in self.__dict__.items():
            if not isinstance(value, (int, float)) or value <= 0:
                # Zero integration mass is useful for a verification case.
                if key == 'integration_mass_per_engine_kg' and value == 0:
                    continue
                raise ValueError(f'{key} must be positive, got {value!r}')
        if not isinstance(self.reference_engine_count, int):
            raise ValueError('reference_engine_count must be an integer')


@dataclass(frozen=True)
class Mission:
    # Prescribed state AFTER earlier recovery maneuvers, not stage separation.
    terminal_entry_altitude_m: float = 2_000.0
    touchdown_velocity_m_s: float = -0.5  # Upward is positive.
    # Ideal-impulse requirement INCLUDING a fixed ascent-loss allowance.
    required_ideal_delta_v_m_s: float = 9_400.0
    # Consumed BEFORE the terminal-descent initial condition; not simulated.
    other_recovery_propellant_kg: float = 8_000.0
    landing_margin_fraction: float = 0.10
    trapped_residual_kg: float = 300.0
    max_landing_propellant_kg: float = 25_000.0
    min_landing_burn_s: float = 2.0
    max_landing_burn_s: float = 120.0
    max_landing_proper_accel_g: float = 5.0  # abs((thrust + drag)/(m*g0)); excludes gravity.
    max_terminal_dynamic_pressure_pa: float = 80_000.0
    min_liftoff_twr: float = 1.2
    allowed_landing_engine_counts: tuple[int, ...] = (1, 3)
    # Low-altitude illustrative atmosphere and base-first drag.
    sea_level_density_kg_m3: float = 1.225
    density_scale_height_m: float = 8_500.0
    landing_drag_coefficient: float = 0.8

    def __post_init__(self) -> None:
        if self.terminal_entry_altitude_m <= 0:
            raise ValueError('terminal_entry_altitude_m must be positive')
        if not -5.0 <= self.touchdown_velocity_m_s < 0:
            raise ValueError('Use a small negative touchdown velocity, e.g. -0.5')
        if not 0 <= self.landing_margin_fraction <= 1:
            raise ValueError('landing_margin_fraction must be in [0, 1]')
        if self.trapped_residual_kg < 0 or self.other_recovery_propellant_kg < 0:
            raise ValueError('Propellant allowances must be nonnegative')
        if not 0 < self.min_landing_burn_s < self.max_landing_burn_s:
            raise ValueError('Invalid burn-time bounds')
        if not self.allowed_landing_engine_counts or any(
            not isinstance(k, int) or k < 1 for k in self.allowed_landing_engine_counts
        ):
            raise ValueError('Landing engine counts must be positive integers')
        if self.landing_drag_coefficient < 0 or self.max_landing_propellant_kg <= 0:
            raise ValueError('Invalid drag or landing propellant cap')
        positive = (
            'required_ideal_delta_v_m_s', 'max_landing_proper_accel_g',
            'max_terminal_dynamic_pressure_pa', 'min_liftoff_twr',
            'sea_level_density_kg_m3', 'density_scale_height_m',
        )
        for key in positive:
            if getattr(self, key) <= 0:
                raise ValueError(f'{key} must be positive')


@dataclass(frozen=True)
class Design:
    engine_count: int = 9
    fixed_engine_mass_fraction: float = 0.25
    min_throttle: float = 0.40
    terminal_entry_speed_m_s: float = 200.0  # Positive downward-speed magnitude.

    def __post_init__(self) -> None:
        if not isinstance(self.engine_count, int) or self.engine_count < 1:
            raise ValueError('engine_count must be a positive integer')
        if not 0 <= self.fixed_engine_mass_fraction <= 1:
            raise ValueError('fixed_engine_mass_fraction must be in [0, 1]')
        if not 0 < self.min_throttle <= 1:
            raise ValueError('min_throttle must be in (0, 1]')
        if self.terminal_entry_speed_m_s <= 0:
            raise ValueError('terminal_entry_speed_m_s must be positive')


@dataclass(frozen=True)
class Numerics:
    physics: str = 'drag'  # 'drag' = numerical atmosphere; 'analytic' = no drag.
    multistarts: int = 4
    rtol: float = 2e-7
    atol: float = 1e-8
    max_step_s: float = 1.0
    max_iterations: int = 160
    optimizer_ftol: float = 1e-10
    path_samples: int = 25
    altitude_tolerance_m: float = 0.05
    velocity_tolerance_m_s: float = 0.02
    constraint_tolerance: float = 1e-5

    def __post_init__(self) -> None:
        if self.physics not in ('drag', 'analytic'):
            raise ValueError("physics must be 'drag' or 'analytic'")
        if self.multistarts < 1 or self.path_samples < 5:
            raise ValueError('Need at least one start and five path samples')
        for key in ('rtol', 'atol', 'max_step_s', 'optimizer_ftol'):
            if getattr(self, key) <= 0:
                raise ValueError(f'{key} must be positive')
