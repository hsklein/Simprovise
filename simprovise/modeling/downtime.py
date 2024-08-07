#===============================================================================
# MODULE downtime
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the DowntimeAgentMixin, SimDowntimeAgent, SimResourceFailureAgent,
# SimScheduledDowntimeAgent, DowntimeSchedule and related event and
# exception classes.  
#
# This program is free software: you can redistribute it and/or modify it under 
# the terms of the GNU General Public License as published by the Free Software 
# Foundation, either version 3 of the License, or (at your option) any later 
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#===============================================================================
__all__ = ['SimDowntimeAgent', 'SimResourceFailureAgent',
           'SimScheduledDowntimeAgent', 'DowntimeSchedule',
           'SimResourceDownException', 'SimResourceUpException']

from typing import NamedTuple
from enum import Enum

from simprovise.core import SimError
from simprovise.core.simclock import SimClock
from simprovise.core.simlogging import SimLogging
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.modeling.agent import SimAgent, SimMsgType
from simprovise.modeling.resource import SimResource
from simprovise.core.simevent import SimEvent
from simprovise.core.simexception import SimInterruptException
from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)

_DOWNTIME_ERROR = "Downtime Error"

class DownAction(Enum):
    """
    An enum used to indicate the last action performed by a
    :class:`SimDowntimeAgent`.
    """
    UP = 'Up'
    GOING_DOWN = 'GoingDown'
    DOWN = 'Down'


