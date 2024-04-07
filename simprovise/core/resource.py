#===============================================================================
# MODULE resource
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimResource-related classes - SimResourceAssignment,
# SimResource, SimSimpleResource, SimResourceAssignmentAgent and
# SimAssignmentAgentMixin.
#===============================================================================
__all__ = ['SimResource', 'SimSimpleResource', 'SimResourcePool', 
           'SimResourceAssignment']

from itertools import chain
from inspect import isclass
#from abc import ABCMeta, abstractmethod, abstractproperty

from simprovise.core import (SimCounter, SimUnweightedDataCollector, SimError,
                            SimTime, SimClock, SimLogging)
from simprovise.core.agent import SimAgent, SimMsgType
from simprovise.core.location import SimStaticObject
from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.getLogger(__name__)

# a constant
#ALL = None
_REQUEST_ERROR = "Resource Request Error"
_RELEASE_ERROR = "Resource Release Error"
_POOL_ERROR = "Resource Pool Error"

def _resourceNameList(resourceSeq):
    """
    """
    return [resource.element_id for resource in resourceSeq]

@apidoc
class SimResourceAssignment(object):
    """
    Encapsulates a set of zero or more resources assigned to a process
    via :meth:`.SimTransaction.acquire`.

    Args:
        transaction (SimProcess):   Process (transaction) to which resource(s)
                                    are being assigned
        assignmentAgent (SimAgent): Agent managing the assigned resource(s)
        resources (sequence):       Sequence of SimResource(s) to be included
                                    in assignment
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
               ", Agent:" + str(self.assignmentAgent) + ", Resources: " + \
               str(self.resources)

    @property
    def transaction(self):
        "The transaction (SimProcess) to which these resources are assigned"
        return self._txn

    @property
    def assignmentAgent(self):
        """
        The SimAgent (possibly the resource itself, possibly not) that manages
        acquisition and release of this assignment.
        """
        return self._assignmentAgent

    @property
    def count(self):
        "The number of resources assigned"
        return len(self._resources)

    @property
    def resources(self):
        "A tuple of the resources assigned"
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

        Returns:
            SimResource: The single SimResource instance included in this
                         assignment
        """
        if 1 < len(set(self._resources)):
            raise SimError("Attempt to access (singular) resource property on ResourceAssignment with multiple resources: " + str(self))
        if self.count == 0:
            raise SimError("Attempt to access resource property on a null (no resources) assignment: " + str(self))
        return self._resources[0]

    @property
    def assignTime(self):
        """
        The SimTime that this assignment was created/made.
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
            raise SimError("Resource List ({0}) not contained in assignment {1}".format(resourcesToSubtract, self))

        self._resources = tuple(rlist)

    def subtractAll(self):
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
    via :meth:`requestPriorityFunc` and/or overriding :meth:`assignFromRequest`
    in a subclass.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_handler(SimMsgType.RSRC_REQUEST, self.handleResourceRequest)
        self.register_handler(SimMsgType.RSRC_RELEASE, self.handleResourceRelease)

    @property
    def requestPriorityFunc(self):
        """
        Returns/sets the priority function for Resource Request messages.
        The priority function must take a request message as it's sole argument
        and return a numeric priority, where the lower value is the higher
        priority (e.g., priority 1 is higher than priority 2).
        """
        return self.priority_func(SimMsgType.RSRC_REQUEST)

    @requestPriorityFunc.setter
    def requestPriorityFunc(self, f):
        self.register_priority_func(SimMsgType.RSRC_REQUEST, f)

    def createResourceAssignment(self, txn, resource, numToAssign=1):
        """
        Create and return a SimResourceAssignment involving a single resource
        object, though if this resource has capacity > 1, we may assign more
        than one of that capacity.

        Args:
            txn (SimProcess):       Process to which resource(s) are to be
                                    assigned
            resource (SimResource): Resource object to be assigned
            numToAssign (int > 0):  Amount of resource to assign; must be <= the
                                    capacity of resource
        Returns:
            SimResourceAssignment: Resource assignment as specified by above
                                   parameters
        """
        assert numToAssign > 0, "Number of resources to assign must be greater than zero"
        assert resource.capacity >= numToAssign, "Resource does not have capacity for assignment"
        return SimResourceAssignment(txn, self, (resource,) * numToAssign)

    def createMultipleResourceAssignment(self, txn, *resources):
        """
        Create and return a SimResourceAssignment from the passed resources,
        which may be any combination of resource instances and/or sequences
        of resources. A generalized version of createResourceAssignment().

        Args:
            txn (SimProcess): Process to which resource(s) are to be assigned
            resources:        One or more SimResource objects to be assigned
        Returns:
            SimResourceAssignment: Resource assignment as specified by above
                                   parameters
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

    def handleResourceRequest(self, msg):
        """
        The handler registered to handle resource request messages.

        Handle a resource request as it comes in. If all of the resources
        requested are available - and there is no other request (presumably
        needing more resources than currently available) ahead of it, fulfill
        the request by responding with a resource assignment message, and
        marking the request message as "handled" by returning True.

        If the requested cannot be fulfilled, just return False, which should
        place the request on the message queue for later processing/fulfillment.

        Args:
            msg (SimMessage): Resource Request message

        Returns:
            bool: True if request is fulfilled immediately, False if queued for
                  fulfillment later.
        """
        assert msg.msgType == SimMsgType.RSRC_REQUEST, "Invalid message type passed to handleResourceRequest()"

        # Validate the message, raising an exception if there is a problem.
        self._validateRequest(msg)

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
        nextRequest = self.nextRequestMessage()
        if nextRequest and (self.message_priority(msg) is None or
                            self.message_priority(nextRequest) <= self.message_priority(msg)):
            return False
        else:
            return self._processRequest(msg)


    def _validateRequest(self, requestMsg):
        """
        Validate request message data.
        This default implementation works when the message data specifies a
        specific resource instance; typically should be overridden for agents
        managing multiple resources. (e.g. resource pools)
        """
        txn, numRequested, resource, *otherparms = requestMsg.msgData

        assert numRequested > 0, "number of resources requested not greater than zero"
        assert isinstance(resource, SimResource), "Resource request data does not specify an instance of class SimResource"

        if resource.assignmentAgent is not self:
            errorMsg = "Request for resource {0} sent to agent that does not manage that resource"
            raise SimError(_REQUEST_ERROR, errorMsg, resource.element_id)

        if numRequested > resource.capacity:
            errorMsg = "Number requested ({0}) is higher than than resource {1}'s capacity ({2})"
            raise SimError(_REQUEST_ERROR, errorMsg, numRequested,
                           resource.element_id, resource.capacity)


    def _processRequest(self, requestMsg):
        """
        Attempt to process a resource request, returning True if successful (and
        False otherwise).
        """
        resourceAssignment = self.assignFromRequest(requestMsg)
        if resourceAssignment:
            # Do assignTo(s) and sendResponse
            txn = requestMsg.msgData[0]
            for resource in resourceAssignment.resources:
                resource.assignTo(txn)
            self.send_response(requestMsg, SimMsgType.RSRC_ASSIGNMENT, resourceAssignment)
            # Handled, so return True
            return True
        else:
            return False

    def assignFromRequest(self, requestMsg):
        """
        This method, called by _processRequest(), actually implements the
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

        Args:
            msg (SimMessage): Resource Request message

        Returns:
            SimResourceAssignment or None: Depending on whether request can be
                                           fulfilled now.
        """
        # Extract the message data.
        txn, numRequested, resource = requestMsg.msgData

        assert numRequested > 0, "number of resources requested not greater than zero"
        assert isinstance(resource, SimResource), "Resource request data does not specify an instance of class SimResource"


        if numRequested <= resource.available:
            return self.createResourceAssignment(txn, resource, numRequested)
        else:
            return None

    def handleResourceRelease(self, msg):
        """
        The handler registered to handle resource release messages.

        Handles each resource release notification as it comes in, returning
        ``True`` to indicate that it was, in fact handled. The
        :class:`SimProcess` (or the agent owning that process) is responsible
        for updating the resource assignment object that is included in the
        message.

        After releasing the resources, this handler will attempt to respond
        to one or more request messages in the message queue if they can now
        be fulfilled using the newly released resource(s).

        Args:
            msg (SimMessage): Resource Release message

        Returns:
            bool: ``True`` always
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
            if resource.assignmentAgent is not self:
                errorMsg = "Release for resource {0} sent to agent that does not manage that resource"
                raise SimError(_RELEASE_ERROR, errorMsg, resource.element_id)
            resource.releaseFrom(assignment.transaction, 1)

        assignment.subtract(resourcesToRelease)

        # Now that we have one or more available resources, attempt to
        # respond to outstanding (queued) resource requests.
        self.processQueuedRequests()

        # Since we handled the release message, return True
        return True

    def processQueuedRequests(self):
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
        nextRequest = self.nextRequestMessage()
        while nextRequest and self._processRequest(nextRequest):
            self.msgQueue.remove(nextRequest)
            nextRequest = self.nextRequestMessage()

    def nextRequestMessage(self):
        """
        Returns the next request message (type SimResource.REQUEST_MSGTYPE)
        in the resource's message queue, or None if there aren't any.
        Applies priority function, if any.

        Does NOT remove the message from the queue

        Returns:
           SimMessage or None: Next request message in queue (based on priority)
                               or None if the queue is empty.
        """
        return self.next_queued_message(SimMsgType.RSRC_REQUEST)


@apidoc
class SimResource(SimStaticObject):
    """
    Encapsulates a resource that is used (possibly in conjunction with other
    resources) to perform a process. SimResources are locatable static objects.
    Note that while a SimResource may be able to move, the SimLocation to
    which it belongs does not change. (For static objects, location refers
    more directly to ownership than to specific physical location at any
    given simulated time.)

    Args:
        name (str):                 Name of the resource, must be unique within
                                    the resource's location
        locationObj (SimLocation):  Location object to which resource belongs.
                                    If None resource is assigned to Root location
        animationObj:               None if the simulation is not animated
        capacity (int > 0):         Capacity of resource, or number of
                                    subresources. Defaults to 1.
        assignmentAgent (SimAgent): Agent managing (assigning) this resource.
                                    If None, the resource is assumed to be its
                                    own agent.
    """
    #TODO
    #This becomes an abstract base class, with subclasses
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

    def __init__(self, name, locationObj=None, animationObj=None, capacity=1,
                 assignmentAgent=None):
        super().__init__(name, locationObj, animationObj)

        self._processtimeDataCollector = SimUnweightedDataCollector(self, "ProcessTime", SimTime)
        # TODO other data collectors or counters, to measure time by availability and/or reason,
        # policy mechanisms to determine what data to collect

        # The normalize flag will ensure that the dataset associated with
        # this counter has values normalized based on capacity (i.e., dataset
        # values will be over range 0.0-1.0)
        self._utilCounter = SimCounter(self, "Utilization", capacity, normalize=True)

        self._currentTxnAssignments = {}
        if assignmentAgent is not None:
            self.assignmentAgent = assignmentAgent
        else:
            self.assignmentAgent = self

    @property
    def isMoveable(self):
        """
        Indicates whether or not the resource is fixed or moveable. By default,
        resources are moveable.

        Returns:
            bool: True if the resource can move (to SimLocations)
        """
        return True

    @property
    def capacity(self):
        """
        The size/capacity of the resource (number of subresources in this
        resource)

        Returns:
            int: The capacity of the resource, if finite.
        """
        return self._utilCounter.capacity

    def assignTo(self, txn, number=1):
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

        Args:
            txn (SimProcess): Process to which this resource is to be assigned
            number (int > 0): Number of resources to be assigned (can be > 1
                              if the resource has capacity > 1)
        """
        assert number <= self.available, "Resource is not available for assignment"
        assert number > 0, "assignTo() number must be greater than zero"
        self._utilCounter.increment(txn, number)
        if txn in self._currentTxnAssignments:
            self._currentTxnAssignments[txn][1] += number
        else:
            self._currentTxnAssignments[txn] = [SimClock.now(), number]

    @property
    def currentAssignments(self):
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

    @property
    def currentTransactions(self):
        """
        Returns a list of transactions (processes) currently using this resource.
        """
        return list(self._currentTxnAssignments)

    def releaseFrom(self, txn, numToRelease=None):
        """
        Releases this resource (or if this resource has capacity > 1, the
        passed number of subresources) from a previous assignment to the
        passed transaction (task or process).

        Should be called ONLY by the resource's assignment agent.

        TODO change numToRelease to subresource (if None resource to
        release is self)

        Args:
            txn (SimProcess):      Process to which this resource is currently
                                   assigned
            numberToRelease (int): Number of subresources to be released
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
            self._processtimeDataCollector.addValue(SimClock.now() - assignTime)
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

    @property
    @apidocskip
    def minProcessTime(self):
        "Time spent processing an assignment - minimum"
        return self._processtimeDataCollector.min()

    @property
    @apidocskip
    def maxProcessTime(self):
        "Timespent processing an assignment - maximum"
        return self._processtimeDataCollector.max()

    @property
    @apidocskip
    def meanProcessTime(self):
        "Time spent processing an assignment - mean"
        return self._processtimeDataCollector.mean()

    @property
    @apidocskip
    def utilization(self):
        "Resource utilization (range 0-1)"
        return self._utilCounter.utilization

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

    Args:
        name (str):                 Name of the resource, must be unique within
                                    the resource's location
        locationObj (SimLocation):  Location object to which resource belongs.
                                    If None resource is assigned to Root location
        animationObj:               None if the simulation is not animated
        capacity (int > 0):         Capacity of resource, or number of
                                    subresources. Defaults to 1.
    """
    def __init__(self, name, locationObj=None, animationObj=None, capacity=1):
        super().__init__(name, locationObj, animationObj, capacity, self)
        self._capacity = capacity

    @property
    def capacity(self):
        """
        The size/capacity of the resource (number of subresoruces in this
        resource) Default value is 1
        """
        return self._capacity

    @capacity.setter
    def capacity(self, newValue):
        """
        Capacity can only be set in design mode, since we currently do not support
        dynamically raising or reducing capacity during a simulation run.
        """
        self.raiseIfNotInDesignMode("Resource capacity can only be modified at design time")
        self._capacity = int(newValue)
        if self._capacity <= 0:
            msg = "Resource capacity must be > 0"
            raise SimError("Invalid Resource Operation", msg)


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

    Args:
        resources (SimResource): One or more resources initially assigned to
                                 pool, supplied as positional arguments
    """
    #TODO: currentAssignments(rsrcClass) method, maybe currentTransactions(rsrcClass)
    #TODO: think about optional pre-emption logic, either here and/or
    #      SimResourceAssignmentAgent.

    def __init__(self, *resources):
        super().__init__()
        self._resources = []
        for r in resources:
            self.addResource(r)

    def addResource(self, resource):
        """
        Add a resource to the pool, making the pool it's assignment agent.

        Args:
            resource (SimResource): the resource to be added to the pool
        """
        assert isinstance(resource, SimResource), "Attempt to add a non-resource to aSimResourcePool"
        if resource in self._resources:
            errorMsg = "Cannot add resource {0} to the pool; it is already there"
            raise SimError(_POOL_ERROR, errorMsg, resource.element_id)

        elif resource.assignmentAgent and resource.assignmentAgent != resource:
            errorMsg = "Cannot add resource {0} to the pool; it is already managed by another pool or assignment agent"
            raise SimError(_POOL_ERROR, errorMsg, resource.element_id)

        self._resources.append(resource)
        resource.assignmentAgent = self

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

    def availableResources(self, rsrcClass=None):
        """
        Returns a list of all available resources in the pool that are
        instances of the specified resource class (or the entire pool, if the
        specified class is None)
        """
        return [r for r in self.resources(rsrcClass) if r.available]

    def currentAssignments(self, rsrcClass=None):
        """
        Returns an iterable to the current resource assignments for all
        resources in the pool of a specified class.  (Or current resource
        assignments for every resource in the pool, if the specified
        rsrcClass is None)
        """
        return chain.from_iterable(r.currentAssignments
                                   for r in self.resources(rsrcClass))

    def currentTransactions(self, rsrcClass=None):
        """
        Returns a list of all of the transactions/processes using a pool
        resource of the specified class, or to all transactions using any of
        the pool's resources if rsrcClass is None.
        """
        return [assg.transaction for assg in self.currentAssignments(rsrcClass)]

    def _validateRequest(self, requestMsg):
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


    def assignFromRequest(self, requestMsg):
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
            for rsrc in self.availableResources(rsrcClass):
                n = min(rsrc.available, numNeeded)
                rsrcsToAssign.extend((rsrc,) * n)
                numNeeded -= n
                if numNeeded == 0:
                    return SimResourceAssignment(txn, self, rsrcsToAssign)
            assert False, "Should never reach this!!!"


