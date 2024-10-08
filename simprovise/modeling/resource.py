#===============================================================================
# MODULE resource
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimResource-related classes - SimResourceAssignment,
# SimResource, SimSimpleResource, SimResourceAssignmentAgent,
# SimAssignmentAgentMixin and SimResourcePool.
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
__all__ = ['SimResource', 'SimSimpleResource', 'SimResourcePool', 
           'SimResourceAssignment', 'SimResourceAssignmentAgent']

from itertools import chain
from inspect import isclass
from abc import ABCMeta, abstractmethod

from simprovise.core import SimError, simtrace
from simprovise.core.simclock import SimClock
#from simprovise.core.simexception import SimInterruptException
from simprovise.core.datacollector import SimUnweightedDataCollector
from simprovise.core.simlogging import SimLogging
from simprovise.core.simtime import SimTime 
from simprovise.core.simevent import SimEvent

from simprovise.modeling import SimCounter, SimEntity
from simprovise.modeling.agent import SimAgent, SimMsgType, SimMessage
from simprovise.modeling.location import SimStaticObject

from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)

_RESOURCE_ERROR = "Resource Error"
_REQUEST_ERROR = "Resource Request Error"
_RELEASE_ERROR = "Resource Release Error"
_POOL_ERROR = "Resource Pool Error"

@apidoc
class SimResourceAssignment(object):
    """
    Encapsulates a set of zero or more resources assigned to a process
    via :meth:`~.process.SimProcess.acquire` or
    :meth:`~.process.SimProcess.acquire_from`
    
    Can be used as a context manager in order to ensure the assignment
    is released; e.g. with a :meth:`~.transaction.SimTransaction.run`::
    
        with self.acquire(server) as rsrc_assignment:
            self.wait_for(service_time)
            
    The above code invokes `self.release(rsrc_assignment)` when exiting
    the context manager.
    
        :param transaction:     :class:`~.process.SimProcess` to which 
                                resource(s) are being assigned
        :type transaction:      :class:`~.process.SimProcess` 
    
        :param assignmentagent: Agent (which might be the resource itself) 
                                which made this assignment
        :type assignmentagent:  :class:`~.agent.SimAgent`
    
        :param resources:      The resource(s) (at least one) in the assignment.
        :type resources:       Sequence of class :class:`SimResource` objects

    """
    __slots__ = ('_process', '_assignmentAgent', '_resources', '_assignTime')

    def __init__(self, process, assignmentAgent, resources):
        self._process = process
        self._assignmentAgent = assignmentAgent
        self._resources = tuple(resources)
        self._assignTime = SimClock.now()
        
        # Validation
        
        # The assignment must contain at least one resource
        if len(resources) == 0:
            msg =  "A ResourceAssignment must be constructed with at least one resource"
            raise SimError(_RESOURCE_ERROR, msg)
        
        for r in resources:
            # Each passed resource must be a SimLogging
            if not isinstance(r, SimResource):
                msg = "SimResourceAssignment constructed with a non-resource {0} object"
                raise SimError(_RESOURCE_ERROR, msg, r)
                
            # Each passed resource must be managed by the passed assignment agent
            if r.assignment_agent is not assignmentAgent:
                msg = "SimResourceAssignment constructed with resource {0} that is not managed by assignment agent {1}"
                raise SimError(_RESOURCE_ERROR, msg, r, assignmentAgent)
            
            # When a single resource is passed multiple times, the number of times
            # cannot exceed the resource capacity
            n = resources.count(r)
            if n > r.capacity:
                msg = "SimResourceAssignment constructed with {0} of resource {1} which exceeds it's capacity of {2}"
                raise SimError(_RESOURCE_ERROR, msg, n, r, r.capacity)
                

    def __str__(self):
        return "Resource Assignment: Transaction: " + str(self.process) + \
               ", Agent:" + str(self.assignment_agent) + ", Resources: " + \
               str(self.resources)
    
    def __enter__(self):
        """
        To use the assignment as a context manager
        """
        return self
    
    def __exit__(self, type, value, tb):
        """
        When using the assignment with a context manager, release the
        entire assignment on exit
        """
        assert self._process, "Resource Assignment has no process"
        self._process.release(self)
        return False

    @property
    def process(self):
        """
       The transaction (SimProcess) to which these resources are assigned
        """
        return self._process

    @property
    def assignment_agent(self):
        """
        The SimAgent (possibly the resource itself, possibly not) that manages
        acquisition and release of this assignment.
        """
        return self._assignmentAgent

    @property
    def count(self):
        """
        The number of resources assigned
        """
        return len(self._resources)

    @property
    def resources(self):
        """
        A tuple of the resources assigned
        """
        return self._resources

    @property
    def resource(self):
        """
        If the assignment consists of a single resource instance, return it.
        If the assignment consists of the same resource instance allocated
        more than once (e.g., a resource instance with capacity > 1), return
        it. Raises an exception if the assignment consists of multiple and
        different resource instances, or if the assignment does not have any
        resources. (Clients should use the count property to check first)

        :return:  The single SimResource instance included in assignment
        :rtype:   :class:`SimResource`
        
        """
        if 1 < len(set(self._resources)):
            msg = "Attempt to access (singular) resource property on ResourceAssignment with multiple resources: {0}"
            raise SimError(_RESOURCE_ERROR, msg, self)
        
        if self.count == 0:
            msg = "Attempt to access resource property on a null (no resources) assignment: {0}"
            raise SimError(_RESOURCE_ERROR, msg, self)
    
        return self._resources[0]

    @property
    def assign_time(self):
        """
        The :class:`~.SimTime` that this assignment was created/made.
        """
        return self._assignTime

    def contains(self, resources):
        """
        Returns True if the assignment contains the passed sequence of resources
        """
        rset = set(resources)
        rlist = list(resources)
        for resource in rset:
            if rlist.count(resource) > self._resources.count(resource):
                return False
        return True

    def subtract(self, resourcesToSubtract):
        """
        Removes a passed sequence of resources from the assignment
        """
        rlist = list(self._resources)
        try:
            for r in resourcesToSubtract:
                rlist.remove(r)
        except ValueError:
            msg = "Resource List ({0}) not contained in assignment {1}"
            raise SimError(_RESOURCE_ERROR, msg, resourcesToSubtract, self)
  
        self._resources = tuple(rlist)

    def subtract_all(self):
        "Remove all of the assignment's resources"
        self._resources = tuple()
        
@apidocskip
class SimAssignResourcesEvent(SimEvent):  
    """
    An event that schedules a resource assignment agent to process
    resource assignment requests. Set to priority 5 so that concurrent
    resource acquire, resource release, takedown, bringup, timeout and
    transaction interrupt events are processed first.
    """
    __slots__ = ('assignmentAgent')
    
    def __init__(self, assignmentAgent):
        super().__init__(SimClock.now(), priority=5)
        self.assignmentAgent = assignmentAgent
        
    def process_impl(self):
        """
        """
        self.assignmentAgent.process_queued_requests()
        self.assignmentAgent.assignmentEvent = None
    

