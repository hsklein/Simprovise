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
        
        
class SimTransactionBasicTimeoutTests(unittest.TestCase):
    """
    Tests conditions after completion of the following actions:
    - starting a transaction whose run() acquires a resource and waits 2 mins
    - starting a second transaction, same run() with a acquire timeout of 1 min
    """
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        TestTransaction2.rsrc = SimSimpleResource("test", capacity=2)
        self.eventProcessor = simevent.EventProcessor()        

        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        
    def testStartNotExecuting(self):
        """
        Test: After start(), transaction is still not exception
        """
        txn = TestTransaction2(SimAgent())
        txn.start()
        self.assertFalse(txn.is_executing)
        
    def testIsExecuting(self):
        """
        Test: start a transaction that waits for two minutes;
              process_events() for one minute. The transaction is
              still executing
        """
        txn = TestTransaction2(SimAgent())
        txn.start()
        self.eventProcessor.process_events(until_time=ONE_MIN)
        self.assertTrue(txn.is_executing)
        
    def testNegativeTimeout(self):
        """
        Test: A negative timeout value raises a SimError
        """
        negtime = simtime.SimTime(-1, simtime.SECONDS)
        txn = TestTransaction2(SimAgent(), timeout=negtime)
        txn.start()
        self.eventProcessor.process_events()
        self.assertTrue(isinstance(txn.exception, SimError))
        
    def testInvalidTimeout(self):
        """
        Test: A non-time/numeric timeout value raises a SimError
        """
        txn = TestTransaction2(SimAgent(), timeout='x')
        txn.start()
        self.eventProcessor.process_events()
        self.assertTrue(isinstance(txn.exception, SimError))
        
    def testNoResourceRelease(self):
        """
        Test: Failing to release acquired resources when run() ends raises a SimError
        Note that this error is caught outside of run() (in execute()), so the
        exception leaks out to here. (Unlike the exceptions generated with invalid
        timeout values)
        """
        txn = TestNoReleaseTransaction(SimAgent())
        txn.start()
        with self.assertRaises(SimError):
            self.eventProcessor.process_events()
        
    def testPartialResourceRelease(self):
        """
        Test: Failing to release SOME acquired resources when run() ends raises a SimError
        In this case, we acquire two resources but only release one of them.
        Raises the same error when there is no release.
        
        Note that this error is caught outside of run() (in execute()), so the
        exception leaks out to here. (Unlike the exceptions generated with invalid
        timeout values)
        """
        txn = TestPartialReleaseTransaction(SimAgent())
        txn.start()
        with self.assertRaises(SimError):
            self.eventProcessor.process_events()
            
            
class SimTransactionTimeoutTests(unittest.TestCase):
    """
    Tests conditions after completion of the following actions:
    - starting a transaction whose run() acquires a resource and waits 2 mins
    - starting a second transaction, same run() with a acquire timeout of 1 min
    """
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        TestTransaction2.rsrc = SimSimpleResource("test")
        self.eventProcessor = simevent.EventProcessor()        
        self.txn1 = TestTransaction2(SimAgent())
        self.txn1.start()
        self.txn2 = TestTransaction2(SimAgent(), timeout=ONE_MIN)
        self.txn2.start()
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        
    def testTimeout1(self):
        """
        Test: After running all events, four are processed
        """
        nevents = self.eventProcessor.process_events()
        self.assertEqual(nevents, 4)

    def testTimeout2(self):
        """
        Test: After running all events, both transactions are done executing
        """
        self.eventProcessor.process_events()
        self.assertFalse(self.txn1.is_executing or self.txn2.is_executing)

    def testTimeout3(self):
        """
        Test: After running all events, the timed-out transaction did not complete
        """
        self.eventProcessor.process_events()
        self.assertFalse(self.txn2.completed)

    def testTimeout4(self):
        """
        Test: After running all events, he timed-out transaction stopped waiting
              at 1 minute
        """
        self.eventProcessor.process_events()
        self.assertEqual(self.txn2.waitdone_time, ONE_MIN)

    def testTimeout5(self):
        """
        Test: After running all events,t he timed-out transaction run() raised a
              SimTimeOutException
        """
        self.eventProcessor.process_events()
        self.assertTrue(isinstance(self.txn2.exception, SimTimeOutException))

        
