"""Engine-count study: baseline (Experiments A-C) and sensitivity (Experiment D).

Calibrated values are read from a calibration run (never re-tuned here):
    python run_study.py --mode baseline    --calibration results/<ts>_calibration_N9 --basis thrust_only
    python run_study.py --mode sensitivity --calibration ... --basis ... --baseline results/<ts>_baseline
    python run_study.py --mode maps        --calibration ... --basis ... --baseline results/<ts>_baseline
Output: results/<timestamp>_<name>/ with cases.csv, best_counts.csv, manifest.json,
parameters_resolved.json, trajectories (baseline) and tables.
"""
import argparse
import csv
import json
import math
import time
from datetime import datetime
from pathlib import Path

from vtvl.params import load_parameters
from vtvl.study import run_parallel, write_csv, write_manifest

COUNTS = list(range(1, 28, 2))
NEAR_BAND = 0.01   # counts within 1 % of the best payload


def frozen_overrides(calib_dir: Path, basis: str) -> dict:
    cal = json.loads((calib_dir / 'calibration.json').read_text())
    q = cal['step_B'][basis]['frozen_value']
    if q is None:
        raise SystemExit(f'No frozen q_entry_max for basis {basis!r} in {calib_dir}')
    return {'booster.ascent_cd_scale': cal['step_A']['frozen_value'],
            'recovery.entry_severity_limit_peak_q': q,
            'recovery.landing_accel_cap_basis': basis}


def sensitivity_cases(base: dict) -> list[tuple[str, dict, dict]]:
    """(case name, overrides, numerics overrides). One-at-a-time over the JSON ranges."""
    q0 = base['recovery.entry_severity_limit_peak_q']
    oat = [('phi', 'engine.fixed_mass_fraction', [0.0, 0.2, 0.4]),
           ('beta', 'engine.mass_scaling_exponent', [0.8, 1.0]),
           ('u_min', 'engine.min_throttle_sl_thrust_fraction', [0.40, 0.50, 0.65, 0.70]),
           ('m_ref', 'engine.reference_engine_dry_mass', [430.0, 575.0]),
           ('m_int', 'engine.per_engine_integration_mass', [0.0, 50.0]),
           ('Cd_desc', 'booster.descent_drag_coefficient', [0.7, 1.4]),
           ('q_entry_max', 'recovery.entry_severity_limit_peak_q', [0.7 * q0, 1.3 * q0]),
           ('eps_m', 'recovery.landing_propellant_margin', [0.05, 0.15]),
           ('a_max_land', 'recovery.landing_max_accel_g', [2.0, 4.0, 5.0]),
           ('m_d_ref', 'booster.dry_mass_at_reference', [22000.0, 27200.0])]
    out = []
    for label, key, vals in oat:
        for v in vals:
            num = {}
            if key == 'recovery.landing_max_accel_g' and v > 4.0:
                num = {'dt_landing': 0.025}   # keep the stop speed above the RK4 chatter level
            out.append((f'{label}={v:g}', {**base, key: v}, num))
    out.append(('mass_model=akin_scaled', {**base, 'engine.engine_mass_model': 'akin_scaled'}, {}))
    return out


def map_cases(base: dict) -> list[tuple[str, dict, dict]]:
    out = []
    for u in (0.40, 0.50, 0.57, 0.65, 0.70):
        for b in (0.8, 0.9, 1.0):
            out.append((f'map_umin_beta:u_min={u:g},beta={b:g}',
                        {**base, 'engine.min_throttle_sl_thrust_fraction': u, 'engine.mass_scaling_exponent': b}, {}))
        for p in (0.0, 0.07, 0.2, 0.4):
            out.append((f'map_umin_phi:u_min={u:g},phi={p:g}',
                        {**base, 'engine.min_throttle_sl_thrust_fraction': u, 'engine.fixed_mass_fraction': p}, {}))
    return out


