#===============================================================================
# MODULE simdowntime_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for resource downtime
#===============================================================================
import unittest
import itertools
from simprovise.core import *
from simprovise.core import simtime
from simprovise.core.simtime import Unit as tu
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


ONE_MIN = simtime.SimTime(1, tu.MINUTES)
TWO_MINS = simtime.SimTime(2, tu.MINUTES)
THREE_MINS = simtime.SimTime(3, tu.MINUTES)
FOUR_MINS = simtime.SimTime(4, tu.MINUTES)
FIVE_MINS = simtime.SimTime(5, tu.MINUTES)
SIX_MINS = simtime.SimTime(6, tu.MINUTES)
SEVEN_MINS = simtime.SimTime(7, tu.MINUTES)
EIGHT_MINS = simtime.SimTime(8, tu.MINUTES)
NINE_MINS = simtime.SimTime(9, tu.MINUTES)
TEN_MINS = simtime.SimTime(10, tu.MINUTES)
FIFTEEN_MINS = simtime.SimTime(15, tu.MINUTES)
THIRTY_MINS = simtime.SimTime(30, tu.MINUTES)
ONE_HR = simtime.SimTime(1, tu.HOURS)
TWO_HRS = simtime.SimTime(2, tu.HOURS)
THREE_HRS = simtime.SimTime(3, tu.HOURS)
FOUR_HRS = simtime.SimTime(4, tu.HOURS)
SIX_HRS = simtime.SimTime(6, tu.HOURS)
EIGHT_HRS = simtime.SimTime(8, tu.HOURS)
TEN_HRS = simtime.SimTime(10, tu.HOURS)

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
        

class TestResourceTakedownFail(SimSimpleResource):
    """
    A resource where takedown requests can fail
    """
    takedown_successful = False
    def _handle_resource_takedown(self, msg):
        if  TestResourceTakedownFail.takedown_successful:
            return super()._handle_resource_takedown(msg)
        else:           
            msgData = self, False
            self.send_response(msg, SimMsgType.RSRC_DOWN, msgData)
            return True    

