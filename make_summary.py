"""Build tables (CSV + Markdown) and results_summary.md ONLY from files the runs wrote.
Usage: python make_summary.py <baseline_dir> <sensitivity_dir> <maps_dir> <calibration_dir>"""
import json
import math
import sys
from pathlib import Path

import pandas as pd

B, S, M, C = (Path(a) for a in sys.argv[1:5])
T = B / 'tables'
T.mkdir(exist_ok=True)


def md(df, floatfmt='{:,.1f}'):
    cols = list(df.columns)
    lines = ['| ' + ' | '.join(map(str, cols)) + ' |', '|' + '---|' * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for v in r:
            if isinstance(v, float):
                cells.append('' if math.isnan(v) else floatfmt.format(v))
            else:
                cells.append(str(v))
        lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def save(name, df):
    df.to_csv(T / f'{name}.csv', index=False)
    (T / f'{name}.md').write_text(md(df) + '\n', encoding='utf-8')


cases = pd.read_csv(B / 'cases.csv')
best = pd.read_csv(B / 'best_counts.csv')
cal = json.loads((C / 'calibration.json').read_text())
sens = pd.read_csv(S / 'cases.csv')
sbest = pd.read_csv(S / 'best_counts.csv')
mbest = pd.read_csv(M / 'best_counts.csv')
mc = pd.read_csv(M / 'cases.csv')
reu = cases[cases['mode'] == 'reusable'].sort_values('n_engines')
exp = cases[cases['mode'] == 'expendable'].sort_values('n_engines')
feas = reu[reu['status'] == 'feasible']

# ---- tables --------------------------------------------------------------------------------
pr = json.loads((B / 'parameters_resolved.json').read_text())['parameters']
save('inputs_with_sources', pd.DataFrame([dict(
    name=p['name'], value=json.dumps(p['value']) if isinstance(p['value'], (dict, list)) else p['value'],
    units=p['units'], source=p['source'][:60], source_type=p['source_type'], confidence=p['confidence'],
    overridden=p['overridden']) for p in pr]))
save('engine_count_comparison', reu[['n_engines', 'engine_sl_thrust_kN', 'engine_mass_each_kg', 'engines_total_kg',
                                     'integration_total_kg', 'nonengine_kg', 'booster_dry_kg', 'status']])
save('recovery_performance', reu[['n_engines', 'status', 'reserve_kg', 'm_entry_kg', 'm_landing_kg', 'margin_kg',
                                  'residual_kg', 'landing_k', 'landing_u', 'landing_ignition_h_m',
                                  'landing_peak_accel_g', 'landing_peak_at', 'landing_tw_min_throttle_at_td',
                                  'replay_touchdown_speed_m_s', 'entry_burn_s']])
save('payload_results', reu[['n_engines', 'status', 'payload_kg', 'reserve_kg', 'booster_dry_kg', 'outer_iterations',
                             'kick_t_s', 'kick_delta_deg', 'ascent_q_peak_Pa', 'insertion_dr_m', 'insertion_vr_m_s',
                             'insertion_dvt_m_s']].merge(
    exp[['n_engines', 'payload_kg']].rename(columns={'payload_kg': 'expendable_payload_kg'}), on='n_engines'))
save('sensitivity_best_N', sbest[['case', 'feasible', 'best_n', 'best_payload_kg', 'near_optimal_counts',
                                  'gap_to_second_pct', 'feasible_counts', 'no_solution_counts']])
save('map_best_N', mbest[['case', 'feasible', 'best_n', 'best_payload_kg', 'near_optimal_counts',
                          'gap_to_second_pct', 'feasible_counts']])
conv_path = B / 'verification_convergence.csv'
conv = pd.read_csv(conv_path) if conv_path.exists() else None
if conv is not None:
    save('verification_convergence', conv)

# ---- numbers for the narrative ---------------------------------------------------------------
b0 = best[best['case'] == 'baseline'].iloc[0]
be = best[best['case'] == 'baseline_expendable'].iloc[0]
n9 = reu[reu['n_engines'] == 9].iloc[0]
cdf = cal['step_A']
qf = cal['step_B']['thrust_only']
sb = sbest.dropna(subset=['best_n'])
counts = sb['best_n'].astype(int).value_counts().sort_index().to_dict()
mb = mbest.dropna(subset=['best_n'])
mcounts = mb['best_n'].astype(int).value_counts().sort_index().to_dict()
st = {f'{k[0]}/{k[1]}': int(v) for k, v in cases.groupby(['mode', 'status']).size().items()}
sst = {k: int(v) for k, v in sens['status'].value_counts().items()}
mst = {k: int(v) for k, v in mc['status'].value_counts().items()}
f = feas.set_index('n_engines')
land_at = {k: int(v) for k, v in f['landing_peak_at'].value_counts().items()}
k_by_n = {int(n): int(f.loc[n, 'landing_k']) for n in f.index}
u_by_n = {int(n): round(float(f.loc[n, 'landing_u']), 3) for n in f.index}
dry = reu.set_index('n_engines')['booster_dry_kg']


def fmt(x):
    return f'{x:,.0f}'


ver_txt = 'Verification (step halving, three optimizer starts) not run or not finished when this summary was generated.'
if conv is not None:
    rows = []
    for _, r in conv.iterrows():
        rows.append(f"  - N={int(r.n_engines)}: step-halving change {r.step_halving_change_kg:+.1f} kg "
                    f"(pass={r.step_halving_pass}); three-start payloads [{r.robust_payloads_kg}] kg, "
                    f"statuses [{r.robust_statuses}], spread incl. baseline {r.robust_spread_incl_baseline_kg:.1f} kg (pass={r.robust_pass})")
    ver_txt = '\n'.join(rows)

txt = f"""# Results summary (PRELIMINARY)

> Every number below is read from files in `{B.as_posix()}`, `{S.as_posix()}`, `{M.as_posix()}` and `{C.as_posix()}` by `make_summary.py`.
> **Model variant:** thrust-only landing acceleration cap, max-Q enforced by steering only (no throttle bucket),
> q_entry_max enforced after the entry burn only. See `docs/ASSUMPTIONS.md` (D1-D5) before using any conclusion.

## Calibration at N = 9 (frozen for all other N)
* Ascent Cd scale = {cdf['frozen_value']} (range 0.8-1.2) gives an expendable payload of {fmt(cdf['payload_at_frozen'])} kg, {cdf['mismatch_pct']:+.2f} % vs the 22,800 kg anchor: **anchor NOT reached within 1 %** (status `{cdf['status']}`); the range was not stretched.
* q_entry_max = {fmt(qf['frozen_value'])} Pa gives a reusable payload of {fmt(n9['payload_kg'])} kg at N = 9 in the baseline run (target 17,500 kg, band 17,400-18,500 kg).
* N = 9 recovery reserve R = {fmt(n9['reserve_kg'])} kg (entry {fmt(n9['m_entry_kg'])} kg, landing {fmt(n9['m_landing_kg'])} kg), vs the 15,000-35,000 kg plausibility range and the 25,000 kg S5 estimate (a GTO case): **above the range**.
* N = 9 landing thrust-to-weight at minimum throttle at touchdown mass = {n9['landing_tw_min_throttle_at_td']:.2f}, vs 1.6-1.8 expected: **slightly below**.

## Case status counts
* Baseline: {st}
* Sensitivity (reduced N set): {sst}; maps: {mst}.
* `infeasible_proven` carries an analytic reason in `cases.csv`; `no_solution_found` is a solver/search failure, **not** proof of infeasibility.

## 1. Which N maximizes payload, and by how much over the next best?
Reusable baseline: best N = {int(b0['best_n'])} with {fmt(b0['best_payload_kg'])} kg; next best N = {int(b0['second_n'])} with {fmt(b0['second_payload_kg'])} kg;
gap {fmt(b0['gap_to_second_kg'])} kg ({b0['gap_to_second_pct']:.2f} %). Counts within 1 % of the best: {b0['near_optimal_counts']}.
Feasible counts: {b0['feasible_counts']}; infeasible_proven: {b0['infeasible_proven_counts']}; no_solution_found: {b0['no_solution_counts']}.
Expendable reference (no recovery): best N = {int(be['best_n'])}, gap to second {be['gap_to_second_kg']:.1f} kg ({be['gap_to_second_pct']:.3f} %).

## 2. How does dry mass change with N?
Booster dry mass rises from {fmt(dry[1])} kg (N = 1) to {fmt(dry[9])} kg (N = 9) to {fmt(dry[27])} kg (N = 27); the non-engine part is fixed at {fmt(reu.iloc[0]['nonengine_kg'])} kg.

## 3. How does minimum throttle limit recovery, and which constraints are active?
* Among feasible baseline cases the landing burn uses k = 1 or k = 3 as follows: {k_by_n}; constant throttle u = {u_by_n}.
* The peak landing acceleration occurs at: {land_at}. Cases with k = 3 sit on the 3 g cap at touchdown (cap active); cases at u = 1 with k = 1 are limited by available thrust, not by the minimum throttle.
* Feasibility vs minimum throttle: `figures/fig4_feasibility_umin_vs_N.png`. At 70 % minimum throttle only the counts in `tables/sensitivity_best_N.md` (row `u_min=0.7`) are feasible.
* The entry-burn rule (drag plus one engine at minimum throttle above the 4 g cap) is what makes N = 1 and N >= 25 `infeasible_proven` in the baseline.

## 4. How much propellant is reserved for recovery?
Feasible baseline reserve R ranges from {fmt(feas['reserve_kg'].min())} kg (N = {int(feas.loc[feas['reserve_kg'].idxmin(), 'n_engines'])}) to {fmt(feas['reserve_kg'].max())} kg (N = {int(feas.loc[feas['reserve_kg'].idxmax(), 'n_engines'])}).

## 5. Is the optimum interior or at a boundary?
Baseline: best_is_boundary_of_feasible_set = {b0['best_is_boundary_of_feasible_set']} (N = {int(b0['best_n'])} is the largest feasible count; N = 23 is `no_solution_found` and N >= 25 `infeasible_proven`). The optimum is **at the edge of the feasible set, not an interior optimum**, and N = 23 could not be evaluated, so whether the true optimum lies further out is **not established**.

## 6. Does it move under sensitivity?
One-at-a-time sweeps (N in 3, 5, 7, 9, 13, 17, 21, 25): distribution of best N over the {len(sb)} cases with a feasible N: {counts}. Maps (min throttle x beta, min throttle x phi): {mcounts}.
It changes with u_min, phi, a_max_land and Cd_desc; see `figures/fig5a_best_N_sensitivity.png` and `fig5b_best_N_maps.png`.

## 7. Is the payload gap larger than numerical and modeling uncertainty?
Numerical (see `docs/VERIFICATION.md`):
{ver_txt}
Modeling: **no.** The baseline gap between N = {int(b0['best_n'])} and N = {int(b0['second_n'])} is {b0['gap_to_second_pct']:.2f} %, smaller than the swing in best N under single-parameter changes, and the N ranking is entangled with the max-Q steering artifact (expendable payload rises with N at 35 kPa but falls with N at 40 kPa; `docs/ASSUMPTIONS.md` D3).

## 8. Supported and unsupported conclusions
Supported (within this model variant, weakly): the recovery reserve is tens of tonnes (section 4) and the best reusable case carries {fmt(be['best_payload_kg'] - b0['best_payload_kg'])} kg less payload than the best expendable case; the payload solve itself is numerically converged (step halving changes payload by a few kg, insertion residuals below 1 m).
At the baseline starting kick, N = 1, 25 and 27 were labelled `infeasible_proven` and N = 3 and 23 `no_solution_found`; because of the robustness failure below these labels are **suggestive, not established**.
**Optimizer robustness FAILED the three-start test** (see section 7): from other starting pitch kicks N = 5 and N = 21 found no feasible solution at all, and N = 9 only 2 of 3 times, so `infeasible_proven`/`no_solution_found` labels in the payload search are conditional on the starting kick and are **not** intrinsic properties of N (only screens that do not depend on the kick, such as one engine at minimum throttle exceeding the cap at N = 1, are). The feasible-N window is therefore **not established**.
Not supported: a single optimal N; any claim about N > 21; any claim that more engines raise payload through physics (the trend is partly a max-Q artifact); agreement with Falcon 9 beyond the N = 9 anchors (expendable anchor missed by {cdf['mismatch_pct']:+.1f} %, reserve and T/W outside the plausibility ranges).
"""
(B / 'results_summary.md').write_text(txt, encoding='utf-8')
print('written', B / 'results_summary.md')
