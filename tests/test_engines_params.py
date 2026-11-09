"""Verification: parameter loader, engine model, dry-mass bookkeeping, atmosphere, integrator."""
import math
import unittest

import numpy as np

from vtvl.atmosphere import atmosphere, temperature, P0_SEA_LEVEL
from vtvl.config import make_vehicle
from vtvl.engines import (akin_scale, booster_dry_mass, engine_mass, make_engine,
                          massflow_fraction_from_sl_thrust_fraction, stage1_propellant_capacity)
from vtvl.integrate import Event, integrate
from vtvl.params import ParameterError, load_parameters

P = load_parameters()
COUNTS = list(range(1, 28, 2))


class TestParameters(unittest.TestCase):
    def test_every_entry_has_provenance(self):
        for rec in P.records():
            self.assertTrue(rec['source'], rec['name'])
            self.assertTrue(rec['units'], rec['name'])

    def test_unit_check_on_access(self):
        with self.assertRaises(ParameterError):
            P.v('engine.isp_sl', 'kg')

    def test_out_of_range_override_rejected(self):
        with self.assertRaises(ParameterError):
            P.with_overrides({'engine.fixed_mass_fraction': 0.9})
        Q = P.with_overrides({'engine.fixed_mass_fraction': 0.9}, allow_out_of_range=True)
        self.assertEqual(Q.v('engine.fixed_mass_fraction'), 0.9)

    def test_ambiguous_short_name(self):
        with self.assertRaises(KeyError):
            P.get('isp_vac')  # engine.isp_vac and upper_stage.isp_vac

    def test_uncalibrated_value_raises(self):
        with self.assertRaises(ParameterError):
            P.v('recovery.entry_severity_limit_peak_q')


class TestEngine(unittest.TestCase):
    def test_total_liftoff_thrust_identical_for_all_N(self):
        t_tot = P.v('engine.total_sl_thrust')
        for n in COUNTS:
            e = make_engine(P, n)
            self.assertAlmostEqual(e.thrust(1.0, P0_SEA_LEVEL, k=n), t_tot, delta=1.0)

    def test_vacuum_and_sea_level_isp(self):
        for n in (1, 9, 27):
            e = make_engine(P, n)
            self.assertAlmostEqual(e.isp(1.0, 0.0), P.v('engine.isp_vac'), places=9)
            # Derived SL Isp = Isp_vac / r_vs (the stated resolution of the 2 % data inconsistency)
            self.assertAlmostEqual(e.isp(1.0, P0_SEA_LEVEL), P.v('engine.isp_vac') / P.v('engine.vac_to_sl_thrust_ratio'), places=9)

    def test_mass_flow_consistency(self):
        g0 = P.v('mission.earth_model')['g0']
        for n in (3, 9, 21):
            e = make_engine(P, n)
            for u in (0.6, 0.8, 1.0):
                for p in (0.0, 5000.0, P0_SEA_LEVEL):
                    self.assertAlmostEqual(e.massflow(u), e.thrust(u, p) / (g0 * e.isp(u, p)), places=9)

    def test_min_throttle_conversion(self):
        r = P.v('engine.vac_to_sl_thrust_ratio')
        u = massflow_fraction_from_sl_thrust_fraction(0.57, r)
        self.assertAlmostEqual(u, 0.6025878, places=6)
        for n in (1, 9, 27):
            e = make_engine(P, n)
            self.assertAlmostEqual(e.thrust(u, P0_SEA_LEVEL), 0.57 * e.t_sl, places=6)


class TestMassModels(unittest.TestCase):
    def test_powerlaw_reference_anchor_for_all_phi_beta(self):
        for phi in (0.0, 0.07, 0.2, 0.4):
            for beta in (0.8, 0.9, 1.0):
                Q = P.with_overrides({'fixed_mass_fraction': phi, 'mass_scaling_exponent': beta})
                self.assertAlmostEqual(engine_mass(Q, 9), P.v('engine.reference_engine_dry_mass'), places=10)

    def test_akin_equals_mref_at_845kN(self):
        self.assertAlmostEqual(engine_mass(P, 9, 'akin_scaled'), 470.0, places=10)
        self.assertAlmostEqual(akin_scale(P), 0.5643, places=4)  # JSON says 0.56: verified

    def test_dry_mass_reference_and_glow_closure(self):
        d = booster_dry_mass(P, 9)
        self.assertAlmostEqual(d.total, P.v('booster.dry_mass_at_reference'), places=8)
        v = make_vehicle(P, 9)
        self.assertAlmostEqual(v.glow(0.0), P.v('booster.glow_full_vehicle'), places=6)
        self.assertAlmostEqual(stage1_propellant_capacity(P), P.v('booster.propellant_capacity'), places=6)

    def test_no_double_counting(self):
        for n in COUNTS:
            d = booster_dry_mass(P, n)
            self.assertAlmostEqual(d.total, d.nonengine + d.engines_total + d.integration_total, places=8)
            self.assertAlmostEqual(d.nonengine, booster_dry_mass(P, 9).nonengine, places=8)

    def test_beta1_phi0_mint0_total_engine_mass_invariant(self):
        Q = P.with_overrides({'fixed_mass_fraction': 0.0, 'mass_scaling_exponent': 1.0, 'per_engine_integration_mass': 0.0})
        totals = [booster_dry_mass(Q, n).total for n in COUNTS]
        np.testing.assert_allclose(totals, totals[0], rtol=0, atol=1e-8)


class TestAtmosphere(unittest.TestCase):
    def test_us76_reference_values(self):
        # Published US76 table values (geometric altitude)
        for h, p_ref, t_ref in ((0.0, 101325.0, 288.15), (11000.0, 22699.9, 216.774),
                                (20000.0, 5529.3, 216.65), (32000.0, 889.06, 228.49),
                                (50000.0, 79.779, 270.65), (80000.0, 1.0524, 198.64)):
            rho, p, a = atmosphere(h)
            self.assertAlmostEqual(p / p_ref, 1.0, delta=2e-3, msg=f'p at {h}')
            self.assertAlmostEqual(temperature(h), t_ref, delta=0.2, msg=f'T at {h}')
        self.assertAlmostEqual(atmosphere(0.0)[0], 1.225, delta=1e-3)


class TestIntegrator(unittest.TestCase):
    def test_rk4_exponential_and_event(self):
        f = lambda t, y: [-y[0]]
        r = integrate(f, 0.0, [1.0], 0.01, 5.0, events=[Event('half', lambda t, y: y[0] - 0.5, -1)])
        self.assertEqual(r.event, 'half')
        self.assertAlmostEqual(r.t_final, math.log(2.0), places=9)

    def test_harmonic_oscillator_fourth_order(self):
        f = lambda t, y: [y[1], -y[0]]
        errs = []
        for dt in (0.1, 0.05):
            r = integrate(f, 0.0, [1.0, 0.0], dt, 10.0, record=False)
            errs.append(abs(r.y_final[0] - math.cos(10.0)))
        self.assertGreater(errs[0] / errs[1], 14.0)  # ~16 for 4th order


if __name__ == '__main__':
    unittest.main()
