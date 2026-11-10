"""Calibration protocol at N = 9 (prompt section 6.5), written to results/<timestamp>_calibration_N9/.

Step A  expendable N = 9: ascent Cd scale in [0.8, 1.2] -> 22,800 kg (1 %).
Step B  reusable N = 9: q_entry_max -> 17,500 kg (band 17.4-18.5 t), for each landing-cap basis
        ('thrust_plus_drag' = database definition; 'thrust_only' = alternative for the team).
Step C  calibrated N = 9 details (recovery propellant, landing T/W, replays) are in the rows.
Step D  EXPLORATORY preview: all odd N under both bases at the calibrated values (informs the
        cap-basis decision; not the production baseline).
Usage: python run_calibration.py [--workers 8] [--skip-preview]
"""
import argparse
import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

from vtvl.params import load_parameters
from vtvl.study import run_case, run_parallel, write_csv, write_manifest

ANCHOR_EXP = 22800.0
TARGET_REU = 17500.0
BAND_REU = (17400.0, 18500.0)
Q_TRIALS = [40000.0, 50000.0, 60000.0, 70000.0, 80000.0, 100000.0, 140000.0, 200000.0]
BASES = ['thrust_plus_drag', 'thrust_only']
COUNTS = list(range(1, 28, 2))
WINDOW = ['after_burn']


