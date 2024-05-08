#===============================================================================
# MODULE simevent_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for the SimEvent and EventProcessor classes
#===============================================================================
from simprovise.core import simevent, simtime, SimClock, SimTime
import unittest
import copy
from heapq import heappop

class TestEvent(simevent.SimEvent):
    eventCount = 0
    processedCount = 0
    processedEvents = []
    
    def __init__(self, time, priority=1):
        super().__init__(time, priority=priority)
        TestEvent.eventCount += 1       
        self._id = TestEvent.eventCount
        
    def process_impl(self):
        TestEvent.processedCount += 1
        TestEvent.processedEvents.append(self)
        
class TestEventP2(TestEvent):
    
    def __init__(self, time):
        super().__init__(time, 2)        
        
class SimEventTests1(unittest.TestCase):
    "Tests for single SimEvent"
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        self.twoMins = SimTime(2, simtime.MINUTES)
        self.testEvent = TestEvent(self.twoMins)
        self.testEvent.register()

    def testAddEvent1(self):
        "Test: Adding a single new event should create an event heap of length 1"
        self.assertEqual(len(simevent.event_heap), 1)

    def testAddEvent2(self):
        "Test: first item on heap is correct event time"
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(tm, event.time)

    def testAddtEvent3(self):
        "Test: first item on heap is initialized time"
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(tm, self.twoMins)

    def testAddtEvent3a(self):
        "Test: time in event heap entry equals event time"
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(tm, event.time)
        
    def testAddEvent4(self):
        "Test: first item on heap is the event"
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(event, self.testEvent)
        
    def testAddEvent5(self):
        "Test: Registering same event twice (without popping) raises assert exception"
        self.assertRaises(AssertionError, lambda: self.testEvent.register())

    def testAddEvent6(self):
        "Test: Added event is registered"
        self.assertTrue(self.testEvent.is_registered())

    def testAddEvent7(self):
        "Test: deregistration - event is not registered"
        self.testEvent.deregister()
        self.assertFalse(self.testEvent.is_registered())

    def testAddEvent8(self):
        "Test: deregistration/registration - event is registered"
        self.testEvent.deregister()
        self.testEvent.register()
        self.assertTrue(self.testEvent.is_registered())

    def testAddEvent9(self):
        "Test: registration of an event scheduled prior to SimClock.now() raises"
        event = TestEvent(self.twoMins)
        SimClock.advance_to(SimTime(3, simtime.MINUTES))
        self.assertRaises(AssertionError, lambda: self.testEvent.register())
        
        
class SimEventTests2(unittest.TestCase):
    "Tests for two SimEvents scheduled at same time"
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        self.twoMins = simtime.SimTime(2, simtime.MINUTES)
        self.testEvent1 = TestEvent(self.twoMins)
        self.testEvent1.register()
        self.testEvent2 = TestEvent(self.twoMins)
        self.testEvent2.register()

    def testAdd1(self):
        "Test: Adding a two new events should create an event heap of length 2"
        self.assertEqual(len(simevent.event_heap), 2)

    def testAdd2(self):
        "Test: first item on heap is the first registered event"
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(event, self.testEvent1)

    def testAdd3(self):
        "Test: first item on heap is scheduled for initialized time"
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(tm, self.twoMins)

    def testAdd4(self):
        "Test: second item on heap is the second registered event"
        for i in range(2):
            tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(event, self.testEvent2)

    def testAdd5(self):
        "Test: second item on heap is scheduled for initialized time"
        for i in range(2):
            tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(tm, self.twoMins)
        
    def testAdd6(self):
        "Test: Registering same event twice (without popping) raises assert exception"
        self.assertRaises(AssertionError, lambda: self.testEvent1.register())

        
