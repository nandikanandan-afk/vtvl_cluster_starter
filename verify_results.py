"""Reintegrate accepted cases with tighter tolerances and an actual ground event.

This checks numerical consistency, not agreement with flight data.
Usage: python verify_results.py results/baseline_drag
"""
import argparse
import csv
from dataclasses import replace
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from vtvl import Design, Mission, Numerics, Vehicle
from vtvl.config import G0
from vtvl.engines import booster_dry_mass_kg
from vtvl.landing import density, propagate
from run_study import write_csv


def touchdown_replay(design, vehicle, mission, physics, active, coast_s, burn_s, throttle, loaded):
    """Independent event-terminated ODE; switches engine off at planned burnout."""
    dry = booster_dry_mass_kg(design, vehicle)
    force = active * vehicle.total_sl_thrust_n / design.engine_count * throttle
    cd_area = mission.landing_drag_coefficient * math.pi * vehicle.diameter_m**2 / 4 if physics == 'drag' else 0.0
    initial = np.array([mission.terminal_entry_altitude_m,
                        -design.terminal_entry_speed_m_s, dry + loaded])

    def ground(t, y):
        return y[0]
    ground.terminal = True
    ground.direction = -1

    def empty(t, y):
        return y[2] - dry - mission.trapped_residual_kg
    empty.terminal = True
    empty.direction = -1

    time = 0.0
    # A short coast after planned shutdown captures positive endpoint roundoff.
    for duration, thrust in ((coast_s, 0.0), (burn_s, force), (10.0, 0.0)):
        if duration <= 0:
            continue
        def rhs(t, y):
            h, velocity, mass = y
            drag = -0.5 * density(h, mission) * cd_area * velocity * abs(velocity)
            return (velocity, (thrust + drag)/mass-G0, -thrust/(G0*vehicle.landing_isp_s))
        sol = solve_ivp(rhs, (time, time+duration), initial, events=(ground, empty),
                        rtol=1e-11, atol=1e-11, max_step=0.02)
        if not sol.success:
            return {'touchdown_event_found': False, 'replay_status': sol.message}
        if len(sol.t_events[0]):
            return dict(touchdown_event_found=True, replay_status='GROUND_EVENT',
                        actual_touchdown_time_s=float(sol.t_events[0][0]),
                        actual_touchdown_speed_m_s=float(sol.y_events[0][0,1]),
                        actual_touchdown_mass_kg=float(sol.y_events[0][0,2]))
        if len(sol.t_events[1]):
            return {'touchdown_event_found': False, 'replay_status': 'USABLE_PROPELLANT_EXHAUSTED'}
        initial, time = sol.y[:,-1], float(sol.t[-1])
    return {'touchdown_event_found': False, 'replay_status': 'NO_GROUND_EVENT_WITHIN_EXTENSION'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory',type=Path)
    args=parser.parse_args()
    meta=json.loads((args.run_directory/'manifest.json').read_text())
    vehicle,mission=Vehicle(**meta['vehicle']),Mission(**meta['mission'])
    num=replace(Numerics(**meta['numerics']),rtol=1e-11,atol=1e-11,max_step_s=0.02)
    rows=[]
    for old in csv.DictReader((args.run_directory/'cases.csv').open()):
        if old['payload_feasible']!='True':
            continue
        design=Design(int(old['engine_count']),float(old['fixed_engine_mass_fraction']),
                      float(old['min_throttle']),float(old['terminal_entry_speed_m_s']))
        active=int(old['landing_active_engines'])
        coast,burn,u=[float(old['landing_'+name]) for name in ('coast_s','burn_s','throttle')]
        p=propagate(design,vehicle,mission,num,active,coast,burn,u,samples=1001,force_numeric=True)
        result=touchdown_replay(design,vehicle,mission,num.physics,active,coast,burn,u,p['loaded'])
        rows.append(dict(engine_count=design.engine_count,
                         final_altitude_error_m=p['h_final'],
                         final_velocity_error_m_s=p['v_final']-mission.touchdown_velocity_m_s,
                         dense_peak_proper_accel_g=p['peak_proper_g'],
                         dense_peak_dynamic_pressure_pa=p['peak_q'], **result))
        if design.engine_count==9:
            trajectory=[dict(t_s=float(t),altitude_m=float(h),vertical_velocity_m_s=float(v),
                             mass_kg=float(m),thrust_n=float(f),dynamic_pressure_pa=float(q))
                        for t,h,v,m,f,q in zip(p['t'],p['h'],p['v'],p['mass'],p['thrust'],p['dynamic_pressure'])]
            write_csv(args.run_directory/'reference_trajectory.csv',trajectory)
    write_csv(args.run_directory/'independent_verification.csv',rows)
    summary=dict(
        checked_cases=len(rows),
        max_abs_final_altitude_error_m=max(abs(r['final_altitude_error_m']) for r in rows),
        max_abs_final_velocity_error_m_s=max(abs(r['final_velocity_error_m_s']) for r in rows),
        ground_events_found=sum(r['touchdown_event_found'] for r in rows),
        max_abs_event_touchdown_velocity_error_m_s=max(
            abs(r.get('actual_touchdown_speed_m_s',math.inf)-mission.touchdown_velocity_m_s) for r in rows),
        interpretation='Numerical consistency only; not flight-data validation or global optimality.'
    )
    (args.run_directory/'verification_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