def secant_refine(args):
    """Illinois on L(q) - target between a bracketing pair of trial rows (runs in a worker)."""
    basis, cd, (qa, La, ka), (qb, Lb, kb), window = args
    WINDOW[0] = window
    rows = []
    fa, fb = La - TARGET_REU, Lb - TARGET_REU
    a, b = qa, qb
    kick = ka
    side = 0
    for _ in range(12):
        q = b - fb * (b - a) / (fb - fa)
        row = run_case(dict(overrides={'booster.ascent_cd_scale': cd, 'recovery.entry_severity_limit_peak_q': q,
                                       'recovery.landing_accel_cap_basis': basis, 'recovery.entry_q_window': WINDOW[0]},
                            n=9, mode='reusable', kick0=kick, tag=f'calib_reusable_{basis}_refine'))
        rows.append(row)
        if row['status'] != 'feasible':
            break
        kick = (row['kick_t_s'], row['kick_delta_deg'])
        fq = row['payload_kg'] - TARGET_REU
        if abs(fq) <= 10.0 or abs(b - a) < 50.0:
            break
        if (fq > 0) == (fb > 0):
            b, fb = q, fq
            if side == -1:
                fa *= 0.5
            side = -1
        else:
            a, fa = q, fq
            if side == +1:
                fb *= 0.5
            side = +1
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--skip-preview', action='store_true')
    ap.add_argument('--window', default='after_burn', choices=['after_burn', 'burn_and_after'])
    args = ap.parse_args()
    out = Path('results') / (datetime.now().strftime('%Y%m%d_%H%M') + f'_calibration_N9_{args.window}')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    P = load_parameters()
    P.write(out / 'parameters_resolved_uncalibrated.json')
    log = {}

    # ---- Step A ---------------------------------------------------------------------------
    lo, hi = P.get('booster.ascent_cd_scale').range
    cds = [lo, 1.0, hi]
    rows_a = run_parallel([dict(overrides={'booster.ascent_cd_scale': s}, n=9, mode='expendable',
                                tag=f'calib_expendable_cd{s}') for s in cds], args.workers)
    pay = {s: r['payload_kg'] for s, r in zip(cds, rows_a)}
    print('Step A', pay, flush=True)
    f = {s: pay[s] - ANCHOR_EXP for s in cds}
    if f[lo] * f[hi] <= 0:
        # bracketed: refine (Illinois) sequentially
        a, b, fa, fb = lo, hi, f[lo], f[hi]
        for _ in range(10):
            s = b - fb * (b - a) / (fb - fa)
            r = run_case(dict(overrides={'booster.ascent_cd_scale': s}, n=9, mode='expendable', tag='calib_expendable_refine'))
            rows_a.append(r)
            fs = r['payload_kg'] - ANCHOR_EXP
            if abs(fs) < 0.002 * ANCHOR_EXP:
                break
            if (fs > 0) == (fb > 0):
                b, fb = s, fs
            else:
                a, fa = s, fs
        cd_star, cal_a_status = s, 'calibrated'
    else:
        cd_star = min(cds, key=lambda s: abs(pay[s] - ANCHOR_EXP))
        cal_a_status = 'calibrated' if abs(pay[cd_star] - ANCHOR_EXP) <= 0.01 * ANCHOR_EXP else 'anchor_not_reachable'
    log['step_A'] = dict(knob='booster.ascent_cd_scale', range=[lo, hi], trials=pay, status=cal_a_status,
                         frozen_value=cd_star, payload_at_frozen=pay.get(cd_star),
                         mismatch_pct=100 * (pay[cd_star] / ANCHOR_EXP - 1) if cd_star in pay else math.nan)
    write_csv(out / 'calibration_expendable_cases.csv', rows_a)

    # ---- Step B ---------------------------------------------------------------------------
    jobs = [dict(overrides={'booster.ascent_cd_scale': cd_star, 'recovery.entry_severity_limit_peak_q': q,
                            'recovery.landing_accel_cap_basis': b, 'recovery.entry_q_window': args.window},
                 n=9, mode='reusable', tag=f'calib_reusable_{b}_q{q:.0f}') for b in BASES for q in Q_TRIALS]
    rows_b = run_parallel(jobs, args.workers)
    print('Step B trials done', flush=True)
    refine_jobs = []
    WINDOW[0] = args.window
    log['step_B'] = {}
    for b in BASES:
        tr = [(r['q_entry_max_Pa'], r['payload_kg'] if r['status'] == 'feasible' else math.nan,
               (r.get('kick_t_s'), r.get('kick_delta_deg')), r['status']) for r in rows_b if r['land_cap_basis'] == b]
        log['step_B'][b] = dict(trials=[dict(q=q, payload=L, status=s) for q, L, k, s in tr])
        feas = [(q, L, k) for q, L, k, s in tr if math.isfinite(L)]
        for x, y in zip(feas, feas[1:]):
            if (x[1] - TARGET_REU) * (y[1] - TARGET_REU) <= 0:
                refine_jobs.append((b, cd_star, x, y, args.window))
                break
    with ProcessPoolExecutor(max_workers=max(1, len(refine_jobs))) as ex:
        refined = list(ex.map(secant_refine, refine_jobs)) if refine_jobs else []
    rows_b_all = list(rows_b)
    for (b, *_), rr in zip(refine_jobs, refined):
        rows_b_all += rr
    for b in BASES:
        cand = [r for r in rows_b_all if r['land_cap_basis'] == b and r['status'] == 'feasible']
        if not cand:
            log['step_B'][b].update(status='no_feasible_point', frozen_value=None)
            continue
        best = min(cand, key=lambda r: abs(r['payload_kg'] - TARGET_REU))
        in_band = BAND_REU[0] <= best['payload_kg'] <= BAND_REU[1]
        log['step_B'][b].update(status='calibrated' if in_band else 'anchor_not_reachable',
                                frozen_value=best['q_entry_max_Pa'], payload_at_frozen=best['payload_kg'],
                                reserve_at_frozen=best['reserve_kg'], tag=best['tag'])
    write_csv(out / 'calibration_reusable_cases.csv', rows_b_all)
    print('Step B', json.dumps(log['step_B'], default=str)[:2000], flush=True)

    # ---- Step D (exploratory preview) -----------------------------------------------------------
    if not args.skip_preview:
        q_ref = log['step_B'].get('thrust_only', {}).get('frozen_value')
        prev = []
        for b in BASES:
            qb = log['step_B'][b].get('frozen_value') or q_ref
            if qb is None:
                continue
            prev += [dict(overrides={'booster.ascent_cd_scale': cd_star, 'recovery.entry_severity_limit_peak_q': qb,
                                     'recovery.landing_accel_cap_basis': b, 'recovery.entry_q_window': args.window}, n=n, mode='reusable',
                          tag=f'preview_{b}') for n in COUNTS]
        rows_d = run_parallel(prev, args.workers)
        write_csv(out / 'exploratory_preview_all_N.csv', rows_d)
        log['step_D_preview'] = [dict(basis=r['land_cap_basis'], n=r['n_engines'], status=r['status'],
                                      payload=r.get('payload_kg'), q_entry=r['q_entry_max_Pa'],
                                      reason=str(r.get('reason', ''))[:300]) for r in rows_d]
    log['wall_time_s'] = time.perf_counter() - t0
    (out / 'calibration.json').write_text(json.dumps(log, indent=2, default=str) + '\n', encoding='utf-8')
    write_manifest(out, dict(purpose='N = 9 calibration protocol + exploratory preview',
                             anchors=dict(expendable=ANCHOR_EXP, reusable_target=TARGET_REU, reusable_band=BAND_REU),
                             q_trials=Q_TRIALS, bases=BASES, entry_q_window=args.window))
    print(f'done in {log["wall_time_s"]:.0f} s -> {out}', flush=True)


if __name__ == '__main__':
    main()
