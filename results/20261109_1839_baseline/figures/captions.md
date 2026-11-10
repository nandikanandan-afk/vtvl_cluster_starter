# Figure captions

- **fig1_dry_mass_vs_N**: Booster dry mass vs engine count, split into non-engine mass (fixed), engine mass and per-engine integration mass (baseline φ=0.07, β=0.90, m_int=25 kg; calculation from the parameter database).
- **fig2_recovery_propellant_vs_N**: Recovery reserve at MECO vs engine count (simulation result): entry-burn and landing-burn propellant plus the carried margin and residual. Letters mark N with no feasible recovery.
- **fig3_payload_vs_N**: PRIMARY RESULT. Maximum payload to a 200 km, 28.5° circular orbit vs engine count, re-optimised for every N (simulation result). Shaded: within 1 % of the best; letters: P infeasible (proven), N no solution found.
- **fig6_recovery_trajectories**: Example recovery trajectories from MECO to touchdown (simulation result): coast, entry burn, aerodynamic descent, landing burn. Propellant is shown relative to the on-board margin + residual at touchdown.
- **fig4_feasibility_umin_vs_N**: Recovery/ascent feasibility vs minimum throttle and engine count at the tested N (baseline β, φ; simulation result). P cells carry an analytic reason in cases.csv; N cells are solver/search failures, not proofs.
- **fig5a_best_N_sensitivity**: Best engine count under one-at-a-time sensitivity (simulation result); hollow markers show every tested N within 1 % of the best payload.
- **fig5b_best_N_maps**: Best engine count over (minimum throttle × β) and (minimum throttle × φ); "–" = no feasible N (simulation result).
