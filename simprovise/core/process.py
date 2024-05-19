#===============================================================================
# MODULE process
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimProcess and SimProcessElement classes.
#===============================================================================
__all__ = ['SimProcess']

from simprovise.core.transaction import SimTransaction, BaseInterruptEvent
from simprovise.core.simevent import SimEvent
from simprovise.core.simelement import SimClassElement 
from simprovise.core.agent import SimMsgType
from simprovise.core.apidoc import apidoc, apidocskip

from simprovise.core import (SimEntity, SimCounter, SimTime, SimClock,
                             SimUnweightedDataCollector)
from simprovise.core import SimLogging, SimError, SimTimeOutException
logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "SimProcessError"
_ACQUIRE_ERROR = "Resource Acquisition Error"


@apidocskip
class SimTimeOutEvent(BaseInterruptEvent):
    """
    Timeout a resource acquisition request. As with the base class
    Interrupt event, we rely on the higher priority of Resume events
    to ensure that if the resume and timeout occur at the
    same simulated time, the resume will be processed first and
    deregister this event.
    """
    __slots__ = ('assignmentAgent', 'requestMsg')
    def __init__(self, process, agent, msg, timeout=0):
        super().__init__(process, SimTimeOutException(),
                         SimClock.now() + timeout, priority=3)
        self.assignmentAgent = agent
        self.requestMsg = msg
        
    def process_impl(self):
        """
        This event has a higher priority than SimAssignResourcesEvents
        in order to prevent a race condition where the process handles
        the timeout exception by requesting a different resource while
        a lower priority resource concurrently requests that same resource.
        The higher priority timedout process should win, but won't if a
        SimAssignResourcesEvent is processed before the SimTimeOutEvent.
        (See simresource_test.AcquireTimeoutTests.testTimeoutAlternateRsrc2)
        
        But we also have to handle the case where the originally requested
        resource becomes available at the same time as the timeout. So
        we start by doing a partial rssource assignment, starting with
        the highest priority requests and going through (if we get that far)
        to this about-to-timeout request. We don't attempt to process
        requests of lower priority than this one, because by doing so we
        might inadvertently assign a resource that this process is about
        to request after timing out.
        
        The call to _process_queued_requests will only return True
        if this request was fulfilled; if it was not, we go ahead and
        wake up and raise an exception in the timed-out resource request via
        base class implementation (which also cancels events rendered moot
        by the timeout/interrupt), and  then asks the assignment agent
        to handle the timeout by remove the request and scheduling another
        round of resource assignments
        """
        handled = self.assignmentAgent._process_queued_requests(self.requestMsg)
        if not handled:
            super().process_impl()
            self.assignmentAgent.request_timed_out(self.requestMsg)

        
