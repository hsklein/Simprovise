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
from simprovise.core import simtime, simevent, SimError
from simprovise.core.simrandom import SimDistribution
from simprovise.core.simclock import SimClock
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.core.model import SimModel
from simprovise.modeling.downtime import (SimDowntimeAgent, DowntimeSchedule,
                                          SimResourceFailureAgent,
                                          SimScheduledDowntimeAgent,
                                          SimResourceDownException)
#from simprovise.modeling.resource import SimResourceDownException
from simprovise.modeling.agent import SimAgent, SimMsgType
#from simprovise.core.simexception import SimError
from simprovise.modeling import (SimEntity, SimEntitySource, SimProcess,
                                 SimSimpleResource)

        
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
SIXTEEN_MINS = simtime.SimTime(16, tu.MINUTES)
THIRTY_MINS = simtime.SimTime(30, tu.MINUTES)
THIRTY_ONE_MINS = simtime.SimTime(31, tu.MINUTES)
ONE_HR = simtime.SimTime(1, tu.HOURS)
TWO_HRS = simtime.SimTime(2, tu.HOURS)
THREE_HRS = simtime.SimTime(3, tu.HOURS)
FOUR_HRS = simtime.SimTime(4, tu.HOURS)
SIX_HRS = simtime.SimTime(6, tu.HOURS)
EIGHT_HRS = simtime.SimTime(8, tu.HOURS)
NINE_HRS = simtime.SimTime(9, tu.HOURS)
TEN_HRS = simtime.SimTime(10, tu.HOURS)
THIRTEEN_HRS = simtime.SimTime(13, tu.HOURS)
FOURTEEN_HRS = simtime.SimTime(14, tu.HOURS)

class TestDowntimeAgent(SimDowntimeAgent):
    def __init__(self, resource, setgoingdown=False, goingdowntimeout=None):
        super().__init__(resource)
        self.setgoingdown = setgoingdown
        self.goingdowntimeout = goingdowntimeout
        self.notified_down = False
        self.notified_goingdown = False
        self.notified_up = False
        self.notified_downtime = None
        self.notified_uptime = None
        self.notified_goingdowntime = None
        
    def start_resource_takedown(self):
        if not self.setgoingdown:
            super().start_resource_takedown()
        else:
            self._set_resource_going_down(self.goingdowntimeout)

    def _handle_resource_down(self, msg):
        self.notified_down = True
        self.notified_downtime = SimClock.now()
        return super()._handle_resource_down(msg)
        
    def _handle_resource_up(self, msg):
        self.notified_up = True
        self.notified_uptime = SimClock.now()
        return super()._handle_resource_up(msg)
        
    def _handle_resource_goingdown(self, msg):
        self.notified_goingdown = True
        self.notified_goingdowntime = SimClock.now()
        return super()._handle_resource_goingdown(msg)

        
        
