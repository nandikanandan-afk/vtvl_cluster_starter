| name | value | units | source | source_type | confidence | overridden |
|---|---|---|---|---|---|---|
| engine.total_sl_thrust | 7,605,000.0 | N | S1 section 2.3 text (845 kN x 9) | official | high | False |
| engine.reference_engine_count | 9 | - | S1 | official | high | False |
| engine.vac_to_sl_thrust_ratio | 1.1 | - | S5 Table A1 (8,227 / 7,607 kN) | peer_reviewed | medium | False |
| engine.isp_sl | 283.0 | s | S5 Table A1 | peer_reviewed | medium | False |
| engine.isp_vac | 312.0 | s | S5 Table A1 | peer_reviewed | medium | False |
| engine.min_throttle_sl_thrust_fraction | 0.6 | - | S1/S2 Table 2-1 (108,300 of 190,000 lbf) | official | high | False |
| engine.max_throttle | 1.0 | - | assumption | assumption | medium | False |
| engine.engine_restart | True | - | S1 Table 2-1 | official | high | False |
| engine.reference_engine_dry_mass | 470.0 | kg | S13 (no SpaceX primary source found) | unofficial | low | False |
| engine.engine_mass_model | fixed_plus_powerlaw | - | assumption | assumption | medium | False |
| engine.fixed_mass_fraction | 0.1 | - | derived from S7 (Akin MER fixed term 59 kg, scaled by 0.56 s | derived | low | False |
| engine.mass_scaling_exponent | 0.9 | - | assumption (research report recommends sweeping 0.8-1.0) | assumption | low | False |
| engine.akin_mer_coefficients | {"a_thrust_kg_per_N": 0.000781, "b_expansion_kg_per_N": 3.37e-05, "c_fixed_kg": 59.0, "calibration_scale_to_merlin": 0.56} | kg, N | S7 slide 25: m = 7.81e-4*T + 3.37e-5*T*sqrt(Ae/At) + 59 | academic | medium | False |
| engine.nozzle_expansion_ratio | 16.0 | - | S19 Wevolver (unofficial) | unofficial | low | False |
| engine.thrust_structure_coefficient | 0.0 | kg/N | S7 slide 25 | academic | medium | False |
| engine.per_engine_integration_mass | 25.0 | kg | assumption (no published relationship ties thrust-structure  | assumption | low | False |
| engine.entry_burn_engines | 3 | count | S9, S11 | academic | medium | False |
| engine.landing_burn_engines_allowed | [1, 3] | count | S11, S9 (1 engine usual; 3-engine landing burns have been fl | secondary | medium | False |
| booster.glow_full_vehicle | 549,054.0 | kg | S3 | official | high | False |
| booster.dry_mass_at_reference | 26,000.0 | kg | between S5 (27.2 t) and S19 (25.6 t); community 22-27 t | unofficial | low | False |
| booster.recovery_hardware_fraction | 0.1 | - | S5 uses +15% of dry mass; S6 scales legs/fins linearly with  | peer_reviewed | low | False |
| booster.propellant_capacity | 404,654.0 | kg | derived: 549,054 (S3) - 26,000 booster dry - 4,500 upper dry | derived | low | False |
| booster.diameter | 3.7 | m | S1 Table 2-1, S3 | official | high | False |
| booster.descent_drag_coefficient | 1.0 | - | assumption (no published numeric value in the sources review | assumption | low | False |
| booster.ascent_drag_coefficient_table | {"mach": [0.0, 0.8, 1.1, 1.5, 3.0, 5.0, 10.0], "cd": [0.3, 0.3, 0.55, 0.45, 0.3, 0.25, 0.25]} | - | assumption (generic slender launcher shape) | assumption | low | False |
| upper_stage.vac_thrust | 981,000.0 | N | S1 Table 2-1, S3 | official | high | False |
| upper_stage.isp_vac | 348.0 | s | S5 Table A1 | peer_reviewed | medium | False |
| upper_stage.burn_time | 397.0 | s | S3 | official | high | False |
| upper_stage.dry_mass | 4,500.0 | kg | S5 Table A1 | peer_reviewed | medium | False |
| upper_stage.propellant | 111,500.0 | kg | S5 Table A1 | peer_reviewed | medium | False |
| upper_stage.min_throttle | 0.6 | - | S1 Table 2-1 (140,679 of 220,500 lbf) | official | high | False |
| upper_stage.payload_bay_overhead | 2,400.0 | kg | derived from S5 (7.4 t payload bay for 5.0 t payload) | derived | low | False |
| mission.target_orbit_altitude | 200,000.0 | m | research team choice; matches S5 LEO case and the secondary- | assumption | medium | False |
| mission.target_inclination_deg | 28.5 | deg | S1 Table 3-1 (Eastern Range minimum without penalty) | official | high | False |
| mission.launch_site_latitude_deg | 28.6 | deg | S2 section 6.1.1 (SLC-40) | official | high | False |
| mission.max_dynamic_pressure | 35,000.0 | Pa | unofficial proxy (SpaceX does not publish max-Q) | unofficial | low | False |
| mission.ascent_axial_accel_cap_g | 4.0 | g0 | assumption bounded by S14 telemetry (3.43 g peak) and S2 lim | assumption | low | False |
| mission.earth_model | {"mu": 398600441800000.0, "R_E": 6378137.0, "omega_E": 7.2921159e-05, "g0": 9.80665} | SI | standard constants | official | high | False |
| mission.atmosphere_model | US Standard Atmosphere 1976 (0-86 km), exponential above | - | NOAA/NASA/USAF 1976 | official | high | False |
| recovery.recovery_mode | downrange drone ship, no boostback | - | research question | assumption | high | False |
| recovery.entry_burn_start_altitude | 70,000.0 | m | S9 (entry burn 70 to 36 km), S6 (F9 about 50 km) | academic | medium | False |
| recovery.entry_severity_limit_peak_q | 70,231.8 | Pa | CALIBRATED at N = 9 (see prompt); DLR model bound q < 200 kP | derived | low | True |
| recovery.landing_max_accel_g | 3.0 | g0 (non-gravitational, thrust+drag over mass) | S17 (DLR: landing T/W above 3 treated as infeasible) | conference | medium | False |
| recovery.touchdown_speed_max | 2.0 | m/s | assumption (not published) | assumption | low | False |
| recovery.landing_propellant_margin | 0.1 | - | assumption (S5 uses 5% margin inside its landing delta-v) | assumption | low | False |
| recovery.residual_propellant | 1,500.0 | kg | assumption | assumption | low | False |
| validation_targets.expendable_leo_payload | 22,800.0 | kg | S3 | official | high | False |
| validation_targets.reusable_drone_ship_leo_payload | 17,400.0 | kg | S16 (demonstrated, more than 17.4 t, Starlink 5-2) | official | high | False |
| validation_targets.landing_propellant_estimate | 25,000.0 | kg | S5 Table A1 (unofficial, GTO 5 t mission) | peer_reviewed | low | False |
| validation_targets.landing_tw_at_min_throttle_N9 | [1.6, 1.8] | - | derived from S1 (482 kN) and 27-30 t landing mass | derived | medium | False |
| upper_stage.fairing_jettison_mass | 1,900.0 | kg | parameters_baseline.json upper_stage.payload_bay_overhead.us | assumption | low | False |
| upper_stage.fairing_jettison_dynamic_pressure | 10.0 | Pa | parameters_baseline.json upper_stage.payload_bay_overhead.us | assumption | low | False |
| booster.ascent_cd_scale | 0.8 | - | parameters_baseline.json booster.ascent_drag_coefficient_tab | assumption | low | True |
| recovery.entry_q_window | after_burn | - | prompt section 6.4.2 ('peak dynamic pressure afterward'); pa | assumption | medium | True |
| recovery.landing_accel_cap_basis | thrust_only | - | parameters_baseline.json recovery.landing_max_accel_g.units  | assumption | medium | True |
| mission.launch_pad_altitude | 0.0 | m | assumption (pad at sea level; SLC-40 pad elevation is not in | assumption | medium | False |
