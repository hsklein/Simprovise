#===============================================================================
# MODULE simstats_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for core.stats functions
#===============================================================================
from simprovise.core import SimError
from simprovise.core import stats as simstats
from simprovise.core.stats import CIType
import unittest
import numpy as np

_NAN = float('nan')

class ConfidenceIntervalTests(unittest.TestCase):
    "Tests for confidence interval functions"
    def setUp(self):
        # example from https://statisticalpoint.com/confidence-interval-for-median/
        self.vals = (8, 11, 12, 13, 15, 17, 19, 20, 21, 21, 22, 23, 25, 26, 28)
        self.expected_t_95ci = (15.46, 22.01)
        self.expected_norm_95ci = (15.74, 21.72)
        self.expected_quantile50_95ci = (13, 23)

    def testT_CI1(self):
        "Test: t_confidence_interval() returns expected values"
        ci = simstats.t_confidence_interval(self.vals, 0.95)
        for i in range(1):
            with self.subTest():
                self.assertAlmostEqual(ci[i], self.expected_t_95ci[i], 2)

    def testT_CI2(self):
        "Test: t_confidence_interval() and confidence_interval(CIType.T) return same values"
        self.assertEqual(simstats.t_confidence_interval(self.vals, 0.95),
                         simstats.confidence_interval(CIType.T, self.vals, 0.95))

    def testT_Norm1(self):
        "Test: norm_confidence_interval() returns expected values"
        ci = simstats.norm_confidence_interval(self.vals, 0.95)
        for i in range(1):
            with self.subTest():
                self.assertAlmostEqual(ci[i], self.expected_norm_95ci[i], 2)

    def testT_Norm2(self):
        "Test: norm_confidence_interval() and confidence_interval(CIType.NORMAL) return same values"
        self.assertEqual(simstats.norm_confidence_interval(self.vals, 0.95),
                         simstats.confidence_interval(CIType.NORMAL, self.vals, 0.95))


    def testQuantile_CI1(self):
        "Test: quantile_confidence_interval() returns expected values"
        ci = simstats.quantile_confidence_interval(self.vals, 0.5, 0.95)
        for i in range(1):
            with self.subTest(i=i):
                self.assertAlmostEqual(ci[i], self.expected_quantile50_95ci[i], 2)

    def testQuantile_CI2(self):
        "Test: quantile_confidence_interval() and confidence_interval(CIType.QUANTILE) return same values"
        self.assertEqual(simstats.quantile_confidence_interval(self.vals, 0.5, 0.95),
                         simstats.confidence_interval(CIType.QUANTILE, self.vals, 0.95,
                                                      quantile=0.5))
       
    def testInvalidCITypeRaises(self):
        "confidence_interval raises with invalid CIType"
        with self.assertRaises(SimError):
            simstats.confidence_interval(2, self.vals, 0.95)
       
    def testInvalidConfidenceLevelRaises(self):
        "confidence_interval raises with invalid confidence level"
        citypes = (CIType.T, CIType.NORMAL, CIType.QUANTILE)
        invalid_levels = (0.0, 1.0, -1, 'a', None)
        for citype in citypes:
            for clevel in invalid_levels:
                with self.subTest():                    
                    with self.assertRaises(Exception):
                        simstats.confidence_interval(citype, self.vals, clevel,
                                                     quantile=0.5)
       
    def testInvalidQuantileRaises(self):
        "Quantile confidence_interval raises with invalid quantile"
        invalid_quantiles = (0.0, 1.0, -1, 'a', None)
        for q in invalid_quantiles:
            with self.subTest():                    
                with self.assertRaises(Exception):
                    simstats.confidence_interval(CIType.QUANTILE, self.vals,
                                                 0.9, quantile=q)
        
class WeightedPercentileTests(unittest.TestCase):
    "Tests for weighted_percentiles function"

    def test_unweighted1(self):
        "Test: weighted_percentiles for equal weights vs np.percentile"
        vals = (8, 11, 12, 13, 15, 17, 19, 20, 21, 21, 22, 23, 25, 26, 28,
                  5, 71, 33, 36, 25, 22, 54, 42, 54, 61, 12, 16, 6, 45, 36, 18)
        vals = sorted(vals)
        weights = [1] * len(vals)
        pcts = simstats.weighted_percentiles(vals, weights)
        for i in range(101):
            with self.subTest(i=i):
                self.assertAlmostEqual(pcts[i], np.percentile(vals, i))
                
    def test_weighted(self):
        "Test weighted percentile with weights"
        vals = (2, 3, 7, 8, 11)
        weights = (1, 2, 1, 2, 3)
        test_percentiles = [1, 25, 50, 75, 99, 100]
        expected_values = [2.05, 3.67, 7.33, 8.9, 10.92, 11.0]
        pcts = simstats.weighted_percentiles(vals, weights)
        for i, p in enumerate(test_percentiles):
            with self.subTest(percentile = p):
                self.assertAlmostEqual(pcts[p], expected_values[i], 2)
                
    def test_weighted_onevalue1(self):
        "Test: weighted_percentiles() with only one value returns that value for all percentiles"
        vals = (42, )
        weights = (2, )
        pcts = simstats.weighted_percentiles(vals, weights)
        test_percentiles = [1, 25, 50, 75, 99, 100]
        for p in test_percentiles:
            with self.subTest(percentile = p):
                self.assertEqual(pcts[p], vals[0])
                
    def test_weighted_onevalue2(self):
        "Test: weighted_percentiles() with only one value with a non-zero weight returns that value for all percentiles"
        vals = (27, 42, 3)
        weights = (0, 2, 0)
        pcts = simstats.weighted_percentiles(vals, weights)
        test_percentiles = [1, 25, 50, 75, 99, 100]
        for p in test_percentiles:
            with self.subTest(percentile = p):
                self.assertEqual(pcts[p], 42)
                
    def test_weighted_zerovalues1(self):
        "Test: weighted_percentiles() with no values returns NaN for all percentiles"
        vals = []
        weights = []
        pcts = simstats.weighted_percentiles(vals, weights)
        test_percentiles = [1, 25, 50, 75, 99, 100]
        for p in test_percentiles:
            with self.subTest(percentile = p):
                self.assertTrue(np.isnan(pcts[p]))
                
    def test_weighted_zerovalues2(self):
        "Test: weighted_percentiles() with no values with a non-zero weight returns NaN for all percentiles"
        vals = (27, 42, 3)
        weights = (0, 0, 0)
        pcts = simstats.weighted_percentiles(vals, weights)
        test_percentiles = [1, 25, 50, 75, 99, 100]
        for p in test_percentiles:
            with self.subTest(percentile = p):
                self.assertTrue(np.isnan(pcts[p]))
            
    def test_negative_weight_raises(self):
        "Test: weighted_percentiles() raises a SimError if any weight < 0"
        vals = (27, 42, 3)
        weights = (2, 1, -.02)
        with self.assertRaises(SimError):
            simstats.weighted_percentiles(vals, weights)
            
    def test_different_lengths_raises(self):
        "Test: weighted_percentiles() raises a SimError if the number of values does not match the number of weights"
        vals = (27, 42, 3)
        weights = (2, 1)
        with self.assertRaises(SimError):
            simstats.weighted_percentiles(vals, weights)
        
        
    
    
        
def makeTestSuite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(ConfidenceIntervalTests))
    suite.addTest(loader.loadTestsFromTestCase(WeightedPercentileTests))
    return suite
        
if __name__ == '__main__':
    unittest.main()
    