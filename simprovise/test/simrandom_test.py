#===============================================================================
# MODULE simrandom_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for the simrandom module (and SimDistribution class)
#===============================================================================
from simprovise.core import simrandom, simtime, SimError
from simprovise.core.simrandom import SimDistribution
from simprovise.core.simlogging import SimLogging
from simprovise.core.simtime import SimTime, Unit as tu

import unittest, logging

class RandomInitializationTests(unittest.TestCase):
    "simrandom Initialize Tests"
    def setUp(self):
        """
        """
        SimLogging.set_level(logging.WARN)
        
    def testRunZero(self):
        "Test: Initialize(run = 0) raises"
        self.assertRaises(SimError, simrandom.initialize, 0)
        
    def testRunBelowMin(self):
        "Test: Initialize(run < min_run_number()) raises"
        run = simrandom.min_run_number() - 1
        self.assertRaises(SimError, simrandom.initialize, run)
        
    def testRunOverMax(self):
        "Test: Initialize(run > max_run_number()) raises"
        run = simrandom.max_run_number() + 1
        self.assertRaises(SimError, simrandom.initialize, run)
        
    def testStreamZero(self):
        "Test: sampling from stream zero raises"
        simrandom.initialize(1)
        with self.assertRaises(SimError):
            SimDistribution.exponential(3, streamNum=0)
        
    def testStreamOverMax(self):
        "Test: sampling from stream greater than max_streams() raises"
        simrandom.initialize(1)
        stream_num = simrandom.max_streams() + 1
        with self.assertRaises(SimError):
            SimDistribution.exponential(3, streamNum=stream_num)
        
    def testNoIdenticalStreams(self):
        "Test: confirm that the states of every PRN stream are different"
        stateset = set()
        nruns = simrandom.max_run_number()
        # This test runs for several seconds with 100 runs
        #nruns = 5
        nstreams = simrandom.max_streams()
        
        for run in range(1, nruns+1):
            simrandom.initialize(run)
            for i in range(simrandom.max_streams()):
                bg = simrandom._rng[i].bit_generator
                stateval = bg.state['state']['state']
                stateset.add(stateval)
                
        self.assertEqual(len(stateset), nruns * nstreams)
        
        
class SimDistributionTestsBase(unittest.TestCase):
    "Base class for SimDistribution Test Case"
    def setUp(self):
        SimLogging.set_level(logging.WARN)
        simrandom.initialize(1)
        
    def _run_gen(self, gen, n=10000):
        total = 0
        for i in range(n):
            total += next(gen)
        mean = total / n
        return mean
    
    