class BasicDowntimeTests(unittest.TestCase):
    """
    TestCase for basic downtime functionality, bringing resources
    down and up.
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        self.rsrc1 = SimSimpleResource("TestResource1")
        self.rsrc2 = SimSimpleResource("TestResource2")
        self.rsrc3 = SimSimpleResource("TestResource3")
        self.rsrccap2 = SimSimpleResource("TestResourceCap2", capacity=2)
        self.agent1 = TestDowntimeAgent(self.rsrc1)
        self.agent2a = TestDowntimeAgent(self.rsrc2)
        self.agent2b = TestDowntimeAgent(self.rsrc2)
        self.agent3a = TestDowntimeAgent(self.rsrc3)
        self.agent3b = TestDowntimeAgent(self.rsrc3)
        self.agent4 = TestDowntimeAgent(self.rsrccap2)
        SimClock.advance_to(TWO_MINS)
        self.agent2a.start_resource_takedown()
        self.eventProcessor.process_events()
        SimClock.advance_to(FOUR_MINS)
        self.agent3a.start_resource_takedown()
        self.agent4.start_resource_takedown()
        self.agent2a.bringup_resource()
        self.eventProcessor.process_events()
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimModel.model().clear_registry_partial()
        
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
        
    def testResource2DownNotification(self):
        "Test: other rsrc2 agent notified of takedown"
        self.assertTrue(self.agent2b.notified_down)
        
    def testResource2DownNotificationTime(self):
        "Test: other rsrc2 agent notified of takedown"
        self.assertEqual(self.agent2b.notified_downtime, TWO_MINS)
        
    def testResource2UpNotification(self):
        "Test: other rsrc2 agent notified of bringup"
        self.assertTrue(self.agent2b.notified_up)
        
    def testResource2UpNotificationTime(self):
        "Test: other rsrc2 agent notified of takedown"
        self.assertEqual(self.agent2b.notified_uptime, FOUR_MINS)
        
    def testResource2NotGoingDownNotification(self):
        "Test: other rsrc2 agent notified of bringup"
        self.assertFalse(self.agent2b.notified_goingdown)
        
    def testResource2AgentANoDownNotification(self):
        "Test: agent2a gets no notifications"
        self.assertFalse(self.agent2a.notified_down or self.agent2a.notified_up)
        
    def testResource3DownNotification(self):
        "Test: other rsrc3 agent notified of takedown"
        self.assertTrue(self.agent3b.notified_down)
        
    def testResource3NoUpNotification(self):
        "Test: other rsrc3 agent notified of takedown time"
        self.assertFalse(self.agent3b.notified_up)
        
    def testResource3NDownNotificationTime(self):
        "Test: other rsrc3 agent notified of takedown time"
        self.assertEqual(self.agent3b.notified_downtime, FOUR_MINS)
        
    def testMultiCapResourceDown(self):
        "Test: multicapacity resource is down after takedown"
        self.assertTrue(self.rsrccap2.down)
        
    def testMultiCapResourceNotAvailable(self):
        "Test: multicapacity resource is not available after takedown"
        self.assertEqual(self.rsrccap2.available, 0)
        
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
        self.agent3b.start_resource_takedown()
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc3.down)
    
    def testTwoTakedowns2(self):
        "Test: after second takedown, first agent is NOT notified (since resource already down)"
        SimClock.advance_to(FIVE_MINS)
        self.agent3b.start_resource_takedown()
        self.eventProcessor.process_events()
        self.assertEqual(self.agent3a.notified_downtime, None)
    
    def testTwoTakedownsOneBringup1(self):
        "Test: after two takedowns, one bringup rsrc3 is still down"
        SimClock.advance_to(FIVE_MINS)
        self.agent3b.start_resource_takedown()
        SimClock.advance_to(SIX_MINS)
        self.agent3a.bringup_resource()
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc3.down)
    
    def testTwoTakedownsOneBringup2(self):
        "Test: after two takedowns, one bringup rsrc3 is still not available"
        SimClock.advance_to(FIVE_MINS)
        self.agent3b.start_resource_takedown()
        SimClock.advance_to(SIX_MINS)
        self.agent3a.bringup_resource()
        self.eventProcessor.process_events()
        self.assertFalse(self.rsrc3.available)
    
    def testTwoTakedownsTwoBringups1(self):
        "Test: after two takedowns, two bringups rsrc3 is sup"
        SimClock.advance_to(FIVE_MINS)
        self.agent3b.start_resource_takedown()
        SimClock.advance_to(SIX_MINS)
        self.agent3a.bringup_resource()
        SimClock.advance_to(SEVEN_MINS)
        self.agent3b.bringup_resource()
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc3.up)
    
    def testTwoTakedownsTwoBringups2(self):
        "Test: after two takedowns, two bringups (in opposite order) rsrc3 is still down"
        SimClock.advance_to(FIVE_MINS)
        self.agent3b.start_resource_takedown()
        SimClock.advance_to(SIX_MINS)
        self.agent3b.bringup_resource()
        SimClock.advance_to(SEVEN_MINS)
        self.agent3a.bringup_resource()
        self.eventProcessor.process_events()
        self.assertTrue(self.rsrc3.up)
    
    def testInvalidBringup1(self):
        "Test: requesting a bringup on a resource that was never down raises a SimError"
        self.assertRaises(SimError, lambda: self.agent1.bringup_resource())
    
    def testInvalidBringup2(self):
        "Test: requesting a second bringup on a resource by the same agent raises a SimError"
        self.assertRaises(SimError, lambda: self.agent2a.bringup_resource())
    
    def testInvalidBringup3(self):
        "Test: requesting a bringup on a resource taken down by a different agent raises a SimError"
        self.assertRaises(SimError, lambda: self.agent3b.bringup_resource())
    
    def testInvalidTakedown1(self):
        "Test: requesting a takedown on a resource that this agent has already taken down raises a SimError"
        self.assertRaises(SimError, lambda: self.agent4.start_resource_takedown())

        
class BasicGoingDownTests(unittest.TestCase):
    """
    TestCase for default handling of cases where a downtime agent invokes
    _set_resource_going_down() in start_resource_takedown()
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        self.rsrc1 = SimSimpleResource("TestResource1")
        self.agent1a = TestDowntimeAgent(self.rsrc1, setgoingdown=True)
        self.agent1b = TestDowntimeAgent(self.rsrc1, setgoingdown=False)
        self.agent1c = TestDowntimeAgent(self.rsrc1, setgoingdown=True,
                                         goingdowntimeout=TWO_MINS)
        self.agent1a.start_resource_takedown()
        SimClock.advance_to(TWO_MINS)
        self.eventProcessor.process_events()
        
         
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimModel.model().clear_registry_partial()
        
    def testResource1UpAfterSetup(self):
        "Test: after setup, resource is up"
        self.assertTrue(self.rsrc1.up)
        
    def testResource1GoingDownAfterSetup(self):
        "Test: after setup, resource is going down"
        self.assertTrue(self.rsrc1.going_down)
        
    def testResource1NotAvailableAfterSetup(self):
        "Test: after setup, resource is going down"
        self.assertFalse(self.rsrc1.available)
    
    def testInvalidGoingDown1(self):
        "Test: requesting set going down on a resource that this agent has already set that for raises a SimError"
        self.assertRaises(SimError, lambda: self.agent1a.start_resource_takedown())
        
    def testGoingDownTwiceOK(self):
        "Test: setting a resource that's already going down (from a different agent) to going down is OK"
        self.agent1c.start_resource_takedown()
        self.assertTrue(self.rsrc1.going_down)
        
    def testDown1(self):
        "Test: take down the going down resource - resource is down"
        self.agent1b.start_resource_takedown()
        self.assertTrue(self.rsrc1.down)
    
    def testInvalidGoingDown2(self):
        "Test: requesting set going down on a resource that is already down raises a SimError"
        self.agent1b.start_resource_takedown()
        self.assertRaises(SimError, lambda: self.agent1c.start_resource_takedown())
   
    def testInvalidBringup1(self):
        "Test: bringing up a resource that is going down (but not down) raises a SimError"
        self.assertRaises(SimError, lambda: self.agent1a.bringup_resource())
        
    def testDown2(self):
        "Test: take down the going down resource with second agent, then bringup - resource is still down (2 downs/1 up)"
        self.agent1b.start_resource_takedown()
        self.eventProcessor.process_events(FOUR_MINS)
        self.agent1a.bringup_resource()
        self.assertTrue(self.rsrc1.down)
        
    def testDown3(self):
        "Test: take down the going down resource with second agent, then bringup with 2nd agent - resource is still down (2 downs/1 up)"
        self.agent1b.start_resource_takedown()
        self.eventProcessor.process_events(FOUR_MINS)
        self.agent1b.bringup_resource()
        self.assertTrue(self.rsrc1.down)
        
    def testDown4(self):
        "Test: take down the going down resource with second agent, then bringup with both agents (2 downs/2 up) resource is up"
        self.agent1b.start_resource_takedown()
        self.eventProcessor.process_events(FOUR_MINS)
        self.agent1b.bringup_resource()
        SimClock.advance_to(FIVE_MINS)
        self.eventProcessor.process_events()
        self.agent1a.bringup_resource()
        self.assertTrue(self.rsrc1.up)
        
    def testGoingDownTimeout1(self):
        "Test: set resource to goingdown with two min timeout; 1 min later, resource is going down"
        # complete resource takedown with agent1b, then 1a and 1b bring up the resource
        self.agent1b.start_resource_takedown()
        self.agent1b.bringup_resource()
        self.agent1a.bringup_resource()
        # resource now up; start a goingdown with a two minute timeout
        self.agent1c.start_resource_takedown()
        self.eventProcessor.process_events(THREE_MINS)
        self.assertTrue(self.rsrc1.going_down)
       
    def testGoingDownTimeout2(self):
        "Test: set resource to goingdown with two min timeout; 2 min later, resource is down"
        # complete resource takedown with agent1b, then 1a and 1b bring up the resource
        self.agent1b.start_resource_takedown()
        self.agent1b.bringup_resource()
        self.agent1a.bringup_resource()
        # start a goingdown with a two minute timeout
        self.agent1c.start_resource_takedown()
        self.eventProcessor.process_events(FOUR_MINS)
        self.assertTrue(self.rsrc1.down)
        
        
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
        self.rsrc1 = SimSimpleResource("TestResource1")
        self.rsrc2 = SimSimpleResource("TestResource2")
        self.rsrc3 = SimSimpleResource("TestResource3", capacity=2)
        self.agent1 = TestDowntimeAgent(self.rsrc1)
        self.agent2 = TestDowntimeAgent(self.rsrc2)
        self.agent3 = TestDowntimeAgent(self.rsrc3)
        self.process1 = TestProcess1(self)
        self.process2 = TestProcess1(self, acquire_rsrc2=True)
        SimClock.advance_to(ONE_MIN)
        self.agent1.start_resource_takedown()
        self.eventProcessor.process_events()
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimModel.model().clear_registry_partial()
        
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
        self.agent1.bringup_resource()
        self.eventProcessor.process_events()
        self.assertEqual(self.process1.acquire_tm, TWO_MINS)
        
    def testResourceAcquiredWhenResourceComesUp2(self):
        "Test: acquire request fulfilled when resource comes back up, waits for 2 mins"
        self.process1.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.bringup_resource()
        self.eventProcessor.process_events()
        self.assertEqual(self.process1.runend_tm, FOUR_MINS)
      
    def testRaisesWhenResourceGoesDownDuringWait1(self):
        "Test: resource down after acquire(), exception raised"
        self.agent1.bringup_resource()
        self.process1.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.start_resource_takedown()
        self.eventProcessor.process_events()
        self.assertIsNotNone(self.process1.exception)
      
    def testRaisesWhenResourceGoesDownDuringWait2(self):
        "Test: resource down after acquire(), exception raised for that resource"
        self.agent1.bringup_resource()
        self.process1.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.start_resource_takedown()
        self.eventProcessor.process_events()
        self.assertIs(self.process1.exception.resource, self.rsrc1)
      
    def testRaisesWhenResourceGoesDownDuringWait3(self):
        "Test: resource down after acquire(), exception raised and process run() ends"
        self.agent1.bringup_resource()
        self.process1.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.start_resource_takedown()
        self.eventProcessor.process_events()
        self.assertEqual(self.process1.runend_tm, TWO_MINS)
      
    def testRaisesWhenResourc1eGoesDownWhileAcquiring2ndResource1(self):
        "Test: process acquires rsrc1, rsrc1 goes down while acquiring rsrc2, exception raised"
        self.agent1.bringup_resource()
        self.agent2.start_resource_takedown()
        self.process2.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.start_resource_takedown()
        self.eventProcessor.process_events()
        self.assertIsNotNone(self.process2.exception)
      
    def testRaisesWhenResourc1eGoesDownWhileAcquiring2ndResource2(self):
        "Test: process acquires rsrc1, rsrc1 goes down while acquiring rsrc2, exception raised for rsrc1"
        self.agent1.bringup_resource()
        self.agent2.start_resource_takedown()
        self.process2.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.start_resource_takedown()
        self.eventProcessor.process_events()
        self.assertIs(self.process2.exception.resource, self.rsrc1)
      
    def testRaisesWhenResourc1eGoesDownWhileAcquiring2ndResource3(self):
        "Test: process acquires rsrc1, rsrc1 goes down while acquiring rsrc2, run() ends"
        self.agent1.bringup_resource()
        self.agent2.start_resource_takedown()
        self.process2.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.start_resource_takedown()
        self.eventProcessor.process_events()
        self.assertEqual(self.process2.runend_tm, TWO_MINS)
      
    def testRaisesWhenResourc1eGoesDownWhileAcquiring2ndResource4(self):
        "Test: process acquires rsrc1, rsrc1 goes down while acquiring rsrc2, no rsrc2 assignment"
        self.agent1.bringup_resource()
        self.agent2.start_resource_takedown()
        self.process2.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.start_resource_takedown()
        self.eventProcessor.process_events()
        self.assertIsNone(self.process2.assignment2)
      
    def testRaisesWhenResourc1eGoesDownWhileAcquiring2ndResource5(self):
        "Test: process acquires rsrc1, rsrc1 goes down while acquiring rsrc2, rsrc2 request cancelled"
        # Bring up rsrc1 so that process2 will acquire it immediately
        self.agent1.bringup_resource()
        
        # takedown rsrc 2 so that process2 acquire() call on it will block
        self.agent2.start_resource_takedown()
        
        self.process2.start()
        self.eventProcessor.process_events(TWO_MINS)
        self.agent1.start_resource_takedown()
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
        self.agent3.start_resource_takedown()
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
        SimModel.model().clear_registry_partial()
        
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
        SimModel.model().clear_registry_partial()
        
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
        SimModel.model().clear_registry_partial()
        
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
        
        
#class ScheduledDowntimeAgentTakedownFailTests(unittest.TestCase):
    #"""
    #TestCase for testing SimScheduledDowntimeAgent with a
    #resource for whom takedown requests fail.
    #"""
    #def setUp(self):
        #SimClock.initialize()
        #simevent.initialize()
        #self.eventProcessor = simevent.EventProcessor()
        #self.rsrc1 = TestResourceTakedownFail("TestResourceTDF")
        #self.baseScheduleLength = EIGHT_HRS
        #self.breaks = [(TWO_HRS, FIFTEEN_MINS), (FOUR_HRS, THIRTY_MINS),
                       #(SIX_HRS, FIFTEEN_MINS)]
        
        #self.sched = DowntimeSchedule(EIGHT_HRS, self.breaks)
        #self.scheduleAgent = SimScheduledDowntimeAgent(self.rsrc1, self.sched)       
        #SimAgent.final_initialize_all()
        #TestResourceTakedownFail.takedown_successful = False
                 
    #def tearDown(self):
        ## Hack to allow recreation of static objects/agents for each test case
        #SimModel.model().clear_registry_partial()
        #TestResourceTakedownFail.takedown_successful = False
        
    #def testResourceNotDownAtFirstBreak1(self):
        #"Test: resource not down at start of first break"
        #self.eventProcessor.process_events(TWO_HRS)
        #self.assertFalse(self.rsrc1.down)
        
    #def testResourceNotDownAtFirstBreak2(self):
        #"Test: resource not down tem minutes first break"
        #self.eventProcessor.process_events(TWO_HRS+TEN_MINS)
        #self.assertFalse(self.rsrc1.down)
        
    #def testResourceUp15MinutesFirstBreak(self):
        #"Test: resource up at end of first break"
        #self.eventProcessor.process_events(TWO_HRS+FIFTEEN_MINS)
        #self.assertTrue(self.rsrc1.up)
                            
    #def testResourceDownAtSecondBreakAfterTakedownSuccess1(self):
        #"Test: after first takedown fails, resource down successfully at start of second break"
        #self.eventProcessor.process_events(THREE_HRS)
        #TestResourceTakedownFail.takedown_successful = True
        #self.eventProcessor.process_events(FOUR_HRS)
        #self.assertTrue(self.rsrc1.down)

    #def testResourceDownAtSecondBreakAfterTakedownSuccess2(self):
        #"Test: after first takedown fails, resource down successfully in middle of second break"
        #self.eventProcessor.process_events(THREE_HRS)
        #TestResourceTakedownFail.takedown_successful = True
        #self.eventProcessor.process_events(FOUR_HRS+FIFTEEN_MINS)
        #self.assertTrue(self.rsrc1.down)
        
    #def testResourceUp30MinutesSecondBreak(self):
        #"Test: after first takedown fails, resource up sat end of second break"
        #self.eventProcessor.process_events(THREE_HRS)
        #TestResourceTakedownFail.takedown_successful = True
        #self.eventProcessor.process_events(FOUR_HRS+THIRTY_MINS)
        #self.assertTrue(self.rsrc1.up)

