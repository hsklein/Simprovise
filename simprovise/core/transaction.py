#===============================================================================
# MODULE transaction
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimTransaction and related event classes. SimTransaction is the
# base class representing actions (or a sequence of actions) that are initiated
# by or on behalf of SimAgents and take place over simulated time.
#
# The two subclasses of SimTransaction are SimProcess (for entities) and SimTask
# (for resources).  FWIW the term "transaction" is adopted from the GPSS
# terminology (where a transaction is really a process, as it applies to
# entities).
#===============================================================================
from greenlet import greenlet           # pylint: disable=E0611

from simprovise.core import (SimClock, SimError, simevent,
                            SimInterruptException)

from simprovise.core.simevent import SimEvent
from simprovise.core.agent import SimMsgType
from simprovise.core.counter import SimNullCounter
from simprovise.core.datacollector import NullDataCollector
from simprovise.core.apidoc import apidoc, apidocskip
from simprovise.core import SimLogging
logger = SimLogging.get_logger(__name__)

_ACQUIRE_ERROR = "Resource Acquisition Error"

class SimTransactionStartEvent(SimEvent):
    """
    Start a transaction by switching to it's greenlet (which should be setup to
    run the transaction's execute() method)
    """
    __slots__ = ('transaction', '_greenlet')
    def __init__(self, transaction, gr):
        super().__init__(SimClock.now())
        self.transaction = transaction
        self._greenlet = gr

    def process_impl(self):
        self._greenlet.switch()

    def __str__(self): return super().__str__() + " Transaction: " + str(self.transaction) + " Greenlet: " + str(self._greenlet)

class SimTransactionResumeEvent(SimEvent):
    """
    Wake up the transaction and resume now.  If through some sort or race
    condition, an interrupt has also been scheduled, cancel the interrupt
    by deregistering the interrupt event.  (In other words, if an interrupt
    and "regular" resume are somehow scheduled for the same simulated time,
    the "regular" resume should take precedence.)
    """
    __slots__ = ('transaction')
    def __init__(self, transaction, wait=0):
        super().__init__(SimClock.now() + wait)
        self.transaction = transaction
        transaction.resumeEvent = self

    def process_impl(self):
        self.transaction.resumeEvent = None
        interruptEvent = self.transaction.interruptEvent
        if interruptEvent and interruptEvent.isRegistered():
            logger.debug("cancelling interrupt in favor of concurrently scheduled resume event")
            interruptEvent.deregister()
        self.transaction.wakeup()

    def __str__(self):
        return super().__str__() + " Transaction: " + str(self.transaction)

# TODO consider a SimTransactionWaitUntilEvent, which could be passed either a lambda or a function to evaluate (the "until" condition)
# Alternatively, we could use a transaction scheduler of some sort, which would own the list of "waitingUntil" transactiones, checking them as required


class SimTransactionInterruptEvent(SimEvent):
    """
    Interrupt the waiting transaction by waking it and raising a
    SimInterruptException (with the supplied reason).

    If a concurrent "regular" resume has also been scheduled (i.e. for the
    same simulated time), that resume takes precedence and should be allowed
    to proceed by ignoring the interrupt.
    """
    __slots__ = ('transaction', 'reason')
    def __init__(self, transaction, reason=None):
        super().__init__(SimClock.now())
        self.transaction = transaction
        self.reason = reason
        transaction.interruptEvent = self

    def process_impl(self):
        self.transaction.interruptEvent = None
        resumeEvent = self.transaction.resumeEvent
        if resumeEvent and resumeEvent.time == self.time:
            logger.debug("Ignoring interrupt in favor of concurrently scheduled resume event")
        else:
            if resumeEvent:
                resumeEvent.deregister()
                self.transaction.resumeEvent = None
            self.transaction.wakeup_and_interrupt(self.reason)

    def __str__(self):
        return super().__str__() + \
            " Transaction: {0}, reason: {1}".format(self.transaction, self.reason)