@apidoc
class ResourceAssignmentAgentMixin(object):
    """
    A mix-in class that provides a :class:`~.agent.SimAgent` (which may or may
    not be a resource) with basic resource assignment functionality - the
    ability to handle resource-related messages, such as request and release.
    The mixin defines handler functions for all of those message types.

    By default, this mix-in fulfills requests on a first-in/first-out basis.
    That behavior may be overridden by registering a request priority function
    via :meth:`requestPriorityFunc` and/or overriding :meth:`assign_from_request`
    in a subclass.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assignmentEvent = None
        self.register_handler(SimMsgType.RSRC_REQUEST, self._handle_resource_request)
        self.register_handler(SimMsgType.RSRC_RELEASE, self._handle_resource_release)
        self.register_handler(SimMsgType.RSRC_GOING_DOWN, self._handle_resource_going_down)
        self.register_handler(SimMsgType.RSRC_DOWN, self._handle_resource_takedown)
        self.register_handler(SimMsgType.RSRC_UP, self._handle_resource_bringup)

    @property
    def request_priority_func(self):
        """
        Returns/sets the priority function for Resource Request messages.
        The priority function must take a request message as it's sole argument
        and return a numeric priority, where the lower value is the higher
        priority (e.g., priority 1 is higher than priority 2).
        """
        return self.priority_func(SimMsgType.RSRC_REQUEST)

    @request_priority_func.setter
    def request_priority_func(self, f):
        self.register_priority_func(SimMsgType.RSRC_REQUEST, f)

    def _create_multiple_resource_assignment(self, txn, *resources):
        """
        Create and return a SimResourceAssignment from the passed resources,
        which may be any combination of resource instances and/or sequences
        of resources. A generalized version of :meth:_create_resource_assignment`

        :param txn:       The transaction to which resources are to be assigned
        :type txn:        :class:`~.process.SimProcess`
        
        :param resources: Sequence of resource object to be assigned
        :type resources:  Sequence of class :class:`SimResource`
                
        :return:          Resource assignment as specified by above parameters
        :rtype:           :class:`SimResourceAssignment`
        
        """
        def flatten(rsrcList):
            """
            rsrcList may be composed of any combination of resource instances
            and lists of resource instances. Flatten it into a single list of
            resource instances. See:
            stackoverflow.com/questions/2158395/flatten-an-irregular-list-of-lists-in-python
            """
            for item in rsrcList:
                try:
                    yield from flatten(item)
                except TypeError:
                    assert isinstance(item, SimResource), "non-resource passed to createMultipleResourceAssignment()"
                    yield item

        return SimResourceAssignment(txn, self, flatten(resources))

    def _handle_resource_request(self, msg):
        """
        The handler registered to handle resource request messages.
        
        Resource requests are handled by:
        1. Validating the request
        2. Scheduling assignment request processing for the current simulated
           time, but after all other events have been processed.
        3. Returning False, since the request is not processed immediately.
           This places the request in the message queue for later processing.
           
        We do NOT attempt to respond immediately in order to avoid race
        conditions with other resource-related events that may be processed
        after this but at the same simulated time - e.g., a higher priority
        request for the same resource or pool.

        :param msg: Resource Request message (SimMsgType RSRC_REQUEST)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    True if request is fulfilled immediately, False if queued for
                    fulfillment later.
        :rtype:     bool

        """
        assert msg.msgType == SimMsgType.RSRC_REQUEST, "Invalid message type passed to handleResourceRequest()"

        # Validate the message, raising an exception if there is a problem.
        self._validate_request(msg)
        
        # schedule resource assignment to occur after all other messages
        # arriving at the current simulated time are (at least initially)
        # processed. _schedule_assignment_request_processing() ensures that
        # this only happens once for the current simulated time.
        # Since we don't yet completely handle the request, return False
        self._schedule_assignment_request_processing()
        return False
 
    def _validate_request(self, requestMsg):
        """
        Validate request message data.
        This default implementation works when the message data specifies a
        specific resource instance; typically should be overridden for agents
        managing multiple resources. (e.g. resource pools)
        """
        txn, numRequested, resource, *otherparms = requestMsg.msgData

        assert numRequested > 0, "number of resources requested not greater than zero"
        assert isinstance(resource, SimResource), "Resource request data does not specify an instance of class SimResource"

        if resource.assignment_agent is not self:
            errorMsg = "Request for resource {0} sent to agent that does not manage that resource"
            raise SimError(_REQUEST_ERROR, errorMsg, resource.element_id)

        if numRequested > resource.capacity:
            errorMsg = "Number requested ({0}) is higher than than resource {1}'s capacity ({2})"
            raise SimError(_REQUEST_ERROR, errorMsg, numRequested,
                           resource.element_id, resource.capacity)
        
    def _schedule_assignment_request_processing(self):
        """
        If we have not already done so, create and register a SimAssignResourcesEvent
        for this agent and now() that will fire after we have finished processing events
        for the current simulated time. This event will invoke _process_queued_events()
        to assign-resources/respond-to-requests based on on the prioritized request
        message queue and the resources available once all othe processing completes
        for thecurrent simulated time. It should be called any time there is a need
        or opportunity to fulfill resource requests.
        
        By postponing resource assignment, we should avoid simulated race conditions.
        """
        if self.assignmentEvent is None:
            self.assignmentEvent = SimAssignResourcesEvent(self)
            self.assignmentEvent.register()

    def process_queued_requests(self, throughRequest=None):
        """
        This method should be called only by :class:`SimAssignResourcesEvent` or
        :class:`.process.SimAcquireTimeOutEvent` It is responsible for (at
        least attempting) to fulfill resource requests in the message queue.

        This (default) implementation loops through the request queue in
        priority order until it either:

        a) Cannot handle a request (i.e., assign resources to the requestor)
        b) Attempts to handle a passed throughRequest (!= None)
           or
        c) Empties the queue
                  
        A non-None throughRequest is typically passed by SimTimeOutEvent
        processing, which wants to make a last ditch effort to fulfill the
        request before raising the timeout exception - without fulfilling
        lower priority requests that a higher priority timing out process
        might request as a response to the timeout.
    
        Note that if this implementation cannot fulfill an earlier/higher
        priority request remaining, it does NOT allow a later/lower priority
        request to "jump the queue". Some subclassed agents (resource pools in
        particular) will modify this behavior.
        
        This is also a primary method to be overloaded by model-specific
        code to implement specialized resource assignment behavior.
        """        
        for requestMsg in self.queued_resource_requests():
            handled = self._process_request_msg(requestMsg)
            if not handled:
                return 
            if throughRequest is not None and requestMsg == throughRequest:
                return 
    
    def queued_resource_requests(self):
        """
        Returns the resource assignment agent's queued RSRC_REQUEST 
        messages.
        
        Primarily for the use of model-specific implementations of
        process_queued_requests()
        
        TODO - overload priority_func to operate on SimResourceRequest
        objects, and apply it here. which means that all code (not just
        model-specific) will have to use this in place of queued_messages()
        and probably SimResourceRequest will have to be made into a
        subclass of SimMessage.
        """
        return self.queued_messages(SimMsgType.RSRC_REQUEST)
        #return [SimResourceRequest(*msg)
                #for msg in self.queued_messages(SimMsgType.RSRC_REQUEST)]
    
    @apidocskip
    def cancel_request(self, msg):
        """
        Cancel a resource request by removing the request from the message
        queue and making sure the request queue is reprocessed in case
        other requests can now be fulfilled. (e.g., if another, lower
        priority request is asking for the same resources, but fewer)
        """
        assert msg.msgType == SimMsgType.RSRC_REQUEST, "Invalid message type passed to handleResourceRequest()"
        self.msg_queue.remove(msg)
        self._schedule_assignment_request_processing()
        
    def _process_request_msg(self, requestMsg):
        """
        Attempt to process a resource request, returning True if successful (and
        False otherwise). If successful, the message is handled so remove it
        from the message queue.
        """
        resourceAssignment = self._assign_from_request(requestMsg)
        if resourceAssignment:
            self._process_assignment(requestMsg, resourceAssignment)
            return True
        else:
            return False
        
    def _process_assignment(self, requestMsg, resourceAssignment):
        """
        Actually do the work of resource assignment:
        - Tell the resource object(s) themselves of the assignment via assign_to()
        - Send a response message of type RSRC_ASSIGNMENT to the requesting entity
        - Remove the request message from the queue since it is not handled.
        """
        assert resourceAssignment, "null resource assignment passed to _process_assignment()"
        process = requestMsg.process
        for resource in resourceAssignment.resources:
            resource.assign_to(process)
        self.send_response(requestMsg, SimMsgType.RSRC_ASSIGNMENT, resourceAssignment)
        # Handled, so remove the message from the queue and return True
        self.msg_queue.remove(requestMsg)
        

    def _assign_from_request(self, requestMsg):
        """
        This method, called by _process_request(), actually implements the
        logic that determines whether a resource (or resources) can be
        assigned to a request, and if so, the specifics of that assignment.
        Those specifics are in the form of a SimResourceAssignment object,
        which is returned. If no assignment can to be made in response to the
        request, this method returns None.

        The implementation here implements default behavior of
        SimSimpleResources; it creates an assignment if (a) there is
        available capacity to fulfill the request and (b) there is not an
        older request on the queue of equal or greater priority. (or any
        older request, if this queue is FIFO, i.e. no priority.)

        Specializations of resource assignment agents may provide their own
        assignFromRequest() implementation to customize this behavior.

        :param msg: Resource Request message (SimMsgType RSRC_REQUEST)
        :type msg:  :class:`SimMessage`
                
        :return:    SimResourceAssignment or None: Depending on whether
                    request can be fulfilled now.
        :rtype:     :class:`SimResourceAssignment` or None

        """
        # Extract the message data.
        nrequested = requestMsg.nrequested
        resource = requestMsg.resource
        process = requestMsg.process
        
        assert nrequested > 0, "number of resources requested not greater than zero"
        assert isinstance(resource, SimResource), "Resource request data does not specify an instance of class SimResource"

        if nrequested <= resource.available:
            return SimResourceAssignment(process, self, (resource,) * nrequested)
        else:
            return None

    def _handle_resource_release(self, msg):
        """
        The handler registered to handle resource release messages.

        Handles each resource release notification as it comes in, returning
        ``True`` to indicate that it was, in fact handled. This handler
        also updates the resource assignment object that is included in the
        message, reflecting the resource(s) released. Note that the process
        requesting the release expects in to be fulfilled immediately/
        synchronously - there is presently no RSRC_RELEASED response message
        that is/can be sent to the process agent.

        After releasing the resources, this handler will:
        
        - Notify all downtime agents for all released resources of the
          release via message; the downtime agent might take down the resource
          after the release.
        - Schedule a round of new resource assignments, as one or more request
          messages in the queue may now be fulfillable using the newly
          released resource(s).

        :param msg: Resource Request message (`SimMsgType` `RSRC_RELEASE`)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    ``True`` always, as the message is always handled
        :rtype:     ``bool``

        """
        assert msg.msgType == SimMsgType.RSRC_RELEASE, "Invalid message type passed to handleResourceRelease()"

        assignment, resourcesToRelease = msg.msgData

        if len(assignment.resources) == 0:
            errorMsg = "Invalid release: assignment passed to handleResourceRelease() has no resources"
            raise SimError(_RELEASE_ERROR, errorMsg)

        if not assignment.contains(resourcesToRelease):
            errorMsg = "Invalid release: release specifies resources that are not currently in the assignment"
            raise SimError(_RELEASE_ERROR, errorMsg)

        for resource in resourcesToRelease:
            if resource.assignment_agent is not self:
                errorMsg = "Release for resource {0} sent to agent that does not manage that resource"
                raise SimError(_RELEASE_ERROR, errorMsg, resource.element_id)
            resource.release_from(assignment.process, 1)

        assignment.subtract(resourcesToRelease)
        
        # Notify downtime agents of resource's that were released
        # (They may want to now  take that resource down, so do this before
        # resource request processing.)
        for rsrc in resourcesToRelease:
            for downtimeAgent in rsrc.downtime_agents():
                self.send_message(downtimeAgent, SimMsgType.RSRC_RELEASE, rsrc)                 
         
        # We now have available resources, but defer scheduling until all
        # other messages for the current simulated time are processed.
        self._schedule_assignment_request_processing()

        # Since we handled the release message, return True
        return True
    
    def _handle_resource_going_down(self, msg):
        """
        The default handler registered to handle resource going-down messages.
        Does nothing except mark the message as handled by returning ``True``.
                        
        :param msg: Resource Request message (SimMsgType RSRC_RELEASE)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    ``True`` always, as the message is always handled
        :rtype:     ``bool``

        """
        assert msg.msgType == SimMsgType.RSRC_GOING_DOWN, "Invalid message type passed to _handle_resource_going_down()"        
        return True

    def _handle_resource_takedown(self, msg):
        """
        The default handler registered to handle resource takedown messages.

        Handles each resource takedown notification as it comes in, returning
        ``True`` to indicate that it was, in fact handled.
        
        If the resource is already down (i.e., this is a nested or
        overlapping takedown of that resource) the handler invokes
        the resource's _takedown() method and returns. Otherwise...

        ... if the taken-down resource is currently assigned to one or more
        processes, the handler will interrupt those processes with a
        SimResourceDownException. Note that processes that have requested
        the resource but not yet obtained it (i.e. are blocked in acquire()
        calls) are NOT interrupted. If other behavior is desired, use of
        resource pools and/or timeouts are probably the way to go.
        
        At that point, it is up to the process to appropriately handle the
        takedown - e.g.  releasing the resource, possibly acquiring a different
        resource, possibly reacquiring this resource. In any event, this
        handler will schedule a round of resource assignment processing in
        case new resource acquire requests are made in response to the
        takedown.
        
        Note: specialized assignment agent subclasses can implement different
        takedown behavior by overriding this method - e.g., a subclass
        could respond to shift break takedowns by finishing some or all
        current processing before taking down the resource.
        
        :param msg: Resource Request message (SimMsgType RSRC_RELEASE)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    `True` always, as the message is always handled
        :rtype:     `bool`

        """
        # TODO most of this behavior moved to downtime agent.
        # This handler should take RSRC_DOWN messages instead, and default
        # to just scheduling resouorece assignments
        # Also need similar changes to handler for RSRC_GOING_DOWN
        assert msg.msgType == SimMsgType.RSRC_DOWN, "Invalid message type passed to _handle_resource_takedown()"
        resource = msg.msgData        
        assert resource.assignment_agent is self, "RSRC_DOWN sent to wrong assignment agent"
        assert resource.down, "RSRC_DOWN sent for resource that is not down"
        
        self._schedule_assignment_request_processing()            
        return True    

    def _handle_resource_bringup(self, msg):
        """
        The default handler registered to handle resource bringup messages.

        Handles each resource bringup notification as it comes in, returning
        ``True`` to indicate that it was, in fact handled.
        
        Handler invokes the resource's _bringup() method. if this is a nested/
        overlapping bringup request and the resource is still down after that
        _bringup() call, the handler returns. Otherwise...
        
        ... if the resource is currently assigned to one or more processes, the
        handler will interrupt those processes with a SimResourceUpException.

        After bringing up the resource, this handler will attempt to respond
        to one or more request messages in the message queue if they can now
        be fulfilled using the newly available resource.

        :param msg: Resource bringup message (SimMsgType RSRC_BRINGUPRSRC_BRINGUP)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    `True` always, as the message is always handled
        :rtype:     `bool`

        """
        assert msg.msgType == SimMsgType.RSRC_UP, "Invalid message type passed to _handle_resource_bringup()"
        resource = msg.msgData
        assert resource.assignment_agent is self, "RSRC_UP sent to wrong assignment agent"
        assert resource.up, "RSRC_UP sent for resource that is not up"
                
        self._schedule_assignment_request_processing()
        return True

#@apidoc
#class SimResourceDownException(SimInterruptException):
    #"""
    #Exception raised when a process :meth:`~.transaction.wait_for` is
    #interrupted because a resource the process holds has been taken down.
    
    #Exception provides a `resource` attribute that identifies the
    #resource taken down.
    #"""
    #def __init__(self, resource):
        #super().__init__("Resource Down")
        #self.resource = resource

    #def __str__(self):
        #return 'SimResourceDownException for resource {0}'.format(self.resource.element_id)

#@apidoc
#class SimResourceUpException(SimInterruptException):
    #"""
    #Exception raised when a process :meth:`~.transaction.wait_for` is
    #interrupted because a resource the process holds has come back up.
    
    #Exception provides a `resource` attribute that identifies the
    #resource taken down.
    #"""
    #def __init__(self, resource, timedown):
        #super().__init__("Resource Up")
        #self.resource = resource
        #self.timedown = timedown

    #def __str__(self):
        #return 'SimResourceUpException for resource {0}'.format(self.resource.element_id)

@apidoc
class SimResource(SimStaticObject):
    """
    Encapsulates a resource that is used (possibly in conjunction with other
    resources) to perform a process. SimResources are locatable static objects.
    Note that while a SimResource may be able to move, the SimLocation to
    which it belongs does not change. (For static objects, location refers
    more directly to ownership than to specific physical location at any
    given simulated time.)
    
    :param name:            Resource name. As with other static objects, it
                            must be unique within it's location
    :type name:             str

    :param parentLocation: Location object to which resource belongs.
                           If None defaults to Root location
    :type parentLocation:  :class:`~.location.SimLocation` or None

    :param initialLocation: Initial location object for the resource.
                            If None, will default to parent location.
    :type initialLocation:  :class:`~.location.SimLocation` or None

    :param capacity:       Capacity of resource, or number of subresources.
                           Defaults to 1. Must be > 0. 
    :type capacity:        int

    :param assignmentAgent: Agent managing (assigning) this resource.
                            If None, the resource is assumed to be its
                            own agent.
    :type assignmentAgent:  :class:`~.agent.SimAgent` or None

    :param moveable:        True if the resource can move (within it's
                            parent location), False if it is filling
                            Defaults to True. 
    :type moveable:         bool
        
    """
    #TODO
    #Maybe this becomes an abstract base class, with subclasses
    #SimCompositeResource and SimLeafResource (or similar name)
    #Add a __parentResource attribute (which must be None or a composite
    #resource) and a parent atttribute setter/getter
    #Add isComposite read-only property which defaults to False
    #assignTo() and releaseFrom() become LeafResource methods, which
    #call childAssigned() and childReleased() methods on parent composite
    #Add _assigned() and _released() methods, which update util and
    #process time data collectors, and call _assigned/_released on parent

    __slots__ = ('__processtimeDataCollector', '_capacity', '_utilCounter',
                 '_currentTxnAssignments', 'assignmentAgent', '_downCount',
                 '_downPctCounter', '_downtimeStart', '_goingDown',
                 '_downtimeAgents')

    def __init__(self, name, parentLocation=None, initialLocation=None, 
                 capacity=1, assignmentAgent=None, moveable=True):
        """
        """       
        super().__init__(name, parentLocation, initialLocation, moveable)
        
        if not isinstance(capacity, int) or capacity <= 0: 
            msg = "Resource {0} assigned invalid capacity of {1}: must be a positive integer"
            raise SimError(_RESOURCE_ERROR, msg, self.element_id, capacity)
        
        self._processtimeDataCollector = SimUnweightedDataCollector(self, "ProcessTime", SimTime)
        # TODO other data collectors or counters, to measure time by availability and/or reason,
        # policy mechanisms to determine what data to collect

        # The normalize flag will ensure that the dataset associated with
        # this counter has values normalized based on capacity (i.e., dataset
        # values will be over range 0.0-1.0)
        self._utilCounter = SimCounter(self, "Utilization", capacity, normalize=True)
        self._downCount = 0
        self._downPctCounter = SimCounter(self, "DownTime")
        self._downtimeStart = None
        self._goingDown = False
        self._downtimeAgents = set()

        self._currentTxnAssignments = {}
        if assignmentAgent is not None:
            self._assignmentAgent = assignmentAgent
        elif isinstance(self, SimAgent):
            self._assignmentAgent = self
        else:
            logger.debug("Resource %s initialized with no assignment agent",
                         self.element_id)
            
    @property
    def capacity(self):
        """
        The size/capacity of the resource (number of subresources in this
        resource)
               
        :return:    The resource's capacity
        :rtype:     int

        """
        return self._utilCounter.capacity
    
    @property
    def assignment_agent(self):
        """
        Return the resource's assignment agent. Once the simulation starts,
        This should never be None.
        
        :return:    The resource's assignment agent
        :rtype:     :class:`~.agent.SimAgent` or None
        
        """
        return self._assignmentAgent
    
    def set_assignment_agent(self, assignmentAgent):
        """
        Set the resource's assignment agent.
        
        :param assignmentAgent: Agent responsible for managing this resource's assignments
        :type assignmentAgent:  :class:`~.agent.SimAgent`
        """
        self._assignmentAgent = assignmentAgent

    def assign_to(self, txn, number=1):
        """
        Assign this resource (or if this resource has capacity > 1, the passed
        number of subresources) to the passed transaction (task or process).

        Should be called ONLY by the resource's assignment agent, which
        should ensure that the resource is available before making this
        assignment.

        Updates the _currentTxnAssignments dictionary, which is a list
        containing two elements - initial assignment time and number of
        assignments - keyed by the transaction (task or process) requesting
        the assignment.

            :param txn:    Transaction/process to which the resource is assigned.
            :type txn:     :class:`~.process.SimProcess`

            :param number: Number of resources to be assigned (can be > 1 if the
                           resource has capacity > 1)
            :type number:  `int`

        """
        if number <= 0:
            msg = "Resource {0}: resources assigned ({1}} must be > 0"
            raise SimError(_REQUEST_ERROR, msg, self.element_id, number)
            
        if number > self.available:
            msg = "Resource {0}: resources available ({1}} is less than number assigned ({2})"
            raise SimError(_REQUEST_ERROR, msg, self.element_id, self.available, number)        
        
        self._utilCounter.increment(txn, amount=number)
        if txn in self._currentTxnAssignments:
            self._currentTxnAssignments[txn][1] += number
        else:
            self._currentTxnAssignments[txn] = [SimClock.now(), number]

    def current_assignments(self):
        """
        Return a list of all resource assignments involving this resource.
        """
        # Create a iterator over all resource assignments for each transaction
        # to which this resource is assigned
        assgIter = chain.from_iterable([txn.resource_assignments()
                                        for txn in self._currentTxnAssignments])
        # return only those assignments that actually refer to this resource
        # (since transactions can have multiple resources assigned to them at once)
        return [assg for assg in assgIter if self in assg.resources]

    def current_transactions(self):
        """
        Returns a list of transactions (processes) currently using this resource.
        """
        return list(self._currentTxnAssignments)

    def release_from(self, txn, numToRelease=None):
        """
        Releases this resource (or if this resource has capacity > 1, the
        passed number of subresources) from a previous assignment to the
        passed transaction (task or process).

        Should be called ONLY by the resource's assignment agent.

        TODO change numToRelease to subresource (if None resource to
        release is self)
        
        :param txn:             Transaction/process to which the resource
                                is currently assigned.
        :type txn:              :class:`~.process.SimProcess`

        :param numberToRelease: subresources to be released
        :type numberToRelease:  `int`

        """
        assert txn, "Null transaction (task/process) passed to releaseFrom()"
        assert txn in self._currentTxnAssignments, "releaseFrom() call on process/task that was never assigned to this resource."

        txnAssignment = self._currentTxnAssignments[txn]
        assignTime, numAssigned = txnAssignment
        if numToRelease is None:
            numToRelease = numAssigned

        assert numAssigned > 0, "releaseFrom() called with task/process that has already released all resources"
        assert numToRelease <= numAssigned, "releaseFrom() attempting to release more resources than have been assigned to this task/process"
        assert numToRelease > 0, "releaseFrom() number to release is not > 0"

        self._utilCounter.decrement(numToRelease)
        numAssigned -= numToRelease
        if numAssigned == 0:
            self._processtimeDataCollector.add_value(SimClock.now() - assignTime)
            del self._currentTxnAssignments[txn]
        else:
            txnAssignment[1] = numAssigned
            
    def add_downtime_agent(self, agent):
        """
        Attach a new downtime agent to the resource
        """
        assert agent, "null downtime agent added to resource"
        self._downtimeAgents.add(agent)
        
    def downtime_agents(self):
        """
        Return the registered downtime agents as a list
        """
        return list(self._downtimeAgents)

    @property
    def in_use(self):
        "The number of subresources currently assigned to a process"
        return self._utilCounter.value

    @property
    def down(self):
        """
        Returns True if the resource has been taken down (for a failure
        or other reason)
        """
        return (self._downCount > 0)
    
    @property
    def going_down(self):
        """
        Returns True if the resource is "about" to go down, but has not yet.
        
        Motivating use case is a person scheduled to go on break, but does
        not do so until completing some in-progress task.
        """
        assert not (self._goingDown and self.down), "a resource that is down cannot be going down"
        return self._goingDown

    @property
    def up(self):
        """
        Returns True if the resource is not down.
        """
        return not self.down
    
    @property
    def time_down(self):
        """
        If the resource is down, returns the total simulated time that
        has passed since it went from up to down. If the resource is up,
        returns None.
        """
        if self.up:
            return None
        assert self._downtimeStart is not None, "_downtimeStart not set for time_down() call"
        tmdown = SimClock.now() - self._downtimeStart
        assert tmdown >= 0, "Invalid _downtimeStart > SimClock.now()"
        return tmdown

    @property
    def available(self):
        """
        The number of resources currently available - zero if the resource is
        down OR going down, capacity - inUse if the resource is up.
        """
        if self.down or self.going_down:
            return 0
        else:
            return self.capacity - self.in_use

    @apidocskip
    def _start_going_down(self):
        """
        Indicate that this resource is about/getting ready to go down.
        
        Motivating use case is the human operator who's scheduled to go
        on break/off shift,  but needs to complete something first - and
        therefore shouldn't be assigned any new work.
        """
        assert not self._goingDown, "Going-down already started"
        assert not self.down, "resource is already down"
        self._goingDown = True
        # TODO new sim_trace action?
        #simtrace.trace_event(self, simtrace.Action.GOING_DOWN)

    @apidocskip
    def _takedown(self):
        """
        Take down this resource.

        Note that this method takes down all of the subresources if
        the resource capacity is greater than one. It does not support
        taking down some, but not all of the subresources.  That
        behavior should be modeled using separate SimResource instances
        (using the same assignment agent, probably via a resource pool).

        Should be called only by the resource's assignment agent.

        Takedowns are initiated via SimDownTimeAgents which send
        RSRC_TAKEDOWN_REQ to the assignment agent. The use of
        multiple downtime agents independently taking down the same
        resource is supported - i.e., the resource might be taken down
        more than once at overlapping times - therefore, each _takedown()
        call increments a _downCount attribute (which is decremented
        by _bringup(). The resource is down when _downCount is > 0.
        
        Also ensures that the _downPctCounter value is set to 1, to
        accurately report percentage of time down for the resource.
        """
        assert self._downCount >= 0, "_takedown() called with negative _downCount"
        self._downCount += 1
        if self._downCount == 1:
            # The resource is newly down
            self._downtimeStart = SimClock.now()
            assert self._downPctCounter.value == 0, "_downPctCounter.value not zero on first takedown()"
            self._downPctCounter.increment()
            self._goingDown = False
            simtrace.trace_event(self, simtrace.Action.DOWN)
            
    @apidocskip
    def _bringup(self):
        """
        Bring this resource back up.
        
        Decrements the _downCount attribute - the resource comes back
        up if this is now zero. (As noted for _takedown(), overlapping
        resource takedown/bringup pairs are supported.)
        
        If the resource is in fact now available, the _downPctCounter
        is set to zero to report downtime percentage.

        Should be called only by the resource's assignment agent.
        """
        assert self.down, "_bringup() called on resource that is not down"
        assert self._downCount > 0, "_bringup() called with non-positive _downCount"
        assert self._downPctCounter.value == 1, "_bringup() called when _downPctCounter is not 1"
        
        self._downCount -= 1
        if self._downCount == 0:
            self._downPctCounter.decrement()
            simtrace.trace_event(self, simtrace.Action.UP)


@apidoc
class SimSimpleResource(ResourceAssignmentAgentMixin, SimResource):
    """
    A basic SimResource that functions as its own assignment agent, filling
    resource reqests on a FIFO basis (via the assignment mix-in class). Can
    be used to represent either a single, indivisible resource object, or (if
    capacity is greater than one) multiple resources with identical behavior.

    By default, resource requests are fulfilled on a FIFO basis; that can be
    altered by registering a priority function for message type RSRC_REQUEST.

    :param name:            Name of the resource, must be unique within
                            the resource's location
    :type name:             str
    
    :param parentLocation:  Location object to which resource belongs.
                            Defaults to the Root location (if None)
    :type parentLocation:   :class:`~.location.SimLocation`

    :param initialLocation: Location where the resource is initially
                            located. May be the parent location or
                            or a sub-location of the parent. Defaults to
                            the parent location (if None)
    :type initialLocation:  :class:`~.location.SimLocation`
 
    :param capacity:        Capacity of resource, or number of
                            subresources. Defaults to 1.
    :type capacity:         int (> 0)
 
    :param moveable:        If True, the resource can move within its
                            parent location; if False, it is fixed to
                            its initial location. Defaults to True.
    :type moveable:         bool
   
    """
    def __init__(self, name, parentLocation=None, initialLocation=None, 
                 *, capacity=1, moveable=False):
        super().__init__(name, parentLocation, initialLocation, capacity,
                             self, moveable)
        self._capacity = capacity

    @property
    def capacity(self):
        """
        
        :return: The size/capacity of the resource (number of
                 subresoruces in this resource)  
        :rtype:  int (will be greater than zero)
        
        """
        return self._capacity


@apidoc
class SimResourceAssignmentAgent(ResourceAssignmentAgentMixin, SimAgent):
    """
    Useful base class for a stand-alone resource assignment agent.
    """

@apidoc
class SimResourcePool(SimResourceAssignmentAgent):
    """
    Assignment agent that manages a pool of resources. The default
    implementation allows requests to (optionally) specify the class of the
    resource requested. (That specified class could be a base class.) This
    facilitates models with heterogeneous resource pools, and processes that
    request from a sub-pool based on resource class.
    
    Client code can still request a specific resource object that belongs
    to the pool; in that case, the request processing (validation and
    assignment) is delegated to the base class implementations.
    
    The pool provides its own implementation of process_queued_requests()
    which allows sufficiently heterogenous requests of lower priority to
    be process and potentially assigned even after a higher priority
    request is not handled/assigned. The base class implementation assumes
    that all requests in its queue are competing for the same resource(s);
    for a pool, they may not be. If a pool resource request is not fulfilled
    (because the resource(s) requested are not all available), lower
    priority/later requests will be processed for potential assignment only
    if they don't compete - that is, the resource(s) requested don't overlap
    with any higher priority request that could not be fulfilled.

    The pool class defines a set of convenience methods that facilitate
    the identification of pool resources and attributes by resource class.

    :param resources: One or more resources initially assigned to
                      pool, supplied as positional arguments
    :type resources:  :class:`SimResource`
    
    """
    #TODO: currentAssignments(rsrcClass) method, maybe currentTransactions(rsrcClass)
    #TODO: think about optional pre-emption logic, either here and/or
    #      SimResourceAssignmentAgent.

    def __init__(self, *resources):
        super().__init__()
        self._resources = []
        for r in resources:
            self.add_resource(r)
    
    def add_resource(self, resource):
        """
        Add a resource to the pool, making the pool it's assignment agent.

        :param resource: The resource to be added to the pool
        :type resource:  :class:`SimResource`
 
         """
        assert isinstance(resource, SimResource), "Attempt to add a non-resource to aSimResourcePool"
        if resource in self._resources:
            errorMsg = "Cannot add resource {0} to the pool; it is already there"
            raise SimError(_POOL_ERROR, errorMsg, resource.element_id)

        elif resource.assignment_agent and resource.assignment_agent != resource:
            errorMsg = "Cannot add resource {0} to the pool; it is already managed by another pool or assignment agent"
            raise SimError(_POOL_ERROR, errorMsg, resource.element_id)

        self._resources.append(resource)
        resource.set_assignment_agent(self)

    def poolsize(self, rsrcClass=None):
        """
        Returns the sum of the resource capacities in the pool for all
        resources of a specified resource class (or the sum for all resources
        in the pool, if None is specified).
        """
        return sum([r.capacity for r in self.resources(rsrcClass)])

    def available(self, rsrcClass=None):
        """
        Returns the number of available resources of a specified resource
        class (or all classes if the specified value is None) in the pool by
        summing the available property value of the pool's resources. Note
        that an unused resource with capacity greater than one will
        contribute more than one to this sum.
        """
        return sum([r.available for r in self.resources(rsrcClass)])

    def resources(self, rsrcClass=None):
        """
        Returns a list of all resources in the pool that are instances of the
        specified resource class (or the entire pool, if the specified class
        is None)
        """
        assert rsrcClass is None or issubclass(rsrcClass, SimResource), "resources() argument must be a SimResource subclass"
        if rsrcClass is None:
            return list(self._resources)
        else:
            return [r for r in self._resources if isinstance(r, rsrcClass)]

    def available_resources(self, rsrcClass=None):
        """
        Returns a list of all available resources in the pool that are
        instances of the specified resource class (or the entire pool, if the
        specified class is None)
        """
        return [r for r in self.resources(rsrcClass) if r.available]

    def current_assignments(self, rsrcClass=None):
        """
        Returns an iterable to the current resource assignments for all
        resources in the pool of a specified class.  (Or current resource
        assignments for every resource in the pool, if the specified
        rsrcClass is None)
        """
        return chain.from_iterable(r.current_assignments()
                                   for r in self.resources(rsrcClass))

    def current_transactions(self, rsrcClass=None):
        """
        Returns a list of all of the transactions/processes using a pool
        resource of the specified class, or to all transactions using any of
        the pool's resources if rsrcClass is None.
        """
        return [assg.process for assg in self.current_assignments(rsrcClass)]
            
    def process_queued_requests(self, throughRequest=None):
        """
        Resource Pool specific implementation.
        
        Unlike the default ResourceAssignmentAgent implementation, if no
        throughRequest is specified, tthe pool continues to process requests
        after encountering a request that could not be processed/assigned
        resources. We stop only after going through the entire queue or
        processing the throughRequest (if any).
        
        As long as the request does not involve a resource or resource class
        that was specified by an earlier (higher priority) unfulfilled request,
        we attempt to process it - if the resources aren't available to fulfill it
        (_process_request() returns False) the requested resource or resource
        class is added to the set defining which later requests should be blocked
        from processing.
        
        Note that if an earlier/higher priority request specified a resource
        class, later requests that specify a subclass of that resource class
        (or a specific resource that is a subclass) will be blocked as well.
        """
        blocked_rsrc_classes = set()
        blocked_resources = set()
        
        def is_blocked(rsrc, rsrc_class):
            if rsrc is not None and rsrc in blocked_resources:
                return True
            if [cls for cls in blocked_rsrc_classes if issubclass(rsrc_class, cls)]:
                return True
            return False
                         
        # Start by running the base class algorithm.
        # If we handle every request in the queue successfully (i.e., the queue
        # is now empty), we're done. We're also done if the throughRequest
        # was processed.
        super().process_queued_requests(throughRequest)
        remaining_requests = self.queued_resource_requests()
        if not remaining_requests:
            return
        if throughRequest and throughRequest not in remaining_requests:
            return
             
        # Starting with the first request msg that could not be assigned, go 
        # through the entire queue (or until we try to process the throughRequest)  
        # in priority order. For each request msg, check for any overlap 
        # with earlier requests via is_blocked(). If there is no overlap,
        # attempt to process the request message. If the request cannot be 
        # assigned, update the blocked_resources/blocked_rsrc_classes sets as 
        # required.
        for requestMsg in remaining_requests:
            resource = requestMsg.resource
            rsrc_class = requestMsg.resource_cls
            if rsrc_class is None:
                assert resource, "resource request contains neither a resource nor a resource class"
                rsrc_class = resource.__class__
                
            if not is_blocked(resource, rsrc_class):
                handled = self._process_request_msg(requestMsg)
                if not handled:
                    if resource is not None:
                        blocked_resources.add(resource)
                    else:
                        blocked_rsrc_classes.add(rsrc_class)
            if requestMsg == throughRequest:
                return
            
                       
    def _validate_request(self, requestMsg):
        """
        Validate request message data. Specialization for resource pools,
        which assumes that last message parameter (if any) is either None
        or the class of a resource managed by the pool.
        
        If the message is in fact for a specific resource, use the
        superclass implementation.
        """
        if requestMsg.resource is not None:
            super()._validate_request(requestMsg)
            return
            
        txn, numRequested, *otherparms = requestMsg.msgData

        assert numRequested > 0, "number of resources requested not greater than zero"

        if otherparms:
            rsrcClass = otherparms[0]
        else:
            rsrcClass = None

        if rsrcClass is not None:
            if not isclass(rsrcClass) or not issubclass(rsrcClass, SimResource):
                errorMsg = "Resource Request parameter {0} from SimResourcePool is not a SimResource-derived class"
                raise SimError(_REQUEST_ERROR, errorMsg, rsrcClass)
            if not self.resources(rsrcClass):
                errorMsg = "Request for resource class {0} from a pool that does not manage any instances of that class"
                raise SimError(_REQUEST_ERROR, errorMsg, rsrcClass.__name__)

        if numRequested > self.poolsize(rsrcClass):
            errorMsg = "Number requested ({0}) is higher than than resource pool {1}'s size ({2}) for resource class {3}"
            raise SimError(_REQUEST_ERROR, errorMsg, numRequested, self,
                           self.poolsize(rsrcClass), rsrcClass.__name__)

    def _assign_from_request(self, requestMsg):
        """
        Overridden method that will, if possible, create and return
        a resource assignment that meets the passed resource request.
        
        If the message is in fact for a specific resource, use the
        superclass implementation.
        """
        if requestMsg.resource is not None:
            return super()._assign_from_request(requestMsg)
            
        numRequested = requestMsg.nrequested
        rsrcClass = requestMsg.resource_cls

        if self.available(rsrcClass) < numRequested:
            # Not enough available resources to fulfill the request
            return None
        else:
            # Build a list of available resources that fulfills the request
            # Once that list is complete (has enough resources), create and
            # return a SimResourceAssignment
            rsrcsToAssign = []
            numNeeded = numRequested
            for rsrc in self.available_resources(rsrcClass):
                n = min(rsrc.available, numNeeded)
                rsrcsToAssign.extend((rsrc,) * n)
                numNeeded -= n
                if numNeeded == 0:
                    process = requestMsg.process
                    return SimResourceAssignment(process, self, rsrcsToAssign)
            assert False, "Should never reach this!!!"


class SimResourceRequest(SimMessage):
    """
    A subclass of the SimMessage namedtuple that:
    
    * Defines properties returning the basic SimMessage data fields, but 
      with property names reflecting this specific message type.
    * Defines properties extracting data from the message's msgData field.
    * Adds methods for making/processing resource assignments
      (including sending resource assignment response messages),
      primarily for the benefit of model-specific ResourceAssignmentAgent
      subclasses.
       
    SimProcess should pass this class when sending resource request
    (SimMsgType RSRC_REQUEST) messages, so that the handling assignment
    agent will create message objects of this type.
    """
    __slots__ = []
    if __debug__:
        def __new__(cls, *args, **kwargs):
            """
            Confirm this is a RSRC_REQUEST message typ before continuing.
            """
            newmsg = SimMessage.__new__(cls, *args, **kwargs)
            assert newmsg.msgType == SimMsgType.RSRC_REQUEST, " attempt to create SimResourceRequest with a non RSRC_REQUEST message type"
            return newmsg
    
    @property
    def request_time(self):
        """
        Returns the time the request message was sent/made
        
        :return: The (simulated) time the request was made
        :rtype:  :class:`~simprovise.core.simtime.SimTime`
        """
        return self.sendTime
        
    @property
    def entity(self):
        """
        :return: The entity making the resource request
        :rtype:  :class:`~.entity.SimEntity`
        """
        assert isinstance(self.sender, SimEntity), "SimResourceRequest sender is not a SimEntity"
        return self.sender
    
    @property
    def assignment_agent(self):
        """
        :return: The resource assignment agent managing the requested resource(s)
        :rtype:  :class::`SimResourceAssignmentAgent`
        """
        return self.receiver
    
    @property
    def process(self):
        """
        :return: The process making the resource request
        :rtype:  :class:`~.process.SimProcess`
        """
        process, *otherparms = self.msgData
        return process
    
    @property
    def resource(self):
        """
        Returns the specific resource requested, or None if a the request is
        for a :class:`SimResource` class
        
        :return: The specific resource requested, or None if a the request is
                 for a :class:`SimResource` class
        :rtype:  :class:`SimResource` or `None`
        """
        process, numRequested, *otherparms = self.msgData
        assert otherparms, "resource request message missing resource/class data"
        if isinstance(otherparms[0], SimResource):
            return otherparms[0]
        else:
            assert self.resource_cls, "Resource request specifies neither a resource nor resource class"
            return None
    
    @property
    def resource_cls(self):
        """
        Returns the :class:`SimResource` class requested, or None if the
        request is for a specific :class:`SimResource` instance.
        
        :return: The class resource requested, or None if a the request is
                 for a specific :class:`SimResource` instance
        :rtype:  subclass of :class:`SimResource` or `None`
        """
        process, numRequested, *otherparms = self.msgData
        assert otherparms, "resource request message missing resource/class data"

        p = otherparms[0]
        if isinstance(p, type) and issubclass(p, SimResource):
            return p
        else:
            assert isinstance(p, SimResource), "Resource request specifies neither a resource nor resource class"
            return None
    
    @property
    def nrequested(self):
        """
        Returns the number of :class:`resources <SimResource>` requested,
        which typically defaults to one.
        
        :return: The number of resources requested
        :rtype:  `int`        
        """
        process, numRequested, *otherparms = self.msgData
        return numRequested
    
    def assign_resource(self, resource, numAssigned=1):
        """
        Assign a passed resource (or more than one of that resource, if
        it has capacity > 1) to the requesting :class:~`.entity.SimEntity`.
        Also removes the request from the assignment agent's message queue,
        since the request has now been handled/fulfilled.
        
        Really just a convenience method - delegates directly to
        :meth:`assign_resources`.
        
        :param resource:    The resource( to be assigned in fulfillment of this
                            request.
        :type resources:    :class:`SimResource`
         
        :param numAssigned: The number/amount of `resource` to be assgined.
                            Defaults to one, cannot be greater than the
                            resource's capacity                            
        :type numAssigned:  `int`
            
        """
        self.assign_resources((resource, ) * numAssigned)
             
    def assign_resources(self, resources):
        """
        Assign the passed resource(s) to the requesting :class:~`.entity.SimEntity`.
        Also removes the request from the assignment agent's message queue,
        since the request has now been handled/fulfilled.
        
        :param resources: The resource(s) to be assigned in fulfillment of this
                          request.
        :type resources:  An iterable to instances of class :class:`SimResource`
        """        
        assert self in self.assignment_agent.queued_resource_requests(), "request message already removed from queue - has it already been assigned?"
        
        # Create the resource assignment (which will also validate)
        assignment = SimResourceAssignment(self.process,
                                           self.assignment_agent, resources)
        
        # Process the resource assignment  by sending it as a response to the 
        # requesting entity and removing the request from the assignment agent's 
        # message queue.
        self._process_resource_assignment(assignment)
        
    def _process_resource_assignment(self, assignment):
        """
        For now at least, let the resource assignment agent do this,
        since there might be assignment agent subclasses that modify
        the behavior. We'll also keep this as a non-public API for
        the time being.
        """
        self.assignment_agent._process_assignment(self, assignment)

                
#class TakedownResourceEvent(SimEvent):
    #"""
    #An event that initiates a single resource takedown via a passed
    #SimDownTimeAgent.
    #"""
    #__slots__ = ('_downtimeController', '_resource')
    
    #def __init__(self, controller, resource, tm):
        #super().__init__(tm, priority=3)
        #self._downtimeController = controller
        #self._resource = resource
        
    #def process_impl(self):
        #"""
        #Tell the downtime agent to request a resource takedown
        #"""
        #self._downtimeController.takedown_resource()
    
    
#class BringupResourceEvent(SimEvent):
    #"""
    #An event that initiates a single resource bring-up via a passed
    #SimDownTimeAgent. Should be the same agent that brought the
    #resource down.
    #"""
    #__slots__ = ('_downtimeController', '_resource')
    
    #def __init__(self, controller, resource, tm):
        #super().__init__(tm, priority=3)
        #self._downtimeController = controller
        #self._resource = resource
        
    #def process_impl(self):
        #"""
        #Tell the downtime agent to request a resource bringup
        #"""
        #self._downtimeController.bringup_resource()        

#class SimDownTimeController(metaclass=ABCMeta):
    #"""
    #"""
    #__slots__ = ('_resource')
    #def __init__(self, resource):
        #"""
        #"""
        #assert resource, "Null resource supplied to SimResourceDownTime"
        #assert isinstance(resource, SimResource), "SimResourceDownTime resource parameter is not a SimResource"
        #self._resource = resource
        #resource.add_downtime_controller(self)
        
    #def initialize(self):
        #"""
        #Create and chedule the initial takedown event.
        
        #Invoked by the :meth:`SimResource.final_initialize` after the
        #event processor/event heap are initialized.
        #"""
        #takedown_time = self._next_takedown_time()
        #takedownEvent = TakedownResourceEvent(self, _resource, takedown_time)
        #takedownEvent.register()
                
    #def takedown_resource(self):
        #"""
        #"""
        #self._resource._takedown()
                    
    #def bringup_resource(self):
        #"""
        #"""
        #self._resource._bringup()
        #takedownEvent = TakedownResourceEvent(self._resource,
                                              #self._next_takedown_time())
        #takedownEvent.register()
        
    #@abstractmethod
    #def _next_takedown_time(self):
        #"""
        #"""
        #pass