@apidoc
class SimDowntimeAgent(SimAgent):
    """
    Base class for agents that control downtime for a single
    :class:`resource <.resource.SimResource>`.
              
    :param resource: Resource being managed by this agent
    :type resource:  :class:`~.resource.SimResource`
    
    Every `SimDowntimeAgent` has a single resource, but every resource can
    have zero or more downtime agents; e.g. one for failures and one for
    scheduled breaks.
    
    When a resource has multiple downtime agents, the down periods they
    specify can overlap; the resource will be considered down, by default,
    until all overlapping downtimes complete.
    
    The primary public methods for this class are:
    
    - :meth:`start_resource_takedown`, which initiates a takedown of the
      agent's resource. The base class implementation takes the resource
      down immediately. Subclasses could choose to delay the takedown until
      the right conditions are met, typically by setting the resource's
      status to `going-down` via method :meth:`_set_resource_going_down`.
      (When a resource is "going down", it is still considered up, but
      by default it is not available for new resource assignments.)
      
    - :meth:`bringup_resource`, which ends the down time started by this
      agent's resource takedown. Note that if another downtime agent has
      also taken down this resource, the resource will not come up/be
      available as a result of this call.
      
    Typically, these methods are invoked by :class:`TakeDownResourceEvent`
    and :class:`BringUpResourceEvent` respectively, and not model-specific
    code; in most cases - e.g. :class:`SimResourceFailureAgent`,
    :class:`SimScheduledDowntimeAgent`, and any of their subclasses -
    the agent initiates all takedown and bring-up actions by scheduling
    those events. But it is possible to use code, such as a monitor process,
    that calls these methods directly instead.
    
    Inter-Agent Communication
    =========================
    
    A resource's assignment agent and all of it's downtime agents
    communicate/coordinate with each other via messages.
    :class:`downtime agents <>SimDowntimeAgent>` send the following
    messages to the resource agent and any other downtime agents:
    
    - After a resource takedown which actually changes the resource
      status to down (i.e., the resource was not already down thanks to
      a different downtime agent), the downtime agent sends ``RSRC_DOWN``
      message(s) to the other agent(s).
      
    - After a resource going-down which actually changes the resource
      status to going-down (i.e., again a different downtime agent
      didn't beat this agent to the punch), the downtime agent sends
      ``RSRC_GOING_DOWN`` message(s) to the other agent(s) .
      
    - After a resource bringup (with the same caveat about other downtime
      agents), the downtime agent sends ``RSRC_UP`` message(s) to the other
      agent(s).
      
    - After a resource release, the resource assignment agent sends
      ``RSRC_RELEASE`` messages to all of the resource's downtime agents.
      
    :class:`SimDowntimeAgent` includes handler methods for all of these
    message types.
    
    Subclassing by Model Developers
    *******************************
       
    :class:`SimDowntimeAgent`, :class:`SimResourceFailureAgent`, and
    :class:`SimScheduledDowntimeAgent` are designed to be subclassed by
    model developers.
    
    Methods that (may be) Overridden by Subclasses
    +++++++++++++++++++++++++++++++++++++++++++++++
    
    Model-specific downtime agent subclasses would typically override
    one or more of the following methods:
    
    - :meth:`start_resource_takedown`.  As noted above, a modeler might
      choose to delay takedown by calling :meth:`_set_resource_going_down`
      if the resource is currently in-use.
      
    - :meth:`_next_downtime`. Called at the start of a simulation and again
      every time the resourceis brought back up. If it returns a
      :class:`~simprovise.core.simtime.SimTime` then the next takedown will
      be scheduled for that time. The :class:`SimDowntimeAgent` implementation
      returns ``None``, so it does no scheduling on it's own.
      :class:`SimResourceFailureAgent` and :class:`SimScheduledDowntimeAgent`
      do generate takedown times, via a (typically random) generator in the
      case of the failure agent, and according to a schedule in the case of
      the scheduled downtime agent.
      
    - :meth:`_next_bringuptime`. Called every time the resource is taken down
      by this agent (**NOT** when the agent invokes just resource-going-down.)
      If it returns a :class:`~simprovise.core.simtime.SimTime` then the 
      bring-up will be scheduled for that time. Again the
      :class:`SimDowntimeAgent` implementation returns ``None``, so it does
      no scheduling on it's own.
      
    Model developers *might* also override one or more of the agent's
    message handler methods:
    
    - :meth:`_handle_resource_down`. Handles ``RSRC_DOWN`` messages.
      The base implementation takes the resource down if the agent had
      previously set it to "going down" via :meth:`_set_resource_going_down`.
    
    - :meth:`_handle_resource_goingdown`. Handles ``RSRC_GOING_DOWNDOWN``
      messages. The base implementation does nothing.

    - :meth:`_handle_resource_up`. Handles ``RSRC_UP`` messages. The base
      implementation does nothing.

    - :meth:`_handle_resource_release`. Handles ``RSRC_RELEASE`` messages.
      The base implementation takes down the resource
      (:meth:`_takedown_resource`) IF:
      
      * The agent had previously set the resource to "going down", and
      * The resource is now completely idle (not in-use)
    
    All handler method implementations should return ``True``, to indicate
    that the message is, in fact, handled. (Otherwise it will be erroneously
    queued.)
    
    Methods to be Used/Called by Model-Specific Subclasses
    +++++++++++++++++++++++++++++++++++++++++++++++++++++++
    
    The model-specific downtime agent code will typically call one or
    bool of the following :class:`SimDowntimeAgent` internal methods as part of
    the subclass implementation:
    
    - :meth:`_takedown_resource`. Takes down the resource immediately and
      performs any required notifications. The only call of the base
      :meth:`start_resource_takedown` implementation.
      
    - :meth:`_set_resource_going_down`. Sets (or at least ensures that)
      the resource to "going down" status and performs any required
      notifications.
   
    """
    __slots__ = ('_resource', '_lastAction', '_timeoutEvent')
    
    def __init__(self, resource):
        super().__init__()
        assert resource, "DowntimeAgent resource is null"
        assert isinstance(resource, SimResource), "Downtime resource not a SimResource"
        self._resource = resource
        self._lastAction = DownAction.UP
        self._timeoutEvent = None
        self.register_handler(SimMsgType.RSRC_DOWN, self._handle_resource_down)
        self.register_handler(SimMsgType.RSRC_GOING_DOWN,
                              self._handle_resource_goingdown)
        self.register_handler(SimMsgType.RSRC_UP, self._handle_resource_up)
        self.register_handler(SimMsgType.RSRC_RELEASE,
                              self._handle_resource_release)
        
        resource.add_downtime_agent(self)
       
    @apidocskip 
    def final_initialize(self):
        """
        Perform initialization that must occur after the simulation clock,
        event processor, and random number streams are initialized - in
        this case, schedule the first down time.
        """
        self._schedule_next_takedown()
        
    @property
    def resource(self):
        """
        Return the resource associated with this :class:`SimDowntimeAgent`
        """
        return self._resource
        
    @property
    def last_action(self):
        """
        Returns the last action taken by this downtime agent, one of:
        - DownAction.GOING_DOWN
        - DownAction.DOWN
        - DownAction.UP
        
        :return: The last action taken by this agent
        :rtype:  :class`DownAction`
        
        """
        return self._lastAction
        
    def start_resource_takedown(self):
        """
        Initiate a resource takedown. The default implementation just
        takes the resource down immediately, regardless.
        
        Subclasses may override this method and call
        :meth:`_set_resource_going_down` instead under the appropriate
        circumstances - e.g., if we do not want the resource to go on
        break while serving a customer.
        """
        self._takedown_resource()
        
    def _set_resource_going_down(self, timeout=None):
        """
        Set the resource status to going down, and notify all of the
        resource's other agents (assignment and downtime) of that status.
        If the resource is already going down, skip te set and the
        notification, but update this agent's status.
        
        The resource must not already be down.
        
        :meta public:
        """
        if self._lastAction != DownAction.UP:
            msg = "Downtime agent trying to set resource ({0}) to going down more than once or after taking it down"
            raise SimError(_DOWNTIME_ERROR, msg, self._resource.element_id)
        if self._resource.down:
            msg = "Downtime agent trying to set resource ({0}) to going down that is already down"
            raise SimError(_DOWNTIME_ERROR, msg, self._resource.element_id)
        
        assert not self._resource.down, "resource is already down"
        assert self._lastAction == DownAction.UP
        
        resource = self._resource
        if not self._resource.going_down:           
            resource._start_going_down()
            self._send_notifications(SimMsgType.RSRC_GOING_DOWN)
            
        self._lastAction = DownAction.GOING_DOWN
        
        if timeout:
            self._timeoutEvent = SimGoingDownTimeOutEvent(self, timeout)
            self._timeoutEvent.register()
         
    @apidoc
    def _takedown_resource(self):
        """
        Take down the resource and notify the resource's other agents
        (assignment and downtime) if the resource is newly down. Also
        notify any :class:`processes <simprovise.modeling.process.SimProcess>`
        assigned to the resource by raising a :class:`SimResourceDownException`.
        
        Then schedule a bringup event (if :meth:`_next_downtime` is
        overridden to return a :class:`~simprovise.core.simtime.SimTime`
        value).
        
        :meta public:
        """
        if self._lastAction == DownAction.DOWN:
            msg = "Downtime agent cannot take down resource ({0}) more than once"
            raise SimError(_DOWNTIME_ERROR, msg, self._resource.element_id)
        
        # If the resource was in the going-down state with a timeout scheduled,
        # cancel the timeout and reset the Errors
        if self._timeoutEvent:
            assert self.last_action == DownAction.GOING_DOWN, "Going-down timeout without going-down last action"
            self._timeoutEvent.deregister()
            self._timeoutEvent = None
        
        resource = self._resource       
        alreadyDown = resource.down
        resource._takedown()
        self._lastAction = DownAction.DOWN
        if not alreadyDown:
            # The resource is newly down. Interrupt any processes using the
            # resource, and then schedule assignment processing in case new
            # resource requests are made as a result.
            
            # Multiple assignments for this resource might refer to the same 
            # process. We only want to interrupt each process once, so create
            # a set first.
            pset = set(assg.process for assg in resource.current_assignments())
            for process in pset:
                e = SimResourceDownException(resource)
                process.interrupt(e)
                
            self._send_notifications(SimMsgType.RSRC_DOWN)
        self._schedule_bringup()
        
    def bringup_resource(self):
        """
        Bring up the resource. If it is now truly up (there are no other
        down times in progress from other downtime agents), then
        notify all of the resource's other agents (assignment and downtime)
        of the new status by sending them a message; notify any
        :class:`processes <simprovise.modeling.process.SimProcess>`
        still assigned to the resource by raising a
        :class:`SimResourceUpException`.
        
        Last but not least, schedule the next bringup (if
        :meth:`_next_bringuptime` is overridden to return a
        :class:`~simprovise.core.simtime.SimTime` value).
        """
        if self._lastAction != DownAction.DOWN:
            msg = "Downtime agent must take down resource ({0}) before bringing it up"
            raise SimError(_DOWNTIME_ERROR, msg, self._resource.element_id)
        if not self._resource.down:
            msg = "Downtime agent bringing up resource ({0}) that is not down"
            raise SimError(_DOWNTIME_ERROR, msg, self._resource.element_id)
            
        assert self._lastAction == DownAction.DOWN, "bringing up resource that agent has not taken down"
        assert self._resource.down, "bringing up resource that is not down"
        
        resource = self._resource
        timedown = resource.time_down
        resource._bringup()       
        self._lastAction = DownAction.UP
        if resource.up:
            # Notify other agents only if the resource is now up (i.e., no
            # other down times from other agents are still in progress)
            # Also notify any processes assigned this resouorce by raising
            # and exception
            pset = set(assg.process for assg in resource.current_assignments())
            for process in pset:
                e = SimResourceUpException(resource, timedown)
                process.interrupt(e)
            self._send_notifications(SimMsgType.RSRC_UP)
            
        self._schedule_next_takedown()
            
    def _schedule_next_takedown(self):
        """
        Schedule the next takedown (or to be precise,
        :meth:`start_resource_takedown` call) by creating and registering
        a TakeDownResourceEvent - if and only if :meth:`_next_downtime`
        returns a value other than ``None``.
        
        Must be called after the resource is brought back up.
        """
        assert self.last_action == DownAction.UP
        
        takedownTime = self._next_downtime()
        if takedownTime is not None:
            takedownEvent = TakeDownResourceEvent(self, takedownTime)
            takedownEvent.register()
                
    @apidoc   
    def _next_downtime(self):
        """
        Returns the next down time. Default returns ``None``. If a subclass
        wants to automatically and continously generate one takedown after
        another, it must override this method and return a simulated time
        value.
        
        :return: The next down time
        :rtype:  :class:`~simprovise.core.simtime.SimTime`
        
        :meta public:
        """
        return None
            
    def _schedule_bringup(self):
        """
        Schedule a resource bringup by creating and registering
        a BringUpResourceEvent - if and only if :meth:`_next_bringuptime`
        returns a value other than ``None``.
        
        Must/should be called after the resource is taken down (NOT just
        set to GOING_DOWN)
        """
        assert self.last_action == DownAction.DOWN
        
        bringupTime = self._next_bringuptime()
        if bringupTime is not None:
            bringupEvent = BringUpResourceEvent(self, bringupTime)
            bringupEvent.register()
        
    @apidoc   
    def _next_bringuptime(self):
        """
        Returns the next bring up time. Default returns ``None``. If a subclass
        wants to automatically generate a bringup event after each takedown,
        it must override this method and return a simulated time value.
        
        :return: The next bringup time
        :rtype:  :class:`~simprovise.core.simtime.SimTime`
        
        :meta public:
        """
        return None
            
    def _send_notifications(self, msgType):
        """
        Notify the resource's assignment agent and any other downtime agents
        of the resource's new status via SimMsgType RSRC_GOING_DOWN,
        RSRC_DOWN or RSRC_UP
        """
        resource = self._resource
        msgData = resource
        self.send_message(resource.assignment_agent, msgType, msgData)
        for dt_agent in resource.downtime_agents():
            if dt_agent is not self:
                self.send_message(dt_agent, msgType, msgData)
               
    @apidoc   
    def _handle_resource_down(self, msg):
        """
        The handler registered to process resource down (RSRC_DOWN) messages
        sent by other downtime agents for this agent's resource,
        implementing a default behavior for agents that set a resource to
        'going down' in :meth:`start_resource_takedown`
        
        This default handler implementation takes down the resource itself
        **IF** the current `_lastAction` value is `GOING_DOWN`. That last
        action indicates that this agent is in the process of taking the
        resource down; it's just waiting for the right conditions. The
        default assumption is that if the resource goes down due to some
        other reason (other downtime agent), those conditions are met and/or
        don't matter any more, and this agent should continue with it's
        take down immediately. (Remember that a resource can be taken down by
        multiple downtime agents, and will not come back up until they
        all bring it back up.) Subclasses can override this behavior with
        a different implementation.
        
        :param msg: Resource Down message (SimMsgType RSRC_DOWN)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    `True` always, as the message is always handled
        :rtype:     `bool`
     
        :meta public:
        """
        assert msg.msgType == SimMsgType.RSRC_DOWN, "Invalid message type passed to _handle_resource_down()"
        resource = msg.msgData
        assert resource == self._resource, "RSRC_DOWN message sent to agent of different resource" 
        
        if self.last_action == DownAction.GOING_DOWN:          
            self._takedown_resource()
            
        return True
        
    @apidoc   
    def _handle_resource_up(self, msg):
        """
        The handler registered to process resource up (RSRC_UP) messages
        sent by other downtime agents.
        
        This message is always sent to newly UP resource's other downtime
        agents (if any) - but downtime agents may subscribe to additional
        RSRC_UP messages, (most typically all RSRC_UP messages within a
        resource pool).
        
        This default implementation does nothing other than return `True`.
        
        :param msg: Resource bringup message (SimMsgType RSRC_UP)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    `True` always, as the message is always handled
        :rtype:     `bool`
        
        :meta public:
        """
        assert msg.msgType == SimMsgType.RSRC_UP, "Invalid message type passed to _handle_resource_up()"
        resource = msg.msgData
        return True
        
    @apidoc   
    def _handle_resource_goingdown(self, msg):
        """
        The handler registered to process resource up (RSRC_GOING_DOWN) messages
        sent by other downtime agents for this agent's resource.
        
        This default implementation does nothing other than return `True`.
        
        :param msg: Resource bringup message (SimMsgType RSRC_UP)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    `True` always, as the message is always handled
        :rtype:     `bool`
        
        :meta public:
        """
        assert msg.msgType == SimMsgType.RSRC_GOING_DOWN, "Invalid message type passed to _handle_resource_goingdown()"
        resource = msg.msgData
        return True
     
    @apidoc   
    def _handle_resource_release(self, msg):
        """
        The handler registered to process resource up (RSRC_RELEASE) messages
        sent by other downtime agents for this agent's resource.
        
        It implement a default behavior for agents that set a resource to
        'going down' in :meth:`start_resource_takedown`; the default
        assumption is that the agent is waiting for the resource to be
        completely idle.
               
        :param msg: Resource release message (SimMsgType RSRC_RELEASE)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    `True` always, as the message is always handled
        :rtype:     `bool`
        
        :meta public:
        """
        assert msg.msgType == SimMsgType.RSRC_RELEASE, "Invalid message type passed to _handle_resource_release()"
        
        if self.last_action == DownAction.GOING_DOWN and not self._resource.in_use:
            self._takedown_resource()
        
        return True
    
    def _process_going_down_timeout(self, timeoutEvent):
        """
        Process/handle a resource going-down timeout by taking down the agent's
        resource.
        """
        assert self._timeoutEvent is timeoutEvent, "unexpected timeout event being processed"
        self._timeoutEvent = None
        self._takedown_resource()


