#===============================================================================
# MODULE simdataacollector_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for SimDataCollector and the aggregate classes
#===============================================================================
from simprovise.core import *
import unittest

class SimUnweightedAggregateTests(unittest.TestCase):
    "Tests for unweighted data aggregate"
    def setUp(self):
        self.dc1 = datacollector.UnweightedAggregate()

    def testNoEntries(self):
        "Test: unweighted mean of no values == None" 
        self.assertEqual(self.dc1.mean(), None)

    def testOneEntry(self):
        "Test: unweighted mean of one value"
        self.dc1 += 2.5
        self.assertEqual(self.dc1.mean(), 2.5)

    def testMultipleEntries(self):
        "Test: unweighted mean of multple values"
        self.dc1 += 1
        self.dc1 += 3
        self.dc1 += 3.5
        self.assertEqual(self.dc1.mean(), 2.5)

    def testReinitialize(self):
        "Test: unweighted mean reset after initialization"
        self.dc1 += 1
        self.dc1 += 3
        self.dc1 += 4.5
        self.dc1.initialize()
        self.dc1 += 3                
        self.assertEqual(self.dc1.mean(), 3)

    def testReset(self):
        "Test: unweighted mean reset after reset - same as re-initialization"
        self.dc1 += 1
        self.dc1 += 3
        self.dc1 += 4.5
        self.dc1.reset()
        self.dc1 += 3                
        self.assertEqual(self.dc1.mean(), 3)        
        
class SimTimeWeightedAggregateTests(unittest.TestCase):
    "Tests for class TimeWeightedAggregate"
    def setUp(self):
        SimClock.initialize()
        self.dc1 = datacollector.TimeWeightedAggregate()

    def testZeroTime1(self):
        "Test: Before time starts to advance, Time-weighted mean has a value of none, regardless of added values"
        self.dc1 += 1
        self.dc1 += 55
        self.assertEqual(self.dc1.mean(), None)

    def testZeroTime2(self):
        "Test: Time-weighted values added after advancing clock do not effect mean"
        SimClock.advance_to(simtime.SimTime(100))
        self.dc1 += 1
        self.dc1 += 55
        self.assertEqual(self.dc1.mean(), 0.0)
        
    def testZeroTime3(self):
        "Test: Time-weighted mean of 0 (1 min), zero-length values and 3 (2 min) is 2"
        self.dc1 += 0
        SimClock.advance_to(simtime.SimTime(1, simtime.MINUTES))
        self.dc1 += 20
        self.dc1 += 50
        self.dc1 += 3
        SimClock.advance_to(simtime.SimTime(3, simtime.MINUTES))
        self.assertEqual(self.dc1.mean(), 2)
        
    def testOneValue(self):
        "Test: Time-weighted mean of a single value is that value"
        self.dc1 += 1
        SimClock.advance_to(simtime.SimTime(100))
        self.assertEqual(self.dc1.mean(), 1)
        
    def testTwoValues(self):
        "Test: Time-weighted mean of 0 (1 min) and 3 (2 min) is 2"
        self.dc1 += 0
        SimClock.advance_to(simtime.SimTime(1, simtime.MINUTES))
        self.dc1 += 3
        SimClock.advance_to(simtime.SimTime(3, simtime.MINUTES))
        self.assertEqual(self.dc1.mean(), 2)
        
    def testTwoValues2(self):
        "Test: Time-weighted mean works with mean() call in middle"
        self.dc1 += 0
        SimClock.advance_to(simtime.SimTime(1, simtime.MINUTES))
        x = self.dc1.mean()
        self.dc1 += 3
        SimClock.advance_to(simtime.SimTime(3, simtime.MINUTES))
        self.assertEqual(self.dc1.mean(), 2)
        
    def testReset1(self):
        "Test: Time-weighted mean after reset: if no time passes after reset, mean is None"
        self.dc1 += 0
        SimClock.advance_to(simtime.SimTime(1, simtime.MINUTES))
        self.dc1 += 3
        SimClock.advance_to(simtime.SimTime(3, simtime.MINUTES))
        self.dc1.reset()
        self.assertEqual(self.dc1.mean(), None)
        
    def testReset2(self):
        "Test: Time-weighted mean after reset: value at reset is 3, after a minute, add a 5 (and wait one more minute"
        self.dc1 += 0
        SimClock.advance_to(simtime.SimTime(1, simtime.MINUTES))
        self.dc1 += 3
        SimClock.advance_to(simtime.SimTime(3, simtime.MINUTES))
        self.dc1.reset()
        SimClock.advance_to(simtime.SimTime(4, simtime.MINUTES))
        self.dc1 += 5
        SimClock.advance_to(simtime.SimTime(5, simtime.MINUTES))
        self.assertEqual(self.dc1.mean(), 4)
        