class SimTransactionTimeoutTests2(unittest.TestCase):
    """
    Tests conditions after completion of the following actions:
    - starting a transaction whose run() acquires a resource and waits 2 mins
    - starting a second transaction, same run() with a acquire timeout of 2 min
    - starting a third transaction, same run() with a acquire timeout of 3 min
    - starting a fourth transaction, same run() with a acquire timeout of 4 min
    - Processing all events
    
    Transactions 1, 2, and 4 should acquire their resource and run to completion.
    Transaction 3 should time out.
    
    This tests the boundary condition where timeout coincides with requested
    resource becoming available (for transactions 2 and 4)
    """
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        TestTransaction2.rsrc = SimSimpleResource("test")
        self.eventProcessor = simevent.EventProcessor()        
        self.txn1 = TestTransaction2(SimAgent())
        self.txn1.start()
        self.txn2 = TestTransaction2(SimAgent(), timeout=TWO_MINS)
        self.txn2.start()
        self.txn3 = TestTransaction2(SimAgent(), timeout=THREE_MINS)
        self.txn3.start()
        self.txn4 = TestTransaction2(SimAgent(), timeout=FOUR_MINS)
        self.txn4.start()
        self.nevents = self.eventProcessor.process_events()
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        
    def testTimeout1(self):
        """
        Test: After running all events, ten events are processed:
              txn1 - start, resume (after wait for)
              txn2 and 4 - start, resume (after acquire), resume (after wait)
              txn3 - start, interrupt
        """
        self.assertEqual(self.nevents, 10)

    def testTimeout2(self):
        """
        Test: After running all events, all transactions are done executing
        """
        self.assertFalse(self.txn1.is_executing or self.txn2.is_executing or
                         self.txn3.is_executing or self.txn4.is_executing)

    def testTimeout3(self):
        """
        Test: After running all events, the transaction that timed out as
              the first transaction completed DID complete
        """
        self.eventProcessor.process_events()
        self.assertTrue(self.txn2.completed)

    def testTimeout3a(self):
        """
        Test: After running all events, the transaction that timed at 3 minutes
              DID NOT complete
        """
        self.eventProcessor.process_events()
        self.assertFalse(self.txn3.completed)

    def testTimeout3b(self):
        """
        Test: After running all events, the transaction that timed out at
              four minutes DID complete
        """
        self.eventProcessor.process_events()
        self.assertTrue(self.txn4.completed)

    def testTimeout4(self):
        """
        Test: After running all events, he timed-out transaction stopped waiting at 3 minutes
        """
        self.eventProcessor.process_events()
        self.assertEqual(self.txn3.waitdone_time, THREE_MINS)

    def testTimeout5(self):
        """
        Test: After running all events,t he timed-out transaction run() raised a SimTimeOutException
        """
        self.eventProcessor.process_events()
        self.assertTrue(isinstance(self.txn3.exception, SimTimeOutException))
     
       
class SimTransactionZeroTimeoutTests(unittest.TestCase):
    """
    Tests acquire calls with timeout of zero.
    Scenario starts two transactions at the same time with timeout of zero
    The first should complete normally; the second should timeout and raise
    a SimTimeOutException
   """
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        TestTransaction2.rsrc = SimSimpleResource("test")
        self.eventProcessor = simevent.EventProcessor()        
        self.txn1 = TestTransaction2(SimAgent(), timeout=0)
        self.txn1.start()
        self.txn2 = TestTransaction2(SimAgent(), timeout=0)
        self.txn2.start()
        self.eventProcessor.process_events()
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}

    def testTimeout1(self):
        """
        Test: After running all events, both transactions are done executing
        """
        self.eventProcessor.process_events()
        self.assertFalse(self.txn1.is_executing or self.txn2.is_executing)

    def testTimeout2(self):
        """
        Test: After running all events,txn1 DID complete
        """
        self.assertTrue(self.txn1.completed)

    def testTimeout3(self):
        """
        Test: After running all events,txn2 did NOT complete
        """
        self.assertFalse(self.txn2.completed)

    def testTimeout4(self):
        """
        Test: After running all events, the timed-out txn2 stopped waiting at zero 
        """
        self.assertEqual(self.txn2.waitdone_time, 0)

    def testTimeout5(self):
        """
        Test: After running all events, the timed-out txn2.run() raised a SimTimeOutException
        """
        self.eventProcessor.process_events()
        self.assertTrue(isinstance(self.txn2.exception, SimTimeOutException))
        
        
def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SimTransactionTests))
    suite.addTest(unittest.makeSuite(SimTransactionInterruptTests))
    suite.addTest(unittest.makeSuite(SimTransactionBasicTimeoutTests))
    suite.addTest(unittest.makeSuite(SimTransactionTimeoutTests))
    suite.addTest(unittest.makeSuite(SimTransactionTimeoutTests2))
    suite.addTest(unittest.makeSuite(SimTransactionZeroTimeoutTests))
    return suite
        
if __name__ == '__main__':
    unittest.main()
