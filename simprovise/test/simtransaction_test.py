#===============================================================================
# MODULE simtransaction_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for the SimTransaction and related classes
#===============================================================================
from simprovise.core import (simevent, simtime, SimClock, SimTime,
                             SimSimpleResource, SimResourceAssignmentAgent, SimError)
from simprovise.core.transaction import (SimTransaction,
                                         SimTransactionResumeEvent,
                                         SimTransactionInterruptEvent)
from simprovise.core.agent import SimAgent
from simprovise.core.simexception import SimInterruptException, SimTimeOutException
import unittest
from heapq import heappop
from simprovise.core.location import SimStaticObject

ONE_MIN = simtime.SimTime(1, simtime.MINUTES)
TWO_MINS = simtime.SimTime(2, simtime.MINUTES)
THREE_MINS = simtime.SimTime(3, simtime.MINUTES)
FOUR_MINS = simtime.SimTime(4, simtime.MINUTES)



class TestRsrcAssignmentAgent(SimResourceAssignmentAgent):
    def __init__(self):
        super().__init__()
    

        
class SimTransactionTests(unittest.TestCase):
    """
    SimTransaction tests that can be executed without a running (in it's own
    greenlet) process or testWait2
    """
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        self.agent = SimAgent()
        self.txn = SimTransaction(self.agent)
        self.txn._executing = True


    def testWait1(self):
        "Test: wait_for(2 minutes) creates one event at two minutes"
        self.txn.wait_for(TWO_MINS)
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(tm, TWO_MINS)

    def testWait2(self):
        "Test: wait_for(2 minutes) after 1 minute advance creates one event at 3 minutes"
        SimClock.advance_to(ONE_MIN)
        self.txn.wait_for(TWO_MINS)
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(tm, THREE_MINS)

    def testWait3(self):
        "Test: wait_for(2 minutes) creates a SimTransactionResumeEvent"
        self.txn.wait_for(TWO_MINS)
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertTrue(isinstance(event, SimTransactionResumeEvent))

    def testInterruptWait1(self):
        """
        Test: wait_for(2 mins)
              advance clock (1 min)
              interrupt()
        results in next event being an interrupt event
        """
        self.txn.wait_for(TWO_MINS)
        SimClock.advance_to(ONE_MIN)
        self.txn.interrupt(SimInterruptException())
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertTrue(isinstance(event, SimTransactionInterruptEvent))

    def testInterruptWait2(self):
        """
        Test: wait_for(2 mins)
              advance clock (1 min)
              interrupt()
        results in 2nd event in heap being a resume event
        """
        self.txn.wait_for(TWO_MINS)
        SimClock.advance_to(ONE_MIN)
        self.txn.interrupt(SimInterruptException())
        tm, priority, seq, event = heappop(simevent.event_heap)
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertTrue(isinstance(event, SimTransactionResumeEvent))


class TestTransaction1(SimTransaction):
    def __init__(self, agent):
        super().__init__(agent)
        self.exception = None
        self.waitdone_time = None
        
    def run(self):
        try:
            self.runimpl()
        except Exception as e:
            self.exception = e
        finally:
            self.waitdone_time = SimClock.now()
            
    def runimpl(self):
        self.wait_for(TWO_MINS)
        
            
        
class SimTransactionInterruptTests(unittest.TestCase):
    """
    Tests conditions after completion of the following actions:
    - starting a transaction whose run() waits for 2 minutes
    - executing the first event in the simevent heap
    - advancing the simulation clock 1 minute
    - interrupting the running transaction (via txn.interrupt())
    - executing the next event in the simevent heap
    """
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        self.agent = SimAgent()
        self.txn = TestTransaction1(self.agent)
        self.txn.start()
        tm, priority, seq, event = heappop(simevent.event_heap)
        event.process()
        SimClock.advance_to(ONE_MIN)
        self.txn.interrupt(SimInterruptException())
        tm, priority, seq, event = heappop(simevent.event_heap)
        event.process()

    def testInterruptWait1(self):
        """
        Test: A SimInterruptException was raised in the transaction run()
        """
        self.assertTrue(isinstance(self.txn.exception, SimInterruptException))

    def testInterruptWait2(self):
        """
        Test: transaction run() was interrupted at one minute
        """
        self.assertEqual(self.txn.waitdone_time, ONE_MIN)

    def testInterruptWait3(self):
        """
        Test: the next event in the heap is a REMOVED (resume) event
        """
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(event, simevent.REMOVED)

    def testInterruptWait4(self):
        """
        Test: There is only one event left in heap
        """
        self.assertEqual(len(simevent.event_heap), 1)


class TestTransaction2(TestTransaction1):
    rsrc = None
    
    def __init__(self, agent, timeout=None):
        super().__init__(agent)
        self.timeout = timeout
        self.completed = False
    
    def runimpl(self):
        assignment = self.acquire(TestTransaction2.rsrc, timeout=self.timeout)
        self.wait_for(TWO_MINS)
        self.release(assignment)
        self.completed = True

class TestNoReleaseTransaction(TestTransaction2):
    def runimpl(self):
        assignment = self.acquire(TestTransaction2.rsrc, timeout=self.timeout)
        self.wait_for(TWO_MINS)
        #self.release(assignment)
        self.completed = True        

class TestPartialReleaseTransaction(TestTransaction2):
    def runimpl(self):
        # Acquire two resources, but release only one
        assignment = self.acquire(TestTransaction2.rsrc, 2)
        self.wait_for(TWO_MINS)
        self.release(assignment, 1)
        self.completed = True
        
        
def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SimTransactionTests))
    suite.addTest(unittest.makeSuite(SimTransactionInterruptTests))
    return suite
        
if __name__ == '__main__':
    unittest.main()
