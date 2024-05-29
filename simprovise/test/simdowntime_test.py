#===============================================================================
# MODULE simdowntime_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for resource downtime
#===============================================================================
import unittest
from simprovise.core import *
from simprovise.core.downtime import SimDowntimeAgent
from simprovise.core.resource import SimResourceDownException
from simprovise.core.agent import SimAgent, SimMsgType
from simprovise.core.simexception import SimError
from simprovise.core.location import SimStaticObject

        
class MockSource(SimEntitySource):
    def __init__(self):
        super().__init__("MockSource")

class MockEntity(SimEntity):
    ""


ONE_MIN = simtime.SimTime(1, simtime.MINUTES)
TWO_MINS = simtime.SimTime(2, simtime.MINUTES)
THREE_MINS = simtime.SimTime(3, simtime.MINUTES)
FOUR_MINS = simtime.SimTime(4, simtime.MINUTES)
FIVE_MINS = simtime.SimTime(5, simtime.MINUTES)
SIX_MINS = simtime.SimTime(6, simtime.MINUTES)
SEVEN_MINS = simtime.SimTime(7, simtime.MINUTES)
EIGHT_MINS = simtime.SimTime(8, simtime.MINUTES)
NINE_MINS = simtime.SimTime(9, simtime.MINUTES)
TEN_MINS = simtime.SimTime(10, simtime.MINUTES)

