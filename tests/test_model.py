"""Numerical/physics verification. These are NOT flight-data validation."""
from dataclasses import replace
import unittest
import numpy as np
from vtvl import Design, Mission, Numerics, Vehicle, evaluate_design
from vtvl.config import G0
from vtvl.engines import booster_dry_mass_kg, engine_mass_kg
from vtvl.landing import propagate, solve_landing
from vtvl.performance import mass_and_delta_v, solve_payload


class TestMassAndPerformance(unittest.TestCase):
    def test_reference_mass_anchor_independent_of_phi(self):
        v = Vehicle()
        for phi in (0.0,0.2,0.8,1.0):
            self.assertAlmostEqual(engine_mass_kg(Design(9,phi), v), v.reference_engine_mass_kg)

    def test_linear_scaling_zero_overhead_total_mass_invariant(self):
        v = replace(Vehicle(), engine_mass_exponent=1.0, integration_mass_per_engine_kg=0.0)
        masses = [booster_dry_mass_kg(Design(n,0.0),v) for n in (1,3,9,19)]
        np.testing.assert_allclose(masses, masses[0], atol=1e-10)

    def test_reserve_reduces_payload(self):
        v,m = Vehicle(),Mission()
        a = solve_payload(25000.0,10000.0,v,m)
        b = solve_payload(25000.0,15000.0,v,m)
        self.assertTrue(a['payload_feasible'] and b['payload_feasible'])
        self.assertLess(b['payload_proxy_kg'],a['payload_proxy_kg'])

    def test_mass_and_delta_v_closure(self):
        v,m = Vehicle(),Mission()
        dry,reserve = 25000.0,11000.0
        result = solve_payload(dry,reserve,v,m)
        self.assertAlmostEqual(result['delta_v_m_s'],m.required_ideal_delta_v_m_s,places=6)
        self.assertAlmostEqual(result['liftoff_mass_kg'],dry + result['first_stage_loaded_propellant_kg']
                               + v.upper_stage_dry_kg+v.upper_stage_propellant_kg+result['payload_proxy_kg'])
        self.assertAlmostEqual(result['first_stage_loaded_propellant_kg'],
                               result['first_stage_ascent_propellant_kg']+reserve)
        self.assertLessEqual(result['liftoff_mass_kg'],v.liftoff_mass_cap_kg+1e-6)

    def test_invalid_design(self):
        for kwargs in ({'engine_count':0},{'min_throttle':1.1},{'fixed_engine_mass_fraction':-0.1}):
            with self.assertRaises(ValueError):
                Design(**kwargs)


class TestLanding(unittest.TestCase):
    def test_zero_thrust_ballistic_limit(self):
        d,v,m=Design(),Vehicle(),Mission()
        p=propagate(d,v,m,Numerics(physics='analytic'),1,2.0,3.0,0.0)
        self.assertAlmostEqual(p['h_final'],m.terminal_entry_altitude_m-d.terminal_entry_speed_m_s*5-0.5*G0*25)
        self.assertAlmostEqual(p['v_final'],-d.terminal_entry_speed_m_s-G0*5)
        self.assertAlmostEqual(p['used'],0.0)

    def test_closed_form_matches_independent_ode(self):
        d,v,m = Design(),Vehicle(),Mission()
        num=Numerics(physics='analytic',rtol=1e-10,atol=1e-11,max_step_s=0.05)
        p=propagate(d,v,m,num,1,2.0,10.0,0.8,samples=101)
        q=propagate(d,v,m,num,1,2.0,10.0,0.8,samples=101,force_numeric=True)
        np.testing.assert_allclose(p['h'],q['h'],atol=2e-7)
        np.testing.assert_allclose(p['v'],q['v'],atol=2e-8)
        np.testing.assert_allclose(p['mass'],q['mass'],atol=2e-7)

    def test_fuel_and_margin_mass_balance(self):
        d,v,m,num=Design(),Vehicle(),Mission(),Numerics(physics='analytic')
        p=propagate(d,v,m,num,1,2.0,10.0,0.8)
        expected=0.8*v.total_sl_thrust_n/d.engine_count/(v.landing_isp_s*G0)*10
        self.assertAlmostEqual(p['used'],expected)
        self.assertAlmostEqual(p['mass'][0]-p['mass'][-1],expected)
        self.assertAlmostEqual(p['loaded'],(1+m.landing_margin_fraction)*expected+m.trapped_residual_kg)
        self.assertAlmostEqual(p['touchdown_propellant'],m.landing_margin_fraction*expected+m.trapped_residual_kg)

    def test_cannot_hover_does_not_mean_cannot_land(self):
        d,v,m=Design(3),Vehicle(),Mission()
        num=Numerics(physics='analytic',multistarts=3)
        result=solve_landing(d,v,m,num)
        self.assertTrue(result.feasible)
        final_mass=booster_dry_mass_kg(d,v)+result.touchdown_propellant_kg
        self.assertGreater(d.min_throttle*v.total_sl_thrust_n/d.engine_count/(final_mass*G0),1.0)
        self.assertLess(abs(result.final_altitude_error_m),0.01)
        self.assertLess(abs(result.final_velocity_error_m_s),0.01)

    def test_throttle_feasible_set_monotonicity(self):
        # Lower min throttle must admit any existing higher-min-throttle control.
        v,m,num=Vehicle(),Mission(),Numerics(physics='analytic',multistarts=4)
        d=Design(5,min_throttle=0.6)
        high=solve_landing(d,v,m,num)
        low=solve_landing(replace(d,min_throttle=0.2),v,m,num)
        self.assertTrue(high.feasible and low.feasible)
        self.assertLessEqual(low.burn_propellant_kg,high.burn_propellant_kg+0.1)

    def test_drag_solution_independent_tight_reintegration(self):
        d,v,m=Design(),Vehicle(),Mission()
        num=Numerics(multistarts=3)
        result=solve_landing(d,v,m,num)
        self.assertTrue(result.feasible)
        fine=replace(num,rtol=1e-10,atol=1e-11,max_step_s=0.05)
        p=propagate(d,v,m,fine,result.active_engines,result.coast_s,result.burn_s,result.throttle,samples=1001)
        self.assertLess(abs(p['h_final']),0.01)
        self.assertLess(abs(p['v_final']-m.touchdown_velocity_m_s),0.005)
        self.assertLessEqual(p['peak_proper_g'],m.max_landing_proper_accel_g+1e-5)

    def test_one_engine_high_minimum_throttle_not_silently_accepted(self):
        row=evaluate_design(Design(1,min_throttle=0.6),numerics=Numerics(physics='analytic'))
        self.assertFalse(row['landing_feasible'])
        self.assertTrue(np.isnan(row['payload_proxy_kg']))

    def test_drag_opposes_fall(self):
        # At identical control and initial mass, drag leaves the coast higher/slower.
        d,v,m=Design(),Vehicle(),Mission()
        p=propagate(d,v,m,Numerics(physics='analytic'),1,2.0,10.0,0.8)
        q=propagate(d,v,m,Numerics(physics='drag'),1,2.0,10.0,0.8)
        self.assertGreater(q['ignition_h'],p['ignition_h'])


if __name__ == '__main__':
    unittest.main()
