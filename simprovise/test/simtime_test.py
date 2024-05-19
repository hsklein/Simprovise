#===============================================================================
# MODULE simtime_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for SimTime class
#===============================================================================
from simprovise.core import *

import unittest

class SimTimeTests(unittest.TestCase):
    "Tests for class SimTime"
    def setUp(self):
        self.ti_30secs = simtime.SimTime(30, simtime.SECONDS)
        self.ti_120secs = simtime.SimTime(120, simtime.SECONDS)
        self.ti_3600secs = simtime.SimTime(3600, simtime.SECONDS)
        self.ti_2mins = simtime.SimTime(2, simtime.MINUTES)
        self.ti_1hr = simtime.SimTime(1, simtime.HOURS)

    def testAssign1(self):
        "Test: Assignment of invalid 3 for units raises SimException error"
        self.assertRaises(simexception.SimError, lambda: simtime.SimTime(1, 3))

    # 1/4/2012 - negative time intervals should be OK (needed for statistical calculations on time intervals)
    #def testAssign2(self):
    #    "Test: Assignment of negative integer value raises SimException error"
    #    self.assertRaises(simexception.Error, lambda: simtime.SimTime(-1, simtime.HOURS))

    def testAssign3(self):
        "Test: Assignment from another SimTime"
        self.assertEqual(self.ti_2mins, simtime.SimTime(self.ti_2mins))

    def testAssign4(self):
        "Test: Assignment from another SimTime, no unit argument - units are preserved from original"
        self.assertEqual(self.ti_2mins.units, simtime.SimTime(self.ti_2mins).units)

    def testAssign5(self):
        "Test: Assignment from another SimTime, HOUR unit argument - units are preserved from original"
        self.assertEqual(self.ti_2mins.units, simtime.SimTime(self.ti_2mins, simtime.HOURS).units)

    def testConvert1(self):
        "Test:  120 seconds converted to minutes, units is MINUTES"
        self.assertEqual(self.ti_120secs.to_units(simtime.MINUTES).units, simtime.MINUTES)

    def testConvert2(self):
        "Test:  120 seconds converted to minutes, value is 2"
        self.assertEqual(self.ti_120secs.to_units(simtime.MINUTES).value, 2)

    def testConvert3(self):
        "Test:  1 hour converted to minutes, units is MINUTES"
        self.assertEqual(self.ti_1hr.to_units(simtime.MINUTES).units, simtime.MINUTES)

    def testConvert4(self):
        "Test: 1 hour converted to minutes, value is 60"
        self.assertEqual(self.ti_1hr.to_units(simtime.MINUTES).value, 60)

    def testConvert5(self):
        "Test: 1 hour converted to seconds, value is 3600"
        self.assertEqual(self.ti_1hr.to_units(simtime.SECONDS).value, 3600)

    def testConvert6(self):
        "Test: conversion to invalid units raises an error"
        self.assertRaises(SimError, lambda: self.ti_1hr.to_units(5))

    def testConvert7(self):
        "Test: toSeconds() conversion"
        self.assertEqual(self.ti_1hr.to_seconds().value, 3600)

    def testConvert8(self):
        "Test: toMinutes() conversion"
        self.assertEqual(self.ti_1hr.to_minutes().value, 60)

    def testConvert9(self):
        "Test: toHours() conversion"
        self.assertEqual(self.ti_3600secs.to_hours().value, 1)

    def testConvert10(self):
        "Test: toHours() conversion, units"
        self.assertEqual(self.ti_3600secs.to_hours().units, simtime.HOURS)

    def testAdd1(self):
        "Test: 30 seconds + 120 seconds = 150 seconds"
        self.assertEqual(self.ti_30secs + self.ti_120secs, simtime.SimTime(150, simtime.SECONDS))
        
    def testAdd2(self):
        "Test: 30 seconds + 120 seconds = 2.5 minutes"
        self.assertEqual(self.ti_30secs + self.ti_120secs, simtime.SimTime(2.5, simtime.MINUTES))
         
    def testAdd3(self):
        "Tests that 30 seconds + 120 seconds != 151 seconds"
        self.assertNotEqual(self.ti_30secs + self.ti_120secs, simtime.SimTime(151, simtime.SECONDS))
        
    def testAdd4(self):
        "Test: 30 seconds + 2 minutes = 2.5 minutes"
        self.assertEqual(self.ti_30secs + self.ti_2mins, simtime.SimTime(2.5, simtime.MINUTES))
        
    def testAdd4a(self):
        "Test: 2 minutes + 30 seconds = 2.5 minutes"
        self.assertEqual(self.ti_2mins + self.ti_30secs, simtime.SimTime(2.5, simtime.MINUTES))
         
    def testAdd5(self):
        "Test: 30 seconds + 90 (no units) = 120 seconds"
        self.assertEqual(self.ti_30secs + 90, self.ti_120secs)
               
    def testAdd6a(self):
        "Test: 30 seconds + 90 (no units) = 2 minutes"
        self.assertEqual(self.ti_30secs + 90, self.ti_2mins)
               
    def testAdd6b(self):
        "Test: 90 (no units) + 30 seconds = 2 minutes"
        self.assertEqual(90 + self.ti_30secs, self.ti_2mins)
          
    def testSub1(self):
        "Test: 2 minutes - 90 seconds = 30 seconds"
        self.assertEqual(self.ti_2mins - simtime.SimTime(90, simtime.SECONDS), self.ti_30secs)
         
    def testSub2(self):
        "Test: 30 seconds - 10 (no units) == 20 seconds"
        self.assertEqual(self.ti_30secs - 10, simtime.SimTime(20, simtime.SECONDS))
          
    def testSub3(self):
        "Test: 30 seconds - 120 seconds == -90 seconds"
        self.assertEqual(self.ti_30secs -  self.ti_120secs, simtime.SimTime(-90, simtime.SECONDS))
         
    def testSub4(self):
        "Test: 2 minutes - 1 (no units) = 1 minute"
        self.assertEqual(self.ti_2mins - 1, SimTime(1, simtime.MINUTES))
         
    def testSub5(self):
        "Test: 1 hour - 0 (no units) = 60 minutes"
        self.assertEqual(self.ti_1hr - 0, SimTime(60, simtime.MINUTES))

    def testMultiply1(self):
        "Test: 30 seconds * 4 = 120 seconds"
        self.assertEqual(self.ti_30secs * 4, self.ti_120secs)

    def testMultiply2(self):
        "Test: 4* 30 seconds = 120 seconds"
        self.assertEqual(4 * self.ti_30secs, self.ti_120secs)

    def testDivide(self):
        "Test: 120 seconds / 4 = 30 seconds"
        self.assertEqual(self.ti_120secs / 4, self.ti_30secs)
        
    def testCompare1(self):
        "Test: 120 seconds == 2 minutes"
        self.assertEqual(self.ti_120secs, self.ti_2mins)
         
    def testCompare2(self):
        "Test: 3600 seconds == 1 hour"
        self.assertEqual(self.ti_3600secs, self.ti_1hr)
         
    def testCompare2a(self):
        "Test: 1 hour == 3600 seconds"
        self.assertEqual(self.ti_1hr, self.ti_3600secs )
        
    def testCompare3(self):
        "Test: 30 seconds < 2 minutes"
        self.assertTrue(self.ti_30secs < self.ti_2mins)    
        
    def testCompare3a(self):
        "Test: 2 minutes > 30 seconds"
        self.assertTrue(self.ti_2mins > self.ti_30secs)
        
    def testCompare4(self):
        "Test: 3600 seconds > 2 minutes"
        self.assertTrue(self.ti_3600secs > self.ti_2mins)
       
    def testCompare5(self):
        "Test: 1 hour > 2 minutes"
        self.assertTrue(self.ti_1hr > self.ti_2mins)
       
    def testCompare5a(self):
        "Test: 2 minutes < 1 hour"
        self.assertTrue( self.ti_2mins < self.ti_1hr)
        
    def testCompare6a(self):
        "Test: SimTime < integer value raises a simexception.Error"
        self.assertRaises(simexception.SimError, lambda: self.ti_30secs < 40)
        
    def testCompare6b(self):
        "Test: integer value  == SimTime raises a simexception.Error"
        self.assertRaises(simexception.SimError, lambda: 30 == self.ti_30secs)
        
    def testHash1(self):
        "Test: 120 seconds and 2 minutes hash to same value"
        testDict = {}
        testDict[ self.ti_2mins ] = 42
        self.assertEqual(testDict[self.ti_120secs], 42)
        
    def testHash2(self):
        "Test: five different time values result in five dictionary entries"
        testDict = {}
        ti1 = simtime.SimTime(0, simtime.SECONDS)
        ti2 = simtime.SimTime(0.1, simtime.SECONDS)
        ti3 = simtime.SimTime(1, simtime.SECONDS)
        ti4 = simtime.SimTime(1, simtime.MINUTES)
        ti5 = simtime.SimTime(1, simtime.HOURS)
        testDict[ ti1 ] = 1
        testDict[ ti2 ] = 2
        testDict[ ti3 ] = 3
        testDict[ ti4 ] = 4
        testDict[ ti5 ] = 5
        self.assertEqual(len(testDict), 5)
        
    def testScalarComparison(self):
        "Test: comparing SimTime to scalar value raises when base time unit is not None"
        t1 = SimTime(2, simtime.MINUTES)
        self.assertRaises(simexception.SimError, lambda: t1 == 2)
        
    def testScalar(self):
        "Test to_scalar for various simtime base units"
        if simtime.base_unit() == simtime.SECONDS:
            self.assertEqual(self.ti_1hr.to_scalar(), 3600)
        elif simtime.base_unit() == simtime.MINUTES:
            self.assertEqual(self.ti_1hr.to_scalar(), 60)
        else:
            self.assertEqual(self.ti_1hr.to_scalar(), 1)
   

