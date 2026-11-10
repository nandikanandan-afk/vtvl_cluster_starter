"""Case evaluation, parallel execution and provenance output.

A *case* = (parameter overrides, engine count N, mode). ``run_case`` re-optimises the pitch kick
for that case (never reusing another N's controller; only the optimizer's starting point is
shared), then re-evaluates the optimum with full diagnostics and independent replays.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .ascent import Kick
from .atmosphere import P0_SEA_LEVEL
from .config import Numerics, make_earth, make_vehicle
from .params import ROOT, load_parameters
from .performance import Warm, evaluate_payload, optimize_kick
from .verification import replay_landing, replay_stage2

DEFAULT_KICK = (9.85, 1.31)
DEFAULT_WARM = (17500.0, 30000.0, (0.3, 0.3))


def _f(x):
    return float(x) if x is not None and isinstance(x, (int, float, np.floating)) else x


def run_case(job: dict) -> dict:
    """job keys: overrides, n, mode, kick0, warm, numerics, tag, keep_traj."""
    t_start = time.perf_counter()
    P = load_parameters().with_overrides(job.get('overrides') or {}, reason=job.get('tag', 'case'),
                                         allow_out_of_range=job.get('allow_out_of_range', False))
    num = Numerics(**(job.get('numerics') or {}))
    n, mode = job['n'], job.get('mode', 'reusable')
    veh = make_vehicle(P, n, mode, job.get('mass_model'))
    earth = make_earth(P)
    kick0 = Kick(*job.get('kick0', DEFAULT_KICK))
    L0, R0, st0 = job.get('warm', DEFAULT_WARM)
    warm = Warm(L=L0, R=R0 if mode == 'reusable' else 0.0, steer=tuple(st0))
    row = dict(tag=job.get('tag', ''), n_engines=n, mode=mode)
    row.update(_vehicle_columns(veh, earth))
    try:
        if job.get('optimize', True):
            ko = optimize_kick(veh, earth, num, kick0, warm)
            best = ko.best
            row.update(kick_evaluations=ko.evaluations, kick_message=ko.message)
            kick = best.kick
        else:
            kick, best = kick0, None
            row.update(kick_evaluations=0, kick_message='fixed kick (not optimised)')
        if best is None or best.status == 'feasible':
            final = evaluate_payload(veh, earth, num, kick, warm, final=True)
        else:
            final = best
        row.update(_payload_columns(veh, earth, final))
        if final.status == 'feasible':
            row.update(_replay_columns(veh, earth, final))
        if job.get('keep_traj') and final.status == 'feasible':
            row['_trajectory'] = _trajectory(final)
    except Exception as exc:  # never lose a case: record it as a solver failure
        import traceback
        row.update(status='no_solution_found', reason=f'exception: {exc!r}',
                   traceback=traceback.format_exc()[-800:])
    row['wall_time_s'] = time.perf_counter() - t_start
    return row


def _vehicle_columns(veh, earth) -> dict:
    e, d = veh.engine, veh.dry
    return dict(
        engine_sl_thrust_kN=e.t_sl / 1e3, engine_vac_thrust_kN=e.t_vac / 1e3, engine_exit_area_m2=e.a_e,
        engine_exit_diameter_m=math.sqrt(4 * e.a_e / math.pi), total_exit_area_fraction_of_base=veh.n_engines * e.a_e / veh.area,
        engine_mass_each_kg=d.engine_each, engines_total_kg=d.engines_total, integration_total_kg=d.integration_total,
        nonengine_kg=d.nonengine, recovery_hardware_kg=d.recovery_hardware, booster_dry_kg=veh.m_dry1,
        p1_kg=veh.p1, u_min_massflow=veh.u_min, u_min_sl_fraction=veh.u_min_sl_fraction,
        landing_tw_min_throttle_1eng_at_dry_plus_res=e.thrust(veh.u_min, P0_SEA_LEVEL, 1) / ((veh.m_dry1 + veh.m_res) * earth.g0),
        q_entry_max_Pa=veh.q_entry_max, land_cap_basis=veh.land_cap_basis, entry_q_window=veh.entry_q_window,
    )


def _payload_columns(veh, earth, r) -> dict:
    out = dict(status=r.status, reason=r.reason, payload_kg=r.payload, reserve_kg=r.reserve,
               outer_iterations=r.iterations, inner_iterations=r.inner_iterations,
               kick_t_s=r.kick.t_kick, kick_delta_deg=r.kick.delta_deg)
    s1 = r.s1
    if s1 is not None and s1.ok:
        rr, th, vr, vt, m = s1.y_meco
        vrt = vt - earth.omega_eff * rr
        out.update(meco_t_s=s1.t_meco, meco_h_km=(rr - earth.r_e) / 1e3, meco_vrel_m_s=math.hypot(vr, vrt),
                   meco_gamma_deg=math.degrees(math.atan2(vr, vrt)), meco_v_inertial_m_s=math.hypot(vr, vt),
                   ascent_q_peak_Pa=s1.q_peak, ascent_t_qpeak_s=s1.t_qpeak, ascent_a_peak_g=s1.a_ng_peak / earth.g0,
                   stage1_throttle_floor_hit=s1.throttle_floor_hit, fairing_jettison_t_s=s1.t_fairing,
                   glow_kg=s1.m0, liftoff_tw=veh.engine.thrust(1.0, P0_SEA_LEVEL, veh.n_engines) / (s1.m0 * earth.g0))
    if r.status == 'feasible':
        dr, v_r, dvt = r.residual
        out.update(insertion_dr_m=dr, insertion_vr_m_s=v_r, insertion_dvt_m_s=dvt,
                   steer_a=r.steer[0], steer_c=r.steer[1])
        if r.s2 is not None:
            out.update(stage2_burn_s=r.s2.burn_time, stage2_a_peak_g=r.s2.a_ng_peak / earth.g0 if math.isfinite(r.s2.a_ng_peak) else math.nan,
                       stage2_throttle_floor_hit=r.s2.throttle_floor_hit,
                       fairing_jettison_stage2_t_s=r.s2.t_fairing)
    rec = r.rec
    if rec is not None:
        out.update(recovery_status=rec.status, h_apogee_km=rec.h_apogee / 1e3, entry_start_h_km=rec.entry_start_h / 1e3,
                   entry_start_speed_m_s=rec.entry_start_speed, entry_burn_s=rec.t_eb, m_entry_kg=rec.m_entry,
                   entry_k_profile=';'.join(f'{t:.2f}s:k{k}' for t, k in rec.entry_k_profile),
                   q_peak_descent_Pa=rec.q_peak_desc, h_qpeak_descent_km=rec.h_qpeak / 1e3,
                   q_peak_entry_burn_Pa=rec.q_peak_burn,
                   m_landing_kg=rec.m_landing, margin_kg=rec.margin, residual_kg=rec.residual,
                   downrange_km=rec.downrange_m / 1e3 if math.isfinite(rec.downrange_m) else math.nan)
        land = rec.landing
        if land is not None:
            out.update(landing_status=land.status, landing_reason=land.reason, landing_k=land.k, landing_u=land.u,
                       landing_ignition_h_m=land.h_ig, landing_peak_accel_g=land.peak_accel_g, landing_peak_at=land.peak_at,
                       landing_burn_s=land.t_burn, landing_m_td_kg=land.m_td, landing_v_ign_m_s=land.v_ign,
                       landing_tw_min_throttle_at_td=land.tw_min_td)
            for kr in land.per_k:
                out[f'landing_k{kr.k}_status'] = kr.status
                out[f'landing_k{kr.k}_reason'] = kr.reason
                if kr.scan:
                    out[f'landing_k{kr.k}_scan'] = ';'.join(f'{u:.4f}|{int(ok)}|{p:.1f}|{a:.3f}' for u, ok, p, a in kr.scan)
                    feas = [s for s in kr.scan if s[1]]
                    out[f'landing_k{kr.k}_scan_min_prop_kg'] = min(s[2] for s in feas) if feas else math.nan
    return out


def _replay_columns(veh, earth, r) -> dict:
    s1 = r.s1
    rp = replay_stage2(veh, earth, s1.t_meco, s1.y_meco, s1.fairing_on, r.payload, r.steer)
    out = dict(replay_insertion_dr_m=rp['dr'], replay_insertion_vr_m_s=rp['vr'], replay_insertion_dvt_m_s=rp['dvt'])
    if r.rec is not None and r.rec.landing is not None and r.rec.landing.status == 'feasible':
        land = r.rec.landing
        tl = replay_landing(veh, earth, land.t_ig, land.y_ig, land.k, land.u)
        out.update(replay_touchdown_found=tl['touchdown_found'], replay_touchdown_speed_m_s=tl['speed'],
                   replay_touchdown_v_vertical_m_s=tl['v_vertical'], replay_touchdown_v_horizontal_m_s=tl['v_horizontal'],
                   replay_touchdown_mass_kg=tl['mass'])
    return out


def _trajectory(r) -> list[dict]:
    rows = []
    phases = list(r.rec.phases) if r.rec is not None else []
    for ph in phases:
        if ph is None:
            continue
        for i in range(len(ph.t)):
            rows.append(dict(phase=ph.name, t_s=float(ph.t[i]), h_m=float(ph.h[i]), speed_m_s=float(ph.vrel[i]),
                             mass_kg=float(ph.y[i][4]), thrust_N=float(ph.thrust[i]), q_Pa=float(ph.q[i]),
                             a_ng_g=float(ph.a_ng[i] / 9.80665), downrange_km=float(ph.y[i][1] * 6378.137)))
    return rows


# ----------------------------------------------------------------------------------------------
def run_parallel(jobs: list[dict], workers: int) -> list[dict]:
    if workers <= 1:
        return [run_case(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(run_case, jobs, chunksize=1))


def write_csv(path: Path, rows: list[dict]) -> None:
    rows = [{k: v for k, v in r.items() if not k.startswith('_')} for r in rows]
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: ('' if isinstance(v, float) and not math.isfinite(v) else v) for k, v in r.items()})


def git_hash() -> str:
    try:
        h = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = subprocess.run(['git', 'status', '--porcelain', 'vtvl', 'data'], cwd=ROOT, capture_output=True,
                               text=True, timeout=10).stdout.strip()
        return h + ('-dirty' if dirty else '')
    except Exception:
        return 'unknown'


def write_manifest(out: Path, extra: dict) -> None:
    import scipy
    import pandas
    import matplotlib
    src = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted((ROOT / 'vtvl').glob('*.py'))}
    src.update({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / 'data').glob('*.json'))})
    man = dict(git_commit=git_hash(), python=platform.python_version(), numpy=np.__version__,
               scipy=scipy.__version__, pandas=pandas.__version__, matplotlib=matplotlib.__version__,
               platform=platform.platform(), numerics_default=asdict(Numerics()), random_seeds='none used (deterministic)',
               source_sha256=src, **extra)
    (out / 'manifest.json').write_text(json.dumps(man, indent=2, default=str) + '\n', encoding='utf-8')