@apidoc
class SimResourceFailureAgent(SimDowntimeAgent):
    """
    A :class:`SimDowntimeAgent` that generates failure downtimes for a
    single resource.
    
    Failures are defined by two time intervals:
    
    - **Time to Failure**: the time from the end of the previous failure (i.e.,
      the last time the resource came back up from a failure) to the start
      of the next failure.
      
    - **Time to Repair**: the time from the start of a failure until it comes
      back up.
      
    These two time parameters are obtained by sampling from passed
    distributions.
    
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
    __slots__ = ('_timeToFailureGenerator', '_timeToRepairGenerator')
    
    def __init__(self, resource, timeToFailureGenerator, timeToRepairGenerator):
        super().__init__(resource)
        self._timeToFailureGenerator = timeToFailureGenerator
        self._timeToRepairGenerator = timeToRepairGenerator
        
    def _next_downtime(self):
        """
        Returns the next down time, obtained via time-to-failure generator. 
        
        :return: The next down time
        :rtype:  :class:`~simprovise.core.simtime.SimTime`
        
        :meta public:
        """
        takedownTime = SimClock.now() + next(self._timeToFailureGenerator)
        return takedownTime
        
    def _next_bringuptime(self):
        """
        Returns the next bring up time, obtained via time-to-repair generator.
        
        :return: The next bringup time
        :rtype:  :class:`~simprovise.core.simtime.SimTime`
        
        :meta public:
        """
        bringupTime = SimClock.now() + next(self._timeToRepairGenerator)
        return bringupTime
        

@apidoc
class DowntimeSchedule(object):
    """
    Class representing a fixed downtime schedule, accessed via a generator
    producing a :class:`~simprovise.core.simtime.SimTime` pair for the start
    and length of the the next down time in the schedule.
    
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
    would be::
    
        2:00,  2:15
        4:00,  4:30
        7:00,  7:15
        11:00, 11:15
        13:00, 13:30
        16:00, 16:15

    :param scheduleLength: The length of each schedule cycle
    :type scheduleLength:  :class:`~.simtime.SimTime` 

    :param downIntervals:  An iterable collection of (start time, period length)
                           pairs
    :type downIntervals:   Iterable of pairs of
                           :class:`~.simprovise.core.simtime.SimTime` values
         
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
                #endTime = startTime + interval.length
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
                raise SimError(_DOWNTIME_ERROR, msg, interval,
                               self._scheduleLength)
            if interval.length <= 0:
                msg = "Length of interval {0} must be a SimTime > 0"
                raise SimError(_DOWNTIME_ERROR, msg, interval)
            if interval.start <= prevEnd:
                msg = "Start of interval {0} must be a SimTime > the end of the previous interval"
                raise SimError(_DOWNTIME_ERROR, msg, interval)
                
            end = interval.start + interval.length            
            if end > self._scheduleLength:
                msg = "End of interval {0} must be a SimTime >= the schedule length: {1}"
                raise SimError(_DOWNTIME_ERROR, msg, interval,
                               self._scheduleLength)
            prevEnd = end
    