class SimDataCollectorInitialStateTests(unittest.TestCase):
    "Tests initial state for class SimDataCollector (unweighted), SimTimeWeightedDataCollector"
    def setUp(self):
        SimClock.initialize()
        self.dc1 = datacollector.SimUnweightedDataCollector()
        self.dcTW = datacollector.SimTimeWeightedDataCollector()

    def testEntries(self):
        "Test: DataCollector (unweighted) entry count"
        self.assertEqual(self.dc1.entries(), 0)

    def testMean(self):
        "Test: DataCollector (unweighted) mean"
        self.assertEqual(self.dc1.mean(), None)

    def testMin(self):
        "Test: DataCollector (unweighted) min"
        self.assertEqual(self.dc1.min(), None)

    def testMax(self):
        "Test: DataCollector (unweighted) max"
        self.assertEqual(self.dc1.max(), None) 

    def testEntriesTW(self):
        "Test: DataCollector (unweighted) entry count"
        self.assertEqual(self.dcTW.entries(), 0)

    def testMeanTW(self):
        "Test: DataCollector (unweighted) mean"
        self.assertEqual(self.dcTW.mean(), None)

    def testMeanTW2(self):
        "Test: DataCollector (unweighted) mean - no entries, but clock advanced"
        SimClock.advance_to(simtime.SimTime(1, simtime.MINUTES))
        self.assertEqual(self.dcTW.mean(), 0)

    def testMinTW(self):
        "Test: DataCollector (unweighted) min"
        self.assertEqual(self.dcTW.min(), 0)

    def testMaxTW(self):
        "Test: DataCollector (unweighted) max"
        self.assertEqual(self.dcTW.max(), 0) 
        
class SimDataCollectorTests(unittest.TestCase):
    "Tests for class SimDataCollector (unweighted), SimTimeWeightedDataCollector"
    def setUp(self):
        SimClock.initialize()
        self.dc1 = datacollector.SimUnweightedDataCollector()
        self.dcTW = datacollector.SimTimeWeightedDataCollector()
        self.dc1.add_value(3)
        self.dc1.add_value(1)
        self.dc1.add_value(2)
        self.dcTW.add_value(1)
        SimClock.advance_to(simtime.SimTime(1))
        self.dcTW.add_value(4)
        SimClock.advance_to(simtime.SimTime(3))
        self.dcTW.add_value(100) # won't count without further clock advance

    def testEntries1(self):
        "Test: DataCollector (unweighted) entry count"
        self.assertEqual(self.dc1.entries(), 3)
        
    def testEntriesTW(self):
        "Test: DataCollector (time-weighted) entry count"
        self.assertEqual(self.dcTW.entries(), 3)

    def testMin1(self):
        "Test: DataCollector (unweighted) minimum entry"
        self.assertEqual(self.dc1.min(), 1)

    def testMinTW(self):
        "Test: DataCollector (time-weighted) minimum entry"
        self.assertEqual(self.dcTW.min(), 0)
        
    def testMax1(self):
        "Test: DataCollector (unweighted) maximum entry"
        self.assertEqual(self.dc1.max(), 3)
        
    def testMaxTW(self):
        "Test: DataCollector (time-weighted) maximum entry"
        self.assertEqual(self.dcTW.max(), 100)

    def testMean1(self):
        "Test: DataCollector (unweighted) mean entry value"
        self.assertEqual(self.dc1.mean(), 2)

    def testMeanTW(self):
        "Test: DataCollector (time-weighted) mean entry value"
        self.assertEqual(self.dcTW.mean(), 3)
        
    def testResetMean1(self):
        "Test:  after reset, unweighted data collector mean is None"
        self.dc1.reset()
        self.assertEqual(self.dc1.mean(), None)
        
    def testResetEntries1(self):
        "Test:  after reset, unweighted data collector entry count is zero"
        self.dc1.reset()
        self.assertEqual(self.dc1.entries(), 0)
        
    def testResetMax1(self):
        "Test:  after reset, unweighted data collector max is None"
        self.dc1.reset()
        self.assertEqual(self.dc1.max(), None)
        
    def testResetMin1(self):
        "Test:  after reset, unweighted data collector min is None"
        self.dc1.reset()
        self.assertEqual(self.dc1.min(), None)
        
    def testResetMeanTW(self):
        "Test:  after reset, advance 1 second, add value of 200 to weighted collector (value 100 before reset), advance 1 second.  Mean = 150"
        self.dcTW.reset()
        SimClock.advance_to(simtime.SimTime(4))
        self.dcTW.add_value(200)
        SimClock.advance_to(simtime.SimTime(5))
        self.assertEqual(self.dcTW.mean(), 150)
        
    def testResetEntriesTW(self):
        "Test:  after reset, advance 1 second, add value of 200 to weighted collector (value 100 before reset), advance 1 second.  entry count = 1"
        self.dcTW.reset()
        SimClock.advance_to(simtime.SimTime(4))
        self.dcTW.add_value(200)
        SimClock.advance_to(simtime.SimTime(5))
        self.assertEqual(self.dcTW.entries(), 1)
        
    def testResetMaxTW(self):
        "Test:  after reset, advance 1 second, add value of 200 to weighted collector (value 100 before reset), advance 1 second.  max = 200"
        self.dcTW.reset()
        SimClock.advance_to(simtime.SimTime(4))
        self.dcTW.add_value(200)
        SimClock.advance_to(simtime.SimTime(5))
        self.assertEqual(self.dcTW.max(), 200)
        
    def testResetMinTW(self):
        "Test:  after reset, advance 1 second, add value of 200 to weighted collector (value 100 before reset), advance 1 second.  min = 100"
        self.dcTW.reset()
        SimClock.advance_to(simtime.SimTime(4))
        self.dcTW.add_value(200)
        SimClock.advance_to(simtime.SimTime(5))
        self.assertEqual(self.dcTW.min(), 100)
          
