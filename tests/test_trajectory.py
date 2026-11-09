"""Verification of the trajectory code (does the code solve its equations correctly?).

These tests use a FIXED pitch kick and, where a feasible recovery is needed, the 'thrust_only'
landing-cap basis with q_entry_max = 100 kPa. Those settings are chosen only so that every
code path is exercised; they are not study results or baseline choices.
"""
import math
import unittest
from dataclasses import replace

import numpy as np

from vtvl import Numerics, load_parameters, make_earth, make_vehicle
from vtvl.ascent import Kick, run_stage1, run_stage2
from vtvl.dynamics import angular_momentum, constant_cd, make_dynamics, specific_energy
from vtvl.integrate import Event, integrate
from vtvl.performance import Warm, evaluate_payload
from vtvl.verification import replay_landing, replay_stage2

P = load_parameters()
P_REC = P.with_overrides({'recovery.entry_severity_limit_peak_q': 100000.0,
                          'recovery.landing_accel_cap_basis': 'thrust_only'}, 'test')
E = make_earth(P)
NUM = Numerics()
KICK = Kick(9.85, 1.31)


class TestDynamics(unittest.TestCase):
    def test_vacuum_kepler_coast_conserves_energy_and_momentum(self):
        earth = replace(E, atmosphere=False)
        rhs, _ = make_dynamics(earth, 10.0, constant_cd(0.0), lambda *a: (0.0, 1.0, 0.0, 0.0))
        y0 = [E.r_e + 100e3, 0.0, 1500.0, 2500.0, 30000.0]
        res = integrate(rhs, 0.0, y0, NUM.dt('coast'), 600.0)
        e0, e1 = specific_energy(earth, y0), specific_energy(earth, res.y_final)
        h0, h1 = angular_momentum(y0), angular_momentum(res.y_final)
        self.assertLess(abs(e1 / e0 - 1), 1e-10)
        self.assertLess(abs(h1 / h0 - 1), 1e-12)

    def test_landing_burn_matches_analytic_constant_gravity_no_drag(self):
        """1-D vertical burn: v(t) = v0 - g t + c ln(m0/m), h(t) = h0 + v0 t - g t^2/2 + c[t - (m/mdot) ln(m0/m)]."""
        earth = replace(E, atmosphere=False, gravity='constant', omega_eff=0.0)
        veh = make_vehicle(P, 9)
        eng = veh.engine
        u, k = 0.8, 1
        T, mdot = eng.thrust(u, 0.0, k), eng.massflow(u, k)

        def ctl(t, y, h, p, q, d, vr, vrt, vrel):
            return T, -vr / vrel, -vrt / vrel, mdot
        rhs, _ = make_dynamics(earth, veh.area, constant_cd(0.0), ctl)
        h0, v0, m0 = 3000.0, -250.0, 32000.0
        tb = 15.0
        res = integrate(rhs, 0.0, [E.r_e + h0, 0.0, v0, 0.0, m0], NUM.dt('landing'), tb)
        c = T / mdot
        m = m0 - mdot * tb
        v_an = v0 - E.g0 * tb + c * math.log(m0 / m)
        h_an = h0 + v0 * tb - 0.5 * E.g0 * tb ** 2 + c * (tb - (m / mdot) * math.log(m0 / m))
        self.assertAlmostEqual(res.y_final[2], v_an, delta=1e-6)
        self.assertAlmostEqual(res.y_final[0] - E.r_e, h_an, delta=1e-5)
        self.assertAlmostEqual(res.y_final[4], m, delta=1e-6)


