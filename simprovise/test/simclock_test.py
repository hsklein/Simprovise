#===============================================================================
# MODULE simclock_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for class SimClock
#===============================================================================
from simprovise.core import *

import unittest

class simclockTests( unittest.TestCase ):
    "Tests for class simclock"
    def setUp( self ):
        SimClock.initialize()
        self.ti_10secs = simtime.SimTime( 30, simtime.SECONDS )
        self.ti_120secs = simtime.SimTime( 120, simtime.SECONDS )
        self.ti_2mins = simtime.SimTime( 2, simtime.MINUTES )
        self.ti_1hr = simtime.SimTime( 1, simtime.HOURS )

    def testNow( self ):
        "Test: now()is initially zero"
        self.assertEqual( simtime.SimTime( 0 ), SimClock.now() )
        
    def testAdvance1( self ):
        "Test: advance from zero to 10 seconds"
        SimClock.advance_to( self.ti_10secs )
        self.assertEqual( SimClock.now(), self.ti_10secs )
        
    def testAdvance2( self ):
        "Test: advance from 10 seconds to two minutes"
        SimClock.advance_to( self.ti_10secs )
        SimClock.advance_to( self.ti_2mins )
        self.assertEqual( SimClock.now(), self.ti_2mins )
        
    def testAdvance3( self ):
        "Test: advance from two minutes to 10 seconds raises simexception.Error"
        SimClock.advance_to( self.ti_2mins )
        self.assertRaises( simexception.SimError, SimClock.advance_to, self.ti_10secs  )
        
    def testAdvance4( self ):
        "Test: advanceTo() with integer parameter raises simexception.Error"
        self.assertRaises( simexception.SimError, SimClock.advance_to, 5  )

    def testClockProtect1( self ):
        "Test: Return value of now() is not a reference to the clock"
        t1 = SimClock.now()
        t1 += 1       
        self.assertNotEqual( t1, SimClock.now() )
        
def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite( simclockTests ))
    return suite
        
if __name__ == '__main__':
    unittest.main()        