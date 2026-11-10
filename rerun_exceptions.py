"""Rerun ONLY the cases of a finished run that died from a code exception (reason starts with
'exception'), after the bug was fixed. Original cases.csv is kept as cases_original.csv; replaced rows are
flagged `rerun_after_bugfix=True`. Successful original rows are NOT recomputed.
Usage: python rerun_exceptions.py results/<run_dir> [--workers 8]
"""
import argparse
import csv
import json
import shutil
from pathlib import Path

import pandas as pd

import run_study as rs
from vtvl.study import run_parallel, write_csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir', type=Path)
    ap.add_argument('--workers', type=int, default=8)
    args = ap.parse_args()
    man = json.loads((args.run_dir / 'manifest.json').read_text())
    base = man['frozen_calibration']
    cases = rs.sensitivity_cases(base) if man['mode'] == 'sensitivity' else rs.map_cases(base)
    by_name = {c[0]: c for c in cases}
    df = pd.read_csv(args.run_dir / 'cases.csv')
    bad = df[df['reason'].astype(str).str.startswith('exception')]
    print(f'{len(bad)} exception cases to rerun in {args.run_dir}', flush=True)
    if bad.empty:
        return
    starts = rs.baseline_kicks(Path(man['kick_start_source'])) if man.get('kick_start_source', 'default') != 'default' else {}
    jobs = []
    for _, r in bad.iterrows():
        name, ov, num = by_name[r['tag']]
        j = dict(overrides=ov, n=int(r['n_engines']), mode='reusable', tag=name, numerics=num)
        if j['n'] in starts:
            j['kick0'], j['warm'] = starts[j['n']]
        jobs.append(j)
    new = run_parallel(jobs, args.workers)
    for r in new:
        r['rerun_after_bugfix'] = True
    shutil.copy(args.run_dir / 'cases.csv', args.run_dir / 'cases_original.csv')
    keep = df[~df.index.isin(bad.index)].to_dict('records')
    rows = keep + new
    rows.sort(key=lambda r: (str(r['tag']), int(r['n_engines'])))
    write_csv(args.run_dir / 'cases.csv', rows)
    write_csv(args.run_dir / 'best_counts.csv', rs.best_counts(rows))
    man['rerun_after_bugfix'] = dict(count=len(new), note='exception-killed cases rerun after fixing landing bracket fallback and a_max_land>=4 stop-speed guard')
    (args.run_dir / 'manifest.json').write_text(json.dumps(man, indent=2, default=str) + '\n', encoding='utf-8')
    print('rerun done:', pd.Series([r['status'] for r in new]).value_counts().to_dict(), flush=True)


if __name__ == '__main__':
    main()