class TestScheduledDowntimeAgent(SimScheduledDowntimeAgent):
    """
    """
    def __init__(self, resource, schedule, goingdowntimeout=None):
        super().__init__(resource, schedule)
        self.goingdowntimeout = goingdowntimeout
        self.notified_down = False
        self.notified_goingdown = False
        self.notified_up = False
        self.notified_downtime = None
        self.notified_uptime = None
        self.notified_goingdowntime = None
        
    def start_resource_takedown(self):
        if not self.resource.in_use or self.resource.down:
            super().start_resource_takedown()
        else:
            self._set_resource_going_down(self.goingdowntimeout)
            
class TestProcess2(SimProcess):
    def __init__(self, testcase, *, start_at=None, wait_time=None):
        super().__init__()
        self.testcase = testcase
        self.rsrc = testcase.rsrc1
        self.start_at_time = start_at
        self.wait_time = wait_time
        self.assignment = None
        self.runstart_tm = None
        self.acquire_tm = None
        self.runend_tm = None
        entity = MockEntity(testcase.source, self)
        
    def run(self):
        initial_wait = self.start_at_time - SimClock.now()
        self.wait_for(initial_wait)
        self.runstart_tm = SimClock.now()
        with self.acquire(self.rsrc) as self.assignment:
            self.acquire_tm = SimClock.now()
            self.wait_for(self.wait_time, extend_through_downtime=True)        
            self.runend_tm = SimClock.now()
        
         
    
        