class SimDistributionSmokeTests(SimDistributionTestsBase):
    "Basic SimDistribution Tests"
        
    def testInvalidStream0(self):
        "Test: SimDistribution generator with stream 0 raises"
        self.assertRaises(SimError, SimDistribution.exponential, 42, streamNum=0)
        
    def testInvalidStreamOverMax(self):
        "Test: SimDistribution generator with stream greater than max_streams raises"
        s = simrandom.max_streams() + 1
        self.assertRaises(SimError, SimDistribution.exponential, 42, streamNum=s)
        
    def testConstant(self):
        "Test: SimDistribution.constant generator generates a constant"
        gen = SimDistribution.constant(42)
        self.assertEqual(next(gen), 42)
        
    def testExponential(self):
        "Test: SimDistribution.exponential generator"
        gen = SimDistribution.exponential(142, streamNum=100)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean, 142, delta=1.42)
        
    def testUniform(self):
        "Test: SimDistribution.uniform generator"
        gen = SimDistribution.uniform(10.0, 20.0)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean, 15, delta=0.15)
        
    def testTriangular(self):
        "Test: SimDistribution.triangular generator"
        gen = SimDistribution.triangular(10.0, 20.0, 60.0, streamNum=1000)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean, 30, delta=0.15)
        
    def testNormal(self):
        "Test: SimDistribution.normal generator with no floor"
        gen = SimDistribution.normal(10.0, 5.0, floor=None)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean, 10, delta=0.05)        
        
    def testNormalFloorZero1(self):
        "Test: SimDistribution.normal generator with default floor of zero - mean greater than mu"
        gen = SimDistribution.normal(10.0, 5.0)
        mean = self._run_gen(gen)
        self.assertGreater(mean, 10)        
        
    def testNormalFloorZero2(self):
        "Test: SimDistribution.normal generator with default floor of zero - min value is zero"
        gen = SimDistribution.normal(10.0, 5.0)
        vals = []
        for i in range(100):
            vals.append(next(gen))
        self.assertEqual(min(vals), 0.)        
        
    def testlogistic(self):
        "Test: SimDistribution.logistic generator with no floor"
        gen = SimDistribution.logistic(10.0, 5.0, floor=None)
        mean = self._run_gen(gen, 25000)
        self.assertAlmostEqual(mean, 10, delta=0.10)        
        
    def testlogisticFloorZero1(self):
        "Test: SimDistribution.logistic generator with default floor of zero - mean greater than mu"
        gen = SimDistribution.logistic(10.0, 5.0)
        mean = self._run_gen(gen)
        self.assertGreater(mean, 10)        
        
    def testlogisticFloorZero2(self):
        "Test: SimDistribution.logistic generator with default floor of zero - min value is zero"
        gen = SimDistribution.logistic(10.0, 5.0)
        vals = []
        for i in range(100):
            vals.append(next(gen))
        self.assertEqual(min(vals), 0.)
        
    def testChoice(self):
        "Test: SimDistribution.choice generator"
        gen = SimDistribution.choice((2, 4, 6))
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean, 4, delta=0.05)        
        
    def testRoundRobin(self):
        "Test: SimDistribution.round_robin generator"
        gen = SimDistribution.round_robin((2, 4, 6))
        vlist = [next(gen) for i in range(6)]
        self.assertEqual(vlist, [2, 4, 6, 2, 4, 6])        
        
    def testweibull(self):
        "Test: SimDistribution.weibull generator"
        gen = SimDistribution.weibull(1.0)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean, 1., delta=0.05)        
        
    def testpareto(self):
        "Test: SimDistribution.pareto generator"
        gen = SimDistribution.pareto(2.0)
        mean = self._run_gen(gen)
        self.assertGreater(mean, 0)        
        
    def testlognormal(self):
        "Test: SimDistribution.lognormal generator"
        gen = SimDistribution.lognormal(10.0, 2.0)
        mean = self._run_gen(gen)
        self.assertGreater(mean, 0)        
        
    def testbeta(self):
        "Test: SimDistribution.beta generator"
        gen = SimDistribution.beta(10.0, 2.0)
        mean = self._run_gen(gen)
        self.assertGreater(mean, 0)        
        
    def testgamma(self):
        "Test: SimDistribution.gamma generator"
        gen = SimDistribution.gamma(10.0, 2.0)
        mean = self._run_gen(gen)
        self.assertGreater(mean, 0)        
        
    def testgeometric(self):
        "Test: SimDistribution.geometric generator"
        gen = SimDistribution.geometric(0.4)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean, 1 / .4, delta=0.05)        
        
    def testbinomial(self):
        "Test: SimDistribution.binomial generator"
        gen = SimDistribution.binomial(5, 0.4)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean, 5 * 0.4, delta=0.05)
        
    def testwald(self):
        "Test: SimDistribution.wald generator"
        gen = SimDistribution.wald(5.0, 0.5)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean, 5.0, delta=0.05)
        
    
