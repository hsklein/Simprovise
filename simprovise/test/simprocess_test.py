#===============================================================================
# MODULE simprocess_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for the SimTransaction and related classes
#===============================================================================
#from simprovise.core import (simevent, simtime, SimClock, SimTime, SimProcess, 
                             #SimSimpleResource, SimResourceAssignmentAgent, SimError)
from simprovise.core import * 
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

        
class MockSource(SimEntitySource):
    def __init__(self):
        super().__init__("MockSource")

class MockEntity(SimEntity):
    ""
    
#class TestTransaction1(SimTransaction):
    #def __init__(self, agent):
        #super().__init__(agent)
        #self.exception = None
        #self.waitdone_time = None
        
    #def run(self):
        #try:
            #self.runimpl()
        #except Exception as e:
            #self.exception = e
        #finally:
            #self.waitdone_time = SimClock.now()
            
    #def runimpl(self):
        #self.wait_for(TWO_MINS)
        

class TestProcess(SimProcess):
    rsrc = None
    source = MockSource()
    
    def __init__(self, timeout=None):
        super().__init__()
        self.exception = None
        self.waitdone_time = None
        self.timeout = timeout
        self.completed = False
        entity = MockEntity(TestProcess.source, self)
        
    def run(self):
        try:
            self.runimpl()
        except Exception as e:
            self.exception = e
        finally:
            self.waitdone_time = SimClock.now()
    
    def runimpl(self):
        assignment = self.acquire(TestProcess.rsrc, timeout=self.timeout)
        self.wait_for(TWO_MINS)
        self.release(assignment)
        self.completed = True

class TestNoReleaseProcess(TestProcess):
    def runimpl(self):
        assignment = self.acquire(TestProcess.rsrc, timeout=self.timeout)
        self.wait_for(TWO_MINS)
        #self.release(assignment)
        self.completed = True        

class TestPartialReleaseProcess(TestProcess):
    def runimpl(self):
        # Acquire two resources, but release only one
        assignment = self.acquire(TestProcess.rsrc, 2)
        self.wait_for(TWO_MINS)
        self.release(assignment, 1)
        self.completed = True
        
        
        
class BasicTimeoutTests(unittest.TestCase):
    """
    Tests conditions after completion of the following actions:
    - starting a transaction whose run() acquires a resource and waits 2 mins
    - starting a second transaction, same run() with a acquire timeout of 1 min
    """
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        TestProcess.rsrc = SimSimpleResource("test", capacity=2)
        self.eventProcessor = simevent.EventProcessor()        

        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        
    def testStartNotExecuting(self):
        """
        Test: After start(), transaction is still not executing
        """
        process = TestProcess()
        process.start()
        self.assertFalse(process.is_executing)
        
    def testIsExecuting(self):
        """
        Test: start a transaction that waits for two minutes;
              process_events() for one minute. The transaction is
              still executing
        """
        process = TestProcess()
        process.start()
        self.eventProcessor.process_events(until_time=ONE_MIN)
        self.assertTrue(process.is_executing)
        
    def testNegativeTimeout(self):
        """
        Test: A negative timeout value raises a SimError
        """
        negtime = simtime.SimTime(-1, simtime.SECONDS)
        process = TestProcess(timeout=negtime)
        process.start()
        self.eventProcessor.process_events()
        self.assertTrue(isinstance(process.exception, SimError))
        
    def testInvalidTimeout(self):
        """
        Test: A non-time/numeric timeout value raises a SimError
        """
        process = TestProcess(timeout='x')
        process.start()
        self.eventProcessor.process_events()
        self.assertTrue(isinstance(process.exception, SimError))
        
    def testNoResourceRelease(self):
        """
        Test: Failing to release acquired resources when run() ends raises a SimError
        Note that this error is caught outside of run() (in execute()), so the
        exception leaks out to here. (Unlike the exceptions generated with invalid
        timeout values)
        """
        process = TestNoReleaseProcess()
        process.start()
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
        process = TestPartialReleaseProcess()
        process.start()
        with self.assertRaises(SimError):
            self.eventProcessor.process_events()
            
            