class TestAscent(unittest.TestCase):
    def setUp(self):
        self.veh = make_vehicle(P, 9, 'expendable')

    def test_stage1_mass_bookkeeping_and_massflow(self):
        R = 12345.0
        veh = make_vehicle(P_REC, 9)
        s1 = run_stage1(veh, E, NUM, KICK, 17000.0, R)
        self.assertTrue(s1.ok, s1.reason)
        jettisoned = 0.0 if s1.fairing_on else veh.m_fair
        burned = s1.m0 - s1.y_meco[4] - jettisoned
        self.assertAlmostEqual(burned, veh.p1 - R, delta=1e-6)   # MECO exactly at P1 - R
        # mass flow integral (trapezoid over RK4 nodes) equals the mass change in every phase
        for ph in s1.phases:
            if len(ph.t) < 3:
                continue
            integral = np.trapezoid(ph.mdot, ph.t)
            dm = ph.y[0, 4] - ph.y[-1, 4]
            self.assertAlmostEqual(integral / dm, 1.0, delta=2e-4, msg=ph.name)

    def test_liftoff_thrust_and_accel_cap(self):
        s1 = run_stage1(self.veh, E, NUM, KICK, 22000.0, 0.0)
        ph = s1.phases[0]
        self.assertAlmostEqual(ph.thrust[0], P.v('engine.total_sl_thrust'), delta=1.0)
        self.assertLessEqual(s1.a_ng_peak, self.veh.a_max_asc * (1 + 1e-9) + 1e-6)

    def test_insertion_residuals_independent_replay(self):
        r = evaluate_payload(self.veh, E, NUM, KICK, Warm(L=23000.0, R=0.0))
        self.assertEqual(r.status, 'feasible', r.reason)
        dr, vr, dvt = r.residual
        self.assertLess(abs(dr), 100.0)
        self.assertLess(abs(vr), 1.0)
        self.assertLess(abs(dvt), 1.0)
        s1 = r.s1
        rp = replay_stage2(self.veh, E, s1.t_meco, s1.y_meco, s1.fairing_on, r.payload, r.steer)
        self.assertTrue(rp['success'])
        self.assertLess(abs(rp['dr']), 100.0)
        self.assertLess(abs(rp['vr']), 1.0)
        self.assertLess(abs(rp['dvt']), 1.0)


class TestRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.veh = make_vehicle(P_REC, 9)
        cls.r = evaluate_payload(cls.veh, E, NUM, KICK, Warm(L=18000.0, R=30000.0), final=True)

    def test_feasible_and_converged(self):
        self.assertEqual(self.r.status, 'feasible', self.r.reason)
        h = self.r.history[-1]
        self.assertLess(abs(h[2] - h[1]), NUM.fixed_point_tol_R)

    def test_reserve_bookkeeping(self):
        rec, veh = self.r.rec, self.veh
        loaded = veh.p1
        ascent = veh.p1 - self.r.reserve
        total = ascent + rec.m_entry + rec.m_landing + rec.margin + rec.residual
        self.assertAlmostEqual(total, loaded, delta=NUM.fixed_point_tol_R + 1e-6)
        # touchdown mass = dry + margin + residual (margin and residual stay on board)
        m_td = rec.landing.m_td
        self.assertAlmostEqual(m_td, veh.m_dry1 + rec.margin + rec.residual, delta=2.0 * NUM.fixed_point_tol_R)

    def test_touchdown_independent_replay(self):
        land = self.r.rec.landing
        rp = replay_landing(self.veh, E, land.t_ig, land.y_ig, land.k, land.u)
        self.assertTrue(rp['touchdown_found'])
        self.assertLessEqual(rp['speed'], self.veh.v_td)

    def test_landing_cap_respected(self):
        land = self.r.rec.landing
        self.assertLessEqual(land.peak_accel_g, self.veh.a_max_land / E.g0 + 1e-6)

    def test_scanned_throttle_is_fuel_optimal(self):
        for kr in self.r.rec.landing.per_k:
            if kr.status != 'feasible':
                continue
            feas = [s for s in kr.scan if s[1]]
            self.assertTrue(feas)
            self.assertLessEqual(kr.burn.propellant, min(s[2] for s in feas) + 1e-6)


if __name__ == '__main__':
    unittest.main()