def best_counts(rows: list[dict]) -> list[dict]:
    groups = {}
    for r in rows:
        groups.setdefault((r['tag'], r['mode']), []).append(r)
    out = []
    for (tag, mode), rs in groups.items():
        feas = sorted([r for r in rs if r['status'] == 'feasible'], key=lambda r: -r['payload_kg'])
        e = dict(case=tag, mode=mode, evaluated=len(rs), feasible=len(feas),
                 feasible_counts=';'.join(str(r['n_engines']) for r in sorted(feas, key=lambda r: r['n_engines'])),
                 infeasible_proven_counts=';'.join(str(r['n_engines']) for r in rs if r['status'] == 'infeasible_proven'),
                 no_solution_counts=';'.join(str(r['n_engines']) for r in rs if r['status'] == 'no_solution_found'))
        if feas:
            b = feas[0]
            band = [r for r in feas if r['payload_kg'] >= (1 - NEAR_BAND) * b['payload_kg']]
            e.update(best_n=b['n_engines'], best_payload_kg=b['payload_kg'],
                     near_optimal_counts=';'.join(str(r['n_engines']) for r in sorted(band, key=lambda r: r['n_engines'])),
                     best_is_boundary_of_feasible_set=b['n_engines'] in (min(r['n_engines'] for r in feas), max(r['n_engines'] for r in feas)))
            if len(feas) > 1:
                s = feas[1]
                e.update(second_n=s['n_engines'], second_payload_kg=s['payload_kg'],
                         gap_to_second_kg=b['payload_kg'] - s['payload_kg'],
                         gap_to_second_pct=100 * (b['payload_kg'] - s['payload_kg']) / b['payload_kg'])
        out.append(e)
    return out


def baseline_kicks(baseline_dir: Path | None) -> dict:
    """Starting points for the per-N kick optimisation (re-optimised in every case)."""
    if baseline_dir is None:
        return {}
    kicks = {}
    with (baseline_dir / 'cases.csv').open(encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['status'] == 'feasible' and r['mode'] == 'reusable':
                kicks[int(r['n_engines'])] = ((float(r['kick_t_s']), float(r['kick_delta_deg'])),
                                              (float(r['payload_kg']), float(r['reserve_kg']),
                                               (float(r['steer_a']), float(r['steer_c']))))
    return kicks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mode', choices=['baseline', 'sensitivity', 'maps'], required=True)
    ap.add_argument('--calibration', type=Path, required=True)
    ap.add_argument('--basis', default='thrust_plus_drag', choices=['thrust_plus_drag', 'thrust_only'])
    ap.add_argument('--baseline', type=Path, help='baseline run dir (kick starting points)')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--counts', type=int, nargs='+', default=COUNTS)
    ap.add_argument('--name', default=None)
    ap.add_argument('--only', nargs='*', help='subset of sensitivity case names')
    args = ap.parse_args()
    base = frozen_overrides(args.calibration, args.basis)
    out = Path('results') / (datetime.now().strftime('%Y%m%d_%H%M') + '_' + (args.name or args.mode))
    out.mkdir(parents=True, exist_ok=True)
    load_parameters().with_overrides(base, 'calibrated (frozen)').write(out / 'parameters_resolved.json')
    starts = baseline_kicks(args.baseline)
    jobs = []
    if args.mode == 'baseline':
        for n in args.counts:
            jobs.append(dict(overrides=base, n=n, mode='reusable', tag='baseline', keep_traj=n in (3, 9, 15)))
            jobs.append(dict(overrides=base, n=n, mode='expendable', tag='baseline_expendable'))
    else:
        cases = sensitivity_cases(base) if args.mode == 'sensitivity' else map_cases(base)
        if args.only:
            cases = [c for c in cases if c[0] in args.only]
        for name, ov, num in cases:
            for n in args.counts:
                j = dict(overrides=ov, n=n, mode='reusable', tag=name, numerics=num)
                if n in starts:
                    j['kick0'], j['warm'] = starts[n]
                jobs.append(j)
    print(f'{len(jobs)} cases on {args.workers} workers -> {out}', flush=True)
    t0 = time.perf_counter()
    rows = run_parallel(jobs, args.workers)
    elapsed = time.perf_counter() - t0
    for r in rows:
        traj = r.pop('_trajectory', None)
        if traj:
            write_csv(out / f'trajectory_recovery_N{r["n_engines"]}.csv', traj)
    write_csv(out / 'cases.csv', rows)
    write_csv(out / 'best_counts.csv', best_counts(rows))
    write_manifest(out, dict(mode=args.mode, calibration_dir=str(args.calibration), frozen_calibration=base,
                             landing_cap_basis=args.basis, counts=args.counts, case_count=len(rows),
                             elapsed_seconds=elapsed, near_optimal_band_fraction=NEAR_BAND,
                             kick_start_source=str(args.baseline) if args.baseline else 'default'))
    print(f'done: {len(rows)} cases in {elapsed:.0f} s', flush=True)


if __name__ == '__main__':
    main()
