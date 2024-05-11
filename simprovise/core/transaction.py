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

from simprovise.core import (SimClock, SimError, SimTime, simevent,
                             SimInterruptException, SimTimeOutException)

from simprovise.core.simevent import SimEvent
from simprovise.core.agent import SimMsgType
from simprovise.core.counter import SimNullCounter
from simprovise.core.datacollector import NullDataCollector
from simprovise.core.apidoc import apidoc, apidocskip
from simprovise.core import SimLogging
logger = SimLogging.get_logger(__name__)

_ACQUIRE_ERROR = "Resource Acquisition Error"
_TXN_ERROR = "SimTransaction Error"

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
    Wake up the transaction and resume now.  If an interrupt has also been
    scheduled, cancel the interrupt by deregistering the interrupt event.
    In other words, if an there is both an interrupt and resume event
    scheduled for this transaction, the resume takes precedence unless
    the interrupt is scheduled for an earlier simulated time. The resume
    event is set to a higher priority to ensure that it executes first
    if the resume and interrupt are scheduled for the same simulated time.
    """
    __slots__ = ('transaction')
    def __init__(self, transaction, wait=0):
        super().__init__(SimClock.now() + wait, priority=1)
        self.transaction = transaction
        transaction.resumeEvent = self

    def process_impl(self):
        self.transaction.resumeEvent = None
        interruptEvent = self.transaction.interruptEvent
        if interruptEvent and interruptEvent.is_registered():
            logger.debug("cancelling interrupt in favor of concurrently scheduled resume event")
            interruptEvent.deregister()
        self.transaction._wakeup()

    def __str__(self):
        return super().__str__() + " Transaction: " + str(self.transaction)

# TODO consider a SimTransactionWaitUntilEvent, which could be passed either a lambda or a function to evaluate (the "until" condition)
# Alternatively, we could use a transaction scheduler of some sort, which would own the list of "waitingUntil" transactiones, checking them as required


class SimTransactionInterruptEvent(SimEvent):
    """
    Interrupt the waiting transaction by waking it and raising a supplied
    exception (expected to be derived from SimInterruptException)
    
    The priority of the Interrupt event is set to 3, so that any resume
    event (priority 1) for this transaction scheduled for the same time is
    executed before (and instead of) the interrupt.

    If a concurrent "regular" resume has also been scheduled (i.e. for the
    same simulated time), that resume takes precedence and should be allowed
    to proceed by ignoring the interrupt.
    """
    __slots__ = ('transaction', 'exception')
    def __init__(self, transaction, exception, wait=0):
        super().__init__(SimClock.now() + wait, priority=3)
        self.transaction = transaction
        self.exception = exception
        transaction.interruptEvent = self

    def process_impl(self):
        self.transaction.interruptEvent = None
        resumeEvent = self.transaction.resumeEvent
        if resumeEvent and resumeEvent.is_registered():
            assert resumeEvent.time != self.time, "Concurrent resume event not executed before interrupt event"
            resumeEvent.deregister()
            self.transaction.resumeEvent = None
        self.transaction._wakeup_and_interrupt(self.exception)

    def __str__(self):
        return super().__str__() + \
            " Transaction: {0}, reason: {1}".format(self.transaction, self.exception)


@apidoc
class SimTransaction(object):
    """
    SimTransaction is the base class representing actions (or a sequence of
    actions) that are initiated by or on behalf of :class:`~.agent.SimAgent`
    objects and take place over simulated time.
    
    At present, the only subclass of SimTransaction is
    :class:`~.process.SimProcess`; SimProcesses are executed for
    :class:`~.entity.SimEntity` objects. (A SimTask class may be implemented
    in the future to work with resources more directly; at that point, this
    class may require refactoring)

    FWIW the term "transaction" is adopted from the GPSS terminology (where a
    transaction is really a process, as it applies to entities), in the search
    for a base class name that is different from both "process" and "task".
    """
    __slots__ = ('_greenlet', '_executing', '_agent', 'resumeEvent',
                 'interruptEvent')

    def __init__(self, agent):
        self._greenlet = None
        self._executing = False
        self._agent = agent
        self.resumeEvent = None
        self.interruptEvent = None

    @property
    @apidocskip
    def agent(self):
        """
        
        :return: The agent which is executing this transaction (process).
        :rtype:  :class:`~.entity.SimEntity`
        
        """
        return self._agent

    @property
    def is_executing(self):
        """
        
        :return: True if the transaction (process or task) is currently
                 executing, False otherwise.
        :rtype:  bool
        
        """
        return self._executing

    def __str__(self):
        return self.__class__.__name__

    def run(self):
        """
        run() is the code that actually specifies transaction/process
        execution. It is implemented by concrete subclasses, typically as
        created by the user/modeler.
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
        #since transactions may synchronously execute subtransactions via execute(),
        # we'll assign the greenlet attributes here.  That way, subtransactions
        # inherit the greenlet of the parent (calling) transaction
        self._greenlet = greenlet.getcurrent()

        # Transactions should have an agent assignment at or immediately after
        # construction.  Definitely before executing!
        assert self.agent, "Attempt to execute a transaction not associated with an agent"

        # As of now, at least, transaction instances are NOT re-entrant
        # The general intent is for a transaction object to execute once over 
        # the course of it's lifetime. At a minimum, we'll ensure that execute() 
        # is not called on an instance that is already executing
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
        finally:
            self._executing = False
            self.decrement(inTransactionCounter)

    @apidocskip
    def start(self):
        """
        Initiate asynchronous execution of the task or process transaction.
        """
        # Create a greenlet for this transaction, and start running by 
        # scheduling a start event
        gr = greenlet(self.execute, simevent.event_processing_greenlet)
        startEvent = SimTransactionStartEvent(self, gr)
        startEvent.register()

    @apidocskip
    def _wakeup(self):
        """
        Restart a waiting transaction. Should be called only by
        SimTransactionResumeEvent. Other code should call resume()
        """
        logger.debug("Waking up transaction %s on greenlet %s", self, self._greenlet)
        self._greenlet.switch()

    @apidocskip
    def _wakeup_and_interrupt(self, exception):
        """
        Interrupt a waiting transaction - i.e., wake it prematurely by
        restarting it and throwing a SimInterruptException with the passed
        reason.

        Should be called only by a SimTransactionInterruptEvent. Other code
        should call interrupt()
        """
        logger.debug("wakeupAndInterrupt on transaction %s on greenlet %s", self, self._greenlet)
        self._greenlet.throw(exception)

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
        NOT _wakeup()
        """
        resumeEvent = SimTransactionResumeEvent(self)
        resumeEvent.register()

    def interrupt(self, exception):
        """
        Interrupt a transaction that is currently waiting - i.e., interrupt
        the wait state and prematurely, resume the transaction, but raise a
        SimInterruptException with the passed reason for the interrupt. Most
        interrupts are implementing resource preemption (quit the job in the
        middle and assign the resource elsewhere); it might also be used to
        implement "go to Plan B" if the wait for resource acquisition takes too
        long. (Though that would typically be done via the timeout parameter
        on :meth:`SimTransaction.acquire` or :meth:`SimTransaction.acquire_from`)

        This is the method that should be called by to restart a waiting
        transaction - NOT _wakeup_and_interrupt()

        Note that the initiator of the interrupt (which is NOT
        this transaction) does __not__ block until the interrupt occurs.
        We might consider a method that facilitates that, though the semantics
        could be confusing.

        :param exception: Exception object that is raised when the waiting
                          transaction is resumed.
        :type exception:  `Exception`
        
        """
        assert self.is_executing, "Cannot interrupt a non-executing transaction"
        assert self._greenlet != greenlet.getcurrent(), "Transaction interrupted from itself (or its own greenlet)"

        # Now schedule the interrupt event
        logger.debug("scheduling interrupt on transaction %s on greenlet %s", self, self._greenlet)
        interruptEvent = SimTransactionInterruptEvent(self, exception)
        interruptEvent.register()

    # methods used by run()

    def wait_for_response(self, msg):
        """
        Blocks until a response (to the passed message) is  received, returning
        that response message.  The agent will continue to handle other messages
        until that response is received - only this transaction blocks.

        Resource acquisition APIs are implemented using wait_for_response(); end
        user modeling code most likely should not be calling this method
        directly unless the model requires customized inter-agent communication.
        
        :param msg: Message that has been sent by this transaction/process, and
                    for which the transaction/process is awaiting a response.
        :type msg:  :class:`~.agent.SimMessage`
        
        :return:    The response to the passed :class:`~.agent.SimMessage`
        :rtype:     :class:`~.agent.SimMessage`

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
        
        :param amount: Length of wait. Can be specified as a
                       :class:`~.simtime.SimTime` or a scalar numeric (int or
                       float). Must be non-negative. If a scalar value, the wait
                       length will be the amount in the :class:`~.simclock.SimClock`
                       default time unit (as defined by :func:`simtime.base_unit`.
                       Scalar values are not recommended unless the base unit
                       is dimensionless (None)
        :type amount:  :class:`~.simtime.SimTime`, `int` or `float`
        
        """
        resumeAtEvent = SimTransactionResumeEvent(self, amount)
        resumeAtEvent.register()
        simevent.event_processing_greenlet.switch()

    def increment(self, counter, amount=1):
        """
        Increment a counter by the designated amount. if the counter's capacity
        is not infinite, this may block.

        :param counter: Counter object to be incremented
        :type counter:  :class:`~.counter.SimCounter`

        :param amount:  Amount to increment the counter by. Should be greater
                        than zero and less than or equal to the counter's
                        capacity. Defaults to 1
        :type amount:   `int` 

        """
        counter.increment(self, amount)

    def decrement(self, counter, amount=1):
        """
        Decrement a counter by the designated amount. Never blocks.

        :param counter: Counter object to be decremented
        :type counter:  :class:`~.counter.SimCounter`

        :param amount:  Amount to decrement the counter by. Should be greater
                        than zero. If greater than the current counter value,
                        will decrement the counter to zero. Defaults to 1
        :type amount:   `int` 

        """
        counter.decrement(amount)