class ScheduledAndFailureDowntimeTests(unittest.TestCase):
    """
    TestCase for testing resource with a SimScheduledDowntimeAgent that
    sets going down when the resource is in-use and up, and a failure agent.
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        self.source = MockSource()
        self.rsrc1 = SimSimpleResource("TestResource1")
        
        self.baseScheduleLength = EIGHT_HRS
        self.breaks = [(TWO_HRS, FIFTEEN_MINS), (SIX_HRS, FIFTEEN_MINS)]
        self.sched = DowntimeSchedule(EIGHT_HRS, self.breaks)
        self.scheduleAgent = TestScheduledDowntimeAgent(self.rsrc1, self.sched)
        
        timeToFailureGenerator1 = SimDistribution.constant(NINE_HRS)
        timeToRepairGenerator1 = SimDistribution.constant(TWO_HRS)
        self.failureAgent1 = SimResourceFailureAgent(self.rsrc1,
                                                     timeToFailureGenerator1,
                                                     timeToRepairGenerator1)
        
        timeToFailureGenerator2 = SimDistribution.constant(FOURTEEN_HRS+ONE_MIN)
        timeToRepairGenerator2 = SimDistribution.constant(FIVE_MINS)
        self.failureAgent1 = SimResourceFailureAgent(self.rsrc1,
                                                     timeToFailureGenerator2,
                                                     timeToRepairGenerator2)
        SimAgent.final_initialize_all()
        
        # All processes use extend_through_downtime = True
        # process 1 starts at 1 hour, encounters 15 min scheduled downtime at
        # 2 hours, completes at 3:15
        self.process1 = TestProcess2(self, start_at=ONE_HR, wait_time=TWO_HRS)
        
        # process 2 starts at 8 hours, waits through 2 hr failure starting at
        # 9 hrs (which overlaps with scheduled break) and completes at 12 hours
        self.process2 = TestProcess2(self, start_at=EIGHT_HRS, wait_time=TWO_HRS)
        
        # process 3 starts at 13 hours. At 14 hours, break is delayed
        # (Resource going down) because resource in use.
        # At 14:01, resource fails (for only 5 mins), so scheduled break starts.
        # At 14:16, break ends; process completes at 14:30
        self.process3 = TestProcess2(self, start_at=THIRTEEN_HRS,
                                     wait_time=ONE_HR+FIFTEEN_MINS)
        
        self.process1.start()
        self.process2.start()
        self.process3.start()
                        
    def tearDown(self):
        # Hack to allow recreation of static objects/agents for each test case
        SimModel.model().clear_registry_partial()
        
    def testResourceNotDownAtFirstBreak(self):
        "Test: Scheduled downtime is going down, not down"
        self.eventProcessor.process_events(TWO_HRS + ONE_MIN)
        self.assertTrue(self.rsrc1.going_down and self.rsrc1.up)
        
    def testProcess1CompleteOnTime(self):
        "Test: Process1 completes on time (no break)"
        self.eventProcessor.process_events(THREE_HRS)
        self.assertEqual(self.process1.runend_tm, THREE_HRS)
        
    def testProcess1CompleteThenResourceDown(self):
        "Test: Process1 completes on time and break commences"
        self.eventProcessor.process_events(THREE_HRS)
        self.assertTrue(self.rsrc1.down)
        
    def testProcess1CompleteThenResourceUpAfterBreak(self):
        "Test: Break completes (rsrc up) 15 minutes after Process1 completes"
        self.eventProcessor.process_events(THREE_HRS + FIFTEEN_MINS)
        self.assertTrue(self.rsrc1.up)
        
    def testProcess2_9HRS_1(self):
        "Test: At 9 hours, process2 in process"
        self.eventProcessor.process_events(NINE_HRS)
        self.assertEqual(self.process2.acquire_tm, EIGHT_HRS)
       
    def testProcess2_9HRS_2(self):
        "Test: At 9 hours, resource is down"
        self.eventProcessor.process_events(NINE_HRS)
        self.assertTrue(self.rsrc1.down)
       
    def testProcess2_11HRS(self):
        "Test: At 11 hours, resource is up (scheduled downtime during failure)"
        self.eventProcessor.process_events(NINE_HRS+TWO_HRS)
        self.assertTrue(self.rsrc1.up)
        
    def testProcess2_12HRS1(self):
        "Test: At 12 hours, process2 is complete"
        self.eventProcessor.process_events(NINE_HRS+THREE_HRS)
        self.assertEqual(self.process2.runend_tm, NINE_HRS+THREE_HRS)
        
    def testProcess2_12HRS2(self):
        "Test: At 12 hours, resource is still up (no delayed break)"
        self.eventProcessor.process_events(NINE_HRS+THREE_HRS)
        self.assertTrue(self.rsrc1.up)
        
    def testProcess3_14HRS1(self):
        "Test: At 14 hours, process3 has started at 13 hrs"
        self.eventProcessor.process_events(FOURTEEN_HRS)
        self.assertEqual(self.process3.acquire_tm, THIRTEEN_HRS)
        
    def testProcess3_14HRS2(self):
        "Test: At 14 hours, resource is going down"
        self.eventProcessor.process_events(FOURTEEN_HRS)
        self.assertTrue(self.rsrc1.going_down)
        
    def testProcess3_14HRS_1MIN(self):
        "Test: At 14:01 hours, resource fails, is down"
        self.eventProcessor.process_events(FOURTEEN_HRS+ONE_MIN)
        self.assertTrue(self.rsrc1.down and not self.rsrc1.going_down)
        
    def testProcess3_14HRS_15MINS(self):
        "Test: At 14:15 hours, resource is still down"
        self.eventProcessor.process_events(FOURTEEN_HRS+FIFTEEN_MINS)
        self.assertTrue(self.rsrc1.down)
        
    def testProcess3_14HRS_16MINS(self):
        "Test: At 14:16 hours, resource is up"
        self.eventProcessor.process_events(FOURTEEN_HRS+SIXTEEN_MINS)
        self.assertTrue(self.rsrc1.up and not self.rsrc1.going_down)
        
    def testProcess3_14HRS_31MINS(self):
        "Test: At 14:30 hours, process3 run has completed"
        self.eventProcessor.process_events(FOURTEEN_HRS+THIRTY_MINS)
        self.assertEqual(self.process3.runend_tm, FOURTEEN_HRS+THIRTY_MINS)
        
        
def makeTestSuite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(BasicDowntimeTests))
    suite.addTest(loader.loadTestsFromTestCase(BasicGoingDownTests))
    suite.addTest(loader.loadTestsFromTestCase(BasicDowntimeAcquireTests1))
    suite.addTest(loader.loadTestsFromTestCase(FailureAgentTests))
    suite.addTest(loader.loadTestsFromTestCase(ExtendThroughDowntimeTests))
    suite.addTest(loader.loadTestsFromTestCase(DowntimeScheduleTests))
    suite.addTest(loader.loadTestsFromTestCase(ScheduledDowntimeAgentTests))
    suite.addTest(loader.loadTestsFromTestCase(ScheduledAndFailureDowntimeTests))
    return suite

if __name__ == '__main__':
    suite = makeTestSuite()
    unittest.main()