@apidoc
class SimProcess(SimTransaction):
    """
    SimProcess is a subclass of SimTransaction, where entities are the agents.
    As such it is the base class for all simulation processes.
    """
    __slots__ = ('__executing', '__entity', '__element',
                 '__resource_assignments')
    
    elements = {}
    
    def __init_subclass__(cls, **kwargs):      
        """
        Register all subclasses of SimProcess by wrapping them in a
        SimProcessElement and adding it to the SimProcess.elements list.
        
        Pretty much straight from the PEP 487 document
        https://peps.python.org/pep-0487/#subclass-registration.
        
        Note models should only use SimProcess subclasses, so no need
        to add SimProcess itself to this list.
        """
        super().__init_subclass__(**kwargs)
        
        # Add a process element to the SimProcess elements dictionary
        pe = SimProcessElement(cls) 
        if pe.element_id in cls.elements:
            msg = "SimProcess class with element ID {0} is already registered"
            raise SimError(_ERROR_NAME, msg, pe.element_id)
              
        logger.info("Creating and registering a process element for %s", pe.element_id)
        cls.elements[pe.element_id] = pe

    @classmethod
    def final_initialize(cls):
        """
        final_initialize() is used to do any :class:`SimProcess`-derived
        class (not instance) member initialization that can't be done when the 
        class's module is imported. This method will be called for each
        SimProcess-derived class IF AND ONLY IF the method is defined
        for that derived class; it will be called at the same time that
        final_initialize() is called on all :class:`SimStaticObject`
        objects in the model - after all simulation elements are created,
        after the simulation clock, random number streams and event processor
        are created/initialized, but before the simulation execution actually
        starts.
        
        While a no-op final_initialize() is defined for :class:`SimProcess`,
        It is not necessary to do so for subclasses that need no final
        initialization processing. If the method is not defined on a subclass,
        final_initialize() will not be called. (The calling code makes sure
        not to call any implementation inherited from a base class)
        
        Client code should not call this method.
        """
        pass

    def __init__(self):
        """
        Initialize the process with a null agent. The entity itself will set
        itself as the process's agent when the entity is instantiated.
        """
        super().__init__(None)
        self.__executing = False
        self.__entity = None
        self.__element = self.__class__.element
        assert self.__element, "No element exists for process class"
        self.__resource_assignments = []

    @property
    def element(self):
        """
        Returns the SimProcessElement associated with this process's class.

        :return: The SimProcessElement associated with this entity's class.
        :rtype:  :class:`SimProcessElement`
        
        """
        return self.__element

    @property
    def entity(self):
        """
        The SimEntity (agent) being processed by this SimProcess instance

        :return: The entity object associated with this process
        :rtype:  :class:`~.entity.SimEntity`
        
        """
        return self.agent

    @entity.setter
    def entity(self, value):
        assert isinstance(value, SimEntity), "Attempt to set SimProcess.entity to an object of type " + str(type(value))
        self._agent = value
        
    @apidocskip
    def execute(self):
        """
        Execute the process (synchronously). Should not be called by client code.

        Invoke the base class execute(), (which in turn invokes run()); when
        complete, make sure there are no resource assignments that have not
        been released. (Process execution should not end with unreleased
        resources.)
        """
        super().execute()
        hasUnreleasedAssignments = any([True for assg in self.__resource_assignments if assg.count > 0])
        if hasUnreleasedAssignments:
            unreleasedAssignments = [assg for assg in self.__resource_assignments if assg.count > 0]
            msg = "Transaction {0} run() error.  All resources must be released prior to the end of process execution (run()).  The following resource assignments have not been released: {1}"
            raise SimError(_ERROR_NAME, msg, self, unreleasedAssignments)
        
        
    def acquire(self, resource, numrequested=1, *, timeout=None):
        """
        Acquires a specified resource (or resources) on behalf of this
        transaction, blocking until either the resource(s) are acquired,
        or the request times out.
        
        If the resource(s) are acquired, a resource assignment is returned.
        If `acquire` times out, a :class:`~.simexception.SimTimeOutException`
        is raised. If the timeout parameter value is `None`, `acquire` will
        not time out. If the timeout is zero, the request times out if the
        requested resource(s) are not immediately available and assigned.
        
        Note that default behavior typically guarantees that all of
        the requested resources will be acquired; client code can
        customize this behavior, possibly providing some but not all
        of the requested resource if the number requested is > 1.

        :param resource:     The resource object to be acquired
        :type resource:      :class:`~.resource.SimResource`

        :param numrequested: The number of resources (subresources) to acquire,
                             Can be more than 1 if resource has capacity greater
                             than 1. Defaults to 1
        :type numrequested:   `int`

        :param timeout:      If not None, the length of simulated time
                             after which the request times out. If None,
                             the request never times out (unless interrupted by
                             the assignment agent) Defaults to `None`.
        :type timeout:       :class:`~.simtime.SimTime` or `None`.
        
        :raises:             :class:`~.simexception.SimTimeOutException`
                             Raised if acquire() request time out.
        
        :return:             Assignment object that specifies assigned resource(s)
        :rtype:              :class:`~.resource.SimResourceAssignment`
        
        """
        assert resource.assignment_agent, "Resource has no assignment agent!"

        if numrequested <= 0 or int(numrequested) != numrequested:
            errorMsg = "Resource acquire() number requested ({0}) must be an integer greater than zero"
            raise SimError(_ACQUIRE_ERROR, errorMsg, numrequested)

        # Send a resource request message to the desired resource's assignment
        # agent (which may or may not be the resource itself)
        assignmentAgent = resource.assignment_agent
        msgData = (self, numrequested, resource)
        return self._acquire_impl(assignmentAgent, msgData, timeout)

    def acquire_from(self, agent, rsrcClass, numrequested=1, *, timeout=None):
        """
        Acquire a resource (or resources) of a specified class that is
        managed by a specified assignment agent, returning a resource
        assignment. Blocks until the resource(s) are assigned. Typically
        used when acquiring resource(s) managed by a
        :class:`.resource.SimResourcePool`.
        
        As with :meth:`~SimTransaction.acquire`, the request can time out
        if a `timeout` parameter value other than `None` is supplied. If
        the request times out, a :class:`~.simexception.SimTimeOutException`
        is raised. If the timeout is zero, the request times out if the
        requested resource(s) are not immediately available and assigned.
        
        Note that default behavior typically guarantees that all of
        the requested resources will be acquired; client code can
        customize this behavior, possibly providing some but not all
        of the requested resource if the number requested is > 1.

        :param agent:        The assignment agent managing the desired
                             resource(s)
        :type agent:         :class:`~.resource.SimResourceAssignmentAgent`

        :param rsrcClass:    The (Python) class of resource object to be
                             acquired. May be a base class, if a heterogenous
                             set of resources can meet the request.
        :type rsrcClass:     `class` derived from :class:`~.resource.SimResource`

        :param numrequested: The number of resources or subresources to acquire.
                             Can be more than 1 if the agent manages multiple
                             resources (or a resource with capacity > 1).
                             Defaults to 1
        :type numrequested:   `int`

        :param timeout:      If not None, the length of simulated time
                             after which the request times out. If None,
                             the request never times out (unless interrupted by
                             the assignment agent) Defaults to `None`.
        :type timeout:       :class:`~.simtime.SimTime` or `None`.
        
        :raises:             :class:`~.simexception.SimTimeOutException`
                             Raised if acquire() request time out.
        
        :return:             Assignment object that specifies assigned resource(s)
        :rtype:              :class:`~.resource.SimResourceAssignment`
        
        """
        assert isinstance(rsrcClass, type), "acquireFrom() rsrcClass parameter is not a class"
        assert agent, "Null agent passed to acquireFrom()"

        if numrequested <= 0 or int(numrequested) != numrequested:
            errorMsg = "Resource acquire() number requested ({0}) must be an integer greater than zero"
            raise SimError(_ACQUIRE_ERROR, errorMsg, numrequested)

        msgData = (self, numrequested, rsrcClass)
        return self._acquire_impl(agent, msgData, timeout)

    def _acquire_impl(self, assignmentAgent, msgData, timeout):
        """
        Implements the bulk of the resource acquisition that is common to both
        acquire() and acquire_from()
        """
        assert self.agent, "Process calling acquire() has no agent"
        assert self.is_executing, "Resources can only be acquired by executing processes"
        
        if timeout is not None:
            if not isinstance(timeout, SimTime):
                # let this raise if timeout cannot be converted to a SimTime
                timeout = SimTime(timeout)
            if timeout < 0:
                msg = "Process {0} invoked a resource acquire with timeout < 0: {1}"
                raise SimError(_ERROR_NAME, msg, self, timeout)
         

        msgType = SimMsgType.RSRC_REQUEST
        msg, responses = self.agent.send_message(assignmentAgent,
                                                msgType, msgData)
        if responses:
            # If the assignment agent responded immediately, grab that response
            # (which should just be a resource assignment message)
            assert len(responses) == 1, "Resource Request message expects zero or one responses"
            response = responses[0]
            assert response.msgType == SimMsgType.RSRC_ASSIGNMENT, "Response to Resource request was not a resource assignment"
        else:
            # If the assignment agent did not respond immediately (presumably
            # because the requested resource is not available), wait for a
            # response. Schedule a timeout that will be executed if the resource
            # request is not fulfilled first.
            if timeout is not None:
                timeoutEvent = SimTimeOutEvent(self, assignmentAgent, msg, timeout)
                timeoutEvent.register()
            response = self.wait_for_response(msg)
            assert response, "No response from waitForRespoonse"
            assert response.msgType == SimMsgType.RSRC_ASSIGNMENT, "Response to Resource request was not a resource assignment"

        # Extract the assignment from the response message and register it
        assignment = response.msgData
        assert assignment.transaction is self, "Resource assignment does not specify this transaction"
        self.__resource_assignments.append(assignment)

        # Finally, return the assignment
        return assignment

    def release(self, rsrcAssignment, releaseSpec=None):
        """
        Release some or all of the resources in the passed assignment (the
        assignment should be to this transaction). If a subset of the
        assignment's resources are to be released, it/they may be specified
        in one of three ways:

            1. As an iterable to the resource objects to be released
            2. As a single resource object
            3. As a number n, specifying the release of the first n resources in
               the passed assignment.

        The default release spec value of None indicates that all resources
        in the assignment are to be released.
        
        The release is actually accomplished by sending a RSRC_RELEASE message
        to the resource asssignment agent, which also subtracts the released
        resources from the resource assignment object.

        :param rsrcAssignment: The resource assignment that is to be fully or
                               partially released.
        :type rsrcAssignment:  :class:`~.resource.SimResourceAssignment`

        :param releaseSpec:    Specification of resources within the assignment
                               to release (as described above) or None, to
                               release all resources in rsrcAssignment.
        :type releaseSpec:     See above.
 
        """
        assert self.agent, "Transaction calling release() has no agent"
        assert self.is_executing, "Resources can only be released by executing transactions"
        assert rsrcAssignment, "Null assignment passed to release()"
        assert rsrcAssignment.assignment_agent, "Resource assignment has no agent"
        assert rsrcAssignment.transaction == self, "Resource assignment transaction is not this transaction"

        assignmentAgent = rsrcAssignment.assignment_agent
        msgType = SimMsgType.RSRC_RELEASE
        msgData = (rsrcAssignment, releaseSpec)
        self.agent.send_message(assignmentAgent, msgType, msgData)
        if rsrcAssignment.count == 0:
            self.__resource_assignments.remove(rsrcAssignment)

    def resource_assignments(self):
        """
        Returns a list of current resource assignments
        (:class:`~.resource.SimResourceAssignment`) for the transaction;
        any assignment with a resource count of zero is ignored
        (i.e., is not included in the returned list).
        """
        return [assg for assg in self.__resource_assignments if assg.count > 0]
        
    def __str__(self):
        return self.__class__.__name__
    