class SimDistributionSimTimeTests(SimDistributionTestsBase):
    "SimDistribution Tests with SimTime parameters"
        
    def testTriangular1(self):
        "Test: SimDistribution.triangular with SimTime, scalar, scalar parameters"
        gen = SimDistribution.triangular(SimTime(10.0, tu.MINUTES), 20.0, 60.0)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 30, delta=0.15)
        
    def testTriangular2(self):
        "Test: SimDistribution.triangular with scalar, scalar, SimTime parameters"
        gen = SimDistribution.triangular(10, 20, SimTime(60, tu.MINUTES))
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 30, delta=0.15)
        
    def testTriangular3(self):
        "Test: SimDistribution.triangular with mixed SimTime time unit parameters"
        gen = SimDistribution.triangular(10, SimTime(20, tu.MINUTES), SimTime(1, tu.HOURS))
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 30, delta=0.15)        
        
    def testUniform1(self):
        "Test: SimDistribution.uniform with SimTime, scalar parameters"
        gen = SimDistribution.uniform(SimTime(10.0), 30.0)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 20, delta=0.15)
        
    def testUniform2(self):
        "Test: SimDistribution.uniform with SimTime, SimTime parameters"
        gen = SimDistribution.uniform(SimTime(10.0, tu.SECONDS),
                                      SimTime(1, tu.MINUTES))
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 35, delta=0.15)
        
    def testWald1(self):
        "Test: SimDistribution.wald with SimTime, scalar parameters"
        gen = SimDistribution.wald(SimTime(1.0, tu.MINUTES), 0.5)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 1, delta=0.1)
        
    def testWald2(self):
        "Test: SimDistribution.wald with SimTime, SimTime parameters"
        gen = SimDistribution.wald(SimTime(1.0, tu.MINUTES),
                                   SimTime(30, tu.SECONDS))
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 1, delta=0.1)
        
    
class SimDistributionSimTimeTests2(SimDistributionTestsBase):
    "SimDistribution Tests with Dimensionless SimTime parameters"
    
    @classmethod
    def setUpClass(cls):
        cls.saved_base_unit = simtime._base_unit
        simtime._base_unit = None
        
    @classmethod
    def tearDownClass(cls):
        simtime._base_unit = cls.saved_base_unit
        
        
    def testTriangular1(self):
        "Test: SimDistribution.triangular with SimTime, scalar, scalar parameters"
        gen = SimDistribution.triangular(SimTime(10.0), 20.0, 60.0)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 30, delta=0.15)
        
    def testTriangular2(self):
        "Test: SimDistribution.triangular with scalar, scalar, SimTime parameters"
        gen = SimDistribution.triangular(10, 20, SimTime(60))
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 30, delta=0.15)
        
    def testTriangular3(self):
        "Test: SimDistribution.triangular with mixed SimTime time unit parameters"
        gen = SimDistribution.triangular(10, SimTime(20), SimTime(60))
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 30, delta=0.15)        
        
    def testUniform1(self):
        "Test: SimDistribution.uniform with SimTime, scalar parameters"
        gen = SimDistribution.uniform(SimTime(10.0), 30.0)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 20, delta=0.15)
        
    def testUniform2(self):
        "Test: SimDistribution.uniform with SimTime, SimTime parameters"
        gen = SimDistribution.uniform(SimTime(10.0),
                                      SimTime(60))
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 35, delta=0.15)
        
    def testWald1(self):
        "Test: SimDistribution.wald with SimTime, scalar parameters"
        gen = SimDistribution.wald(SimTime(1.0), 0.5)
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 1, delta=0.1)
        
    def testWald2(self):
        "Test: SimDistribution.wald with SimTime, SimTime parameters"
        gen = SimDistribution.wald(SimTime(1.0),
                                   SimTime(0.5))
        mean = self._run_gen(gen)
        self.assertAlmostEqual(mean.value, 1, delta=0.1)
        
        
    