class SimEventPriorityTests(unittest.TestCase):
    "Tests for SimEvents of different priorities"
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        self.twoMins = simtime.SimTime(2, simtime.MINUTES)
        self.threeMins = simtime.SimTime(3, simtime.MINUTES)
        self.testEvent1 = TestEventP2(self.twoMins)
        self.testEvent1.register()
        self.testEvent2 = TestEvent(self.threeMins)
        self.testEvent2.register()
        self.testEvent3 = TestEvent(self.twoMins)
        self.testEvent3.register()

    def testAdd1(self):
        "Test: Adding a three new events should create an event heap of length 3"
        self.assertEqual(len(simevent.event_heap), 3)

    def testAdd2(self):
        "Test: first item on heap is the higher priority event"
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(event, self.testEvent3)

    def testAdd3(self):
        "Test: first item on heap is scheduled for initialized time"
        tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(tm, self.twoMins)

    def testAdd4(self):
        "Test: second item on heap is the priority 2 event"
        for i in range(2):
            tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(event, self.testEvent1)

    def testAdd5(self):
        "Test: second item on heap is scheduled for initialized time"
        for i in range(2):
            tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(tm, self.twoMins)
        
    def testAdd6(self):
        "Test: third item on heap is the latest event"
        for i in range(3):
            tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(event, self.testEvent2)

    def testAdd7(self):
        "Test: third item on heap is scheduled for initialized time"
        for i in range(3):
            tm, priority, seq, event = heappop(simevent.event_heap)
        self.assertEqual(tm, self.threeMins)
       