class SimProcessElement(SimClassElement):
    """
    SimProcessElement instances represent an entire process class as an
    element for data collection purposes, since process data are aggregated
    by class, rather than individual executing process instances. To put in
    another way, we create one SimProcessElement instance for each
    :class:`SimProcess`-derived class in the model for which we want to
    collect data. Modeling code should specify the SimProcess-derived
    classes to create elements for by wrapping them via the
    :func:`simelement` decorator.
    
    Analagous to :class:`SimEntityElement`.
       
    :param processclass: The :class:`SimProcess` subclass for which this
                         :class:`SimElement` is a proxy.
    :type processclass:  Class (NOT an instance of the class)
    
    """
    
    __slots__ = ('counter', 'timeDataCollector')
    
    def __init__(self, processclass):
        """
        Create and initialize a SimProcessElement with a passed SimProcess.
        There should be one SimProcessElement for every process
        (SimProcess-derived) class in the simulation model. Also creates
        a :class:`SimCounter` for in-process :class: entities <SimEntity>
        and an :class: `unweighted data collector <SimUnweightedDataCollector>`
        for process times; both of these objects create and register
        :class:`datasets <Dataset>` with the SimProcessElement.
        """
        assert issubclass(processclass, SimProcess)
        super().__init__(processclass)
        self.counter = SimCounter(self, "In-Process")
        self.entryCounter = SimCounter(self, "Entries")
        self.timeDataCollector = SimUnweightedDataCollector(self, "Process-Time", SimTime)

    
if __name__ == '__main__':
    
    
    class MockProcess1(SimProcess):
        """
        """
        
    class MockProcess2(SimProcess):
        """
        """
        
    class MockProcess11(MockProcess1):
        """
        """
  
    for e in SimProcess.elements.values():
        print(e.element_id)