@apidoc
class SimScheduledDowntimeAgent(SimDowntimeAgent):
    """
    A :class:`SimDowntimeAgent` that generates downtimes for a resource based on
    a :class:`DowntimeSchedule`.
    
    If the downtime agent for the resource "behaves" - it takes down and
    brings up the resource exactly on schedule- the result
    will be continuously cycling regular downtimes according to the passed
    :class:`DowntimeSchedule`.
    
    But if the takedown is delayed: the scheduled downtime will start when the
    the resource is actually taken and last for the scheduled length.
    If the end of the downtime overlaps with the next scheduled downtime,
    that next scheduled downtime is skipped. (If the delay is longer,
    multiple scheduled downtimes may be skipped - basically, when the
    resource comes back up, the agent looks at the current simulated time
    and gets the next scheduled downtime that doesn't start before that
    time.)
      
    :param resource:         Resource to be brought up and down on schedule.
    :type resource:          :class:`~.resource.SimResource`
    
    :param downtimeSchedule: The regularly scheduled fixed down intervals
                             for the resource.
    :type downtimeSchedule:  :class:`DowntimeSchedule`
          
    """
    __slots__ = ('_downtimeSchedule', '_downtimeGenerator', '_interval')
    
    def __init__(self, resource, downtimeSchedule):
        super().__init__(resource)
        self._downtimeSchedule = downtimeSchedule
        #self._downtimeGenerator = None
        self._downtimeGenerator = downtimeSchedule.down_intervals()
        self._currentInterval = None
        
    def _next_downtime(self):
        """
        Returns the next down time, obtained via scheduled downtime generator,
        which returns a start-time/time-length interval object.
        
        If the previous scheduled break was delayed (e.g., we implement
        a delay until the resource is idle), we find the next scheduled
        downtime interval that hasn't already started.

        Also saves the interval, as it will be used to calculate bringup time.
        
        :return: The next down time
        :rtype:  :class:`~simprovise.core.simtime.SimTime`
        
        :meta public:
        """
        nextInterval = next(self._downtimeGenerator)
        while nextInterval.start <= SimClock.now():
            nextInterval = next(self._downtimeGenerator)
            
        self._currentInterval = nextInterval
        takedownTime = nextInterval.start
        return takedownTime
        
    def _next_bringuptime(self):
        """
        Returns the next bring up time, obtained via the saved current schedule
        interval - next bring-up time is the current simulated time plus the
        interval length.
        
        :return: The next bringup time
        :rtype:  :class:`~simprovise.core.simtime.SimTime`
        
        :meta public:
        """
        bringupTime = SimClock.now() + self._currentInterval.length
        return bringupTime

                