class TestResourceTakedownNotHandled(SimSimpleResource):
    """
    A resource where takedown and bringup requests are not
    handled initially. complete_takedown() and complete_bringup()
    allow test code to simulate cases where the resource's
    assignment agent responds after some period of time to
    takedown or bringup requests.
    """
    handleTakedown = False
    handleBringup = True
    
    def _handle_resource_takedown(self, msg):
        if TestResourceTakedownNotHandled.handleTakedown:
            return super()._handle_resource_takedown(msg)
        else:
            return False
    
    def _handle_resource_bringup(self, msg):
        if TestResourceTakedownNotHandled.handleBringup:
            return super()._handle_resource_bringup(msg)
        else:
            return False
    
    def complete_takedown(self):
        "Now handle it successfully"
        msg = self.next_queued_message(SimMsgType.RSRC_TAKEDOWN_REQ)
        assert msg, "no takedown request message to complete"
        return super()._handle_resource_takedown(msg)
    
    def complete_bringup(self):
        "Now handle it successfully"
        assert not TestResourceTakedownNotHandled.handleBringup, "bringups handled immediately"
        msg = self.next_queued_message(SimMsgType.RSRC_BRINGUP_REQ)
        assert msg, "no bringup request message to complete"
        return super()._handle_resource_bringup(msg)
        
        
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
        
    def testResource3TimeDownAfterTakedown1(self):
        "Test: after takedown, resource3 time_down is zero"
        self.assertEqual(self.rsrc3.time_down, SimTime(0))
        
    def testResource3TimeDownAfterTakedown2(self):
        "Test: ten minutes after takedown, resource3 time_down is ten minutes"
        untilTime = SimClock.now() + TEN_MINS
        self.eventProcessor.process_events(untilTime)
        self.assertEqual(self.rsrc3.time_down, TEN_MINS)
        
    def testResource3NotAvailableAfterTakedown(self):
        "Test: after takedown, resource3 is not available"
        self.assertFalse(self.rsrc3.available)
        
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

        
class TakedownRequestFailureTests(unittest.TestCase):
    """
    TestCase for handling scenarios where the resource takedown
    fails and/or is not immediately handled, as well as scenarios
    where the bring up is not immediately handled.
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        TestResourceTakedownNotHandled.handleBringup = True
        self.eventProcessor = simevent.EventProcessor()
        self.agent1 = TestDowntimeAgent()
        self.agent2 = TestDowntimeAgent()
        self.rsrc1 = TestResourceTakedownFail("TestResource1")
        self.rsrc2 = TestResourceTakedownNotHandled("TestResource2")
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.request_resource_takedown(self.rsrc1)
        self.agent2.request_resource_takedown(self.rsrc2)
        self.eventProcessor.process_events()
         
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        TestResourceTakedownNotHandled.handleBringup = True
        
    def testResource1UpAfterSetup(self):
        "Test: after setup, resource1 is up"
        self.assertTrue(self.rsrc1.up)
    
    def testInvalidBringup1(self):
        "Test: requesting a bringup on a resource where takedown failed raises a SimError"
        self.assertRaises(SimError, lambda: self.agent1.request_resource_bringup(self.rsrc1))
        
    def testResourceUpAfterSecondTakedown(self):
        "Test: after second takedown attempt, resource1 is up with no exceptions"
        self.eventProcessor.process_events(FOUR_MINS)
        self.agent1.request_resource_takedown(self.rsrc1)
        self.assertTrue(self.rsrc1.up)
        
    def testResource2UpAfterSetup(self):
        "Test: after setup, resource2 is up"
        self.assertTrue(self.rsrc2.up)
    
    def testInvalidBringup2(self):
        "Test: requesting a bringup on a resource where takedown was not handled raises a SimError"
        self.assertRaises(SimError, lambda: self.agent2.request_resource_bringup(self.rsrc2))
        
    def testInvalidSecondTakedown2(self):
        "Test: after second takedown attempt, resource2 is up with no exceptions"
        self.eventProcessor.process_events(FOUR_MINS)
        self.assertRaises(SimError, lambda: self.agent2.request_resource_takedown(self.rsrc2))
        
    def testResource2CompleteTakedown(self):
        "Test: after assignment agent completes takedown, resource2 is down"
        self.eventProcessor.process_events(FOUR_MINS)
        self.rsrc2.complete_takedown()
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc2.down)
        
    def testResource2CompleteTakedownThenBringup(self):
        "Test: after assignment agent completes takedown, bringup succeeds"
        self.eventProcessor.process_events(FOUR_MINS)
        self.rsrc2.complete_takedown()
        self.eventProcessor.process_events(FIVE_MINS)
        self.agent2.request_resource_bringup(self.rsrc2)
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc2.up)
        
    def testResource2CompleteTakedownThenNothandledBringup(self):
        "Test: after assignment agent completes takedown, bringup fails"
        TestResourceTakedownNotHandled.handleBringup = False
        self.eventProcessor.process_events(FOUR_MINS)
        self.rsrc2.complete_takedown()
        self.eventProcessor.process_events(FIVE_MINS)
        self.agent2.request_resource_bringup(self.rsrc2)
        self.eventProcessor.process_events()
        self.assertFalse(self.rsrc2.up)
        
    def testResource2CompleteTakedownThenNothandledBringup2(self):
        "Test: after assignment agent completes takedown, bringup fails - after handled, resource is up"
        TestResourceTakedownNotHandled.handleBringup = False
        self.eventProcessor.process_events(FOUR_MINS)
        self.rsrc2.complete_takedown()
        self.eventProcessor.process_events(FIVE_MINS)
        self.agent2.request_resource_bringup(self.rsrc2)
        self.eventProcessor.process_events(SIX_MINS)
        self.rsrc2.complete_bringup()
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc2.up)
        
    def testResource2NothandledBringupThenBringupThenTakedown(self):
        "Test: bringup fails - after handled, resource can be taken down again"
        TestResourceTakedownNotHandled.handleBringup = False
        self.eventProcessor.process_events(FOUR_MINS)
        self.rsrc2.complete_takedown()
        self.eventProcessor.process_events(FIVE_MINS)
        self.agent2.request_resource_bringup(self.rsrc2)
        self.eventProcessor.process_events(SIX_MINS)
        self.rsrc2.complete_bringup()
        self.eventProcessor.process_events(SEVEN_MINS)
        self.agent2.request_resource_takedown(self.rsrc2)
        self.rsrc2.complete_takedown()
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc2.down)
        
    def testResource2CompleteTakedownThenNothandledBringupTakedownRaises(self):
        "Test: after assignment agent completes takedown, bringup fails, new takedown raises"
        TestResourceTakedownNotHandled.handleBringup = False
        self.eventProcessor.process_events(FOUR_MINS)
        self.rsrc2.complete_takedown()
        self.eventProcessor.process_events(FIVE_MINS)
        self.agent2.request_resource_bringup(self.rsrc2)
        self.eventProcessor.process_events()
        self.assertRaises(SimError, lambda: self.agent2.request_resource_takedown(self.rsrc2))
        
    def testResource2CompleteTakedownThenNothandledBringup2ndBringupRaises(self):
        "Test: after assignment agent completes takedown, bringup fails, second bringup raises"
        TestResourceTakedownNotHandled.handleBringup = False
        self.eventProcessor.process_events(FOUR_MINS)
        self.rsrc2.complete_takedown()
        self.eventProcessor.process_events(FIVE_MINS)
        self.agent2.request_resource_bringup(self.rsrc2)
        self.eventProcessor.process_events()
        self.assertRaises(SimError, lambda: self.agent2.request_resource_bringup(self.rsrc2))

        
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
            self.run_impl()
        except SimResourceDownException as e:
            self.exception = e
        finally:
            self.runend_tm = SimClock.now()
            self.run_tm = self.runend_tm - self.runstart_tm
            if self.assignment:               
                self.release(self.assignment)
            if self.assignment2:               
                self.release(self.assignment2)
                
    def run_impl(self):
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

class TestProcess1a(TestProcess1):
    "Test Process for acquiring the same resource twice"
    def run_impl(self):
        if self.wait_before_start:
            self.wait_for(self.wait_before_start)
            
        self.runstart_tm = SimClock.now()
        self.assignment = self.acquire(self.testcase.rsrc3)
        self.acquire_tm = SimClock.now()
        self.assignment2 = self.acquire(self.testcase.rsrc3)
        self.wait_for(self.wait_time,
                      extend_through_downtime=self.extend_through_downtime)        
    
     
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
        self.rsrc3 = SimSimpleResource("TestResource3", capacity=2)
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
      
    def testRaisesTwoAssignmentsForSameProcess(self):
        "Test: Exception raised, handled cleanly when one process acquires same resource twice, then resource goes down"
        self.process1 = TestProcess1a(self)
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.agent1.request_resource_takedown(self.rsrc3)
        self.eventProcessor.process_events()
        self.assertIs(self.process1.exception.resource, self.rsrc3)

        
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
        
        timeToFailureGenerator1 = SimDistribution.constant(SimTime(4, tu.MINUTES))
        timeToRepairGenerator1 = SimDistribution.constant(SimTime(3, tu.MINUTES))
        self.failureAgent1 = SimResourceFailureAgent(self.rsrc1,
                                                     timeToFailureGenerator1,
                                                     timeToRepairGenerator1)
        
        timeToFailureGenerator2 = SimDistribution.constant(SimTime(3, tu.MINUTES))
        timeToRepairGenerator2 = SimDistribution.constant(SimTime(2, tu.MINUTES))
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
        
        timeToFailureGenerator1 = SimDistribution.constant(SimTime(4, tu.MINUTES))
        timeToRepairGenerator1 = SimDistribution.constant(SimTime(3, tu.MINUTES))
        self.failureAgent1 = SimResourceFailureAgent(self.rsrc1,
                                                     timeToFailureGenerator1,
                                                     timeToRepairGenerator1)
        
        timeToFailureGenerator2 = SimDistribution.constant(SimTime(3, tu.MINUTES))
        timeToRepairGenerator2 = SimDistribution.constant(SimTime(2, tu.MINUTES))
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
        self.eventProcessor.process_events(SimTime(25, tu.MINUTES))
        self.assertEqual(self.process1.run_tm, SimTime(19, tu.MINUTES))
        
class DowntimeScheduleTests(unittest.TestCase):
    """
    TestCase for testing DowntimeSchedule functionality
    """
    def setUp(self):
        SimClock.initialize()
        self.baseScheduleLength = EIGHT_HRS
        self.valid_breaks = [(TWO_HRS, FIFTEEN_MINS), (FOUR_HRS, THIRTY_MINS),
                             (SIX_HRS, FIFTEEN_MINS)]
        self.valid_breaks_reordered = [(FOUR_HRS, THIRTY_MINS),
                             (SIX_HRS, FIFTEEN_MINS), (TWO_HRS, FIFTEEN_MINS)]
        self.expectedIntervals = [(TWO_HRS, FIFTEEN_MINS), (FOUR_HRS, THIRTY_MINS),
                                  (SIX_HRS, FIFTEEN_MINS), (TEN_HRS, FIFTEEN_MINS)]
                 
    def testNonSimTimeScheduleLengthRaises(self):
        "Test: initializing DowntimeSchedule with non-time schedule length raises SimError"
        self.assertRaises(SimError, lambda: DowntimeSchedule('x', self.valid_breaks))
        
    def testnegativeSimTimeScheduleLengthRaises(self):
        "Test: initializing DowntimeSchedule with zero schedule length raises SimError"
        self.assertRaises(SimError, lambda: DowntimeSchedule(0, self.valid_breaks))
        
    def testZeroSimTimeScheduleLengthRaises(self):
        "Test: initializing DowntimeSchedule with negative schedule length raises SimError"
        self.assertRaises(SimError, lambda: DowntimeSchedule(SimTime(-10), self.valid_breaks))
        
    def testScheduleLengthTooShortRaises(self):
        "Test: initializing DowntimeSchedule with interval past schedule length raises SimError"
        self.assertRaises(SimError, lambda: DowntimeSchedule(SimTime(368, tu.MINUTES),
                                                             self.valid_breaks))
        
    def testScheduleLengthToLastInterval(self):
        "Test: initializing DowntimeSchedule with last interval to schedule length works"
        sched = DowntimeSchedule(SimTime(375, tu.MINUTES), self.valid_breaks)
        intervals = sched.down_intervals()
        self.assertEqual(next(intervals), (TWO_HRS, FIFTEEN_MINS))
        
    def testExpectedIntervals(self):
        "Test: first four expected intervals on eight hour schedule"
        sched = DowntimeSchedule(EIGHT_HRS, self.valid_breaks)
        intervals = sched.down_intervals()
        # Do subtests 
        for expected in self.expectedIntervals:
            with self.subTest(expected):
                interval = next(intervals)
                self.assertEqual(interval, expected)
        
    def testExpectedIntervalsUnsorted(self):
        "Test: first four expected intervals on eight hour schedule, works with out-of-order input"
        sched = DowntimeSchedule(EIGHT_HRS, self.valid_breaks_reordered)
        intervals = sched.down_intervals()
        for expected in self.expectedIntervals:
            with self.subTest(expected):
                interval = next(intervals)
                self.assertEqual(interval, expected)
         
    def testNonTimeIntervalRaises1(self):
        "Test: DowntimeSchedule with non-SimTime interval length raises SimError"
        breaks = [(TWO_HRS, 'x'), (FOUR_HRS, THIRTY_MINS), (SIX_HRS, FIFTEEN_MINS)]
        self.assertRaises(SimError, lambda: DowntimeSchedule(EIGHT_HRS, breaks))
         
    def testNonTimeIntervalRaises2(self):
        "Test: DowntimeSchedule with non-SimTime interval start raises SimError"
        breaks = [(TWO_HRS, FIFTEEN_MINS), ('x', THIRTY_MINS), (SIX_HRS, FIFTEEN_MINS)]
        self.assertRaises(SimError, lambda: DowntimeSchedule(EIGHT_HRS, breaks))
         
    def testAdjacentIntervalRaises1(self):
        "Test: DowntimeSchedule with no gap between two intervals start raises SimError"
        breaks = [(TWO_HRS, ONE_HR), (THREE_HRS, THIRTY_MINS), (SIX_HRS, FIFTEEN_MINS)]
        self.assertRaises(SimError, lambda: DowntimeSchedule(EIGHT_HRS, breaks))
         
    def testSameIntervalStartRaises1(self):
        "Test: DowntimeSchedule with no two intervals starts at same time raises SimError"
        breaks = [(TWO_HRS, THIRTY_MINS), (TWO_HRS, THIRTY_MINS), (SIX_HRS, FIFTEEN_MINS)]
        self.assertRaises(SimError, lambda: DowntimeSchedule(EIGHT_HRS, breaks))
         
    def testIntervalOverlapRaises1(self):
        "Test: DowntimeSchedule with 2nd interval within first interval raises SimError"
        breaks = [(TWO_HRS, TWO_HRS), (THREE_HRS, THIRTY_MINS), (SIX_HRS, FIFTEEN_MINS)]
        self.assertRaises(SimError, lambda: DowntimeSchedule(EIGHT_HRS, breaks))
         
    def testIntervalOverlapRaises2(self):
        "Test: DowntimeSchedule with 2nd interval overlapping first interval raises SimError"
        breaks = [(TWO_HRS, TWO_HRS), (THREE_HRS, TWO_HRS), (SIX_HRS, FIFTEEN_MINS)]
        self.assertRaises(SimError, lambda: DowntimeSchedule(EIGHT_HRS, breaks))
         
    def testZeroIntervalRaises(self):
        "Test: DowntimeSchedule with an interval length of zero raises SimError"
        breaks = [(TWO_HRS, TWO_HRS), (THREE_HRS, SimTime(0)), (SIX_HRS, FIFTEEN_MINS)]
        self.assertRaises(SimError, lambda: DowntimeSchedule(EIGHT_HRS, breaks))
         
    def testNegativeIntervalRaises(self):
        "Test: DowntimeSchedule with an interval length of zero raises SimError"
        breaks = [(TWO_HRS, TWO_HRS), (THREE_HRS, SimTime(-10, tu.MINUTES)),
                  (SIX_HRS, FIFTEEN_MINS)]
        self.assertRaises(SimError, lambda: DowntimeSchedule(EIGHT_HRS, breaks))
         
    def testNegativeStartRaises(self):
        "Test: DowntimeSchedule with an interval length of zero raises SimError"
        breaks = [(SimTime(-10, tu.MINUTES), TWO_HRS), (THREE_HRS, FIFTEEN_MINS)]
        self.assertRaises(SimError, lambda: DowntimeSchedule(EIGHT_HRS, breaks))

        
class ScheduledDowntimeAgentTests(unittest.TestCase):
    """
    TestCase for testing basic ScheduledDowntimeAgentTests functionality
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        self.rsrc1 = SimSimpleResource("TestResource1")
        self.baseScheduleLength = EIGHT_HRS
        self.breaks = [(TWO_HRS, FIFTEEN_MINS), (FOUR_HRS, THIRTY_MINS),
                       (SIX_HRS, FIFTEEN_MINS)]
        
        self.sched = DowntimeSchedule(EIGHT_HRS, self.breaks)
        self.scheduleAgent = SimScheduledDowntimeAgent(self.rsrc1, self.sched)       
        SimAgent.final_initialize_all()
                 
    def tearDown(self):
        # Hack to allow recreation of static objects/agents for each test case
        SimStaticObject.elements = {}
        SimAgent.agents.clear()
        
    def testResourceDownAtFirstBreak1(self):
        "Test: resource down at start of first break"
        self.eventProcessor.process_events(TWO_HRS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourceDownAtFirstBreak2(self):
        "Test: resource down ten minutes into first break"
        self.eventProcessor.process_events(TWO_HRS + TEN_MINS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourceUptFirstBreakEnd(self):
        "Test: resource up at end of first break"
        self.eventProcessor.process_events(TWO_HRS + FIFTEEN_MINS)
        self.assertTrue(self.rsrc1.up)
        
    def testResourceDownAtSecondBreak1(self):
        "Test: resource down at start of second break"
        self.eventProcessor.process_events(FOUR_HRS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourceDownAtSecondBreak2(self):
        "Test: resource down fifteen minutes into second break"
        self.eventProcessor.process_events(FOUR_HRS + FIFTEEN_MINS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourceUptSecondBreakEnd(self):
        "Test: resource up at end of second break"
        self.eventProcessor.process_events(FOUR_HRS + THIRTY_MINS)
        self.assertTrue(self.rsrc1.up)
        
    def testResourceDownInSecondCycle1(self):
        "Test: resource down at at start of last break in second cycle"
        self.eventProcessor.process_events(TEN_HRS + FOUR_HRS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourceDownInSecondCycle2(self):
        "Test: resource down tend minutes into last break in second cycle"
        self.eventProcessor.process_events(TEN_HRS + FOUR_HRS + TEN_MINS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourceUpSecondBreakEndCycle(self):
        "Test: resource up fifteen minutes into last break in second cycle"
        self.eventProcessor.process_events(TEN_HRS + FOUR_HRS + FIFTEEN_MINS)
        self.assertTrue(self.rsrc1.up)
        
        
class ScheduledDowntimeAgentTakedownFailTests(unittest.TestCase):
    """
    TestCase for testing SimScheduledDowntimeAgent with a
    resource for whom takedown requests fail.
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        self.rsrc1 = TestResourceTakedownFail("TestResourceTDF")
        self.baseScheduleLength = EIGHT_HRS
        self.breaks = [(TWO_HRS, FIFTEEN_MINS), (FOUR_HRS, THIRTY_MINS),
                       (SIX_HRS, FIFTEEN_MINS)]
        
        self.sched = DowntimeSchedule(EIGHT_HRS, self.breaks)
        self.scheduleAgent = SimScheduledDowntimeAgent(self.rsrc1, self.sched)       
        SimAgent.final_initialize_all()
        TestResourceTakedownFail.takedown_successful = False
                 
    def tearDown(self):
        # Hack to allow recreation of static objects/agents for each test case
        SimStaticObject.elements = {}
        SimAgent.agents.clear()
        TestResourceTakedownFail.takedown_successful = False
        
    def testResourceNotDownAtFirstBreak1(self):
        "Test: resource not down at start of first break"
        self.eventProcessor.process_events(TWO_HRS)
        self.assertFalse(self.rsrc1.down)
        
    def testResourceNotDownAtFirstBreak2(self):
        "Test: resource not down tem minutes first break"
        self.eventProcessor.process_events(TWO_HRS+TEN_MINS)
        self.assertFalse(self.rsrc1.down)
        
    def testResourceUp15MinutesFirstBreak(self):
        "Test: resource up at end of first break"
        self.eventProcessor.process_events(TWO_HRS+FIFTEEN_MINS)
        self.assertTrue(self.rsrc1.up)
                            
    def testResourceDownAtSecondBreakAfterTakedownSuccess1(self):
        "Test: after first takedown fails, resource down successfully at start of second break"
        self.eventProcessor.process_events(THREE_HRS)
        TestResourceTakedownFail.takedown_successful = True
        self.eventProcessor.process_events(FOUR_HRS)
        self.assertTrue(self.rsrc1.down)

    def testResourceDownAtSecondBreakAfterTakedownSuccess2(self):
        "Test: after first takedown fails, resource down successfully in middle of second break"
        self.eventProcessor.process_events(THREE_HRS)
        TestResourceTakedownFail.takedown_successful = True
        self.eventProcessor.process_events(FOUR_HRS+FIFTEEN_MINS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourceUp30MinutesSecondBreak(self):
        "Test: after first takedown fails, resource up sat end of second break"
        self.eventProcessor.process_events(THREE_HRS)
        TestResourceTakedownFail.takedown_successful = True
        self.eventProcessor.process_events(FOUR_HRS+THIRTY_MINS)
        self.assertTrue(self.rsrc1.up)
        
        
class ScheduledDowntimeAgentTakedownDelayed(unittest.TestCase):
    """
    TestCase for testing SimScheduledDowntimeAgent with a
    resource for whom takedown requests fail.
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        self.rsrc1 = TestResourceTakedownNotHandled("TestResourceTDNH")
        self.baseScheduleLength = EIGHT_HRS
        self.breaks = [(TWO_HRS, FIFTEEN_MINS), (FOUR_HRS, THIRTY_MINS),
                       (SIX_HRS, FIFTEEN_MINS)]
        
        self.sched = DowntimeSchedule(EIGHT_HRS, self.breaks)
        self.scheduleAgent = SimScheduledDowntimeAgent(self.rsrc1, self.sched)       
        SimAgent.final_initialize_all()
        TestResourceTakedownNotHandled.handleTakedown = False
        TestResourceTakedownNotHandled.handleBringup = True
                 
    def tearDown(self):
        # Hack to allow recreation of static objects/agents for each test case
        SimStaticObject.elements = {}
        SimAgent.agents.clear()
        TestResourceTakedownNotHandled.handleTakedown = False
        TestResourceTakedownNotHandled.handleBringup = True
        
    def testResourceDownAtFirstBreak1(self):
        "Test: takendown complete immediately resource  down at start of first break"
        self.eventProcessor.process_events(TWO_HRS)
        self.rsrc1.complete_takedown()
        self.eventProcessor.process_events(TWO_HRS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourceDownAtFirstBreak2(self):
        "Test: takendown complete after 1 hour delay, resource down for delayed first break"
        self.eventProcessor.process_events(TWO_HRS)
        self.eventProcessor.process_events(THREE_HRS)
        self.rsrc1.complete_takedown()
        self.eventProcessor.process_events(THREE_HRS + FIVE_MINS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourcUpAtFirstBreak(self):
        "Test: takendown complete after 1 hour delay, resource up 15 minutes later"
        self.eventProcessor.process_events(THREE_HRS)
        self.rsrc1.complete_takedown()
        self.eventProcessor.process_events(THREE_HRS + FIFTEEN_MINS)
        self.assertTrue(self.rsrc1.up)
        
    def testResourcDownAtSecondBreak1(self):
        "Test: takendown complete after 1 hour delay, second break on time"
        self.eventProcessor.process_events(TWO_HRS)
        self.eventProcessor.process_events(THREE_HRS)
        self.rsrc1.complete_takedown()
        TestResourceTakedownNotHandled.handleTakedown = True
        self.eventProcessor.process_events(FOUR_HRS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourceUpDownSecondBreak2(self):
        "Test: takendown complete after 1 hour delay, on middle of second break on time"
        self.eventProcessor.process_events(THREE_HRS)
        self.rsrc1.complete_takedown()
        TestResourceTakedownNotHandled.handleTakedown = True
        self.eventProcessor.process_events(FOUR_HRS + FIFTEEN_MINS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourceExtendedTakedownDelay1(self):
        "Test: takendown complete after 2 hour delay, up after 15 mins (not 30)"
        self.eventProcessor.process_events(FOUR_HRS)
        self.rsrc1.complete_takedown()
        TestResourceTakedownNotHandled.handleTakedown = True
        self.eventProcessor.process_events(FOUR_HRS + FIFTEEN_MINS)
        self.assertTrue(self.rsrc1.up)
        
    def testResourceExtendedTakedownDelay2(self):
        "Test: takendown complete after 2 hour delay, downtime at 6 hrs is on time"
        self.eventProcessor.process_events(FOUR_HRS)
        self.rsrc1.complete_takedown()
        TestResourceTakedownNotHandled.handleTakedown = True
        self.eventProcessor.process_events(SIX_HRS)
        self.eventProcessor.process_events(SIX_HRS)
        self.assertTrue(self.rsrc1.down)
        
    def testResourceExtendedBringupDelay1(self):
        "Test: takedown complete on time, 2 hr bringup delay, break at 4+ hrs skipped"
        TestResourceTakedownNotHandled.handleTakedown = True
        TestResourceTakedownNotHandled.handleBringup = False
        self.eventProcessor.process_events(FOUR_HRS + FIFTEEN_MINS)
        self.rsrc1.complete_bringup()
        self.eventProcessor.process_events(FOUR_HRS + THIRTY_MINS)
        self.assertTrue(self.rsrc1.up)
        
    def testResourceExtendedBringupDelay2(self):
        "Test: takedown complete on time, 2 hr bringup delay, break at 6 hrs on time"
        TestResourceTakedownNotHandled.handleTakedown = True
        TestResourceTakedownNotHandled.handleBringup = False
        self.eventProcessor.process_events(FOUR_HRS + FIFTEEN_MINS)
        self.rsrc1.complete_bringup()
        self.eventProcessor.process_events(SIX_HRS)
        self.assertTrue(self.rsrc1.down)
        
        
def makeTestSuite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(BasicDowntimeTests))
    suite.addTest(loader.loadTestsFromTestCase(TakedownRequestFailureTests))
    suite.addTest(loader.loadTestsFromTestCase(BasicDowntimeAcquireTests1))
    suite.addTest(loader.loadTestsFromTestCase(FailureAgentTests))
    suite.addTest(loader.loadTestsFromTestCase(ExtendThroughDowntimeTests))
    suite.addTest(loader.loadTestsFromTestCase(DowntimeScheduleTests))
    suite.addTest(loader.loadTestsFromTestCase(ScheduledDowntimeAgentTests))
    suite.addTest(loader.loadTestsFromTestCase(ScheduledDowntimeAgentTakedownFailTests))
    suite.addTest(loader.loadTestsFromTestCase(ScheduledDowntimeAgentTakedownDelayed))
    return suite

if __name__ == '__main__':
    suite = makeTestSuite()
    unittest.main()