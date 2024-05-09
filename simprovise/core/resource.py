#===============================================================================
# MODULE resource
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimResource-related classes - SimResourceAssignment,
# SimResource, SimSimpleResource, SimResourceAssignmentAgent,
# SimAssignmentAgentMixin and SimResourcePool.
#===============================================================================
__all__ = ['SimResource', 'SimSimpleResource', 'SimResourcePool', 
           'SimResourceAssignment', 'SimResourceAssignmentAgent']

from itertools import chain
from inspect import isclass

from simprovise.core import (SimCounter, SimUnweightedDataCollector, SimError,
                            SimTime, SimClock, SimLogging)
from simprovise.core.agent import SimAgent, SimMsgType
from simprovise.core.location import SimStaticObject
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
    via :meth:`.SimTransaction.acquire`.
    
        :param transaction:     :class:`SimProcess` to which resource(s)
                                are being assigned
        :type transaction:      :class:`SimProcess` object
    
        :param assignmentagent: Agent (which might be the resource itself) 
                                which made this assignment
        :type assignmentagent:  :class:`SimAgent` object
    
        :param resources:      The resource(s) (at least one) in the assignment.
        :type resources:       Sequence of class :class:`SimResource` objects

    """
    __slots__ = ('_txn', '_assignmentAgent', '_resources', '_assignTime')

    def __init__(self, transaction, assignmentAgent, resources):
        self._txn = transaction
        self._assignmentAgent = assignmentAgent
        self._resources = tuple(resources)
        self._assignTime = SimClock.now()
        if len(resources) == 0:
            raise SimError("A ResourceAssignment must be constructed with at least one resource")

    def __str__(self):
        return "Resource Assignment: Transaction: " + str(self.transaction) + \
               ", Agent:" + str(self.assignment_agent) + ", Resources: " + \
               str(self.resources)

    @property
    def transaction(self):
        """
       The transaction (SimProcess) to which these resources are assigned
        """
        return self._txn

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

@apidoc
class ResourceAssignmentAgentMixin(object):
    """
    A mix-in class that provides a SimAgent (which may or may not be a resource)
    with basic resource assignment functionality - the ability to handle
    resource request and release messages. The mixin defines handler functions
    for both of those message types.

    By default, this mix-in fulfills requests on a first-in/first-out basis.
    That behavior may be overridden by registering a request priority function
    via :meth:`requestPriorityFunc` and/or overriding :meth:`assign_from_request`
    in a subclass.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_handler(SimMsgType.RSRC_REQUEST, self._handle_resource_request)
        self.register_handler(SimMsgType.RSRC_RELEASE, self._handle_resource_release)

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

    def _create_resource_assignment(self, txn, resource, numToAssign=1):
        """
        Create and return a SimResourceAssignment involving a single resource
        object, though if this resource has capacity > 1, we may assign more
        than one of that resource (up to its capacity).
       
        :param txn:        The transaction to which resources are to be assigned
        :type txn:         :class:`~.process.SimProcess`
        
        :param resource:    Resource object to be assigned
        :type resource:     :class:`SimResource`
        
        :param numToAssign: Resource object to be assigned
        :type numToAssign:  int, range [1, resource capacity]
        
        :return:            Resource assignment as specified by above parameters
        :rtype:             :class:`SimResourceAssignment`
 
         """
        if numToAssign <= 0 or numToAssign > resource.capacity: 
            msg = "Assignment for {0} of resource {1} is not in range 1-capacity ({2})"
            raise SimError(_REQUEST_ERROR, msg, numToAssign,
                           resource.element_id, resource.capacity)
        
        return SimResourceAssignment(txn, self, (resource,) * numToAssign)

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

        Handle a resource request as it comes in. If all of the resources
        requested are available - and there is no other request (presumably
        needing more resources than currently available) ahead of it, fulfill
        the request by responding with a resource assignment message, and
        marking the request message as "handled" by returning True.

        If the requested cannot be fulfilled, just return False, which should
        place the request on the message queue for later processing/fulfillment.

        :param msg: Resource Request message (SimMsgType RSRC_REQUEST)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    True if request is fulfilled immediately, False if queued for
                    fulfillment later.
        :rtype:     bool

        """
        assert msg.msgType == SimMsgType.RSRC_REQUEST, "Invalid message type passed to handleResourceRequest()"

        # Validate the message, raising an exception if there is a problem.
        self._validate_request(msg)

        # Determine if there is an earlier request on the queue that we
        # should attempt to fulfill first - if so, we'll defer processing of
        # this message and return False. If not, we will attempt to fulfill
        # this request via a call to _processRequest().
        #
        # If the requests are being handled FIFO (the default, no priority
        # function specified) than we should defer to any message on the
        # queue. If we have a priority function, defer if the next request is
        # a higher (lower-valued) priority as compared to the request we are
        # handling.
        nextRequest = self._next_request_message()
        if nextRequest and (self.message_priority(msg) is None or
                            self.message_priority(nextRequest) <= self.message_priority(msg)):
            return False
        else:
            return self._process_request(msg)


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


    def _process_request(self, requestMsg):
        """
        Attempt to process a resource request, returning True if successful (and
        False otherwise).
        """
        resourceAssignment = self._assign_from_request(requestMsg)
        if resourceAssignment:
            # Do assignTo(s) and sendResponse
            txn = requestMsg.msgData[0]
            for resource in resourceAssignment.resources:
                resource.assign_to(txn)
            self.send_response(requestMsg, SimMsgType.RSRC_ASSIGNMENT, resourceAssignment)
            # Handled, so return True
            return True
        else:
            return False

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
        txn, numRequested, resource = requestMsg.msgData
        
        assert numRequested > 0, "number of resources requested not greater than zero"
        assert isinstance(resource, SimResource), "Resource request data does not specify an instance of class SimResource"


        if numRequested <= resource.available:
            return self._create_resource_assignment(txn, resource, numRequested)
        else:
            return None

    def _handle_resource_release(self, msg):
        """
        The handler registered to handle resource release messages.

        Handles each resource release notification as it comes in, returning
        ``True`` to indicate that it was, in fact handled. The
        :class:`~.process.SimProcess` (or the agent owning that process)
        is responsible for updating the resource assignment object that
        is included in the message.

        After releasing the resources, this handler will attempt to respond
        to one or more request messages in the message queue if they can now
        be fulfilled using the newly released resource(s).

        :param msg: Resource Request message (SimMsgType RSRC_RELEASE)
        :type msg:  :class:`~.agent.SimMessage`
                
        :return:    ``True`` always, as the message is always handled
        :rtype:     bool

        """
        assert msg.msgType == SimMsgType.RSRC_RELEASE, "Invalid message type passed to handleResourceRelease()"

        assignment, releaseSpec = msg.msgData

        if len(assignment.resources) == 0:
            errorMsg = "Invalid release: assignment passed to handleResourceRelease() has no resources"
            raise SimError(_RELEASE_ERROR, errorMsg)

        # The default is to release all resources in the assignment
        if not releaseSpec:
            resourcesToRelease = assignment.resources

        # If the caller has specified a resource instance, handle it by
        # converting it to an iterable
        elif isinstance(releaseSpec, SimResource):
            resourcesToRelease = (releaseSpec,)

        # If the caller has specified a number (n) rather than resources,
        # release the first n resources in the assignment. Raise if n is
        # greater than the number of resources in the assignment.
        elif type(releaseSpec) is int:
            n = releaseSpec
            if n <= assignment.count:
                resourcesToRelease = assignment.resources[:n]
            else:
                errorMsg = "Invalid resource release: release specifies more resources ({0}) that are not currently in the assignment ({1})"
                raise SimError(_RELEASE_ERROR, errorMsg, n, assignment.count)

        # Otherwise, the release spec should be an iterable of SimResources
        else:
            resourcesToRelease = releaseSpec

        if not assignment.contains(resourcesToRelease):
            errorMsg = "Invalid release: release specifies resources that are not currently in the assignment"
            raise SimError(_RELEASE_ERROR, errorMsg)

        for resource in resourcesToRelease:
            if resource.assignment_agent is not self:
                errorMsg = "Release for resource {0} sent to agent that does not manage that resource"
                raise SimError(_RELEASE_ERROR, errorMsg, resource.element_id)
            resource.release_from(assignment.transaction, 1)

        assignment.subtract(resourcesToRelease)

        # Now that we have one or more available resources, attempt to
        # respond to outstanding (queued) resource requests.
        self._process_queued_requests()

        # Since we handled the release message, return True
        return True

    def _process_queued_requests(self):
        """
        This method is called by handleResourceRelease() after resource
        release; it is responsible for (at least attempting) to fulfill
        resource requests in the queue, now that there are one or more
        resources newly available.

        This (default) implementation loops through the request queue until
        it either:

        a) Cannot handle that request (i.e., assign resources to the requestor)
           or
        b) Empties the queue

        Note that if this implementation cannot fulfill the first/highest
        priority request remaining, it does NOT allow a later/lower priority
        request to "jump the queue". Subclassed agents may choose to modify this
        behavior.
        """
        nextRequest = self._next_request_message()
        while nextRequest and self._process_request(nextRequest):
            self.msgQueue.remove(nextRequest)
            nextRequest = self._next_request_message()

    def _next_request_message(self):
        """
        Returns the next request message (type SimResource.REQUEST_MSGTYPE)
        in the resource's message queue, or None if there aren't any.
        Applies priority function, if any.

        Does NOT remove the message from the queue
                
        :return: SimMessage or None: Next request message in queue (based
                 on priority) or None if there are no request messages in
                 the queue
        :rtype:  :class:`~.agent.SimMessage` or None

        """
        return self.next_queued_message(SimMsgType.RSRC_REQUEST)
    
    def remove_request_message(self, msg):
        """
        """
        assert msg.msgType == SimMsgType.RSRC_REQUEST, "Invalid message type passed to handleResourceRequest()"
        self.msgQueue.remove(msg)

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
                 '_currentTxnAssignments', 'assignmentAgent')

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
        
        self._utilCounter.increment(txn, number)
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
        assgIter = chain.from_iterable([txn.resourceAssignments
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

    @property
    def inUse(self):
        "The number of subresources currently assigned to a process"
        return self._utilCounter.value

    @property
    @apidocskip
    def down(self):
        """
        Returns True if the resource has been taken down via a takedown() call.
        Not yet implemented
        """
        return False

    @property
    def available(self):
        """
        The number of resources currently available - zero if the resource is
        down, capacity-inUse if the resource is up.
        """
        if self.down:
            return 0
        else:
            return self.capacity - self.inUse

    @apidocskip
    def takedown(self, reason):
        """
        Take down this resource (if it has capacity > 1, all of the
        resources) for a specified reason. The reason is used for reporting
        purposes; it may also be used to specify takedown behavior as
        implemented by the resource's assignment agent (which should be the
        only object calling this method). For example, going-off-shift might
        imply finishing the existing process first, while fail implies an
        immediate takedown.

        Note that this method does not support taking down some, but not all
        of the subresources when capacity > 1.  That behavior should be modeled
        using separate SimResource instances (probably using the same
        assignment agent).

        Should be called only by the resource's assignment agent.

        TODO implement

        """
        pass

    @apidocskip
    def bringup(self):
        """
        Bring this resource back up, if it is currently down.

        Should be called only by the resource's assignment agent.

        TODO implement
        """
        pass


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
                 capacity=1, moveable=True):
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
        return [assg.transaction for assg in self.current_assignments(rsrcClass)]

    def _validate_request(self, requestMsg):
        """
        Validate request message data. Specialization for resource pools,
        which assumes that last message parameter (if any) is either None
        or the class of a resource managed by the pool.
        """
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
        """
        # Extract the message data.
        txn, numRequested, *otherparms = requestMsg.msgData

        if otherparms:
            rsrcClass = otherparms[0]
        else:
            rsrcClass = None

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
                    return SimResourceAssignment(txn, self, rsrcsToAssign)
            assert False, "Should never reach this!!!"