class TakeDownResourceEvent(SimEvent):
    """
    An event that initiates a resource takedown via a passed
    SimDowntimeAgent for that resource.
    """
    __slots__ = ('_agent')
    
    def __init__(self, downtimeAgent, tm):
        super().__init__(tm, priority=3)
        self._agent = downtimeAgent
        
    def process_impl(self):
        """
        Tell the downtime agent to request a resource takedown
        """
        self._agent.start_resource_takedown()
    
    
class BringUpResourceEvent(SimEvent):
    """
    An event that initiates a single resource bring-up via a passed
    SimDownTimeAgent. Should be the same agent that brought the
    resource down.
    """
    __slots__ = ('_agent', '_resource')
    
    def __init__(self, downtimeAgent, tm):
        super().__init__(tm, priority=3)
        self._agent = downtimeAgent
        
    def process_impl(self):
        """
        Tell the downtime agent to request a resource bringup
        """
        self._agent.bringup_resource()
        

@apidocskip
class SimGoingDownTimeOutEvent(SimEvent):
    """
    Timeout a resource going-down state.
    
    Notifies the downtime agent of the timeout, which will then take
    the resource down.
    
    This is not a :class:`SimInterruptException`,
    since it does not interrupt a process directly (though
    it may indirectly result in an interrupt when the resource
    is taken down)
    
    Event Priority is 1, because the real action are any events generated
    as a result of this notification, most/all of which will be
    scheduled immediately. (to occur at the time of the timeout).
    
    The downtime agent that creates/schedules this event is responsible
    for holding onto it and deregistering it if the resource goes down
    before the timeout occurs.

    """
    __slots__ = ('_agent')
    def __init__(self, downtime_agent, timeout=0):
        super().__init__(SimClock.now() + timeout, priority=1)
        self._agent = downtime_agent
        
    def process_impl(self):
        """
        Delegate processing back to the creating agent.
        """
        self._agent._process_going_down_timeout(self)
    

