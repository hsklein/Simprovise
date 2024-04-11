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
        self.assertEqual(self.ti_2mins.getUnits(), simtime.SimTime(self.ti_2mins).getUnits())

    def testAssign5(self):
        "Test: Assignment from another SimTime, HOUR unit argument - units are preserved from original"
        self.assertEqual(self.ti_2mins.getUnits(), simtime.SimTime(self.ti_2mins, simtime.HOURS).getUnits())

    def testConvert1(self):
        "Test:  120 seconds converted to minutes, units is MINUTES"
        self.assertEqual(self.ti_120secs.toUnits(simtime.MINUTES).units, simtime.MINUTES)

    def testConvert2(self):
        "Test:  120 seconds converted to minutes, value is 2"
        self.assertEqual(self.ti_120secs.toUnits(simtime.MINUTES).value, 2)

    def testConvert3(self):
        "Test:  1 hour converted to minutes, units is MINUTES"
        self.assertEqual(self.ti_1hr.toUnits(simtime.MINUTES).units, simtime.MINUTES)

    def testConvert4(self):
        "Test: 1 hour converted to minutes, value is 60"
        self.assertEqual(self.ti_1hr.toUnits(simtime.MINUTES).value, 60)

    def testConvert5(self):
        "Test: 1 hour converted to seconds, value is 3600"
        self.assertEqual(self.ti_1hr.toUnits(simtime.SECONDS).value, 3600)

    def testConvert6(self):
        "Test: conversion to invalid units raises an error"
        self.assertRaises(SimError, lambda: self.ti_1hr.toUnits(5))

    def testConvert7(self):
        "Test: toSeconds() conversion"
        self.assertEqual(self.ti_1hr.toSeconds().value, 3600)

    def testConvert8(self):
        "Test: toMinutes() conversion"
        self.assertEqual(self.ti_1hr.toMinutes().value, 60)

    def testConvert9(self):
        "Test: toHours() conversion"
        self.assertEqual(self.ti_3600secs.toHours().value, 1)

    def testConvert10(self):
        "Test: toHours() conversion, units"
        self.assertEqual(self.ti_3600secs.toHours().units, simtime.HOURS)

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

    def testSeconds1(self):
        "Test: 2min.seconds() == 120"
        self.assertEqual(self.ti_2mins.seconds(), 120)
        
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
        
def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SimTimeTests))
    return suite
        
if __name__ == '__main__':
    unittest.main()
    