class SimDataCollectionClassMethodTests(unittest.TestCase):
    "Tests for class SimDataCollector (unweighted), where the collected values are SimTimes"
    def setUp(self):
        datacollector.SimDataCollector.reinitialize()
        self.dcA = datacollector.SimUnweightedDataCollector()
        self.dcB = datacollector.SimUnweightedDataCollector()
        self.dcC = datacollector.SimTimeWeightedDataCollector()
        self.dcA.add_value(5)
        self.dcB.add_value(10)
        self.dcC.add_value(20)
        datacollector.SimDataCollector.reset_all()
 
    def testReinitialize1(self):
        "Test: After class reinitialize and creation of three data collectors, the collector list is of length 3"
        self.assertEqual(len(datacollector.SimDataCollector.collectorList), 3)

    def testReinitialize2(self):
        "Test: After class reinitialization, the collector list is of length zero"
        datacollector.SimDataCollector.reinitialize()
        self.assertEqual(len(datacollector.SimDataCollector.collectorList), 0)
        
    def testResetA(self):
        "Test:  After resetAll, all data collector A is reset"
        self.assertEqual(self.dcA.mean(),  None)
       
    def testResetB(self):
        "Test:  After resetAll, all data collector A is reset"
        self.assertEqual(self.dcB.mean(),  None)
       
    def testResetC(self):
        "Test:  After resetAll, all data collector A is reset"
        self.assertEqual(self.dcC.mean(),  None)      
       
    def testCollection(self):
        "Test:  look at class collection"
        self.dcA.add_value(5)
        means = [dc.mean() for dc in datacollector.SimDataCollector.collectorList]
        self.assertEqual(means,  [5, None, None])    
        
        
class SimTimeDataCollectionTests(unittest.TestCase):
    "Tests for class SimDataCollector (unweighted), where the collected values are SimTimes"
    def setUp(self):
        self.dc1 = datacollector.SimUnweightedDataCollector()
        self.dc1.add_value(simtime.SimTime(30, simtime.SECONDS))
        self.dc1.add_value(simtime.SimTime(15, simtime.SECONDS))
        self.dc1.add_value(simtime.SimTime(2, simtime.MINUTES))
 
    def testEntries1(self):
        "Test: DataCollector (unweighted) entry count"
        self.assertEqual(self.dc1.entries(), 3)

    def testMin(self):
        "Test: DataCollector (unweighted) minimum entry"
        self.assertEqual(self.dc1.min(), simtime.SimTime(15, simtime.SECONDS))
        
    def testMax(self):
        "Test: DataCollector (unweighted) maximum entry"
        self.assertEqual(self.dc1.max(), simtime.SimTime(2, simtime.MINUTES))
 
    def testMean(self):
        "Test: DataCollector (unweighted) mean entry value"
        self.assertEqual(self.dc1.mean(), simtime.SimTime(55, simtime.SECONDS))

def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SimUnweightedAggregateTests))
    suite.addTest(unittest.makeSuite(SimTimeWeightedAggregateTests))
    suite.addTest(unittest.makeSuite(SimDataCollectorTests))
    suite.addTest(unittest.makeSuite(SimDataCollectionClassMethodTests))
    suite.addTest(unittest.makeSuite(SimTimeDataCollectionTests))
    return suite        

        
if __name__ == '__main__':
    unittest.main()
 