class SimEventProcessorTests( unittest.TestCase ): 
    "Tests for class SimEventProcessor"
    def setUp( self ):
        simevent.initialize()
        SimClock.initialize()
        # TestEvent class attribute re-initialization
        TestEvent.eventCount = 0
        TestEvent.processedCount = 0
        TestEvent.processedEvents = []

        self.eventProcessor = simevent.EventProcessor()        
        self.twoMins = simtime.SimTime(2, simtime.MINUTES)
        
    def addTestEvents(self, time, count):
        eventList = []
        for i in range(3):
            eventList.append(TestEvent(time))
        for e in eventList:
            e.register()
        return eventList
        
    def addMixedPriorityTestEvents(self, time, count):
        event1_p1 = TestEvent(time)
        event2_p2 = TestEventP2(time)
        event3_p1 = TestEvent(time)
        event4_p2 = TestEventP2(time)
        eventList = [event1_p1, event2_p2, event3_p1, event4_p2]
        prioritized_eventList = [event1_p1, event3_p1, event2_p2, event4_p2]
        for e in eventList:
            e.register()
        return prioritized_eventList
        
    def testProcessCurrentEvents1(self):
        "Test:  Register 3 events at time now - processEvents() hits all three"
        eventList = self.addTestEvents(SimClock.now(), 3)
        self.eventProcessor.process_events()                       
        self.assertEqual(TestEvent.processedEvents, eventList)
        
    def testProcessCurrentEvents2(self):
        "Test:  Register 3 events at time now - processEvents() does not advance clock"
        time1 = SimClock.now()
        eventList = self.addTestEvents(SimClock.now(), 3)
        self.eventProcessor.process_events()                       
        self.assertEqual(time1, SimClock.now())

    def testAdvanceClock1(self):
        "Test:  process events at time zero, two mins - clock is at two minutes"
        eventList = self.addTestEvents(SimClock.now(), 2)
        eventList.extend(self.addTestEvents(self.twoMins, 1))
        self.eventProcessor.process_events()                       
        self.assertEqual(self.twoMins, SimClock.now())

    def testProcessEvents1(self):
        "Test:  process events at time zero, two mins - clock is at two minutes"
        eventList = self.addTestEvents(SimClock.now(), 2)
        eventList.extend(self.addTestEvents(self.twoMins, 1))
        self.eventProcessor.process_events()                       
        self.assertEqual(TestEvent.processedEvents, eventList)

    def testProcessEventsByPriority(self):
        "Test:  process events of priority 1 and 2 in proper order"
        eventList = self.addMixedPriorityTestEvents(SimClock.now(), 2)
        self.eventProcessor.process_events()                       
        self.assertEqual(TestEvent.processedEvents, eventList)

    def testAdvanceClock2(self):
        "Test:  events at time zero, two minutes.  Process events for 1 minute.  Current time is 1 minute"
        eventList = self.addTestEvents(SimClock.now(), 2)
        eventList.extend(self.addTestEvents(self.twoMins, 1))
        self.eventProcessor.process_events(simtime.SimTime(60, simtime.SECONDS))                       
        self.assertEqual(simtime.SimTime(60, simtime.SECONDS), SimClock.now())

    def testAdvanceClock2a(self):
        "Test:  events at time zero, two minutes.  Process events for 1 minute.  event at two minutes is not processed"
        eventList = self.addTestEvents(SimClock.now(), 2)
        eventList2 = self.addTestEvents(self.twoMins, 1)
        self.eventProcessor.process_events(simtime.SimTime(60, simtime.SECONDS))                       
        self.assertEqual(TestEvent.processedEvents, eventList)

    def testAdvanceClock3(self):
        "Test:  events at time zero, two minutes.  Process events for 2 minutes.  All events processed"
        eventList = self.addTestEvents(SimClock.now(), 2)
        eventList.extend(self.addTestEvents(self.twoMins, 1))
        self.eventProcessor.process_events(simtime.SimTime(120, simtime.SECONDS) )                       
        self.assertEqual(TestEvent.processedEvents, eventList)

    def testAdvanceClock3a(self):
        "Test:  events at time zero, two minutes.  Process events for 2 minutes.  event heap is empty"
        eventList = self.addTestEvents(SimClock.now(), 2)
        eventList.extend(self.addTestEvents(self.twoMins, 1))
        self.eventProcessor.process_events(simtime.SimTime(120, simtime.SECONDS))                       
        self.assertEqual(len(simevent.event_heap), 0)

    def testAdvanceClock4(self):
        "Test:  events at time zero, two minutes.  Process events for 1 minute, and repeat.  All events processed"
        eventList = self.addTestEvents(SimClock.now(), 2)
        eventList.extend(self.addTestEvents(self.twoMins, 1))
        self.eventProcessor.process_events(simtime.SimTime(60, simtime.SECONDS) )                       
        self.eventProcessor.process_events(simtime.SimTime(120, simtime.SECONDS) )                       
        self.assertEqual(TestEvent.processedEvents, eventList)

    def testAdvanceClock4a(self):
        "Test:  events at time zero, two minutes.  Process events for 1 minute, and repeat.  event chain is empty"
        eventList = self.addTestEvents(SimClock.now(), 2)
        eventList.extend(self.addTestEvents(self.twoMins, 1))
        self.eventProcessor.process_events(simtime.SimTime(60, simtime.SECONDS))                       
        self.eventProcessor.process_events(simtime.SimTime(120, simtime.SECONDS))                       
        self.assertEqual(len(simevent.event_heap), 0)

    def testAdvanceClock5(self):
        "Test:  events at time zero, two minutes.  Process events for 3 minutes - test that current time is 3 minutes (even though last event is at two minutes"
        eventList = self.addTestEvents(SimClock.now(), 2)
        eventList.extend(self.addTestEvents(self.twoMins, 1))
        self.eventProcessor.process_events(simtime.SimTime(180, simtime.SECONDS))                                          
        self.assertEqual(simtime.SimTime(180, simtime.SECONDS), SimClock.now())
        
    def testDeregister1(self):
        "Test: deregistered event is not executed"
        eventList = self.addTestEvents(SimClock.now(), 3)
        deregisteredEvent = eventList[1]
        deregisteredEvent.deregister()
        eventList.remove(deregisteredEvent)
        self.eventProcessor.process_events()                       
        self.assertEqual(TestEvent.processedEvents, eventList)
        
    def testDeregister2(self):
        "Test: deregistered event is not executed, but still removed from heap"
        eventList = self.addTestEvents(SimClock.now(), 3)
        deregisteredEvent = eventList[1]
        deregisteredEvent.deregister()
        eventList.remove(deregisteredEvent)
        self.eventProcessor.process_events()                       
        self.assertEqual(len(simevent.event_heap), 0)
        
        
def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SimEventTests1))
    suite.addTest(unittest.makeSuite(SimEventTests2))
    suite.addTest(unittest.makeSuite(SimEventPriorityTests))
    suite.addTest(unittest.makeSuite(SimEventProcessorTests))
    return suite
        
if __name__ == '__main__':
    unittest.main()
    