@apidoc
class SimTransaction(object):
    """
    SimTransaction is the base class representing actions (or a sequence of
    actions) that are initiated by or on behalf of SimAgents and take place
    over simulated time.

    The two subclasses of SimTransaction are SimProcess (for entities) and SimTask
    (for resources).  FWIW the term "transaction" is adopted from the GPSS
    terminology (where a transaction is really a process, as it applies to
    entities), in the search for a base class name that is different from both
    "process" and "task".

    Note:
        SimTask is a concept for a future release that has not yet been
        implemented.
    """
    __slots__ = ('_greenlet', '_executing', '_agent', 'resumeEvent',
                 'interruptEvent', '_resourceAssignments')

    def __init__(self, agent):
        self._greenlet = None
        self._executing = False
        self._agent = agent
        self._resourceAssignments = []
        self.resumeEvent = None
        self.interruptEvent = None

    @property
    @apidocskip
    def agent(self):
        """
        Returns the agent - a SimEntity or SimResource - which is executing this
        process or task.
        """
        return self._agent

    @property
    def is_executing(self):
        """
        Returns True if the transaction (process or task) is currently
        executing, False otherwise.
        """
        return self._executing

    def __str__(self):
        return self.__class__.__name__

    def run(self):
        """
        run() is the code that actually specifies process/task execution.
        It is implemented by concrete subclasses, typically as created by
        the user/modeler.
        """
        pass

    @property
    @apidocskip
    def element_counter(self):
        """
        If the transaction class is a simulation element - i.e., the class has
        an element attribute - return that element's counter attribute.
        Otherwise, return a null counter.
        """
        if hasattr(self.__class__, 'element'):
            # pylint: disable=E1101
            return self.__class__.element.counter
        else:
            return SimNullCounter()

    @property
    @apidocskip
    def element_entry_counter(self):
        """
        If the transaction class is a simulation element - i.e., the class has
        an element attribute - return that element's counter attribute.
        Otherwise, return a null counter.
        """
        if hasattr(self.__class__, 'element'):
            # pylint: disable=E1101
            return self.__class__.element.entryCounter
        else:
            return SimNullCounter()

    @property
    @apidocskip
    def element_data_collector(self):
        """
        If the transaction class is a simulation element - i.e., the class has
        an element attribute - return that element's time data collector.
        Otherwise, return a null data collector.
        """
        if hasattr(self.__class__, 'element'):
            # pylint: disable=E1101
            return self.__class__.element.timeDataCollector
        else:
            return NullDataCollector()

    @apidocskip
    def execute(self):
        """
        Execute the task or process transaction (synchronously).

        Currently not called by client code, though if, for example, a process were
        to be broken down into subprocesses, the subprocesses might be executed
        within run() via execute.
        """
        #since transactions may synchronously execute subtransactiones via execute(),
        # we'll assign the greenlet attributes here.  That way, subtransactions
        # inherit the greenlet of the parent (calling) transaction
        self._greenlet = greenlet.getcurrent()

        # Transactions should have an agent assignment at or immediately after
        # construction.  Definitely before executing!
        assert self.agent, "Attempt to execute a transaction not associated with an agent"

        # As of now, at least, transaction instances are NOT re-entrant
        # The general intent is for a transaction object to execute once over the course of it's lifetime
        # At a minimum, we'll ensure that execute() is not called on an instance that is already executing
        assert not self.is_executing, "Attempt to re-execute an already-executing transaction"
        self._executing = True

        inTransactionCounter = self.element_counter
        entryCounter = self.element_entry_counter
        timeDataCollector = self.element_data_collector

        self.increment(inTransactionCounter)
        self.increment(entryCounter)
        try:
            startTime = SimClock.now()
            self.run()
            runTime = SimClock.now() - startTime
            timeDataCollector.add_value(runTime)

            # check for resource assignments that have not been released
            # (Transaction execution cannot end with unreleased resources)
            # TODO should we be cleaning out assignments with zero resource count
            # (all resources released) as we go?
            hasUnreleasedAssignments = any([True for assg in self._resourceAssignments if assg.count > 0])
            if hasUnreleasedAssignments:
                unreleasedAssignments = [assg for assg in self._resourceAssignments if assg.count > 0]
                errstr = "Transaction {0} run() error.  All resources must be released prior to the end of transaction execution (run()).  The following resource assignments have not been released: {1}"
                raise SimError("Transaction Execution Error", errstr.format(str(self), str(unreleasedAssignments)))
        finally:
            self._executing = False
            self.decrement(inTransactionCounter)

    @apidocskip
    def start(self):
        """
        Initiate asynchronous execution of the task or process transaction.
        """
        # Create a greenlet for this transaction, and start running by scheduling a start event
        gr = greenlet(self.execute, simevent.event_processing_greenlet)
        startEvent = SimTransactionStartEvent(self, gr)
        startEvent.register()

    @apidocskip
    def wakeup(self):
        """
        Restart a waiting transaction. Should be called only by
        SimTransactionResumeEvent. Other code should call resume()
        """
        logger.debug("Waking up transaction %s on greenlet %s", self, self._greenlet)
        self._greenlet.switch()

    @apidocskip
    def wakeup_and_interrupt(self, reason):
        """
        Interrupt a waiting transaction - i.e., wake it prematurely by
        restarting it and throwing a SimInterruptException with the passed
        reason.

        Should be called only by a SimTransactionInterruptEvent. Other code
        should call interrupt()
        """
        logger.debug("wakeupAndInterrupt on transaction %s on greenlet %s", self, self._greenlet)
        self._greenlet.throw(SimInterruptException(reason))

    @apidocskip
    def wait_until_notified(self):
        """
        Wait indefinitely, until woken up via a Resume event.
        Generally not to be invoked directly by client modeling code.
        """
        logger.debug("waitUntilNotified on transaction %s on greenlet %s", self, self._greenlet)
        simevent.event_processing_greenlet.switch()

    @apidocskip
    def resume(self):
        """
        Resume transaction by scheduling a continue/resume event. This is the
        method that should be called by to restart a waiting transaction -
        NOT wakeup()
        """
        resumeEvent = SimTransactionResumeEvent(self)
        resumeEvent.register()

    def interrupt(self, reason):
        """
        Interrupt a transaction that is currently waiting - i.e., interrupt
        the wait state and prematurely, resume the transaction, but raise a
        SimInterruptException with the passed reason for the interrupt. Most
        interrupts are implementing resource preemption (quit the job in the
        middle and assign the resource elsewhere); it might also be used to
        implement "go to Plan B" if the wait for resource acquisition takes too
        long.

        This is the method that should be called by to restart a waiting
        transaction - NOT wakeupAndInterrupt()

        Note that the transaction initiating the interrupt (which is NOT
        this transaction) does __not__ block until the interrupt occurs.
        We might consider a method that facilitates that, though the semantics
        could be confusing.

        Args:
            reason (str): Reason for interrupt, e.g. 'preemption'
        """
        assert self.is_executing, "Cannot interrupt a non-executing transaction"
        assert self._greenlet != greenlet.getcurrent(), "Transaction interrupted from itself (or its own greenlet)"

        # Now schedule the interrupt event
        logger.debug("scheduling interrupt on transaction %s on greenlet %s", self, self._greenlet)
        interruptEvent = SimTransactionInterruptEvent(self, reason)
        interruptEvent.register()

    # methods used by run()

    def wait_for_response(self, msg):
        """
        Blocks until a response (to the passed message) is  received, returning
        that response message.  The agent will continue to handle other messages
        until that response is received - only this transaction blocks.

        Resource acquisition APIs are implemented using waitForResponse(); end
        user modeling code most likely should not be calling this method
        directly unless the model requires customized inter-agent communication.

        Args:
            msg (SimMessage): Message that has been sent, and for which the
                              process is awaiting a response.

        Returns:
            SimMessage:       The response to msg
        """
        # TODO handle an interrupt
        assert msg.sender == self.agent, "can't wait on message sent by a different agent"

        response = None
        try:
            def resumeOnResponse(message):
                if message.originatingMsg == msg:
                    nonlocal response
                    response = message
                    self.agent.interceptHandler = savedInterceptHandler
                    self.resume()
                    return True
                else:
                    return False

            savedInterceptHandler = self.agent.interceptHandler
            self.agent.interceptHandler = resumeOnResponse
            self.wait_until_notified()
        finally:
            self.agent.interceptHandler = savedInterceptHandler

        assert response, "Null response returned from waitForResponse()" + str(self._greenlet)
        return response

    def wait_for(self, amount):
        """
        Wait (pause transaction execution) for a fixed amount of simulated time.

        Args:
            amount (SimTime): Length of wait. Though not recommended, amount
                              can also be specified as a positive integer, in
                              which case the wait length will be the amount in
                              SimClock's default time unit (currently seconds).
        """
        # TODO add optional time unit parameter, to be used if amount is not
        # a SimTime instance and to make the wait length more explicit.
        resumeAtEvent = SimTransactionResumeEvent(self, amount)
        resumeAtEvent.register()
        simevent.event_processing_greenlet.switch()

    def increment(self, counter, amount=1):
        """
        Increment a counter by the designated amount. if the counter's capacity
        is not infinite, this may block.

        Args:
            counter (SimCounter):  Counter to be incremented
            amount (positive int): Amount to increment counter by. Should be
                                   less than or equal to the counter's capacity
        """
        #TODO validate counter, amount
        counter.increment(self, amount)

    def decrement(self, counter, amount=1):
        """
        Decrement a counter by the designated amount. Never blocks.

        Args:
            counter (SimCounter):  Counter to be decremented
            amount (positive int): Amount to decrement counter by. Should be
                                   less than or equal to the counter's current
                                   value
        """
        #TODO validate counter, amount
        counter.decrement(amount)

    def acquire(self, resource, numrequested=1):
        """
        Acquires a specified resource on behalf of this transaction, blocking
        until the resource is acquired, and returning a SimResourceAssignment

        Args:
            resource (SimResource): Resource requested / to be acquired
            numrequested (int):     Number of resources (subresources) to
                                    acquire. Can be more than 1 if resource
                                    has capacity greater than 1.

        Returns:
            SimResourceAssignment: Assignment object that specifies assigned
                                   resource(s)
        """
        assert resource.assignment_agent, "Resource has no assignment agent!"

        if numrequested <= 0 or int(numrequested) != numrequested:
            errorMsg = "Resource acquire() number requested ({0}) must be an integer greater than zero"
            raise SimError(_ACQUIRE_ERROR, errorMsg, numrequested)

        # Send a resource request message to the desired resource's assignment
        # agent (which may or may not be the resource itself)
        assignmentAgent = resource.assignment_agent
        msgData = (self, numrequested, resource)
        return self._acquire_impl(assignmentAgent, msgData)

    def acquire_from(self, agent, rsrcClass, numrequested=1):
        """
        Acquire a resource (or resources) of a specified class that is
        managed by a specified assignment agent, returning a
        SimResourceAssignment. Blocks until the resource(s) are assigned.

        Args:
            agent (SimAgent):   The agent managing the resource(s) requested
            rsrcClass (class):  The (Python) class of the resource(s) requested
            numrequested (int): Number of resources being requested. Can be
                                more than 1 if the agent manages multiple
                                resources (or a resource with capacity > 1)

        Returns:
            SimResourceAssignment: Assignment object that specifies assigned
                                   resource(s)
        """
        assert isinstance(rsrcClass, type), "acquireFrom() rsrcClass parameter is not a class"
        assert agent, "Null agent passed to acquireFrom()"

        if numrequested <= 0 or int(numrequested) != numrequested:
            errorMsg = "Resource acquire() number requested ({0}) must be an integer greater than zero"
            raise SimError(_ACQUIRE_ERROR, errorMsg, numrequested)

        msgData = (self, numrequested, rsrcClass)
        return self._acquire_impl(agent, msgData)

    def _acquire_impl(self, assignmentAgent, msgData):
        """
        Implements the bulk of the resource acquisition that is common to both
        acquire() and acquire_from()
        """
        assert self.agent, "Transaction calling acquire() has no agent"
        assert self.is_executing, "Resources can only be acquired by executing transactions"

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
            # response.
            response = self.wait_for_response(msg)
            assert response, "No response from waitForRespoonse"
            assert response.msgType == SimMsgType.RSRC_ASSIGNMENT, "Response to Resource request was not a resource assignment"

        # Extract the assignment from the response message and register it
        assignment = response.msgData
        assert assignment.transaction is self, "Resource assignment does not specify this transaction"
        self._resourceAssignments.append(assignment)

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

        Args:
            rsrcAssignment (SimResourceAssignment): the assignment object
                            including the resources to be released
            releaseSpec:   Specification of resources within the assignment
                           to release (as described above) or None, to release
                           all resources in rsrcAssignment.
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
            self._resourceAssignments.remove(rsrcAssignment)


    # TODO unregisterResourceAssignment()  Confirms that assignment
    # has a resource count of zero, and removes it from __resourceAssignments
    # To be called by the resource/resource assignment release.

    @property
    def resourceAssignments(self):
        """
        Returns a list of current resource assignments for the transaction;
        any assignment with a resource count of zero is ignored (i.e., not part
        of the returned list).
        """
        return [assg for assg in self._resourceAssignments if assg.count > 0]




