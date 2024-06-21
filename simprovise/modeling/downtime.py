#===============================================================================
# MODULE downtime
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the DowntimeAgentMixin, SimDowntimeAgent, SimResourceFailureAgent,
# SimScheduledDowntimeAgent, DowntimeSchedule and related event classes.  
#===============================================================================
__all__ = ['SimDowntimeAgent', 'SimResourceFailureAgent',
           'SimScheduledDowntimeAgent', 'DowntimeSchedule']

from typing import NamedTuple

from simprovise.core import SimError
from simprovise.core.simclock import SimClock
from simprovise.core.simlogging import SimLogging
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.modeling.agent import SimAgent, SimMsgType
from simprovise.core.simevent import SimEvent
from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)

_DOWNTIME_ERROR = "Downtime Error"


class DowntimeAgentMixin(object):
    """
    A mixin class for implementing default DowntimeAgent functionality:
        Methods that send messages to a :class:`~.resource.SimResource` assignment
        agent to request a resource takedown or bringup
             :meth:`_request_resource_takedown`
             :meth:`_request_resource_bringup`

        Handlers for the responses to these messages:
            :meth:`_handle_resource_down`
            :meth:`_handle_resource_up`
            
    Should be inherited with class :class:`~.agent.SimAgent` or a `SimAgent`
    subclass. A class that inherits `DowntimeAgentMixin` must implement
    two other methods:
        _resource_down_impl()
        _resource_up_impl()
        
    These methods are called by :meth:`_handle_resource_down` and
    :meth:`_handle_resource_up`, respectively. No-op implementations are
    provided by :class:`SimDowntimeAgent`.
   
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._downrequests = set()
        self._fulfilled_downrequests = set()
        self._uprequests = set()
        self.register_handler(SimMsgType.RSRC_DOWN, self._handle_resource_down)
        self.register_handler(SimMsgType.RSRC_UP, self._handle_resource_up)
        
    def request_resource_takedown(self, resource):
        """
        Initiate a resource takedown by sending a takedown request to the
        resource's assignment agent. Raises a :class:`~.simexception.SimError`
        if this agent has previously made a request to take down this resource
        and either:
        
        a) This agent is awaiting a response to that request, or
        b) The request was taken down successfully in response to the request
           and this agent has not subsequently requested that the resource
           be brought back up, or
        c) The agent has made a bringup request that has not yet been
           handled/completed/responded to by the assignment agent
                  
        :param resource: Resource to take down
        :type resource:  :class:`~.resource.SimResource`

        """
        # Make sure this downtime agent hasn't already requested a takedown
        # (without an intervening bringup or takedown failure)
        if resource in self._downrequests:
            msg = "This agent already has an open request to take down resource {0}"
            raise SimError(_DOWNTIME_ERROR, msg, resource.element_id)
        if resource in self._fulfilled_downrequests:
            msg = "Request to take down resource {0} that this agent has already taken down"
            raise SimError(_DOWNTIME_ERROR, msg, resource.element_id)
        if resource in self._uprequests:
            msg = "Request to take down resource {0} while waiting for a response to a bringup request by this agent"
            raise SimError(_DOWNTIME_ERROR, msg, resource.element_id)
        
        self._downrequests.add(resource)
        msgType = SimMsgType.RSRC_TAKEDOWN_REQ
        msgData = resource
        msg, responses = self.send_message(resource.assignment_agent, msgType, msgData)
        
        # Delegate handling of the response message to the handler (we didn't really
        # need to intercept)
        assert len(responses) <= 1, "Resource Takedown Request message expects zero or one responses"
        if responses:
            response = responses[0]
            self._dispatch_message(response)
        
    def request_resource_bringup(self, resource):
        """
        Initiate a resource bringup by sending a bringup request to the
        resource's assignment agent. Raises a :class:`~.simexception.SimError`
        if this request does not match a completed, successful takedown
        request.   
                  
        :param resource: Resource to bring up
        :type resource:  :class:`~.resource.SimResource`

        """
        # Make sure this bringup request matches an earlier, successfully completed
        # down request
        if not resource in self._fulfilled_downrequests:
            msg = "Request to bring up resource {0} that this agent has not successfully taken down"
            raise SimError(_DOWNTIME_ERROR, msg, resource.element_id)
        
        self._fulfilled_downrequests.remove(resource)
        self._uprequests.add(resource)
        msgType = SimMsgType.RSRC_BRINGUP_REQ
        msgData = resource
        msg, responses = self.send_message(resource.assignment_agent, msgType, msgData)
        
        # Delegate handling of the response message to the handler (we didn't really
        # need to intercept)
        assert len(responses) <= 1, "Resource Bringup Request message expects zero or one responses"
        if responses:
            response = responses[0]
            self._dispatch_message(response)
               
    def _handle_resource_down(self, msg):
        """
        The handler registered to process resource down (RSRC_DOWN) messages.
        
        RSRC_DOWN messages are sent by the resource assignment agent in
        response to RSRC_TAKEDOWN_REQ messages sent by this agent. These
        response messages contain two data items:
        
        - the resource that was the subject of the takedown request
        - a flag (takedown_successful) indicating whether or not the assignment
          agent did in fact take down the resource.
          
        This handler parses the response message; if the takedown did not
        occur, it removes the resource from the down requests set, since this
        agent should not attempt to bring up a resource when the takedown
        failed. It then delegates further processing to _resource_down_impl()
        which should be implemented by either the agent class also
        inheriting this mixin or a subclass.

        :param msg: Resource bringup message (SimMsgType RSRC_UP)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    `True` always, as the message is always handled
        :rtype:     `bool`

        """
        assert msg.msgType == SimMsgType.RSRC_DOWN, "Invalid message type passed to _handle_resource_down()"
        resource, takedown_successful = msg.msgData
        assert resource in self._downrequests, "ResourceDown message sent to agent that did not request it's takedown"
        
        self._downrequests.remove(resource)           
        if takedown_successful:
            self._fulfilled_downrequests.add(resource)
            
        self._resource_down_impl(resource, takedown_successful)
        
        return True
        
    def _handle_resource_up(self, msg):
        """
        The handler registered to process resource down (RSRC_UP) messages.
        
        RSRC_UP messages are sent by the resource assignment agent in
        response to RSRC_BRINGUP_REQ messages sent by this agent. These
        response messages contain one data item - the resource that was
        brought up. Unlike takedown requests, bring up requests always
        succeed (eventually)
          
        This handler parses the response message and delegates further
        processing to _resource_up_impl() which should be implemented by 
        either the agent class also inheriting this mixin or a subclass.

        :param msg: Resource bringup message (SimMsgType RSRC_UP)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    `True` always, as the message is always handled
        :rtype:     `bool`

        """
        assert msg.msgType == SimMsgType.RSRC_UP, "Invalid message type passed to _handle_resource_up()"
        resource = msg.msgData
        self._uprequests.remove(resource)
        self._resource_up_impl(resource)
        return True


@apidoc
class SimDowntimeAgent(DowntimeAgentMixin, SimAgent):
    """
    Useful base class for a stand-alone downtime agent.
    """        
    def _resource_down_impl(self, resource, takedown_successful):
        """
        Called by RSRC_DOWN message handler. no-op default implementation

        :param resource:            Resource that this agent requested to 
                                    take down
        :type resource:             :class:`~.resource.SimResource`
        
        :param takedown_successful: True if the resource was taken down.
                                    False if not taken down.
        :type takedown_successful:  `bool`
        
        """
        pass
    
    def _resource_up_impl(self, resource):
        """
        Called by RSRC_UP message handler. no-op default implementation

        :param resource: Resource that this agent requested to bring up
        :type resource:  :class:`~.resource.SimResource`
        
        """
        pass


@apidoc
class SimResourceFailureAgent(SimDowntimeAgent):
    """
    A SimDowntimeAgent that generates failure downtimes for a single resource.
    
    Failures are defined by two time intervals:
    
    - Time to Failure: the time from the end of the previous failure (i.e.,
      the last time the resource came back up from a failure) to the start
      of the next failure.
      
    - Time to Repair: the time from the start of a failure until it comes
      back up.
      
    These two time parameters are obtained by sampling from passed
    distributions.
    
    Note that this agent initiates both the start and end of failures by
    sending requests to the resource's assignment agent. The default
    assignment agent implementation responds to these requests immediately,
    but other implementations may not. If the assignment agent delays
    responding to a takedown request, for example, the time to repair
    starts after that delay.

        :param resource:               Resource to be brought up and down for
                                       failure.
        :type resource:                :class:`~.resource.SimResource`
        
        :param timeToFailureGenerator: A generator of :class:`~simtime.SimTime`
                                       values for time to failure (as measured
                                       from the end of the previous failure).
                                       Typically created by a call to
                                       :class:`~.simrandom.SimDistribution`.
        :type timeToRepairGenerator:  `generator`
        
        :param timeToRepairGenerator: A generator of :class:`~simtime.SimTime`
                                      values for time to repair following a
                                      failure. Typically created by a call to
                                      :class:`~.simrandom.SimDistribution`.
        :type timeToRepairGenerator:  `generator`
        
    """
    __slots__ = ('_resource', '_timeToFailureGenerator', '_timeToRepairGenerator')
    
    def __init__(self, resource, timeToFailureGenerator, timeToRepairGenerator):
        super().__init__()
        self._resource = resource
        self._timeToFailureGenerator = timeToFailureGenerator
        self._timeToRepairGenerator = timeToRepairGenerator
               
    def final_initialize(self):
        """
        Perform initialization that must occur after the simulation clock,
        event processor, and random number streams are initialized.
        """
        initialTakedownTime = SimClock.now() + next(self._timeToFailureGenerator)
        initialEvent = TakeDownResourceEvent(self, self._resource, 
                                             initialTakedownTime)
        initialEvent.register()
        
    def _resource_down_impl(self, resource, takedown_successful):
        """
        Called by the downtime agent's RSRC_DOWN message handler. If the
        takedown was successful, schedule the BringUp event. If the
        takedown was NOT successful, this implementation assumes the takedown
        was not merely delayed but cancelled - so we schedule another takedown.        
        """
        if takedown_successful:
            bringupTime = SimClock.now() + next(self._timeToRepairGenerator)
            buEvent = BringUpResourceEvent(self, self._resource, bringupTime)
            buEvent.register()
        else:
            # Unsuccessful takedown. Schedule another one
            nextTakedownTime = SimClock.now() + next(self._timeToFailureGenerator)
            tdEvent = TakeDownResourceEvent(self, self._resource, nextTakedownTime)
            tdEvent.register()
    
    def _resource_up_impl(self, resource):
        """
        Called by the downtime agent's RSRC_UP message handler. Just
        schedules the next takedown event.
        """
        nextTakedownTime = SimClock.now() + next(self._timeToFailureGenerator)
        tdEvent = TakeDownResourceEvent(self, self._resource, nextTakedownTime)
        tdEvent.register()
        

@apidoc
class DowntimeSchedule(object):
    """
    Class representing a fixed downtime schedule, accessed via a generator
    producing a SimTime pair for the start and end of the the next down time
    in the schedule.
    
    The schedule is defined in terms of a total schedule cycle length and a
    list of (start time, time length) pairs, where each pair defines one
    down time period in the cycle. The cycle repeats once all down times for
    the current cycle have been generated.
        
    For example, a nine hour workday with two 15 minute breaks and a
    30 minute lunch could be defined (with appropriate constants) as::
    
        breaks = [(TWO_HRS, FIFTEEN_MINS), (FOUR_HRS, THIRTY_MINS),
                  (SEVEN_HRS, FIFTEEN_MINS)])
        workSchedule = DowntimeSchedule(NINE_HRS, breaks)
    
    For this schedule, the first six generated down time start/end pairs
    would be:   
        2:00,  2:15
        4:00,  4:30
        7:00,  7:15
        11:00, 11:15
        13:00, 13:30
        16:00, 16:15

        :param scheduleLength: The length of each schedule cycle
        :type scheduleLength:  :class:`~.simtime.SimTime` 

        :param downIntervals:  An iterable collection of
                               (start time, period length) pairs
        :type downIntervals:   Iterable of pairs of :class:`~.simtime.SimTime`
                               None
        
    """
    class Interval(NamedTuple):
        start: SimTime
        length: SimTime
        
    def __init__(self, scheduleLength, downIntervals):
        self._scheduleLength = SimTime(scheduleLength)
        if self._scheduleLength <= 0:
            msg = "Schedule Length {0} must be a SimTime > 0"
            raise SimError(_DOWNTIME_ERROR, msg, self._scheduleLength)

        downIntervals.sort()
        self._intervals = [DowntimeSchedule.Interval(SimTime(d[0]), SimTime(d[1]))
                           for d in downIntervals]
        self._validate(self._intervals)

    def down_intervals(self):
        """
        Generator yielding the start and end of the next down time
        according to this schedule
        """
        scheduleBeginTime = SimClock.now()
        while True:
            for interval in self._intervals:
                startTime = scheduleBeginTime + interval.start
                endTime = startTime + interval.length
                yield DowntimeSchedule.Interval(startTime, interval.length)
#                yield startTime, endTime
            
            scheduleBeginTime += self._scheduleLength
            
    def _validate(self, intervals):
        """
        Validate the passed Interval list, raising if error is found.
        Errors include:
        - negative interval start time or interval length
        - overlapping intervals
        - interval starting or ending after the the schedule length
        """
        prevEnd = 0
        for interval in intervals:
            if interval.start < 0:
                msg = "Start of interval {0} must be a SimTime >= 0"
                raise SimError(_DOWNTIME_ERROR, msg, interval)
            if interval.start >= self._scheduleLength:
                msg = "Start of interval {0} must be a SimTime less than the schedule length: {1}"
                raise SimError(_DOWNTIME_ERROR, msg, interval, self._scheduleLength)
            if interval.length <= 0:
                msg = "Length of interval {0} must be a SimTime > 0"
                raise SimError(_DOWNTIME_ERROR, msg, interval)
            if interval.start <= prevEnd:
                msg = "Start of interval {0} must be a SimTime > the end of the previous interval"
                raise SimError(_DOWNTIME_ERROR, msg, interval)
                
            end = interval.start + interval.length            
            if end > self._scheduleLength:
                msg = "End of interval {0} must be a SimTime >= the schedule length: {1}"
                raise SimError(_DOWNTIME_ERROR, msg, interval, self._scheduleLength)
            prevEnd = end
    

@apidoc
class SimScheduledDowntimeAgent(SimDowntimeAgent):
    """
    A SimDowntimeAgent that generates downtimes for a single resource based on
    a :class:`DowntimeSchedule`.
    
    If the assignment agent for the resource "behaves" - successfully takes
    down and brings up the resource immediately upon request - the result
    will be continuously cycling regular downtimes according to the passed
    :class:`DowntimeSchedule`. If the assignment agent does not behave:
    
    - If the takedown succeeds but is delayed, the scheduled downtime will
      start when the resource comes down and last for the scheduled length.
      If the end of the downtime overlaps with the next scheduled downtime,
      that next scheduled downtime is skipped. (If the delay is longer,
      multiple scheduled downtimes may be skipped - basically, when the
      resource comes back up, the agent looks at the current simulated time
      and gets the next scheduled downtime that doesn't start before that
      time.)
      
    - If the takedown is not successful, that downtime interval is skipped.
      If there was a delay in returning a non-successful takedown,
      subsequent scheduled downtime periods may be skipped as well, based
      on the length of the delay. (It follows the same algorithm described
      above, looking for the next schedule period whose start time hasn't
      already passed.)

        :param resource:         Resource to be brought up and down on sched.
        :type resource:          :class:`~.resource.SimResource`
        
        :param downtimeSchedule: The regularly scheduled fixed down intervals
                                 for the resource.
        :type downtimeSchedule:  :class:`DowntimeSchedule`
          
    """
    __slots__ = ('_resource', '_downtimeSchedule', '_downtimeGenerator',
                 '_interval')
    
    def __init__(self, resource, downtimeSchedule):
        super().__init__()
        self._resource = resource
        self._downtimeSchedule = downtimeSchedule
        self._downtimeGenerator = None
        self._interval = None
               
    def final_initialize(self):
        """
        Perform initialization that must occur after the simulation clock
        and event processor are initialized:
        - Creates the downtime generator, which yields schedule intervals
        - Creates and registers  the first takedown event
        """
        assert SimClock.now() == 0, "final initialization called after SimClock advance or before initialization"
        self._downtimeGenerator = self._downtimeSchedule.down_intervals()
        self._interval = self._schedule_next_takedown_event()
               
    def _schedule_next_takedown_event(self):
        """
        Gets the next valid interval from the downtime interval generator
        by skipping those whose start time has already passed. (These skips
        are required if on an earlier cycle, the resource either did not
        come down or did not come back up in a timely fashion)
        
        Then creates/registers a takedown event for that interval, and
        returns the interval.
        """
        nextInterval = next(self._downtimeGenerator)
        while nextInterval.start <= SimClock.now():
            nextInterval = next(self._downtimeGenerator)
            
        takedownEvent = TakeDownResourceEvent(self, self._resource,
                                              nextInterval.start)
        takedownEvent.register()
        return nextInterval
                    
    def _resource_down_impl(self, resource, takedown_successful):
        """
        Called by the downtime agent's RSRC_DOWN message handler
        For successful takedowns, create/register a corresponding
        brinup event. If the takedown was not successful, move on
        and schedule the next takedown, updating  the current
        downtime interval.
        """
        if takedown_successful:
            downEndTime = SimClock.now() + self._interval.length
            buEvent = BringUpResourceEvent(self, self._resource, downEndTime)
            buEvent.register()
        else:
            self._interval = self._schedule_next_takedown_event()            
            
    def _resource_up_impl(self, resource):
        """
        Called by the downtime agent's RSRC_UP message handler. Just
        schedules the next takedown  event and update the current
        downtime interval.
        """
        self._interval = self._schedule_next_takedown_event()

                
class TakeDownResourceEvent(SimEvent):
    """
    An event that initiates a single resource takedown via a passed
    SimDownTimeAgent.
    """
    __slots__ = ('_agent', '_resource')
    
    def __init__(self, downtimeAgent, resource, tm):
        super().__init__(tm, priority=3)
        self._agent = downtimeAgent
        self._resource = resource
        
    def process_impl(self):
        """
        Tell the downtime agent to request a resource takedown
        """
        self._agent.request_resource_takedown(self._resource)
    
    
class BringUpResourceEvent(SimEvent):
    """
    An event that initiates a single resource bring-up via a passed
    SimDownTimeAgent. Should be the same agent that brought the
    resource down.
    """
    __slots__ = ('_agent', '_resource')
    
    def __init__(self, downtimeAgent, resource, tm):
        super().__init__(tm, priority=3)
        self._agent = downtimeAgent
        self._resource = resource
        
    def process_impl(self):
        """
        Tell the downtime agent to request a resource bringup
        """
        self._agent.request_resource_bringup(self._resource)
        
    
if __name__ == '__main__':
    from simprovise.core import SimSimpleResource, SimDistribution
    from simprovise.core import simtime, simevent, SimTime, SimClock
    
    TWO_HRS = simtime.SimTime(2, tu.HOURS)
    FOUR_HRS = simtime.SimTime(4, tu.HOURS)
    SEVEN_HRS = simtime.SimTime(7, tu.HOURS)
    NINE_HRS = simtime.SimTime(9, tu.HOURS)
    BREAK_LEN = SimTime(15, tu.MINUTES)
    LUNCH_LEN = SimTime(30, tu.MINUTES)
    
    
    rsrc = SimSimpleResource("testResource")
    timeToFailureGenerator = SimDistribution.constant(SimTime(4, tu.MINUTES))
    timeToRepairGenerator = SimDistribution.constant(SimTime(2, tu.MINUTES))
    failureAgent = SimResourceFailureAgent(rsrc, timeToFailureGenerator, timeToRepairGenerator)

    breaks = [(TWO_HRS, BREAK_LEN), (FOUR_HRS, LUNCH_LEN), (SEVEN_HRS, BREAK_LEN)]
    sched = DowntimeSchedule(NINE_HRS, breaks)
    rsrc2 = SimSimpleResource("testResource2")
    scheduleAgent = SimScheduledDowntimeAgent(rsrc2, sched)
    
    SimClock.initialize()
    simevent.initialize()
    eventProcessor = simevent.EventProcessor()
            
    SimAgent.final_initialize_all()
  
    for i in range(15):
        n = eventProcessor.process_events(SimTime(i, tu.MINUTES))
        print(i, n, "events processed; resource up:", rsrc.up)
        
    for i in range(30, 1200, 15):      
        n = eventProcessor.process_events(SimTime(i, tu.MINUTES))
        tm = SimClock.now().to_hours()
        print(tm, "resource2 up", rsrc2.up)
        

    #SimClock.initialize()
  
    #intervals = sched.down_intervals() 
    #for i in range(10):
        #start, end = next(intervals)
        #print(start.to_hours(), end.to_hours())
    
