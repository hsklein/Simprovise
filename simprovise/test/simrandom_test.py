#===============================================================================
# MODULE simrandom_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for the simrandom module (and SimDistribution class)
#===============================================================================
from simprovise.core import *

import unittest

class RandomInitializationTests(unittest.TestCase):
    "simrandom Initialize Tests"
    def setUp(self):
        """
        """
    def testRunZero(self):
        "Test: Initialize(run = 0) raises"
        self.assertRaises(simexception.SimError, simrandom.initialize, 0)
        
    def testRunBelowMin(self):
        "Test: Initialize(run < min_run_number()) raises"
        run = simrandom.min_run_number() - 1
        self.assertRaises(simexception.SimError, simrandom.initialize, run)
        
    def testRunOverMax(self):
        "Test: Initialize(run > max_run_number()) raises"
        run = simrandom.max_run_number() + 1
        self.assertRaises(simexception.SimError, simrandom.initialize, run)
        
    def testStreamZero(self):
        "Test: sampling from stream zero raises"
        simrandom.initialize(1)
        with self.assertRaises(simexception.SimError):
            SimDistribution.exponential(3, streamNum=0)
        
    def testStreamOverMax(self):
        "Test: sampling from stream zero raises"
        simrandom.initialize(1)
        stream_num = simrandom.max_streams() + 1
        with self.assertRaises(simexception.SimError):
            SimDistribution.exponential(3, streamNum=stream_num)
        


def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RandomInitializationTests))


if __name__ == '__main__':
    unittest.main()