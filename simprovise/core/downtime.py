#===============================================================================
# MODULE downtime
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the DowntimeAgentMixin, SimDowntimeAgent, SimResourceFailureAgent and 
# related event classes.  
#===============================================================================
__all__ = ['SimDowntimeAgent', 'SimResourceFailureAgent']

from simprovise.core import (SimError, SimClock, SimLogging)
from simprovise.core.agent import SimAgent, SimMsgType
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
    provided by :class:`SimDowntimeAgent` below.
   
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._downrequests = set()
        self.register_handler(SimMsgType.RSRC_DOWN, self._handle_resource_down)
        self.register_handler(SimMsgType.RSRC_UP, self._handle_resource_up)
        
    def request_resource_takedown(self, resource):
        """
        Initiate a resource takedown by sending a takedown request to the
        resource's assignment agent.
        """
        # Make sure this downtime agent hasn't already requested a takedown
        # (without an intervening bringup)
        if resource in self._downrequests:
            msg = "Request to take down resource {0} that this agent has already taken down"
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
        resource's assignment agent.
         """
        # Make sure this bringup request has an earlier matching down request
        if not resource in self._downrequests:
            msg = "Request to bring up resource {0} that this agent has not taken down"
            raise SimError(_DOWNTIME_ERROR, msg, resource.element_id)
        
        self._downrequests.remove(resource)
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
        
        if not takedown_successful:
            self._downrequests.remove(resource)
            
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
        initialTakedownTime = SimClock.now() + next(self._timeToFailureGenerator)
        initialEvent = TakeDownResourceEvent(self, resource, 
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
        

class DowntimeSchedule(object):
    """
    """
    def __init__(self, scheduleLength):
        self._scheduleLength = scheduleLength
        self._downTimeStarts = []
        self._downtimeLengths = []
    
    
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
        """
        self._agent.request_resource_bringup(self._resource)
        
    
if __name__ == '__main__':
    from simprovise.core import SimSimpleResource, SimDistribution
    from simprovise.core import simtime, simevent, SimTime, SimClock

    SimClock.initialize()
    simevent.initialize()
    eventProcessor = simevent.EventProcessor()
    
    rsrc = SimSimpleResource("testResource")
    timeToFailureGenerator = SimDistribution.constant(SimTime(4, simtime.MINUTES))
    timeToRepairGenerator = SimDistribution.constant(SimTime(2, simtime.MINUTES))
    failureAgent = SimResourceFailureAgent(rsrc, timeToFailureGenerator, timeToRepairGenerator)
  
    for i in range(10):
        n = eventProcessor.process_events(SimTime(i, simtime.MINUTES))
        print(i, n, "events processed; resource up:", rsrc.up)
    
