#===============================================================================
# MODULE simdataacollector_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for SimDataCollector and the aggregate classes
#===============================================================================
from simprovise.core.simclock import SimClock
from simprovise.core import simtime, datacollector
from simprovise.core.simtime import Unit as tu
from simprovise.core.model import SimModel
from simprovise.modeling.location import SimLocation
import unittest

        
class SimDataCollectorInitialStateTests(unittest.TestCase):
    "Tests initial state for class SimDataCollector (unweighted), SimTimeWeightedDataCollector"
    def setUp(self):
        SimClock.initialize()
        loc = SimLocation("Test")
        self.dc1 = datacollector.SimUnweightedDataCollector(loc, "Test1", int)
        self.dcTW = datacollector.SimTimeWeightedDataCollector(loc, "Test2", int)
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimModel.model().clear_registry_partial()

    def testEntries(self):
        "Test: DataCollector (unweighted) entry count"
        self.assertEqual(self.dc1.entries(), 0)

    def testEntriesTW(self):
        "Test: DataCollector (unweighted) entry count"
        self.assertEqual(self.dcTW.entries(), 0)
        
class SimDataCollectorTests(unittest.TestCase):
    "Tests for class SimDataCollector (unweighted), SimTimeWeightedDataCollector"
    def setUp(self):
        SimClock.initialize()
        loc = SimLocation("Test")
        self.dc1 = datacollector.SimUnweightedDataCollector(loc, "Test1", int)
        self.dcTW = datacollector.SimTimeWeightedDataCollector(loc, "Test2", int)
        self.dc1.add_value(3)
        self.dc1.add_value(1)
        self.dc1.add_value(2)
        self.dcTW.add_value(1)
        SimClock.advance_to(simtime.SimTime(1))
        self.dcTW.add_value(4)
        SimClock.advance_to(simtime.SimTime(3))
        self.dcTW.add_value(100) # won't count without further clock advance
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimModel.model().clear_registry_partial()

    def testEntries1(self):
        "Test: DataCollector (unweighted) entry count"
        self.assertEqual(self.dc1.entries(), 3)
        
    def testEntriesTW(self):
        "Test: DataCollector (time-weighted) entry count"
        self.assertEqual(self.dcTW.entries(), 3)
        
    def testResetEntries1(self):
        "Test:  after reset, unweighted data collector entry count is zero"
        self.dc1.reset()
        self.assertEqual(self.dc1.entries(), 0)
        
    def testResetEntriesTW(self):
        "Test:  after reset, advance 1 second, add value of 200 to weighted collector (value 100 before reset), advance 1 second.  entry count = 1"
        self.dcTW.reset()
        SimClock.advance_to(simtime.SimTime(4))
        self.dcTW.add_value(200)
        SimClock.advance_to(simtime.SimTime(5))
        self.assertEqual(self.dcTW.entries(), 1)
    
          
class SimDataCollectionClassMethodTests(unittest.TestCase):
    "Tests for class SimDataCollector (unweighted), where the collected values are SimTimes"
    def setUp(self):
        loc = SimLocation("Test")
        # Since SimLocations create their own data collectors, reinitialize
        # here so that only dcA-C are in the list
        datacollector.SimDataCollector.reinitialize()
        self.dcA = datacollector.SimUnweightedDataCollector(loc, "Test1", int)
        self.dcB = datacollector.SimUnweightedDataCollector(loc, "Test2", int)
        self.dcC = datacollector.SimTimeWeightedDataCollector(loc, "Test3", int)
        self.dcA.add_value(5)
        self.dcB.add_value(10)
        self.dcC.add_value(20)
        datacollector.SimDataCollector.reset_all()
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimModel.model().clear_registry_partial()
 
    def testReinitialize1(self):
        "Test: After class reinitialize and creation of three data collectors, the collector list is of length 3"
        self.assertEqual(len(datacollector.SimDataCollector.collectorList), 3)

    def testReinitialize2(self):
        "Test: After class reinitialization, the collector list is of length zero"
        datacollector.SimDataCollector.reinitialize()
        self.assertEqual(len(datacollector.SimDataCollector.collectorList), 0)
        
    def testResetA(self):
        "Test:  After resetAll, data collector A has zero entries"
        self.assertEqual(self.dcA.entries(),  0)
       
    def testResetB(self):
        "Test:  After resetAll, data collector B has zero entries"
        self.assertEqual(self.dcB.entries(),  0)
       
    def testCollection(self):
        "Test:  look at class collection"
        self.dcA.add_value(5)
        entries = [dc.entries() for dc in datacollector.SimDataCollector.collectorList]
        self.assertEqual(entries,  [1, 0, 0])    
        
        
class SimTimeDataCollectionTests(unittest.TestCase):
    "Tests for class SimDataCollector (unweighted), where the collected values are SimTimes"
    def setUp(self):
        loc = SimLocation("Test")
        self.dc1 = datacollector.SimUnweightedDataCollector(loc, "Test1", simtime.SimTime)
        self.dc1.add_value(simtime.SimTime(30, tu.SECONDS))
        self.dc1.add_value(simtime.SimTime(15, tu.SECONDS))
        self.dc1.add_value(simtime.SimTime(2, tu.MINUTES))
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimModel.model().clear_registry_partial()
 
    def testEntries1(self):
        "Test: DataCollector (unweighted) entry count"
        self.assertEqual(self.dc1.entries(), 3)


def makeTestSuite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(SimDataCollectorTests))
    suite.addTest(loader.loadTestsFromTestCase(SimDataCollectionClassMethodTests))
    suite.addTest(loader.loadTestsFromTestCase(SimTimeDataCollectionTests))
    return suite        

        
if __name__ == '__main__':
    unittest.main()
 