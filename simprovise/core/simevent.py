#===============================================================================
# MODULE simevent
#
# Copyright (C) 2014-2016 Howard Klein - All Rights Reserved
#
# Defines the SimEvent and EventProcessor classes.
#
# SimEvent is a base class for specialized event types. This base class
# maintains the simulated time when the event is to occur, and implements a
# register() method that registers the event for eventual
# processing/execution by placing it on an event queue (see below). An event
# is executed via its process() method, which delegates to process_impl(),
# which should be overridden by SimEvent subclasses. A registered event may
# also be removed from the event queue via it's deregister() method. The
# primary use case for deregistration is to facilitate event interruption/
# rescheduling.
#
# The event queue is implemented via a global heap (module heapq), ordered
# by event time and (for events scheduled for the same time) the order of
# registration.  The implementation follows the priority queue example in
# the heapq module documentation, including a separate global dictionary
# (entry_finder) that faciliates deregistration.
#
# SimEvent registration places the event, along with it's scheduled execution
# time and registration sequence number, into the event heap via heappush().
# Deregistration finds that heap queue entry and changes the event element to
# a REMOVED value, indicating that it should be ignored.  (The entry cannot
# be removed from the middle of the queue without violating the heap invariant.)
#
# EventProcessor.processEvents() essentially runs the simulation - it pops
# and processes events in the entry heap queue, advancing the simulation clock
# as required, until we either reach the end time of the simulation or run out
# of events.
#===============================================================================
from abc import ABCMeta, abstractmethod
from heapq import heappop, heappush
import itertools
from greenlet import greenlet        # pylint: disable=E0611
from simprovise.core import SimClock, SimTime, SimLogging
from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)

event_heap = []
entry_finder = {}
counter = itertools.count()
event_processing_greenlet = greenlet.getcurrent()
REMOVED = '<removed-event>'

@apidocskip
def initialize():
    """
    (re)initialize the entry heap data structures for a new simulation run.
    """
    global event_heap
    global entry_finder
    global counter
    global event_processing_greenlet
    event_heap = []
    entry_finder = {}
    counter = itertools.count()
    event_processing_greenlet = greenlet.getcurrent()

class SimEvent(metaclass=ABCMeta):
    """
    Base class for simulation events
    """
    __slots__ = ('_time', '_sequencenum')
    def __init__(self, tm):
        assert isinstance(tm, SimTime), 'SimEvent constructor parameter ' + str(tm) + ' is not a SimTime'
        assert tm >= SimClock.now(), 'SimEvent constructor parameter ' + str(tm) + ' is less than current time:' + str(SimClock.now())
        self._time = tm.makeCopy()
        self._sequencenum = -1

    def register(self):
        """
        Add event to the list of events set to fire at that event's time
        """
        assert not self.isRegistered(), 'SimEvent ' + str(self) + ' is already registered'
        self._sequencenum = next(counter)
        entry = [self._time, self._sequencenum, self]
        heappush(event_heap, entry)
        entry_finder[self] = entry

    def isRegistered(self):
        """
        Returns True if the event is currently in the events chain - i.e., it
        is scheduled for execution now or in the simulated future. Returns
        False if it has never been registered, or has already executed.
        """
        return self._sequencenum >= 0 and self in entry_finder

    def deregister(self):
        """
        Marks the event as removed from the event list (heapq) (if it is
        still there), per the heapq documentation priority queue example. (We
        can't simply remove the event entry, as that would invalidate the
        heapq invariant. So we change the entry to mark it as removed, by
        replacing the event with a REMOVED indicator string) Returns True if
        the event was removed, False if the event is not found on the event
        list (because it was either already executed or previously
        deregistered)

        Used as part of the wait interrupt implementation.  (Get rid of the
        resumeAt event, and issue an interrupt event instead.)
        """
        if not self.isRegistered():
            return False

        entry = entry_finder.pop(self)
        entry[-1] = REMOVED
        return True

    @abstractmethod
    def process_impl(self):
        """
        Polymorphic guts of event processing
        """
        pass

    def process(self):
        """
        Process an event by calling it's polymorphic process_impl() method.
        The extra layer of delegation is preserved in case we want to do
        some generic housekeeping around the event.
        """
        self.process_impl()

    @property
    def time(self):
        """
        The simulated time that the event is scheduled to be processed/executed.
        """
        return self._time

    def __str__(self):
        return self.__class__.__name__  + " scheduled time:" + str(self.time)


class EventProcessor(object):
    """
    Simulation event manager/processor
    """
    def __init__(self):
        """
        Initializer re-initializes the event heap and dictionary, to get rid
        of any events leftover from a previous run.
        """
        initialize()

    def process_events(self, until_time=None):
        """
        Processes (executes) events until until_time; if until_time is None,
        processes until we run out of events.

        Returns the number of events processed.
        """
        global event_processing_greenlet
        event_processing_greenlet = greenlet.getcurrent()
        processCount = itertools.count()

        while event_heap:
            # Pop and ignore if the next entry is a removed event
            if event_heap[0][-1] is REMOVED:
                heappop(event_heap)
            else:
                next_event_time = event_heap[0][0]
                if until_time is not None and next_event_time > until_time:
                    SimClock.advance_to(until_time)
                    break

                next_event = heappop(event_heap)[-1]
                entry_finder.pop(next_event)
                assert next_event.time == next_event_time, "entry time and event time do not match!"
                SimClock.advance_to(next_event_time)
                next_event.process_impl()
                next(processCount)

        # if we run out of events before until time, advance the clock
        if until_time is not None and SimClock.now() < until_time:
            SimClock.advance_to(until_time)

        return next(processCount)

if __name__ == '__main__':
    import time

    class TestEvent(SimEvent):
        def process_impl(self): pass

    n = 100000
    elist = [SimTime(199) for i in range(n)]
    d = {}
    cpustart = time.clock()
    for e in elist:
        d[e] = 42

    for e in elist:
        x = e in d
        assert x, "not found"

    cpuend = time.clock()
    print(cpuend - cpustart)






