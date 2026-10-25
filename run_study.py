"""Run a reproducible engine-count baseline or four-factor sweep.

Examples:
    python run_study.py --mode baseline --out results/baseline_drag
    python run_study.py --mode grid --physics analytic --out results/grid_analytic
    python run_study.py --mode grid --workers 4 --out results/grid_drag
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from dataclasses import asdict, replace
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import platform
from time import perf_counter

import numpy as np
import scipy

from vtvl import Design, Mission, Numerics, Vehicle, evaluate_design


def execute_case(args):
    return evaluate_design(*args)


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        # Missing or failed quantities are blank, not a misleading zero.
        for row in rows:
            writer.writerow({key: ('' if isinstance(value, float) and not math.isfinite(value) else value)
                             for key, value in row.items()})


def summarize_winners(rows: list[dict]) -> list[dict]:
    groups = {}
    for row in rows:
        key = tuple(row[name] for name in ('fixed_engine_mass_fraction', 'min_throttle', 'terminal_entry_speed_m_s'))
        groups.setdefault(key, []).append(row)
    result = []
    for (phi, throttle, speed), candidates in groups.items():
        good = sorted((r for r in candidates if r['payload_feasible']),
                      key=lambda r: r['payload_proxy_kg'], reverse=True)
        entry = dict(fixed_engine_mass_fraction=phi, min_throttle=throttle,
                     terminal_entry_speed_m_s=speed, feasible_count=len(good), evaluated_count=len(candidates))
        if good:
            best = good[0]
            entry.update(best_engine_count=best['engine_count'], best_payload_proxy_kg=best['payload_proxy_kg'],
                         counts_within_one_percent=';'.join(str(r['engine_count']) for r in good
                                                           if r['payload_proxy_kg'] >= 0.99*best['payload_proxy_kg']),
                         runner_up_gap_kg=best['payload_proxy_kg']-good[1]['payload_proxy_kg'] if len(good)>1 else math.nan)
        else:
            entry.update(best_engine_count='', best_payload_proxy_kg=math.nan,
                         counts_within_one_percent='', runner_up_gap_kg=math.nan)
        result.append(entry)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mode', choices=['baseline', 'grid'], default='baseline')
    parser.add_argument('--physics', choices=['analytic', 'drag'], default='drag')
    parser.add_argument('--out', type=Path, default=Path('results/new_run'))
    parser.add_argument('--config', type=Path, help='JSON with optional vehicle/mission/numerics objects')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--starts', type=int, default=4)
    parser.add_argument('--counts', type=int, nargs='+', default=[1,3,5,7,9,11,13,15,17,19])
    parser.add_argument('--phi', type=float, nargs='+')
    parser.add_argument('--throttle', type=float, nargs='+')
    parser.add_argument('--speeds', type=float, nargs='+')
    parser.add_argument('--landing-engines', type=int, nargs='+', default=None)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('--workers must be >= 1')
    overrides = json.loads(args.config.read_text()) if args.config else {}
    vehicle = Vehicle(**overrides.get('vehicle', {}))
    mission = Mission(**overrides.get('mission', {}))
    numerics = Numerics(**overrides.get('numerics', {}))
    numerics = replace(numerics, physics=args.physics, multistarts=args.starts)
    if args.landing_engines is not None:
        mission = replace(mission, allowed_landing_engine_counts=tuple(args.landing_engines))
    phi_values = args.phi or ([0.10,0.25,0.40] if args.mode == 'grid' else [0.25])
    throttle_values = args.throttle or ([0.20,0.40,0.60] if args.mode == 'grid' else [0.40])
    speed_values = args.speeds or ([150.0,200.0,250.0] if args.mode == 'grid' else [200.0])
    designs = [Design(n, phi, u, speed) for n, phi, u, speed in
               product(args.counts, phi_values, throttle_values, speed_values)]
    jobs = [(d, vehicle, mission, numerics) for d in designs]
    args.out.mkdir(parents=True, exist_ok=True)
    start = perf_counter()
    if args.workers == 1:
        rows = list(map(execute_case, jobs))
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            rows = list(executor.map(execute_case, jobs))
    elapsed = perf_counter() - start
    write_csv(args.out / 'cases.csv', rows)
    write_csv(args.out / 'best_counts.csv', summarize_winners(rows))
    root = Path(__file__).resolve().parent
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.rglob('*.py')) if '__pycache__' not in str(p)}
    manifest = dict(
        model='Generic F9-class constant-total-thrust conceptual trade, v0.1',
        fidelity='1D terminal descent + two-stage ideal-delta-v payload proxy',
        vehicle=asdict(vehicle), mission=asdict(mission), numerics=asdict(numerics),
        grid=dict(engine_counts=args.counts, fixed_engine_mass_fractions=phi_values,
                  minimum_throttles=throttle_values, terminal_entry_speeds_m_s=speed_values),
        case_count=len(rows), feasible_count=sum(r['payload_feasible'] for r in rows),
        elapsed_seconds=elapsed, python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
        source_sha256=hashes,
    )
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f"{len(rows)} cases; {manifest['feasible_count']} feasible in this control family; {elapsed:.2f} s")
    print(f'Wrote {args.out.resolve()}')
    for row in rows if args.mode == 'baseline' else []:
        value = row['payload_proxy_kg']
        summary = f"payload proxy={value:,.1f} kg, k={row['landing_active_engines']}" if row['payload_feasible'] else row['landing_status']
        print(f"N={row['engine_count']:2d}: {summary}")


if __name__ == '__main__':
    main()