class TimeoutTests1(unittest.TestCase):
    """
    Tests conditions after completion of the following actions:
    - starting a transaction whose run() acquires a resource and waits 2 mins
    - starting a second transaction, same run() with a acquire timeout of 1 min
    """
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        TestProcess.rsrc = SimSimpleResource("test")
        self.eventProcessor = simevent.EventProcessor()        
        self.process1 = TestProcess()
        self.process1.start()
        self.process2 = TestProcess(timeout=ONE_MIN)
        self.process2.start()
        
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
        self.assertFalse(self.process1.is_executing or self.process2.is_executing)

    def testTimeout3(self):
        """
        Test: After running all events, the timed-out transaction did not complete
        """
        self.eventProcessor.process_events()
        self.assertFalse(self.process2.completed)

    def testTimeout4(self):
        """
        Test: After running all events, he timed-out transaction stopped waiting
              at 1 minute
        """
        self.eventProcessor.process_events()
        self.assertEqual(self.process2.waitdone_time, ONE_MIN)

    def testTimeout5(self):
        """
        Test: After running all events,t he timed-out transaction run() raised a
              SimTimeOutException
        """
        self.eventProcessor.process_events()
        self.assertTrue(isinstance(self.process2.exception, SimTimeOutException))

        
class TimeoutTests2(unittest.TestCase):
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
        TestProcess.rsrc = SimSimpleResource("test")
        self.eventProcessor = simevent.EventProcessor()        
        self.process1 = TestProcess()
        self.process1.start()
        self.process2 = TestProcess(timeout=TWO_MINS)
        self.process2.start()
        self.process3 = TestProcess(timeout=THREE_MINS)
        self.process3.start()
        self.process4 = TestProcess(timeout=FOUR_MINS)
        self.process4.start()
        self.nevents = self.eventProcessor.process_events()
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        
    def testTimeout1(self):
        """
        Test: After running all events, ten events are processed:
              process1 - start, resume (after wait for)
              process2 and 4 - start, resume (after acquire), resume (after wait)
              process3 - start, interrupt
        """
        self.assertEqual(self.nevents, 10)

    def testTimeout2(self):
        """
        Test: After running all events, all transactions are done executing
        """
        self.assertFalse(self.process1.is_executing or self.process2.is_executing or
                         self.process3.is_executing or self.process4.is_executing)

    def testTimeout3(self):
        """
        Test: After running all events, the transaction that timed out as
              the first transaction completed DID complete
        """
        self.eventProcessor.process_events()
        self.assertTrue(self.process2.completed)

    def testTimeout3a(self):
        """
        Test: After running all events, the transaction that timed at 3 minutes
              DID NOT complete
        """
        self.eventProcessor.process_events()
        self.assertFalse(self.process3.completed)

    def testTimeout3b(self):
        """
        Test: After running all events, the transaction that timed out at
              four minutes DID complete
        """
        self.eventProcessor.process_events()
        self.assertTrue(self.process4.completed)

    def testTimeout4(self):
        """
        Test: After running all events, he timed-out transaction stopped waiting at 3 minutes
        """
        self.eventProcessor.process_events()
        self.assertEqual(self.process3.waitdone_time, THREE_MINS)

    def testTimeout5(self):
        """
        Test: After running all events,t he timed-out transaction run() raised a SimTimeOutException
        """
        self.eventProcessor.process_events()
        self.assertTrue(isinstance(self.process3.exception, SimTimeOutException))
     
       
class ZeroTimeoutTests(unittest.TestCase):
    """
    Tests acquire calls with timeout of zero.
    Scenario starts two transactions at the same time with timeout of zero
    The first should complete normally; the second should timeout and raise
    a SimTimeOutException
   """
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        TestProcess.rsrc = SimSimpleResource("test")
        self.eventProcessor = simevent.EventProcessor()        
        self.process1 = TestProcess(timeout=0)
        self.process1.start()
        self.process2 = TestProcess(timeout=0)
        self.process2.start()
        self.eventProcessor.process_events()
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}

    def testTimeout1(self):
        """
        Test: After running all events, both transactions are done executing
        """
        self.eventProcessor.process_events()
        self.assertFalse(self.process1.is_executing or self.process2.is_executing)

    def testTimeout2(self):
        """
        Test: After running all events,process1 DID complete
        """
        self.assertTrue(self.process1.completed)

    def testTimeout3(self):
        """
        Test: After running all events,process2 did NOT complete
        """
        self.assertFalse(self.process2.completed)

    def testTimeout4(self):
        """
        Test: After running all events, the timed-out process2 stopped waiting at zero 
        """
        self.assertEqual(self.process2.waitdone_time, 0)

    def testTimeout5(self):
        """
        Test: After running all events, the timed-out process2.run() raised a SimTimeOutException
        """
        self.eventProcessor.process_events()
        self.assertTrue(isinstance(self.process2.exception, SimTimeOutException))
        
        
def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BasicTimeoutTests))
    suite.addTest(unittest.makeSuite(TimeoutTests1))
    suite.addTest(unittest.makeSuite(TimeoutTests2))
    suite.addTest(unittest.makeSuite(ZeroTimeoutTests))
    return suite
        
if __name__ == '__main__':
    unittest.main()