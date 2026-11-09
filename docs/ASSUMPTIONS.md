# Modeling assumptions and decisions (v0.2)

Categories used throughout: **published data** (in `data/parameters_baseline.json`, with a
source code S1–S20), **assumption** (a choice by us or the team, listed here, swept where
it's uncertain), **calculation** (derived in code from the above), **simulation result**,
and **interpretation**. Assumptions that carry a number live in `data/parameters_supplement.json`
when the database states them only in prose.

Status tags: **[fixed]** a modeling idealization, not swept · **[swept]** varied in Experiment D ·
**[DECISION]** an uncertain choice. These have options and a recommendation, and need team confirmation.

## Vehicle and engines

| ID | Assumption | Status |
|---|---|---|
| A-ODD | Primary sweep uses odd N = 1, 3, …, 27: a centre engine plus a symmetric ring, so 1- and 3-engine burns (centre, or centre plus an opposed pair) are geometrically consistent. Even N would need different landing-engine rules and isn't studied. | fixed |
| A-CYCLE | Every N uses the same cycle, chamber pressure and expansion ratio. Isp_vac and r_vs are identical for all N; only engine size scales with 1/N. | fixed |
| A-ISP | The JSON Isp set is ~2 % inconsistent (312/283 = 1.1025 ≠ r_vs = 1.082). Baseline keeps r_vs (sets A_e) and Isp_vac (sets ṁ), as the JSON `used_for` fields specify. Derived Isp_sl = 288.35 s. | fixed (alternative noted in AUDIT §3.2) |
| A-THRUST | T = u·T_vac − p·A_e with u the mass-flow fraction (fixed-geometry nozzle, exit pressure proportional to chamber pressure). Flow separation at deep throttle isn't modeled. | fixed |
| A-UMIN | Official 57 % (SL thrust fraction) ⇒ u_min = 0.6026 mass-flow fraction. The same conversion is applied to every swept value (0.40–0.70 ⇒ 0.4455–0.7227). | swept |
| A-MASS | m_e(N) = m_ref[φ + (1−φ)(9/N)^β]. The Akin MER scaled to 470 kg at 845 kN is a sensitivity case; it's mathematically the β = 1, φ = 0.0708 member of the same family. | swept |
| A-NONENG | m_nonengine = m_d_ref − 9(m_ref + m_int) is fixed for all N. It contains tanks, structure, the thrust structure (∝ total thrust, constant) and recovery hardware. | fixed |
| A-GLOW | 549,054 kg excludes payload (JSON). Booster tanks are identical and full for every N: P1 = M0 − m_d_ref − m_d2 − P2 − m_bay, re-closed whenever m_d_ref is swept. GLOW(N) = M0 + (m_d(N) − m_d_ref) + payload. There's no GLOW cap; liftoff T/W is reported. | fixed |
| A-PACK | Total nozzle exit area N·A_e is N-invariant (= 58.5 % of the 3.66 m base area at every N). Nozzle packing, gimbal clearance and the octaweb are **not modeled**. | fixed (limitation) |
| A-ENGOUT | No engine-out cases. | fixed (future work) |

## Ascent and orbit

| ID | Assumption | Status |
|---|---|---|
| A-PLANAR | 2-D planar point mass, spherical Earth, inverse-square gravity, due-east launch from 28.562° N. In-plane atmosphere rotation ω_E·cos(28.562°). The resulting inclination (28.562°) differs from the 28.5° target by 0.062°; neglected. | fixed |
| A-ATM | US Standard Atmosphere 1976 to 86 km, isothermal exponential above, no winds. | fixed |
| A-ASCENT-CTRL | Stage 1: vertical rise to t_kick, thrust held at δ from vertical until v_rel has turned to δ, then a zero-AoA gravity turn. (t_kick, δ) are **optimized separately for every case** (COBYLA) to maximize payload subject to q_peak ≤ q_max. All N engines are lit. | fixed |
| A-ACCEL | Axial (T − D)/m ≤ a_max_asc in both stages, by throttling (stage 1 u ≥ u_min; stage 2 u2 ≥ 0.64). Identical logic for every N. | fixed |
| A-MAXQ | Max-Q is enforced **by steering only (no throttle bucket)**, because a bucket isn't needed for feasibility at q_max = 35 kPa. Consequence: this control family can't lower q_peak much below 35 kPa except by strong lofting, so payload is steep in q_max. Same for every N. | **[DECISION D3]** |
| A-STAGING | Stage separation is instantaneous: no coast, no ullage, no separation mass. Optimistic. | fixed (limitation) |
| A-STAGE2 | Linear-tangent pitch tan ψ = a − c·τ/τ_ref above local horizontal. Burn to depletion of P2 (no flight-performance reserve). MVac thrust at its vacuum value. Burn time is an output (~388 s vs 397 s published: the 2 % data inconsistency). | fixed |
| A-FAIRING | 1,900 kg of the 2,400 kg payload-bay mass is jettisoned at the first downward crossing of q = 10 Pa; 500 kg goes to orbit (JSON prose). | fixed |
| A-PAYLOAD | Payload = the mass L for which the linear-tangent family exactly reaches r = R_E + 200 km, v_r = 0, v_t = √(μ/r) at depletion: (a, c, L) solved together. | fixed |

## Recovery

| ID | Assumption | Status |
|---|---|---|
| A-REC-MODE | Downrange drone ship at the impact point, no boostback. The engines-first attitude is assumed immediately after separation; the flip isn't modeled. Descent Cd = Cd_desc is constant (no Mach dependence) on the 3.66 m base area. | Cd_desc swept |
| A-ENTRY-START | The entry burn starts at h_eb = 70 km on the descending leg, or at apogee if apogee < h_eb. | fixed |
| A-ENTRY | **Entry-burn engine rule (all N, including N = 9).** Target thrust T* = (3/9)·N·(T_vac,e − p·A_e) (Falcon 9 practice: 3 of 9 engines). Each allowed k ∈ {1, 3} (k ≤ N) delivers [k·T(u_min), k·T(1)]. The delivered thrust is the point of these sets closest to T* that does not exceed T_cap = a_cap·m − D (the axial load, thrust + drag over mass). It's re-evaluated continuously, and engine-count changes are located exactly as integration events. Thrust is anti-parallel to v_rel. | **[DECISION D2]** for a_cap |
| A-ENTRY-CAP | a_cap for the entry burn = the ascent axial cap a_max_asc (4 g), the vehicle's steady-state axial limit. Alternatives: (i) a_max_land = 3 g, which makes 3-engine entry burns impossible even at N = 9; (ii) no cap. | **[DECISION D2]** |
| A-QENTRY | The entry burn is sized so the peak dynamic pressure of the following ballistic descent equals q_entry_max (zero burn if already below). The peak is taken over the descent integrated to the ground, which is conservative; it equals the peak before landing ignition whenever the q maximum lies above the ignition altitude (checked per case: `h_qpeak_descent_km`). q_entry_max is calibration knob 2. | calibrated, swept ±30 % |
| A-LAND-CTRL | Landing: one burn, k ∈ {1, 3} (k ≤ N), constant u ∈ [u_min, 1], thrust anti-parallel to v_rel. Ignition altitude solved so the vertical velocity reaches −1.0 m/s exactly at h = 0. The 1.0 m/s "touchdown speed" is a numerical stop speed above the RK4 chatter level and ≤ v_td = 2 m/s. The fuel-optimal (k, u) is chosen. Optimality in u is verified by an 11-point scan for every reported case. | fixed |
| A-CAP | **Landing acceleration cap basis.** The database defines a_max_land as non-gravitational **(thrust + drag)/m** (baseline). With constant Cd_desc the booster reaches landing altitudes well above terminal velocity, so drag at ignition is large and the peak is at *ignition*, not near touchdown as the JSON note expected. The alternative reads the DLR threshold (S17, "landing T/W above 3") as **thrust-only T/m**. Switch: `recovery.landing_accel_cap_basis`. | **[DECISION D1]** |
| A-RESERVE | R = (1 + ε_m)(m_entry + m_landing) + m_res. The margin and residual stay on board through all recovery dynamics, so touchdown mass = m_dry + ε_m(m_e + m_l) + m_res. Solved as a fixed point R = Rec(MECO(R)) (safeguarded secant, \|ΔR\| < 1 kg, iteration counts logged). | fixed |

## Status labels (per case)

* `feasible`: all constraints met; insertion and touchdown re-verified by an independent integrator.
* `infeasible_proven`: analytic reason recorded. (a) k·T(u_min, SL)/m_ign > a_max_land: at touchdown v → 0 so D → 0, and T/m_td > T_min/m_ign. (b) k·T(1, SL)/((m_dry + m_res)g0) ≤ 1: velocity can't be nulled. (c) (thrust + drag basis) (k·T(u_min, p) + D)/m > cap at every point of the computed descent, so no ignition point or throttle history works. (d) The entry rule cannot continue the burn because drag + one engine at u_min exceeds the cap, and the longest admissible burn (q_peak decreasing in burn time) still leaves q_peak > q_entry_max. Screens (a), (c) and (d) use the reserve of the iterate at which they fire, which is stated in the reason.
* `no_solution_found`: a solver or search failed (diagnostics in `reason`). This includes "constant-throttle family found no admissible u". It is **not** proof of physical infeasibility.

## Calibration (prompt §6.5)

At most two knobs, each inside its JSON range, calibrated at N = 9 and then frozen. Knob 1: ascent Cd scale in [0.8, 1.2] against 22,800 kg (1 %). Knob 2: q_entry_max ≤ 200 kPa (DLR bound) against 17.5 t (band 17.4–18.5 t). If an anchor can't be reached, the closest in-range value is frozen and the mismatch is reported (`results/*_calibration_N9/calibration.json`).

## Open decisions for the team (see the pause report)

* **D1** Landing-cap basis (A-CAP).
* **D2** Entry-burn acceleration cap (A-ENTRY-CAP).
* **D3** Max-Q by steering only vs an identical-for-all-N throttle bucket (A-MAXQ).
* **D4** What to do about the expendable-anchor mismatch (calibration.json, step A).
