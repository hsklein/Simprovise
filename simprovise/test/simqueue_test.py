from simprovise.core import *
import unittest

class SimQueueTests( unittest.TestCase ):
    "Tests a simple SimQueue"
    def setUp( self ):
        self.queue = simqueue.SimQueue()

    def testNoEntries( self ):
        "Test: initial queue length == 0" 
        self.assertEqual( self.queue.length, 0 )

    def testAdd1( self ):
        "Test: add five entries, length == 5"
        for i in range(5):
            self.queue.add( i )
        self.assertEqual( self.queue.length, 5 )

    def testAdd2( self ):
        "Test: duplicate add raises SimError"
        for i in range(5):
            self.queue.add( i )        
        self.assertRaises( simexception.SimError, lambda: self.queue.add( 2 ) )

    def testRemove1( self ):
        "Test: add five entries, remove 2, length == 3"
        for i in range(5):
            self.queue.add( i )
        for i in range(2):
            self.queue.remove()
        self.assertEqual( self.queue.length, 3 )

    def testRemove2( self ):
        "Test: add five entries, remove 2, last removed obj = 1"
        for i in range(5):
            self.queue.add( i )
        for i in range(2):
            x = self.queue.remove()
        self.assertEqual( x, 1 )

    def testRemove3( self ):
        "Test: add five entries, remove last entry, removed obj = 4"
        for i in range(5):
            self.queue.add( i )
        x = self.queue.remove(-1)
        self.assertEqual( x, 4 )

    def testIndex1( self ):
        "Test - indexed access to queue"
        for i in range(5):
            self.queue.add( i ) 
        self.assertEqual( self.queue[3], 3 )

class SimQueueTimeTests( unittest.TestCase ):
    "Tests queue time measurements in class SimQueue"
    # TODO advance clock prior to first entry
    def setUp( self ):
        self.queue = simqueue.SimQueue()
        SimClock.initialize()
        for i in range(3):
            self.queue.add( i )
            SimClock.advanceTo( simtime.SimTime( i+1 ) )
        for i in range(3):
            self.queue.remove()

    def testMin( self ):
        "Test queue time sample: minimum is 1"
        self.assertEqual( self.queue._timeDataCollector.min(), simtime.SimTime(1) )

    def testMax( self ):
        "Test queue time sample: maximum is 3"
        self.assertEqual( self.queue._timeDataCollector.max(), simtime.SimTime(3) )                                

    def testMean( self ):
        "Test queue time sample: mean is 2.0"
        self.assertEqual( self.queue._timeDataCollector.mean(), simtime.SimTime(2.0) )
        
def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite( SimQueueTests ))
    suite.addTest(unittest.makeSuite( SimQueueTimeTests ))
    return suite            