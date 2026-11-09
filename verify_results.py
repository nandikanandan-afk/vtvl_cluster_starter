"""Numerical verification of a baseline run (not flight-data validation).

1. Step halving: every RK4 step halved (Numerics.step_scale = 0.5), kick re-optimised;
   payload change must be < 10 kg.
2. Optimizer robustness: three different initial pitch-kick guesses per selected N; payloads
   must agree within 10 kg (disagreements are reported, not hidden).
3. Insertion and touchdown residuals of every feasible baseline case (independent DOP853 replay,
   already in cases.csv) are summarised against the tolerances.
Usage: python verify_results.py results/<ts>_baseline [--counts 5 9 15] [--workers 8]
"""
import argparse
import csv
import json
import math
from pathlib import Path

from vtvl.study import run_parallel, write_csv

GUESSES = [(6.0, 0.8), (14.0, 2.0), (25.0, 4.0)]
TOL_PAYLOAD = 10.0
TOL_INS = dict(dr=100.0, vr=1.0, dvt=1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir', type=Path)
    ap.add_argument('--counts', type=int, nargs='+', default=None)
    ap.add_argument('--workers', type=int, default=8)
    args = ap.parse_args()
    man = json.loads((args.run_dir / 'manifest.json').read_text())
    base = man['frozen_calibration']
    rows = list(csv.DictReader((args.run_dir / 'cases.csv').open(encoding='utf-8')))
    feas = [r for r in rows if r['mode'] == 'reusable' and r['status'] == 'feasible']
    counts = args.counts or sorted({int(r['n_engines']) for r in feas})[:1] + [9] + sorted({int(r['n_engines']) for r in feas})[-1:]
    counts = sorted(set(c for c in counts if any(int(r['n_engines']) == c for r in feas)))
    ref = {int(r['n_engines']): float(r['payload_kg']) for r in feas}
    jobs = []
    for n in counts:
        r0 = next(r for r in feas if int(r['n_engines']) == n)
        k0 = (float(r0['kick_t_s']), float(r0['kick_delta_deg']))
        jobs.append(dict(overrides=base, n=n, mode='reusable', tag='step_halving', kick0=k0,
                         numerics={'step_scale': 0.5}))
        for g in GUESSES:
            jobs.append(dict(overrides=base, n=n, mode='reusable', tag=f'robust_guess_{g[0]}_{g[1]}', kick0=g))
    out = run_parallel(jobs, args.workers)
    write_csv(args.run_dir / 'verification_cases.csv', out)
    summary = []
    for n in counts:
        h = next(r for r in out if r['n_engines'] == n and r['tag'] == 'step_halving')
        rb = [r for r in out if r['n_engines'] == n and r['tag'].startswith('robust')]
        pays = [r['payload_kg'] for r in rb if r['status'] == 'feasible']
        summary.append(dict(
            n_engines=n, baseline_payload_kg=ref[n],
            halved_step_payload_kg=h.get('payload_kg'), step_halving_change_kg=(h.get('payload_kg', math.nan) - ref[n]),
            step_halving_pass=abs(h.get('payload_kg', math.nan) - ref[n]) < TOL_PAYLOAD,
            robust_payloads_kg=';'.join(f'{p:.1f}' for p in pays),
            robust_statuses=';'.join(r['status'] for r in rb),
            robust_spread_incl_baseline_kg=(max(pays + [ref[n]]) - min(pays + [ref[n]])) if pays else math.nan,
            robust_pass=bool(pays) and len(pays) == len(rb) and (max(pays + [ref[n]]) - min(pays + [ref[n]])) < TOL_PAYLOAD,
            robust_kicks=';'.join(f'({r.get("kick_t_s", math.nan):.3f},{r.get("kick_delta_deg", math.nan):.4f})' for r in rb)))
    write_csv(args.run_dir / 'verification_convergence.csv', summary)
    # residual summary over all feasible baseline cases
    def mx(col):
        vals = [abs(float(r[col])) for r in feas if r.get(col) not in (None, '')]
        return max(vals) if vals else math.nan
    res = dict(cases=len(feas),
               max_abs_insertion_dr_m=mx('insertion_dr_m'), max_abs_insertion_vr_m_s=mx('insertion_vr_m_s'),
               max_abs_insertion_dvt_m_s=mx('insertion_dvt_m_s'),
               max_abs_replay_insertion_dr_m=mx('replay_insertion_dr_m'), max_abs_replay_insertion_vr_m_s=mx('replay_insertion_vr_m_s'),
               max_abs_replay_insertion_dvt_m_s=mx('replay_insertion_dvt_m_s'),
               all_touchdowns_found=all(r.get('replay_touchdown_found') == 'True' for r in feas),
               max_replay_touchdown_speed_m_s=mx('replay_touchdown_speed_m_s'),
               tolerances=dict(insertion=TOL_INS, payload_kg=TOL_PAYLOAD))
    (args.run_dir / 'verification_summary.json').write_text(json.dumps(res, indent=2) + '\n')
    print(json.dumps(res, indent=2))
    for s in summary:
        print(s)


if __name__ == '__main__':
    main()