@apidoc
class SimResourceDownException(SimInterruptException):
    """
    Exception raised when a process :meth:`~.transaction.wait_for` is
    interrupted because a resource the process holds has been taken down.
    
    Exception provides a `resource` attribute that identifies the
    resource taken down.
    """
    def __init__(self, resource):
        super().__init__("Resource Down")
        self.resource = resource

    def __str__(self):
        return 'SimResourceDownException for resource {0}'.format(self.resource.element_id)

@apidoc
class SimResourceUpException(SimInterruptException):
    """
    Exception raised when a process :meth:`~.transaction.wait_for` is
    interrupted because a resource the process holds has come back up.
    
    Exception provides a `resource` attribute that identifies the
    resource taken down.
    """
    def __init__(self, resource, timedown):
        super().__init__("Resource Up")
        self.resource = resource
        self.timedown = timedown

    def __str__(self):
        return 'SimResourceUpException for resource {0}'.format(self.resource.element_id)        
    
if __name__ == '__main__':
    from simprovise.modeling.resource import SimSimpleResource
    from simprovise.core.simrandom import  SimDistribution
    from simprovise.core import simevent
    
    TWO_HRS = SimTime(2, tu.HOURS)
    FOUR_HRS = SimTime(4, tu.HOURS)
    SEVEN_HRS = SimTime(7, tu.HOURS)
    NINE_HRS = SimTime(9, tu.HOURS)
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
    