class SimDistributionInvalidParameterTests(SimDistributionTestsBase):
    "SimDistribution Tests: invalid parameter values"
        
    def testexponential(self):
        "Test: SimDistribution.exponential non-numeric parameter raises"       
        self.assertRaises(SimError, SimDistribution.exponential, 'abc')
        
    def testuniform1(self):
        "Test: SimDistribution.uniform with non-numeric low parameter raises"       
        self.assertRaises(SimError, SimDistribution.uniform, 'abc', 10.0)
        
    def testuniform2(self):
        "Test: SimDistribution.uniform with non-numeric high parameter raises"       
        self.assertRaises(SimError, SimDistribution.uniform, 1.0, 'abc')
        
    def testuniform3(self):
        "Test: SimDistribution.uniform with non-numeric low and high parameters raises"       
        self.assertRaises(SimError, SimDistribution.uniform, 'q', 'abc')
        
    def testuniform4(self):
        "Test: SimDistribution.uniform with non-numeric low > high raises"       
        self.assertRaises(SimError, SimDistribution.uniform, 10, 5)
        
    def testtriangular1(self):
        "Test: SimDistribution.triangular with non-numeric low parameter raises"       
        self.assertRaises(SimError, SimDistribution.triangular, 'abc', 10.0, 11)
        
    def testtriangular2(self):
        "Test: SimDistribution.triangular with non-numeric mode parameter raises"       
        self.assertRaises(SimError, SimDistribution.triangular, 1, 'xx', 11)
        
    def testtriangular3(self):
        "Test: SimDistribution.triangular with non-numeric high parameter raises"       
        self.assertRaises(SimError, SimDistribution.triangular, 0, 10.0, 'a')
        
    def testtriangular4(self):
        "Test: SimDistribution.triangular with Low > mode raises"       
        self.assertRaises(SimError, SimDistribution.triangular, 7, 4, 10)
        
    def testtriangular5(self):
        "Test: SimDistribution.triangular with high < mode raises"       
        self.assertRaises(SimError, SimDistribution.triangular, 7, 14, 10)
        
    def testtriangular6(self):
        "Test: SimDistribution.triangular with high < mode SimTime raises"       
        low = SimTime(10, tu.SECONDS)
        mode = SimTime(1, tu.MINUTES)
        high = SimTime(50, tu.SECONDS)
        self.assertRaises(SimError, SimDistribution.triangular, low, mode, high)
        
    def testnormal1(self):
        "Test: SimDistribution.normal with non-numeric mu parameter raises"       
        self.assertRaises(SimError, SimDistribution.normal, 'abc', 10.0)
        
    def testnormal2(self):
        "Test: SimDistribution.normal with non-numeric sigma parameter raises"       
        self.assertRaises(SimError, SimDistribution.normal, 5, 'abc')
        
    def testnormal3(self):
        "Test: SimDistribution.normal with non-numeric/non-None floor parameter raises"       
        self.assertRaises(SimError, SimDistribution.normal, 5, 2, floor='a')
        
    def testweibull1(self):
        "Test: SimDistribution.weibull with non-numeric shape parameter raises"       
        self.assertRaises(SimError, SimDistribution.weibull, 'abc')
        
    def testpareto1(self):
        "Test: SimDistribution.pareto with non-numeric shape parameter raises"       
        self.assertRaises(SimError, SimDistribution.pareto, 'abc')
        
    def testlognormal1(self):
        "Test: SimDistribution.lognormal with non-numeric mu parameter raises"       
        self.assertRaises(SimError, SimDistribution.lognormal, 'abc', 10.0)
        
    def testlognormal2(self):
        "Test: SimDistribution.lognormal with non-numeric sigma parameter raises"       
        self.assertRaises(SimError, SimDistribution.lognormal, 5, 'abc')
        
    def testlognormal3(self):
        "Test: SimDistribution.lognormal with sigma = 0 raises"       
        self.assertRaises(SimError, SimDistribution.lognormal, 5, 0)
        
    def testlognormal4(self):
        "Test: SimDistribution.lognormal with sigma < 0 raises"       
        self.assertRaises(SimError, SimDistribution.lognormal, 5, -0.5)
        
    def testbeta1(self):
        "Test: SimDistribution.beta with non-numeric alpha parameter raises"       
        self.assertRaises(SimError, SimDistribution.beta, 'abc', 10.0)
        
    def testbeta2(self):
        "Test: SimDistribution.beta with non-numeric beta parameter raises"       
        self.assertRaises(SimError, SimDistribution.beta, 5, 'abc')
        
    def testbeta3(self):
        "Test: SimDistribution.beta with alpha <= 0 raises"       
        self.assertRaises(SimError, SimDistribution.beta, 0, 2)
        
    def testbeta4(self):
        "Test: SimDistribution.beta with beta <= 0 raises"       
        self.assertRaises(SimError, SimDistribution.beta, 2, -2)
        
    def testgamma1(self):
        "Test: SimDistribution.gamma with non-numeric alpha parameter raises"       
        self.assertRaises(SimError, SimDistribution.gamma, 'abc', 10.0)
        
    def testgamma2(self):
        "Test: SimDistribution.beta with non-numeric beta parameter raises"       
        self.assertRaises(SimError, SimDistribution.gamma, 5, 'abc')
        
    def testgamma3(self):
        "Test: SimDistribution.gamma with alpha < 0 raises"       
        self.assertRaises(SimError, SimDistribution.gamma, -0.1, 2)
        
    def testgamma4(self):
        "Test: SimDistribution.gamma with beta <= 0 raises"       
        self.assertRaises(SimError, SimDistribution.gamma, 2, -2)
        
    def testgeometric1(self):
        "Test: SimDistribution.geometric with non-numeric rho parameter raises"       
        self.assertRaises(SimError, SimDistribution.geometric, 'abc')
        
    def testgeometric2(self):
        "Test: SimDistribution.geometric with rho < 0 raises"       
        self.assertRaises(SimError, SimDistribution.geometric, -0.2)
        
    def testgeometric3(self):
        "Test: SimDistribution.geometric with rho > 1 raises"       
        self.assertRaises(SimError, SimDistribution.geometric, 1.2)
        
    def testlogistic1(self):
        "Test: SimDistribution.logistic with non-numeric loc parameter raises"       
        self.assertRaises(SimError, SimDistribution.logistic, 'abc', 10.0)
        
    def testlogistic2(self):
        "Test: SimDistribution.logistic with non-numeric scale parameter raises"       
        self.assertRaises(SimError, SimDistribution.logistic, 5, 'abc')
        
    def testlogistic3(self):
        "Test: SimDistribution.logistic with non-numeric/non-None floor parameter raises"       
        self.assertRaises(SimError, SimDistribution.logistic, 5, 2, floor='a')
        
    def testbinomial1(self):
        "Test: SimDistribution.binomial with non-numeric n parameter raises"       
        self.assertRaises(SimError, SimDistribution.binomial, 'abc', 0.5)
        
    def testbinomial2(self):
        "Test: SimDistribution.binomial with non-integer n parameter raises"       
        self.assertRaises(SimError, SimDistribution.binomial, 1.3, 0.5)
        
    def testbinomial3(self):
        "Test: SimDistribution.binomial with negative n parameter raises"       
        self.assertRaises(SimError, SimDistribution.binomial, -1, 0.5)
        
    def testbinomial4(self):
        "Test: SimDistribution.binomial with non-numeric rho parameter raises"       
        self.assertRaises(SimError, SimDistribution.binomial, 2, 'a')
        
    def testbinomial5(self):
        "Test: SimDistribution.binomial with rho < 0 raises"       
        self.assertRaises(SimError, SimDistribution.binomial, 2, -0.1)
        
    def testbinomial6(self):
        "Test: SimDistribution.binomial with rho > 1 raises"       
        self.assertRaises(SimError, SimDistribution.binomial, 2, 1.1)
        
    def testwald1(self):
        "Test: SimDistribution.wald with non-numeric mean parameter raises"       
        self.assertRaises(SimError, SimDistribution.wald, 'abc', 0.5)
        
    def testwald2(self):
        "Test: SimDistribution.wald with non-numeric scale parameter raises"       
        self.assertRaises(SimError, SimDistribution.wald, 2.0, 'abc')
        
    def testwald3(self):
        "Test: SimDistribution.wald with non-positive mean parameter raises"       
        self.assertRaises(SimError, SimDistribution.wald, 0.0, 1.5)
        
    def testwald3(self):
        "Test: SimDistribution.wald with non-positive scale parameter raises"       
        self.assertRaises(SimError, SimDistribution.wald, 2.0, -0.5)
       
        
def makeTestSuite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(RandomInitializationTests))
    suite.addTest(loader.loadTestsFromTestCase(SimDistributionSmokeTests))
    suite.addTest(loader.loadTestsFromTestCase(SimDistributionSimTimeTests))
    suite.addTest(loader.loadTestsFromTestCase(SimDistributionInvalidParameterTests))
    return suite


if __name__ == '__main__':
    unittest.main()