class TestDowntimeAgent(SimDowntimeAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.takedown_rsrc = None
        self.takedown_tm = None
        self.takedown_successful = None
        self.up_rsrc = None
        self.up_tm = None
        
    def _resource_down_impl(self, resource, takedown_successful):
        self.takedown_rsrc = resource
        self.takedown_tm = SimClock.now()
        self.takedown_successful = takedown_successful
        
    def _resource_up_impl(self, resource):  
        self.up_rsrc = resource
        self.up_tm = SimClock.now()
        
        
class BasicDowntimeTests(unittest.TestCase):
    """
    TestCase for basic downtime functionality, bringing resources
    down and up.
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        self.agent1 = TestDowntimeAgent()
        self.agent2 = TestDowntimeAgent()
        self.agent3 = TestDowntimeAgent()
        self.rsrc1 = SimSimpleResource("TestResource1")
        self.rsrc2 = SimSimpleResource("TestResource2")
        self.rsrc3 = SimSimpleResource("TestResource3")
        self.rsrccap2 = SimSimpleResource("TestResourceCap2")
        SimClock.advance_to(TWO_MINS)
        self.agent1.request_resource_takedown(self.rsrc2)
        self.eventProcessor.process_events()
        SimClock.advance_to(FOUR_MINS)
        self.agent1.request_resource_takedown(self.rsrc3)
        self.agent3.request_resource_takedown(self.rsrccap2)
        self.agent1.request_resource_bringup(self.rsrc2)
        self.eventProcessor.process_events()
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        
    def testResourceUpAfterSetup(self):
        "Test: after setup, resource1 is up"
        self.assertTrue(self.rsrc1.up)
        
    def testResourceNotDownAfterSetup(self):
        "Test: after setup, resource1 is not down"
        self.assertFalse(self.rsrc1.down)
        
    def testResource2UpAfterTakedownBringUp(self):
        "Test: after takedown and bringup, resource2 is up"
        self.assertTrue(self.rsrc2.up)
        
    def testResource2AvailableAfterTakedownBringUp(self):
        "Test: after takedown and bringup, resource2 is available"
        self.assertTrue(self.rsrc2.available)
        
    def testLastUpResourceIsRsrc2(self):
        "Test: downtime agent's last RSRC_UP is resource2"
        self.assertIs(self.agent1.up_rsrc, self.rsrc2)
        
    def testLastUpResourceTime(self):
        "Test: downtime agent's last RSRC_UP time is 4 minutes"
        self.assertEqual(self.agent1.up_tm, FOUR_MINS)
        
    def testLastDownResourceIsRsrc3(self):
        "Test: downtime agent's last RSRC_DOWN is rsrc3"
        self.assertIs(self.agent1.takedown_rsrc, self.rsrc3)
        
    def testLastDownResourceTime(self):
        "Test: downtime agent's last RSRC_DOWN time is 4 mins"
        self.assertEqual(self.agent1.takedown_tm, FOUR_MINS)
        
    def testLastDownResourceSuccess(self):
        "Test: downtime agent's last RSRC_DOWN was successful"
        self.assertEqual(self.agent1.takedown_successful, True)
        
    def testResource3DownAfterTakedown(self):
        "Test: after takedown, resource3 is down"
        self.assertTrue(self.rsrc3.down)
        
    def testMultiCapacityResourceDownAfterTakedown(self):
        "Test: after takedown, multi-capacity resource is down"
        self.assertTrue(self.rsrccap2.down)
        
    def testMultiCapacityResourceNotAvailableAfterTakedown(self):
        "Test: after takedown, multi-capacity resource is down"
        self.assertFalse(self.rsrccap2.available)
    
    def testResource3NotAvailableAfterTakedownBringUp(self):
        "Test: after takedown, rsrc3 is not available"
        self.assertFalse(self.rsrc3.available)
    
    def testTwoTakedowns1(self):
        "Test: after second takedown, rsrc3 is down"
        SimClock.advance_to(FIVE_MINS)
        self.agent2.request_resource_takedown(self.rsrc3)
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc3.down)
    
    def testTwoTakedownsOneBringup1(self):
        "Test: after two takedowns, one bringup rsrc3 is still down"
        SimClock.advance_to(FIVE_MINS)
        self.agent2.request_resource_takedown(self.rsrc3)
        SimClock.advance_to(SIX_MINS)
        self.agent2.request_resource_bringup(self.rsrc3)
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc3.down)
    
    def testTwoTakedownsOneBringup2(self):
        "Test: after two takedowns, one bringup by first agent, rsrc3 is still down"
        SimClock.advance_to(FIVE_MINS)
        self.agent2.request_resource_takedown(self.rsrc3)
        SimClock.advance_to(SIX_MINS)
        self.agent1.request_resource_bringup(self.rsrc3)
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc3.down)
    
    def testTwoTakedownsTwoBringups1(self):
        "Test: after two takedowns, two bringups rsrc3 is still down"
        SimClock.advance_to(FIVE_MINS)
        self.agent2.request_resource_takedown(self.rsrc3)
        SimClock.advance_to(SIX_MINS)
        self.agent2.request_resource_bringup(self.rsrc3)
        SimClock.advance_to(SEVEN_MINS)
        self.agent1.request_resource_bringup(self.rsrc3)
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc3.up)
    
    def testTwoTakedownsTwoBringups2(self):
        "Test: after two takedowns, two bringups (in opposite order) rsrc3 is still down"
        SimClock.advance_to(FIVE_MINS)
        self.agent2.request_resource_takedown(self.rsrc3)
        SimClock.advance_to(SIX_MINS)
        self.agent1.request_resource_bringup(self.rsrc3)
        SimClock.advance_to(SEVEN_MINS)
        self.agent2.request_resource_bringup(self.rsrc3)
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc3.up)
    
    def testInvalidBringup1(self):
        "Test: requesting a bringup on a resource that was never down raises a SimError"
        self.assertRaises(SimError, lambda: self.agent1.request_resource_bringup(self.rsrc1))
    
    def testInvalidBringup2(self):
        "Test: requesting a second bringup on a resource by the same agent raises a SimError"
        self.assertRaises(SimError, lambda: self.agent1.request_resource_bringup(self.rsrc2))
    
    def testInvalidBringup3(self):
        "Test: requesting a bringup on a resource taken down by a different agent raises a SimError"
        self.assertRaises(SimError, lambda: self.agent2.request_resource_bringup(self.rsrc3))
    
    def testInvalidTakedown1(self):
        "Test: requesting a takedown on a resource that this agent has already taken down raises a SimError"
        self.assertRaises(SimError, lambda: self.agent1.request_resource_takedown(self.rsrc3))

        
class TestProcess1(SimProcess):
    """
    """
        
    def __init__(self, testcase, *, priority=1,
                 wait_before_start=None, extend_through_downtime=False,
                 acquire_rsrc2=False):
        super().__init__()
        self.testcase = testcase
        self.priority = priority
        self.wait_before_start = wait_before_start
        self.extend_through_downtime = extend_through_downtime
        self.acquire_rsrc2 =  acquire_rsrc2
        entity = MockEntity(testcase.source, self)
        self.wait_time = TWO_MINS
        self.assignment = None
        self.assignment2 = None
        self.runstart_tm = None
        self.acquire_tm = None
        self.runend_tm = None
        self.run_tm = None
        self.exception = None
        
    def run(self):
        try:
            if self.wait_before_start:
                # approximates scheduling the process for a later time
                self.wait_for(self.wait_before_start)
                
            self.runstart_tm = SimClock.now()
            self.assignment = self.acquire(self.testcase.rsrc1)
            self.acquire_tm = SimClock.now()
            if self.acquire_rsrc2:
                # for testing situations where the process acquires
                # multiple resources
                self.assignment2 = self.acquire(self.testcase.rsrc2)
            self.wait_for(self.wait_time,
                          extend_through_downtime=self.extend_through_downtime)
        except SimResourceDownException as e:
            self.exception = e
        finally:
            self.runend_tm = SimClock.now()
            self.run_tm = self.runend_tm - self.runstart_tm
            if self.assignment:               
                self.release(self.assignment)
            if self.assignment2:               
                self.release(self.assignment2)

     
class BasicDowntimeAcquireTests1(unittest.TestCase):
    """
    TestCase for testing downtime functionality during and after resource acquire
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        self.source = MockSource()
        self.agent1 = TestDowntimeAgent()
        self.agent2 = TestDowntimeAgent()
        self.rsrc1 = SimSimpleResource("TestResource1")
        self.rsrc2 = SimSimpleResource("TestResource2")
        #self.rsrc3 = SimSimpleResource("TestResource3")
        self.process1 = TestProcess1(self)
        self.process2 = TestProcess1(self, acquire_rsrc2=True)
        SimClock.advance_to(ONE_MIN)
        self.agent1.request_resource_takedown(self.rsrc1)
        self.eventProcessor.process_events()
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        
    def testResourceNotAcquiredFromDownResource1(self):
        "Test: acquire blocks if requested resource is down"
        self.process1.start()
        self.eventProcessor.process_events()
        self.assertIsNone(self.process1.assignment)
        
    def testResourceAcquiredWhenResourceComesUp1(self):
        "Test: acquire request fulfilled when resource comes back up"
        self.process1.start()
        self.eventProcessor.process_events()
        SimClock.advance_to(TWO_MINS)
        self.agent1.request_resource_bringup(self.rsrc1)
        self.eventProcessor.process_events()
        self.assertEqual(self.process1.acquire_tm, TWO_MINS)
        
    def testResourceAcquiredWhenResourceComesUp2(self):
        "Test: acquire request fulfilled when resource comes back up, waits for 2 mins"
        self.process1.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.request_resource_bringup(self.rsrc1)
        self.eventProcessor.process_events()
        self.assertEqual(self.process1.runend_tm, FOUR_MINS)
      
    def testRaisesWhenResourceGoesDownDuringWait1(self):
        "Test: resource down after acquire(), exception raised"
        self.agent1.request_resource_bringup(self.rsrc1)
        self.process1.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.request_resource_takedown(self.rsrc1)
        self.eventProcessor.process_events()
        self.assertIsNotNone(self.process1.exception)
      
    def testRaisesWhenResourceGoesDownDuringWait2(self):
        "Test: resource down after acquire(), exception raised for that resource"
        self.agent1.request_resource_bringup(self.rsrc1)
        self.process1.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.request_resource_takedown(self.rsrc1)
        self.eventProcessor.process_events()
        self.assertIs(self.process1.exception.resource, self.rsrc1)
      
    def testRaisesWhenResourceGoesDownDuringWait3(self):
        "Test: resource down after acquire(), exception raised and process run() ends"
        self.agent1.request_resource_bringup(self.rsrc1)
        self.process1.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.request_resource_takedown(self.rsrc1)
        self.eventProcessor.process_events()
        self.assertEqual(self.process1.runend_tm, TWO_MINS)
      
    def testRaisesWhenResourc1eGoesDownWhileAcquiring2ndResource1(self):
        "Test: process acquires rsrc1, rsrc1 goes down while acquiring rsrc2, exception raised"
        self.agent1.request_resource_bringup(self.rsrc1)
        self.agent1.request_resource_takedown(self.rsrc2)
        self.process2.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.request_resource_takedown(self.rsrc1)
        self.eventProcessor.process_events()
        self.assertIsNotNone(self.process2.exception)
      
    def testRaisesWhenResourc1eGoesDownWhileAcquiring2ndResource2(self):
        "Test: process acquires rsrc1, rsrc1 goes down while acquiring rsrc2, exception raised for rsrc1"
        self.agent1.request_resource_bringup(self.rsrc1)
        self.agent1.request_resource_takedown(self.rsrc2)
        self.process2.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.request_resource_takedown(self.rsrc1)
        self.eventProcessor.process_events()
        self.assertIs(self.process2.exception.resource, self.rsrc1)
      
    def testRaisesWhenResourc1eGoesDownWhileAcquiring2ndResource3(self):
        "Test: process acquires rsrc1, rsrc1 goes down while acquiring rsrc2, run() ends"
        self.agent1.request_resource_bringup(self.rsrc1)
        self.agent1.request_resource_takedown(self.rsrc2)
        self.process2.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.request_resource_takedown(self.rsrc1)
        self.eventProcessor.process_events()
        self.assertEqual(self.process2.runend_tm, TWO_MINS)
      
    def testRaisesWhenResourc1eGoesDownWhileAcquiring2ndResource4(self):
        "Test: process acquires rsrc1, rsrc1 goes down while acquiring rsrc2, no rsrc2 assignment"
        self.agent1.request_resource_bringup(self.rsrc1)
        self.agent1.request_resource_takedown(self.rsrc2)
        self.process2.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.request_resource_takedown(self.rsrc1)
        self.eventProcessor.process_events()
        self.assertIsNone(self.process2.assignment2)
      
    def testRaisesWhenResourc1eGoesDownWhileAcquiring2ndResource5(self):
        "Test: process acquires rsrc1, rsrc1 goes down while acquiring rsrc2, rsrc2 request cancelled"
        # Bring up rsrc1 so that process2 will acquire it immediately
        self.agent1.request_resource_bringup(self.rsrc1)
        
        # takedown rsrc 2 so that process2 acquire() call on it will block
        self.agent1.request_resource_takedown(self.rsrc2)
        
        self.process2.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.request_resource_takedown(self.rsrc1)
        self.eventProcessor.process_events()
        
        # the request on rsrc2 should be cancelled - i.e., the request is deleted from
        # the resource assignment agent's message queue
        rsrc2_msgs = self.rsrc2.assignment_agent.queued_messages(SimMsgType.RSRC_REQUEST)
        self.assertEqual(len(rsrc2_msgs), 0)
        
     
class FailureAgentTests(unittest.TestCase):
    """
    TestCase for testing basic SimResourceFailureAgent functionality
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        self.source = MockSource()
        self.rsrc1 = SimSimpleResource("TestResource1")
        self.rsrc2 = SimSimpleResource("TestResource2")
        
        timeToFailureGenerator1 = SimDistribution.constant(SimTime(4, simtime.MINUTES))
        timeToRepairGenerator1 = SimDistribution.constant(SimTime(3, simtime.MINUTES))
        self.failureAgent1 = SimResourceFailureAgent(self.rsrc1,
                                                     timeToFailureGenerator1,
                                                     timeToRepairGenerator1)
        
        timeToFailureGenerator2 = SimDistribution.constant(SimTime(3, simtime.MINUTES))
        timeToRepairGenerator2 = SimDistribution.constant(SimTime(2, simtime.MINUTES))
        self.failureAgent2 = SimResourceFailureAgent(self.rsrc2,
                                                     timeToFailureGenerator2,
                                                     timeToRepairGenerator2)
        
        SimAgent.final_initialize_all()
                 
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        SimAgent.agents.clear()
        
    def testResourceNotAcquiredFromDownResource1(self):
        "Test: acquire blocks if requested resource is down one minute before and still down"
        self.process1 = TestProcess1(self, wait_before_start=FIVE_MINS)
        self.process1.start()
        self.eventProcessor.process_events(SIX_MINS)
        self.assertIsNone(self.process1.assignment)
        
    def testResourceNotAcquiredFromDownResource2(self):
        "Test: acquire blocks if requested resource is comes down at same time and is still down"
        self.process1 = TestProcess1(self, wait_before_start=FOUR_MINS)
        self.process1.start()
        self.eventProcessor.process_events(SIX_MINS)
        self.assertIsNone(self.process1.assignment)
        
    def testNoExceptionWhenResourceDownAtReleaseTime1(self):
        "Test: Resource released at same time as failure: no exception"
        self.process1 = TestProcess1(self, wait_before_start=TWO_MINS)
        self.process1.start()
        self.eventProcessor.process_events(SIX_MINS)
        self.assertIsNone(self.process1.exception)
        
    def testResourceAcquiredWhenDownResourceComesUp1(self):
        "Test: resource acquired when down at time of request, but when resource comes up"
        self.process1 = TestProcess1(self, wait_before_start=FIVE_MINS)
        self.process1.start()
        self.eventProcessor.process_events(SEVEN_MINS)
        self.assertIsNotNone(self.process1.assignment)
        
    def testResourceAcquiredWhenDownResourceComesUp2(self):
        "Test: resource acquired when resource comes back up"
        self.process1 = TestProcess1(self, wait_before_start=FIVE_MINS)
        self.process1.start()
        self.eventProcessor.process_events(SEVEN_MINS)
        self.assertEqual(self.process1.acquire_tm, SEVEN_MINS)
        
    def testRaisesWhenAcquiredResourceGoesDown1(self):
        "Test: resource down exception raised in process run when resource goes down after acquire"
        self.process1 = TestProcess1(self, wait_before_start=THREE_MINS)
        self.process1.start()
        self.eventProcessor.process_events(SEVEN_MINS)
        self.assertIsNotNone(self.process1.exception)
        
    def testRaisesWhenAcquiredResourceGoesDown2(self):
        "Test: exception raised when resource goes down after acquire is a SimResourceDownException"
        self.process1 = TestProcess1(self, wait_before_start=THREE_MINS)
        self.process1.start()
        self.eventProcessor.process_events(SEVEN_MINS)
        self.assertIsInstance(self.process1.exception, SimResourceDownException)
      
    def testRaisesWhenResourc1eGoesDownWhileAcquiring2ndResource1(self):
        "Test: process acquires rsrc1, rsrc1 goes down while acquiring rsrc2, exception raised"
        self.process1 = TestProcess1(self, wait_before_start=THREE_MINS, acquire_rsrc2=True)
        self.process1.start()
        self.eventProcessor.process_events(FIVE_MINS)
        self.assertIsNotNone(self.process1.exception)
 
     
class ExtendThroughDowntimeTests(unittest.TestCase):
    """
    TestCase for testing extend_through_downtime option on SimProcess.wait_for()
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        self.source = MockSource()
        self.rsrc1 = SimSimpleResource("TestResource1")
        self.rsrc2 = SimSimpleResource("TestResource2")
        
        timeToFailureGenerator1 = SimDistribution.constant(SimTime(4, simtime.MINUTES))
        timeToRepairGenerator1 = SimDistribution.constant(SimTime(3, simtime.MINUTES))
        self.failureAgent1 = SimResourceFailureAgent(self.rsrc1,
                                                     timeToFailureGenerator1,
                                                     timeToRepairGenerator1)
        
        timeToFailureGenerator2 = SimDistribution.constant(SimTime(3, simtime.MINUTES))
        timeToRepairGenerator2 = SimDistribution.constant(SimTime(2, simtime.MINUTES))
        self.failureAgent2 = SimResourceFailureAgent(self.rsrc2,
                                                     timeToFailureGenerator2,
                                                     timeToRepairGenerator2)
        
        SimAgent.final_initialize_all()
        
        self.process1 = TestProcess1(self, wait_before_start=THREE_MINS,
                                     extend_through_downtime=True)
        self.process2 = TestProcess1(self, wait_before_start=TWO_MINS,
                                     extend_through_downtime=True,
                                     acquire_rsrc2=True)
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        SimAgent.agents.clear()
        
    def testProcessCompletesWithoutException(self):
        "Test: acquire blocks if requested resource is down"
        self.process1.start()
        self.eventProcessor.process_events(EIGHT_MINS)
        self.assertIsNone(self.process1.exception)
        
    def testProcessCompletesWithExtendedWait1(self):
        "Test: process run time of 5 mins after resource down for 3 mins"
        self.process1.start()
        self.eventProcessor.process_events(TEN_MINS)
        self.assertEqual(self.process1.run_tm, FIVE_MINS)
        
    def testProcessCompletesWithExtendedWait2(self):
        "Test: process run time of 6 mins after waiting for both rsrc 1 and 2 to come back up"
        self.process2.start()
        self.eventProcessor.process_events(TEN_MINS)
        self.assertEqual(self.process2.run_tm, SIX_MINS)
        
    def testProcessCompletesWithExtendedWait3(self):
        "Test: process wait time of 10 minutes takes 19 minutes after three 3 minute down periods"
        self.process1.wait_time = TEN_MINS
        self.process1.start()
        self.eventProcessor.process_events(SimTime(25, simtime.MINUTES))
        self.assertEqual(self.process1.run_tm, SimTime(19, simtime.MINUTES))
        
        

def makeTestSuite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(BasicDowntimeTests))
    suite.addTest(loader.loadTestsFromTestCase(BasicDowntimeAcquireTests1))
    suite.addTest(loader.loadTestsFromTestCase(FailureAgentTests))
    suite.addTest(loader.loadTestsFromTestCase(ExtendThroughDowntimeTests))
    return suite

if __name__ == '__main__':
    suite = makeTestSuite()
    unittest.main()