class SimMinuteBaseTimeTests(SimTimeTests):
    """
    Run the same tests as SimTimeTests, but with base unit in MINUTES.
    Also check default unit values.
    """
    @classmethod
    def setUpClass(cls):
        cls.baseunit = simtime.base_unit()
        simtime.set_base_unit(simtime.MINUTES)
       
    @classmethod
    def tearDownClass(cls):
        simtime.set_base_unit(cls.baseunit)
                
    def testDefaultUnit(self):
        "Test: That default unit is base unit"
        self.assertEqual(self.ti_2mins, simtime.SimTime(2))

class SimHourBaseTimeTests(SimTimeTests):
    """
    Run the same tests as SimTimeTests, but with base unit in HOURS.
    Also check default unit values.
    """
    @classmethod
    def setUpClass(cls):
        cls.baseunit = simtime.base_unit()
        simtime.set_base_unit(simtime.HOURS)
       
    @classmethod
    def tearDownClass(cls):
        simtime.set_base_unit(cls.baseunit)
        
    def testDefaultUnit(self):
        "Test: That default unit is base unit"
        self.assertEqual(self.ti_1hr, simtime.SimTime(1))

class SimDimensionlessBaseTimeTests(unittest.TestCase):
    """
    Run the same tests as SimTimeTests, but with base unit in HOURS.
    Also check default unit values.
    """
    def setUp(self):
        self.savedbaseunit = simtime.base_unit()
        simtime.set_base_unit(simtime.MINUTES)
        self._ti_3mins = SimTime(3)
        simtime.set_base_unit(None)
        self._ti_3_none = SimTime(3)        
        
    def tearDown(self):
        simtime.set_base_unit(self.savedbaseunit)
        
    def testDimensionlessEquals(self):
        "Equality Test: That default unit is None"
        self.assertEqual(self._ti_3_none, SimTime(3, None))
        
    def testDimensionlessEqualsB(self):
        "Equality Test: That when base unit is dimensionless, scalar comparison is allowed"
        self.assertEqual(self._ti_3_none, 3)
        
    def testDimensionlessAddition(self):
        "Equality Test: That when base unit is dimensionless, scalar addition is allowed"
        self.assertEqual(self._ti_3_none + 3, 6)
        
    def testDimensionlessAddition2(self):
        "Equality Test: That when base unit is dimensionless, scalar addition is allowed"
        self.assertEqual(3 + self._ti_3_none, 6)
                
    def testDimensionlessSubtraction(self):
        "Equality Test: That when base unit is dimensionless, scalar subtraction is allowed"
        self.assertEqual(self._ti_3_none - 2, 1)
                
    def testDimensionlessMultiplication(self):
        "Equality Test: That when base unit is dimensionless, scalar multiplication is allowed"
        self.assertEqual(self._ti_3_none * 5, 15)
                
    def testDimensionlessMultiplication2(self):
        "Equality Test: That when base unit is dimensionless, scalar multiplication is allowed"
        self.assertEqual(self._ti_3_none * 5, SimTime(15))
                
    def testDimensionlessMultiplication3(self):
        "Equality Test: That when base unit is dimensionless, scalar multiplication is allowed"
        self.assertEqual(5 * self._ti_3_none, SimTime(15))
                
    def testDimensionlessDivision(self):
        "Equality Test: That when base unit is dimensionless, scalar division is allowed"
        self.assertEqual(self._ti_3_none / 3, 1)
                
    def testDimensionlessDivision2(self):
        "Equality Test: That when base unit is dimensionless, scalar division is allowed"
        self.assertEqual(self._ti_3_none / 3, SimTime(1))
                
    def testDimensionlessDivisio3(self):
        "Equality Test: That when base unit is dimensionless, scalar division is allowed"
        self.assertEqual(12 / self._ti_3_none, SimTime(4))
        
    def testDimensionedAdditionRaises(self):
        "Using a dimensioned SimTime raises when base unit is dimensionless"
        t1 = SimTime()
        self.assertRaises(SimError, lambda: t1 + self._ti_3mins)
        
    def testDimensionedAdditionRaisesB(self):
        "Dimensioned SmTime use raises in either direction "
        t1 = SimTime()
        self.assertRaises(SimError, lambda: self._ti_3mins + t1)
        
    def testDimensionedComparisonRaises(self):
        "Dimensioned SimTime comparison raises when base unit is dimensionless"
        t1 = SimTime()
        self.assertRaises(SimError, lambda: t1 == self._ti_3mins)
        
    def testDimensionedComparisonRaisesB(self):
        "Dimensioned SimTime use raises in either direction when base unit is dimensionless"
        t1 = SimTime()
        self.assertRaises(SimError, lambda: self._ti_3mins == t1)
        
    def testDimensionedComparisonRaisesC(self):
        "Dimensioned SimTime use raises in either direction when base unit is dimensionless"
        t1 = SimTime(22)
        self.assertRaises(SimError, lambda: self._ti_3mins == t1)
        
    def testToScalar(self):
        "Test to_scalar for dimensionless SimTime"
        self.assertEqual(self._ti_3_none.to_scalar(), 3)
    
    
        
def makeTestSuite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(SimTimeTests))
    suite.addTest(loader.loadTestsFromTestCase(SimMinuteBaseTimeTests))
    suite.addTest(loader.loadTestsFromTestCase(SimHourBaseTimeTests))
    suite.addTest(loader.loadTestsFromTestCase(SimDimensionlessBaseTimeTests))
    return suite
        
if __name__ == '__main__':
    unittest.main()
    